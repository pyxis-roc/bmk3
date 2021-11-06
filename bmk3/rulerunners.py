#/usr/bin/env python3

import datetime
import time
import logging
import textwrap
from collections import namedtuple

logger = logging.getLogger(__name__)

TimeRecord = namedtuple('TimeRecord', 'start end total')

class SerialRunner:
    def run_all(self, cmdscripts, dry_run = False, keep_temps = 'fail', quiet = False):
        assert keep_temps in ('fail', 'never', 'always'), f"Incorrect value for keep_temps: {keep_temps}, must be one of fail, never or always"

        count = 0
        success = 0

        for c in cmdscripts:
            logger.info(f"**** {c.name} from {c.cwd}")

            logger.info(textwrap.indent("\n" + str(c.script), '    '))

            count += 1
            fail = False

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
                    success += 1

                end = time.perf_counter()
                logger.info(f'{c.name} finished at {datetime.datetime.now()}')
                logger.info(f'{c.name} took {end - start:.9f} s')

                c.timing = TimeRecord(start, end, end - start)
            else:
                c.timing = None

            if keep_temps != 'always':
                if keep_temps == 'never' or (keep_temps == 'fail' and not fail):
                    c.cleanup()

        if not dry_run:
            return count, success
        else:
            return count, None

