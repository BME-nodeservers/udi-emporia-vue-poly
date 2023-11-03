#!/usr/bin/env python3
"""
Polyglot v3 node server emporia VUE 
Copyright (C) 2021 Robert Paauwe
"""

import udi_interface
import sys
import time
from datetime import datetime

LOGGER = udi_interface.LOGGER

class VueChannel(udi_interface.Node):
    id = 'channel'
    hint = 0x01030501
    def __init__(self, polyglot, primary, address, name):
        super(VueChannel, self).__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.name = name
        self.address = address
        self.primary = primary

    def update_current(self, raw):
        kwh = round(raw * 3600, 4)
        self.setDriver('CPW', kwh, True, True)

    def update_hour(self, raw):
        kwh = round(raw, 4)
        self.setDriver('GV1', kwh, True, True)

    def update_day(self, raw):
        kwh = round(raw, 4)
        self.setDriver('GV2', kwh, True, True)

    def update_month(self, raw):
        kwh = round(raw, 4)
        self.setDriver('GV3', kwh, True, True)

    def delete(self):
        LOGGER.info('Removing node server')

    def stop(self):
        LOGGER.info('Stopping node server')

    def query(self):
        LOGGER.info('query called')

    commands = {
            'QUERY': query,
            }

    drivers = [
            {'driver': 'CPW', 'value': 0, 'uom': 30, 'name': 'Killowatts'},  # power
            {'driver': 'GV1', 'value': 0, 'uom': 33, 'name': 'Hourly KWh'},  # power
            {'driver': 'GV2', 'value': 0, 'uom': 33, 'name': 'Daily KWh'},  # power
            {'driver': 'GV3', 'value': 0, 'uom': 33, 'name': 'Monthly KWh'},  # power
            ]

    
