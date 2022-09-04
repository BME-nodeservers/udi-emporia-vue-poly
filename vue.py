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

LOGGER = udi_interface.LOGGER
polyglot = None
vue = None
deviceList = []
ready = False

def poll(poll_flag):
    if not ready:
        return

    if poll_flag == 'shortPoll':
        query(pyemvue.enums.Scale.SECOND.value, extra=True)
    else:
        '''
        for longPoll we want to do the same as above, but for the
        different time scales.
        '''
        query(pyemvue.enums.Scale.HOUR.value, extra=False)
        query(pyemvue.enums.Scale.DAY.value, extra=False)
        query(pyemvue.enums.Scale.MONTH.value, extra=False)

def query(scale, extra):
    global vue
    global deviceList
    global polyglot

    usage = vue.get_device_list_usage(deviceList, None, scale=scale,
            unit=pyemvue.enums.Unit.KWH.value)

    for gid, device in usage.items():
        for channelnum, channel in device.channels.items():
            # how are we mapping each channel to child node?
            LOGGER.info('{} -- {}'.format(channelnum, channel.usage))
            if channel.channel_num == '1,2,3':
                address = str(gid)
                polyglot.getNode(address).update_status(1)
            else:
                address = gid + '_' + channel.channel_num

            if channel.usage:
                if scale == pyemvue.enums.Scale.SECOND.value:
                    polyglot.getNode(address).update_current(channel.usage)
                elif scale == pyemvue.enums.Scale.HOUR.value:
                    polyglot.getNode(address).update_hour(channel.usage)
                elif scale == pyemvue.enums.Scale.DAY.value:
                    polyglot.getNode(address).update_day(channel.usage)
                elif scale == pyemvue.enums.Scale.MONTH.value:
                    polyglot.getNode(address).update_month(channel.usage)

        if device.ev_charger and extra:
            # TODO: Should we be using chargerOn, chargingRate, etc.?
            polygot.getNode(str(gid)).update_rate(device.ev_charger.charging_rate)
            polygot.getNode(str(gid)).update_max_rate(device.ev_charger.mac_charging_rate)
            polygot.getNode(str(gid)).update_state(device.ev_charger.charger_on)
            # TODO: what about off peak schedules enabled true/false?
        if device.outlet and extra:
            polygot.getNode(str(gid)).update_state(device.outlet.outlet_on)


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

        # create main device node for GID if needed
        parent_addr = str(dev.device_gid)
        node = polyglot.getNode(parent_addr)
        if not node:
            name = dev.device_name
            if name == None:
                name = dev.model

            LOGGER.info('Creating device node for {} ({})'.format(name, parent_addr))
            if dev.ev_charger:
                node = vueDevice.VueCharger(polyglot, parent_addr, parent_addr, name, vue, dev.ev_charger)
            elif dev.outlet:
                node = vueDevice.VueOutlet(polyglot, parent_addr, parent_addr, name, vue, dev.outlet)
            else:
                node = vueDevice.VueDevice(polyglot, parent_addr, parent_addr, name)
            polyglot.addNode(node)
            node.update_status(0)

        # TODO: look up and create any channel children nodes
        for channel in dev.channels:
            # Look at channel_num == '1', '2', etc.
            # channel_num == '1,2,3' is the parent node usage so skip it
            LOGGER.info('Found channel: {} - {}'.format(channel.channel_num, channel.name))
            if channel.channel_num != '1,2,3':
                address = dev.device_gid + '_' + channel.channel_num
                child = polyglot.getNode(address)
                if not child:
                    if channel.name == '':
                        channel.name = 'channel_' + channel.channel_num
                    child = vueChannel.VueChannel(polyglot, parent_addr, address, channel.name)
                    polyglot.addNode(child)

    ready = True
            

if __name__ == "__main__":
    try:
        polyglot = udi_interface.Interface([])
        polyglot.start('1.0.9')

        polyglot.subscribe(polyglot.CUSTOMPARAMS, parameterHandler)
        polyglot.subscribe(polyglot.POLL, poll)
        polyglot.ready()
        polyglot.updateProfile()
        polyglot.setCustomParamsDoc()
        #control = vue.Controller(polyglot, "controller", "controller", "emporia VUE")
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
        

