#!/usr/bin/env python3

from .runner import run
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

class CmdScript:
    def __init__(self, name, script, varvals, cwd = None):
        self.name = name
        self.script = script
        self.varvals = varvals
        self.cwd = cwd
        self.timing = None # this is set by a runner: to have better logging?

    def get_stats(self):
        out = []

        for r, t in zip([self.result], [self.timing]): # in prep for multiple runs
            out.append({'success': r.success,
                        'start': t.start,
                        'end': t.end,
                        'total': t.total})

        return out

    def run(self):
        h, f = tempfile.mkstemp(suffix='.sh')

        os.write(h, self.script.encode('utf-8'))
        os.close(h)

        self.result = run(['bash', f], cwd=self.cwd)

        os.unlink(f)

        return self.result.success

    def cleanup(self):
        if 'TempFile' in self.varvals:
            for k, v in self.varvals['TempFile'].items():
                if os.path.exists(v):
                    logger.debug(f'Deleting temporary file {v}')
                    os.unlink(v)

    def __str__(self):
        return f"CmdScript(name={repr(self.name)}, script={repr(self.script)})"

    __repr__ = __str__

