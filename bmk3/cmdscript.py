#!/usr/bin/env python3

from .runner import run
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

class CmdScript:
    def __init__(self, name, script, varvals):
        self.name = name
        self.script = script
        self.varvals = varvals

    def run(self):
        h, f = tempfile.mkstemp(suffix='.sh')

        os.write(h, self.script.encode('utf-8'))
        os.close(h)

        self.result = run(['bash', f])
        return self.result.success

    def cleanup(self):
        if 'TempFile' in self.varvals:
            for k, v in self.varvals['TempFile'].items():
                if os.path.exists(v):
                    logger.info(f'Deleting temporary file {v}')
                    os.unlink(v)

    def __str__(self):
        return f"CmdScript(name={repr(self.name)}, script={repr(self.script)})"

    __repr__ = __str__

