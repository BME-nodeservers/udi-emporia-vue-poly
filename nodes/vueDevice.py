#!/usr/bin/env python3
"""
Polyglot v3 node server emporia VUE 
Copyright (C) 2021 Robert Paauwe
"""

import udi_interface
import sys
import time
from datetime import datetime
from pyemvue.pyemvue import Scale

LOGGER = udi_interface.LOGGER

class VueDevice(udi_interface.Node):
    id = 'controller'
    def __init__(self, polyglot, primary, address, name, querys):
        super(VueDevice, self).__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.name = name
        self.address = address
        self.primary = primary
        self.querys = querys

    def update_current(self, raw):
        kwh = round(raw * 3600, 4)
        self.setDriver('CPW', kwh, True, True)

    def update_minute(self, raw):
        kwh = round(raw * 60, 4)
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

    def update_status(self, online):
        self.setDriver('ST', online, True, True)

    def delete(self):
        LOGGER.info('Removing node server')

    def stop(self):
        LOGGER.info('Stopping node server')

    def query(self):
        LOGGER.info('query called')
        # we need to call the main query_device_usage() to get
        # updated usage data and query_device_status() to get
        # updated status info
        self.querys.query_device(self.address, Scale.MONTH.value)
        self.querys.query_device(self.address, Scale.DAY.value)
        self.querys.query_device(self.address, Scale.HOUR.value)
        self.querys.query_device(self.address, Scale.SECOND.value)

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
    def __init__(self, polyglot, primary, address, name, vue, charger, querys):
        super(VueCharger, self).__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.name = name
        self.address = address
        self.primary = primary
        self.vueAPI = vue  # so we can set the charger on/off
        self.charger = charger
        self.querys = querys

    def update_current(self, raw):
        kwh = round(raw * 3600, 4)
        self.setDriver('CPW', kwh, True, False)

    def update_minute(self, raw):
        kwh = round(raw * 60, 4)
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
        self.querys.query_device(self.address, Scale.MONTH.value)
        self.querys.query_device(self.address, Scale.DAY.value)
        self.querys.query_device(self.address, Scale.HOUR.value)
        self.querys.query_device(self.address, Scale.SECOND.value)
        self.querys.query_device_status()

    def set_on(self, cmd):
        self.vueAPI.update_charger(self.charger, on=True)
        self.setDriver('ST', 1, True, False)

    def set_off(self, cmd):
        self.vueAPI.update_charger(self.charger, on=False)
        self.setDriver('ST', 0, True, False)

    def set_rate(self, cmd):
        LOGGER.info('TESTING: set rate to :: {}'.format(cmd))
        LOGGER.info(' -- rate = {}'.format(cmd['query']['SET_RATE.uom1']))
        rate = int(cmd['query']['SET_RATE.uom1'])
        self.vueAPI.update_charger(self.charger, charge_rate=rate)
        self.setDriver('GV4', rate, True, False)

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
            {'driver': 'GV4', 'value': 0, 'uom': 1},   # amps
            {'driver': 'GV5', 'value': 0, 'uom': 1},   # amps
            ]

class VueOutlet(udi_interface.Node):
    id = 'outlet'
    hint = 0x01030501
    def __init__(self, polyglot, primary, address, name, vue, outlet, querys):
        super(VueOutlet, self).__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.name = name
        self.address = address
        self.primary = primary
        self.vueAPI = vue  # so we can set the charger on/off
        self.outlet = outlet
        self.querys = querys

    def update_current(self, raw):
        kwh = round(raw * 3600, 4)
        self.setDriver('CPW', kwh, True, False)

    def update_minute(self, raw):
        kwh = round(raw * 60, 4)
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
        self.querys.query_device(self.address, Scale.MONTH.value)
        self.querys.query_device(self.address, Scale.DAY.value)
        self.querys.query_device(self.address, Scale.HOUR.value)
        self.querys.query_device(self.address, Scale.SECOND.value)
        self.querys.query_device_status()

    def set_on(self, cmd):
        self.vueAPI.update_outlet(self.outlet, on=True)
        self.setDriver('ST', 1, True, False)

    def set_off(self, cmd):
        self.vueAPI.update_outlet(self.outlet, on=False)
        self.setDriver('ST', 0, True, False)

    commands = {
            'QUERY': query,
            'DON': set_on,
            'DOF': set_off,
            }

    drivers = [
            {'driver': 'ST',  'value': 0, 'uom': 25, 'name': 'Status'},      # outlet state
            {'driver': 'CPW', 'value': 0, 'uom': 30, 'name': 'Killowatts'},  # power
            {'driver': 'GV1', 'value': 0, 'uom': 33, 'name': 'Hourly KWh'},  # power
            {'driver': 'GV2', 'value': 0, 'uom': 33, 'name': 'Daily KWh'},   # power
            {'driver': 'GV3', 'value': 0, 'uom': 33, 'name': 'Monthly KWh'}, # power
            ]
