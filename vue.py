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

LOGGER = udi_interface.LOGGER
polyglot = None
vue = None
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

    if not ready:
        return

    if poll_flag == 'shortPoll':
        query(pyemvue.enums.Scale.SECOND.value, extra=True)
        #query(pyemvue.enums.Scale.MINUTE.value, extra=True)

        if hour_update == 10:
            hour_update = 0
            query(pyemvue.enums.Scale.HOUR.value, extra=False)
        else:
            hour_update = hour_update + 1

    else:
        '''
        for longPoll we want to do the same as above, but for the
        different time scales.
        '''
        #query(pyemvue.enums.Scale.HOUR.value, extra=False)
        query(pyemvue.enums.Scale.DAY.value, extra=False)
        query(pyemvue.enums.Scale.MONTH.value, extra=False)

def query(scale, extra):
    global vue
    global deviceList
    global polyglot

    usage = vue.get_device_list_usage(deviceList, None, scale=scale,
            unit=pyemvue.enums.Unit.KWH.value)

    #LOGGER.info('Query: get info for {}'.format(deviceList))
    #for i in usage:
    #    LOGGER.info('Got usage data for {}'.format(i))

    for gid, device in usage.items():
        # device is class VueUsageDevice. this adds channels dictionary
        LOGGER.debug('Found usage data for {}'.format(gid))
        for channelnum, channel in device.channels.items():
            # channel is a VueDeviceChannelUsage class object
            # how are we mapping each channel to child node?
            LOGGER.debug('{} => {} -- {}'.format(gid, channelnum, channel.usage))
            if channel.channel_num == '1,2,3':
                address = str(gid)
            else:
                address = str(gid) + '_' + str(channel.channel_num)
            address = makeValidAddress(address)

            LOGGER.debug('Updating child node {}'.format(address))
            try:
                node = polyglot.getNode(address)
                if node:
                    if scale == pyemvue.enums.Scale.SECOND.value:
                        node.update_current(channel.usage)
                    elif scale == pyemvue.enums.Scale.MINUTE.value:
                        node.update_minute(channel.usage)
                    elif scale == pyemvue.enums.Scale.HOUR.value:
                        node.update_hour(channel.usage)
                    elif scale == pyemvue.enums.Scale.DAY.value:
                        node.update_day(channel.usage)
                    elif scale == pyemvue.enums.Scale.MONTH.value:
                        node.update_month(channel.usage)
                else:
                    LOGGER.error('Node {} is missing!'.format(address))
            except Exception as e:
                LOGGER.error('Update of node {} failed for scale {} :: {}'.format(address, scale, e))

    # Update outlet/charger status
    if extra:
        outlets, chargers = vue.get_devices_status()

        if outlets:
            for outlet in outlets:
                try:
                    node = polyglot.getNode(str(outlet.device_gid))
                    if node:
                        LOGGER.debug('Updating status to {}'.format(outlet.outlet_on))
                        node.update_state(outlet.outlet_on)
                    else:
                        LOGGER.error('Node {} (outlet) is missing!'.format(outlet.device_gid))
                except Exception as e:
                    LOGGER.error('Failed to update {}:: {}'.format(outlet.device_gid, e))

        if chargers:
            for charger in chargers:
                try:
                    node = polyglot.getNode(str(charger.device_gid))
                    if node:
                        LOGGER.debug('Updating status to {}'.format(charger.charger_on))
                        node.update_state(charger.charger_on)
                        node.update_rate(dcharger.charging_rate)
                        node.update_max_rate(charger.mac_charging_rate)
                    else:
                        LOGGER.error('Node {} (charger) is missing!'.format(charger.device_gid))
                except Exception as e:
                    LOGGER.error('Failed to update {}:: {}'.format(charger.device_gid, e))



def parameterHandler(params):
    global polyglot
    global vue
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

    info = {}
    deviceList = []
    devices = vue.get_devices()

    for dev in devices:
        vue.populate_device_properties(dev)

        if not dev.device_gid in deviceList:
            deviceList.append(dev.device_gid)
            info[dev.device_gid] = dev
        else:
            info[dev.device_gid].channels += dev.channels

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
                node = vueDevice.VueCharger(polyglot, parent_addr, parent_addr, name, vue, dev.ev_charger)
                polyglot.addNode(node)
            elif dev.outlet:
                node = vueDevice.VueOutlet(polyglot, parent_addr, parent_addr, name, vue, dev.outlet)
                polyglot.addNode(node)
            else:
                node = vueDevice.VueDevice(polyglot, parent_addr, parent_addr, name)
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

    ready = True
            

if __name__ == "__main__":
    try:
        polyglot = udi_interface.Interface([])
        polyglot.start('1.0.19')

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
        

