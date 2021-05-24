#!/usr/bin/env python3
"""
Polyglot v3 node server Purple Air data
Copyright (C) 2021 Robert Paauwe
"""

import udi_interface
import sys
import time
import pyemvue

LOGGER = udi_interface.LOGGER
Custom = udi_interface.Custom

class Controller(udi_interface.Node):
    id = 'controller'
    def __init__(self, polyglot, primary, address, name):
        super(Controller, self).__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.name = name
        self.address = address
        self.primary = primary
        self.configured = False
        self.force = True
        self.vue = None

        self.Parameters = Custom(polyglot, 'customparams')
        self.Notices = Custom(polyglot, 'notices')

        self.poly.subscribe(self.poly.CUSTOMPARAMS, self.parameterHandler)
        self.poly.subscribe(self.poly.START, self.start, self.address)
        self.poly.subscribe(self.poly.POLL, self.poll)

        self.poly.ready()
        self.poly.addNode(self)

    def query(self):
        LOGGER.debug('Get some data here')
        dev_list = view.get_devices()
        LOGGER.debug('list of devices = {}'.format(dev_list))

        gids = []
        for device in dev_list:
            gids.append(device.device_gid)

        usage = vue.get_devices_usage(gids, None, scale=pyemvue.Scale.DAY.value, units=pyemuve.Unit.KWH.value)
        LOGGER.debug('usage = {}'.format(usage))

    # Process changes to customParameters
    def parameterHandler(self, params):
        self.configured = False
        self.Parameters.load(params)

        valid_u = False
        valid_p = False

        # How to detect that self.Parameters is empty?
        if len(self.Parameters) == 0:
            self.Notices['cfg'] = 'Enter username and password'
            return

        # Check for username and password
        self.Notices.clear()
        for p in self.Parameters:
            self.configured = True
            if p == 'Username' and self.Parameters[p] != '': 
                valid_u = True
            if p == 'Password' and self.Parameters[p] != '': 
                valid_p = True

        if not valid_u:
            self.configured = False
            self.Notices['cfg_u'] = 'Please enter a valid Username'

        if not valid_p:
            self.configured = False
            self.Notices['cfg_p'] = 'Please enter a valid Password'

        if self.configured:
            vue = pyemvue.PyEmVue()
            vue.login(username=self.Parameters['Username'], password=self.Parameters['Password'])

    def start(self):
        LOGGER.info('Starting node server')
        self.poly.updateProfile()
        self.poly.setCustomParamsDoc()

        if len(self.Parameters) == 0:
            self.Notices['cfg'] = 'Enter username and password'

        LOGGER.info('Node server started')

        if self.configured:
            self.query()

    def poll(self, poll):
        if poll == 'shortPoll':
            self.query()

    def delete(self):
        LOGGER.info('Removing node server')

    def stop(self):
        LOGGER.info('Stopping node server')

    commands = {
            'QUERY': query,
            }

    drivers = [
            {'driver': 'ST', 'value': 1, 'uom': 2},    # node server status
            {'driver': 'TWP', 'value': 0, 'uom': 33},  # power
            ]

    
