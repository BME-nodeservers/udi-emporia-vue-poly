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

class VueDevice(udi_interface.Node):
    id = 'controller'
    def __init__(self, polyglot, primary, address, name):
        super(VueDevice, self).__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.name = name
        self.address = address
        self.primary = primary

    def update_current(self, raw):
        kwh = round(raw * 3600, 4)
        self.setDriver('CPW', kwh, True, False)

    def update_hour(self, raw):
        kwh = round(raw, 4)
        self.setDriver('GV1', kwh, True, False)

    def update_day(self, raw):
        kwh = round(raw, 4)
        self.setDriver('GV2', kwh, True, False)

    def update_month(self, raw):
        kwh = round(raw, 4)
        self.setDriver('GV3', kwh, True, False)

    def update_status(self, online):
        self.setDriver('ST', online, True, False)

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
            {'driver': 'ST', 'value': 1, 'uom': 25},   # node server status
            {'driver': 'CPW', 'value': 0, 'uom': 30},  # power
            {'driver': 'GV1', 'value': 0, 'uom': 33},  # power
            {'driver': 'GV2', 'value': 0, 'uom': 33},  # power
            {'driver': 'GV3', 'value': 0, 'uom': 33},  # power
            ]

    
class VueCharger(udi_interface.Node):
    id = 'charger'
    def __init__(self, polyglot, primary, address, name, vue, charger):
        super(VueCharger, self).__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.name = name
        self.address = address
        self.primary = primary
        self.vueAPI = vue  # so we can set the charger on/off
        self.charger = charger

    def update_current(self, raw):
        kwh = round(raw * 3600, 4)
        self.setDriver('CPW', kwh, True, False)

    def update_hour(self, raw):
        kwh = round(raw, 4)
        self.setDriver('GV1', kwh, True, False)

    def update_day(self, raw):
        kwh = round(raw, 4)
        self.setDriver('GV2', kwh, True, False)

    def update_month(self, raw):
        kwh = round(raw, 4)
        self.setDriver('GV3', kwh, True, False)

    def update_status(self, online):
        self.setDriver('ST', online, True, False)

    def update_rate(self, raw):
        self.setDriver('GV4', raw, True, False)

    def update_max_rate(self, raw):
        self.setDriver('GV5', raw, True, False)

    def update_state(self, state):
        self.setDriver('ST', state, True, False)

    def delete(self):
        LOGGER.info('Removing node server')

    def stop(self):
        LOGGER.info('Stopping node server')

    def query(self):
        LOGGER.info('query called')

    def set_on(self, cmd):
        vueAPI.update_charger(self.charger, on=True)

    def set_off(self, cmd):
        vueAPI.update_charger(self.charger, on=False)

    def set_rate(self, cmd):
        LOGGER.info('TESTING: set rate to :: {}'.format(cmd))
        LOGGER.info(' -- rate = {}'.format(cmd['query']['SET_RATE.uom30']))
        rate = int(cmd['query']['SET_RATE.uom30'])
        self.vueAPI.update_charger(self.charger, charge_rate=rate)

    commands = {
            'QUERY': query,
            'DON': set_on,
            'DOF': set_off,
            'SET_RATE': set_rate,
            }

    drivers = [
            {'driver': 'ST', 'value': 1, 'uom': 25},   # charger state
            {'driver': 'CPW', 'value': 0, 'uom': 30},  # power
            {'driver': 'GV1', 'value': 0, 'uom': 33},  # power
            {'driver': 'GV2', 'value': 0, 'uom': 33},  # power
            {'driver': 'GV3', 'value': 0, 'uom': 33},  # power
            {'driver': 'GV4', 'value': 0, 'uom': 30},  # power
            {'driver': 'GV5', 'value': 0, 'uom': 30},  # power
            ]

class VueOutlet(udi_interface.Node):
    id = 'outlet'
    def __init__(self, polyglot, primary, address, name, vue, outlet):
        super(VueOutlet, self).__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.name = name
        self.address = address
        self.primary = primary
        self.vueAPI = vue  # so we can set the charger on/off
        self.outlet = outlet

    def update_current(self, raw):
        kwh = round(raw * 3600, 4)
        self.setDriver('CPW', kwh, True, False)

    def update_hour(self, raw):
        kwh = round(raw, 4)
        self.setDriver('GV1', kwh, True, False)

    def update_day(self, raw):
        kwh = round(raw, 4)
        self.setDriver('GV2', kwh, True, False)

    def update_month(self, raw):
        kwh = round(raw, 4)
        self.setDriver('GV3', kwh, True, False)

    def update_state(self, state):
        if state:
            self.setDriver('ST', 1, True, False)
        else:
            self.setDriver('ST', 0, True, False)

    def delete(self):
        LOGGER.info('Removing node server')

    def stop(self):
        LOGGER.info('Stopping node server')

    def query(self):
        LOGGER.info('query called')

    def set_on(self, cmd):
        vueAPI.update_outlet(self.outlet, on=True)

    def set_off(self, cmd):
        vueAPI.update_outlet(self.outlet, on=False)

    commands = {
            'QUERY': query,
            'DON': set_on,
            'DOF': set_off,
            }

    drivers = [
            {'driver': 'ST',  'value': 0, 'uom': 2},   # outlet state
            {'driver': 'CPW', 'value': 0, 'uom': 30},  # power
            {'driver': 'GV1', 'value': 0, 'uom': 33},  # power
            {'driver': 'GV2', 'value': 0, 'uom': 33},  # power
            {'driver': 'GV3', 'value': 0, 'uom': 33},  # power
            ]
