#!/usr/bin/env python3
"""
Polyglot v3 node server emporia VUE 
Copyright (C) 2021 Robert Paauwe
"""

import udi_interface
import sys
import time
from datetime import datetime
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
        self.deviceList = []

        self.Parameters = Custom(polyglot, 'customparams')
        self.Notices = Custom(polyglot, 'notices')

        self.poly.subscribe(self.poly.CUSTOMPARAMS, self.parameterHandler)
        self.poly.subscribe(self.poly.START, self.start, self.address)
        self.poly.subscribe(self.poly.POLL, self.poll)

        self.poly.ready()
        self.poly.addNode(self, conn_status="ST")

    def query(self):
        if not self.configured:
            return

        LOGGER.info('Query: get device usage for 1s')
        usage = self.vue.get_device_list_usage(self.deviceList, None,
                scale=pyemvue.enums.Scale.SECOND.value,
                unit=pyemvue.enums.Unit.KWH.value)


        for gid, device in usage.items():
            LOGGER.info('Getting usage for {} {}'.format(device.name, device.model))
            for channelnum, channel in device.channels.items():
                if channel.name == 'Main':
                    if channel.usage:
                        kwh = round(channel.usage * 3600, 4)
                        #LOGGER.debug('Second = {}'.format(kwh))
                        self.setDriver('TPW', kwh, True, False)


    def query_day(self):
        if not self.configured:
            return

        # Daily total?
        usage = self.vue.get_device_list_usage(self.deviceList, None,
                scale=pyemvue.enums.Scale.DAY.value,
                unit=pyemvue.enums.Unit.KWH.value)

        for gid, device in usage.items():
            for channelnum, channel in device.channels.items():
                if channel.name == 'Main':
                    if channel.usage:
                        kwh = round(channel.usage, 4)
                        LOGGER.debug('Daily = {}'.format(kwh))
                        self.setDriver('GV1', kwh, True, False)

    def getDeviceId(self):
        dev_list = self.vue.get_devices()
        self.deviceList = []
        for device in dev_list:
            self.deviceList.append(device.device_gid)
            self.vue.populate_device_properties(device)
            LOGGER.info('Device Info:  {}  {}  {}  {}  {}  {}'.format(
                device.device_gid,
                device.manufacturer_id,
                device.model,
                device.firmware,
                device.device_name,
                device.usage_cent_per_kw_hour))

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
        self.configured = False

        for p in self.Parameters:
            if p == 'Username' and self.Parameters[p] != '': 
                valid_u = True
            if p == 'Password' and self.Parameters[p] != '': 
                valid_p = True

        if not valid_u:
            self.Notices['cfg_u'] = 'Please enter a valid Username'

        if not valid_p:
            self.Notices['cfg_p'] = 'Please enter a valid Password'

        if valid_u and valid_p:
            LOGGER.info('Attempting to log into PyEmVue...')
            try:
                self.vue = pyemvue.PyEmVue()
                self.vue.login(username=self.Parameters['Username'], password=self.Parameters['Password'])
                self.getDeviceId()
                self.configured = True
            except Exception as e:
                LOGGER.error('Failed to connect to VUE: {}'.format(e))
                self.Notices['error'] = '{}'.format(e)

    def print_recursive(self, device_usage_dict, info, depth=0):
        for gid, device in device_usage_dict.items():
            for channelnum, channel in device.channels.items():
                name = channel.name
                if name == 'Main':
                    name = info[gid].device_name

                dash = '-'*depth
                LOGGER.info(f'{dash} {gid} {channelnum} {name} {channel.usage} {channel.channel_multiplier} kwh')

                if channel.nested_devices:
                    self.print_recursive(channel.nested_devices, depth+1)

    def deviceinfo(self):
        LOGGER.info('Devices:')
        devices = self.vue.get_devices()
        outlets, chargers = self.vue.get_devices_status()

        for dev in devices:
            dev = self.vue.populate_device_properties(dev)
            LOGGER.info(f'GID:         {dev.device_gid}')
            LOGGER.info(f'Manufacturer:{dev.manufacturer_id}')
            LOGGER.info(f'Model:       {dev.model}')
            LOGGER.info(f'Firmware:    {dev.firmware}')
            LOGGER.info(f'Name:        {dev.device_name}')
            LOGGER.info(f'Price/kwh:   {dev.usage_cent_per_kw_hour}')
            if dev.outlet:
                LOGGER.info(f'Found an outlet:  {dev.outlet.outlet_on}')
            if dev.ev_charger:
                LOGGER.info(f'Found a charger:  {dev.ev_charger.charger_on}')
                LOGGER.info(f'Charge rate:      {dev.ev_charger.charging_rate}')
                LOGGER.info(f'Max charge rate:  {dev.ev_charger.max_charging_rate}')
            LOGGER.info('--------------------------------------------')

        LOGGER.info('Usage Info for scale=Hour:')
        deviceGids = []
        info = {}
        for dev in devices:
            if not dev.device_gid in deviceGids:
                deviceGids.append(dev.device_gid)
                info[dev.device_gid] = dev
            else:
                info[dev.device_gid].channels += dev.channels

        device_usage_dict = self.vue.get_device_list_usage(deviceGids=deviceGids, instant=datetime.utcnow(), scale=pyemvue.enums.Scale.HOUR.value, unit=pyemvue.enums.Unit.KWH.value)

        self.print_recursive(device_usage_dict, info)


    def start(self):
        LOGGER.info('Starting node server')
        self.poly.updateProfile()
        self.poly.setCustomParamsDoc()

        if len(self.Parameters) == 0:
            self.Notices['cfg'] = 'Enter username and password'

        LOGGER.info('Node server started')

        while not self.configured:
            LOGGER.debug('waiting for configuration.')
            time.sleep(2)

        LOGGER.info('Node server configured, get device information')
        self.deviceinfo()

        LOGGER.info('Doing initial queries')
        self.query()
        self.query_day()

    def poll(self, poll):
        if poll == 'shortPoll':
            self.query()
        else:
            self.query_day()

    def delete(self):
        LOGGER.info('Removing node server')

    def stop(self):
        LOGGER.info('Stopping node server')

    commands = {
            'QUERY': query,
            }

    drivers = [
            {'driver': 'ST', 'value': 1, 'uom': 25},    # node server status
            {'driver': 'TPW', 'value': 0, 'uom': 33},  # power
            {'driver': 'GV1', 'value': 0, 'uom': 33},  # power
            ]

    
