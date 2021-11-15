#/usr/bin/env python3

import datetime
import time
import logging
import textwrap
from collections import namedtuple
import random
import itertools
import multiprocessing

logger = logging.getLogger(__name__)

TimeRecord = namedtuple('TimeRecord', 'start end total')

def _run_one(c, dry_run = False, keep_temps = 'fail', quiet = False):
    fail = False

    logger.info(f"**** {c.name} from {c.cwd}")

    logger.info(textwrap.indent("\n" + str(c.script), '    '))

    if not dry_run:
        logger.info(f'Running {c.name} at {datetime.datetime.now()}')
        start = time.perf_counter()
        if not c.run():
            logger.error(f'Running {c.name} FAILED')
            if not quiet:
                logger.info(c.result.output)
                logger.info(c.result.errors)

            fail = True
        else:
            logger.info(f'Running {c.name} SUCCEEDED')
            if not quiet:
                logger.info(c.result.output)
                logger.info(c.result.errors)

        end = time.perf_counter()
        logger.info(f'{c.name} finished at {datetime.datetime.now()}')
        logger.info(f'{c.name} took {end - start:.9f} s')

        c.timing = TimeRecord(start, end, end - start)
    else:
        c.timing = None

    if keep_temps != 'always':
        if keep_temps == 'never' or (keep_temps == 'fail' and not fail):
            c.cleanup()

    return not fail

class SerialRunner:
    def run_all(self, cmdscripts, dry_run = False, keep_temps = 'fail', quiet = False):
        assert keep_temps in ('fail', 'never', 'always'), f"Incorrect value for keep_temps: {keep_temps}, must be one of fail, never or always"

        count = 0
        success = 0

        for c in cmdscripts:
            count += 1
            if _run_one(c, dry_run, keep_temps, quiet) and not dry_run:
                success += 1

        if not dry_run:
            return count, success
        else:
            return count, None

def _run_queue(cmdscripts, dry_run = False, keep_temps = 'fail', quiet = False):
    sr = SerialRunner()
    return sr.run_all(cmdscripts, dry_run, keep_temps, quiet)

class ParallelRunner:
    def __init__(self, nprocs=None):
        self.nprocs = nprocs
        self.pool = multiprocessing.Pool(self.nprocs)

    def run_all(self, cmdscripts, dry_run = False, keep_temps = 'fail', quiet = False):
        assert keep_temps in ('fail', 'never', 'always'), f"Incorrect value for keep_temps: {keep_temps}, must be one of fail, never or always"

        sems = set()

        for c in cmdscripts:
            sem = c.varvals['_semaphores']

            queues = [f"sem:{s.name}:{random.randint(1, s.count)}" for s in sem]
            c._queue = tuple(sorted(queues))
            c._sems = tuple([s.name for s in sorted(sem, key=lambda x: x.name)])

            if len(c._sems):
                sems.add(c._sems)

            #logger.info(f"**** {c.name} from {c.cwd} ({queues})")

        # build a semaphore dag
        dag = {}

        for st in sorted(sems, key=lambda k: len(k)):
            dag[st] = 0
            sts = set(st)
            for x in dag:
                if x == st: continue

                if set(x).intersection(sts):
                    dag[st] = max(dag[st], dag[x] + 1)

        dag[tuple()] = -1

        # build rounds
        rounds = {}
        for c in cmdscripts:
            v = dag[c._sems]
            if v not in rounds:
                rounds[v] = []

            rounds[v].append(c)

        count, success = 0, 0

        for r in sorted(rounds.keys()):
            if r == -1:
                logger.debug(f"Launching all parallel")
                c, s = self._run_parallel(rounds[r], dry_run, keep_temps, quiet)
                count += c
                if not dry_run:
                    success += s
            else:
                queues = dict([(x._queue, []) for x in rounds[r]])
                for x in rounds[r]:
                    queues[x._queue].append(x)

                logger.debug(f"Launching queues on round {r}")

                csl = self.pool.starmap(_run_queue,
                                        [(queues[q], dry_run, keep_temps, quiet) for q in queues])

                for c, s in csl:
                    count += c
                    if s is not None:
                        success += s

                # wait for round to finish

        if dry_run:
            return count, None
        else:
            return count, success

    def _run_parallel(self, cmdscripts, dry_run = False, keep_temps = 'fail', quiet = False):
        res = self.pool.starmap(_run_one, [(c, dry_run, keep_temps, quiet) for c in cmdscripts])

        count = len(res)
        if not dry_run:
            success = len(list(filter(lambda x: x, res)))
        else:
            success = None

        return count, success

