#!/usr/bin/env python3
#
# logging.py
#
# Common utilities for configuring Python loggers when basicConfig
# just won't cut it.
#
# Author: Sreepathi Pai

import logging
import os

def setup_logging(filename = None, filemode='w', stream_level = logging.INFO, file_level = logging.DEBUG, multiprocessing = False):
    rl = logging.getLogger()

    if multiprocessing:
        from multiprocessing_logging import install_mp_handler
        install_mp_handler()

    rl.setLevel(min(stream_level, file_level))

    formatter = logging.Formatter('%(name)s:%(levelname)s: %(message)s')


    sh = logging.StreamHandler()
    sh.setLevel(stream_level)
    sh.setFormatter(formatter)

    rl.addHandler(sh)

    if filename is not None:
        fh = logging.FileHandler(filename, mode=filemode)
        fh.setLevel(file_level)
        fh.setFormatter(formatter)
        rl.addHandler(fh)

def get_auto_log_filename(template):
    k = 0
    while True:
        if k == 0:
            fn = template.format(k="")
        else:
            fn = template.format(k = f"-{k:02d}")

        if not os.path.exists(fn): return fn
        k += 1
