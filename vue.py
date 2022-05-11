#!/usr/bin/env python3
"""
Polyglot v3 node server emporia VUE energy monitor
Copyright (C) 2021 Robert Paauwe
"""

import udi_interface
import sys
import time
from nodes import vue

LOGGER = udi_interface.LOGGER

if __name__ == "__main__":
    try:
        polyglot = udi_interface.Interface([vue.Controller])
        polyglot.start('1.0.4')
        control = vue.Controller(polyglot, "controller", "controller", "emporia VUE")
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
        

