#!/usr/bin/env python3
"""
Polyglot v3 node server emporia VUE energy monitor
Copyright (C) 2021 Robert Paauwe
"""

import udi_interface
import sys
import time
import pyemvue
from nodes import vueDevice
from nodes import vueChannel
import re
import query

LOGGER = udi_interface.LOGGER
polyglot = None
vue = None
querys = None
deviceList = []
ready = False
hour_update = 0

# UDI interface getValidAddress doesn't seem to work right
def makeValidAddress(address):
    address = bytes(address, 'utf-8').decode('utf-8', 'ignore')
    address = re.sub(r"[<>`~!@#$%^&*(){}[\]?/\\;:\"'\-]+", "", address)
    address = address.lower()[:14]
    return address

def poll(poll_flag):
    global hour_update
    global querys

    if not ready:
        return

    if poll_flag == 'shortPoll':
        querys.query(pyemvue.enums.Scale.SECOND.value, extra=True)
        #query(pyemvue.enums.Scale.MINUTE.value, extra=True)

        if hour_update == 10:
            hour_update = 0
            querys.query(pyemvue.enums.Scale.HOUR.value, extra=False)
        else:
            hour_update = hour_update + 1

    else:
        '''
        for longPoll we want to do the same as above, but for the
        different time scales.
        '''
        #query(pyemvue.enums.Scale.HOUR.value, extra=False)
        querys.query(pyemvue.enums.Scale.DAY.value, extra=False)
        querys.query(pyemvue.enums.Scale.MONTH.value, extra=False)

def parameterHandler(params):
    global polyglot
    global vue
    global querys
    valid_u = False
    valid_p = False

    polyglot.Notices.clear()

    for p in params:
        if p == 'Username' and params[p] != '':
            valid_u = True
        if p == 'Password' and params[p] != '':
            valid_p = True

    if not valid_u:
        polyglot.Notices['cfg_u'] = 'Please enter a valid Username'
    if not valid_p:
        polyglot.Notices['cfg_p'] = 'Please enter a valid Password'

    if valid_u and valid_p:
        LOGGER.info('Logging in to Emporia Cloud')
        try:
            vue = pyemvue.PyEmVue()
            vue.login(username=params['Username'], password=params['Password'])
            querys = query.Query(polyglot, vue)
            LOGGER.error('querys is type {}'.format(type(querys)))
        except Exception as e:
            LOGGER.error('Emporia Cloud connection failed: {}'.format(e))

        try:
            discover()
            poll('longPoll') # force initial values
        except Exception as e:
            LOGGER.error('Discovery failed: {}'.format(e))

'''
query for the devices on the account and create corresponding nodes. We
create a node for each GID with child nodes for each channel.
'''
def discover():
    global polyglot
    global deviceList
    global vue
    global ready
    global querys

    info = {}
    deviceList = []
    devices = vue.get_devices()

    for dev in devices:
        vue.populate_device_properties(dev)

        if not dev.device_gid in deviceList:
            deviceList.append(dev.device_gid)
            info[dev.device_gid] = dev
            LOGGER.error('dev.channels is {}'.format(type(dev.channels)))
            for i in dev.channels:
                LOGGER.error('{} channel {} {}'.format(dev.device_gid, i.channel_num, i.name))
        else:
            info[dev.device_gid].channels += dev.channels
            # dev.channels is what, an array of vueChannelDevices
            LOGGER.error('dev.channels is {}'.format(type(dev.channels)))
            for i in dev.channels:
                LOGGER.error('{} channel {}'.format(dev.device_gid, i))

        LOGGER.info(f'GID:               {dev.device_gid}')
        LOGGER.info(f'Manufacturer:      {dev.manufacturer_id}')
        LOGGER.info(f'Model:             {dev.model}')
        LOGGER.info(f'Firmware:          {dev.firmware}')
        LOGGER.info(f'Name:              {dev.device_name}')
        if dev.ev_charger:
            LOGGER.info(f'Charge rate:       {dev.ev_charger.charging_rate}')
            LOGGER.info(f'Max charge rate:   {dev.ev_charger.max_charging_rate}')
        if dev.outlet:
            LOGGER.info(f'Outlet:            {dev.outlet.outlet_on}')

        # create main device node for GID if needed
        parent_addr = str(dev.device_gid)
        node = polyglot.getNode(parent_addr)
        if not node:
            name = dev.device_name
            if name == None:
                name = dev.model
            name = polyglot.getValidName(name)

            LOGGER.info('Creating device node for {} ({})'.format(name, parent_addr))
            if dev.ev_charger:
                node = vueDevice.VueCharger(polyglot, parent_addr, parent_addr, name, vue, dev.ev_charger, querys)
                polyglot.addNode(node)
            elif dev.outlet:
                node = vueDevice.VueOutlet(polyglot, parent_addr, parent_addr, name, vue, dev.outlet, querys)
                polyglot.addNode(node)
            else:
                node = vueDevice.VueDevice(polyglot, parent_addr, parent_addr, name, querys)
                # FIXME: this may only work for one node
                polyglot.addNode(node, conn_status="ST")

        # look up and create any channel children nodes
        for channel in dev.channels:
            # Look at channel_num == '1', '2', etc.
            # channel_num == '1,2,3' is the parent node usage so skip it
            LOGGER.info('Found channel: {} - {} ({})'.format(channel.channel_num, channel.name, channel.channel_type_gid))
            if channel.channel_num != '1,2,3':
                address = str(dev.device_gid) + '_' + str(channel.channel_num)
                address = makeValidAddress(address)
                child = polyglot.getNode(address)
                if not child:
                    name = channel.name
                    if name == '' or name == None:
                        name = 'channel_' + str(channel.channel_num)
                    name = polyglot.getValidName(name)

                    LOGGER.info('Creating child node {} / {}'.format(name, address))
                    child = vueChannel.VueChannel(polyglot, parent_addr, address, name)
                    polyglot.addNode(child)

    querys.devices(deviceList)
    ready = True
            

if __name__ == "__main__":
    try:
        polyglot = udi_interface.Interface([])
        polyglot.start('1.0.22')

        polyglot.subscribe(polyglot.CUSTOMPARAMS, parameterHandler)
        polyglot.subscribe(polyglot.POLL, poll)
        polyglot.subscribe(polyglot.DISCOVER, discover)
        polyglot.ready()
        polyglot.updateProfile()
        polyglot.setCustomParamsDoc()
        #control = vue.Controller(polyglot, "controller", "controller", "emporia VUE")
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
        

