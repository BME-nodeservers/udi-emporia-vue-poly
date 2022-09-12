'''
The Query class holds all the functions that query the Emporia
Cloud for usage/status data.
'''

import udi_interface
import re
import pyemvue
from nodes import vueChannel

LOGGER = udi_interface.LOGGER

class Query(object):
    def __init__(self, polyglot, vue):
        self.polyglot = polyglot
        self.vue = vue
        self.deviceList = []
        LOGGER.info('Query class initialized')

    def devices(self, deviceList):
        self.deviceList = deviceList

    # UDI interface getValidAddress doesn't seem to work right
    def makeValidAddress(self, address):
        address = bytes(address, 'utf-8').decode('utf-8', 'ignore')
        address = re.sub(r"[<>`~!@#$%^&*(){}[\]?/\\;:\"'\-]+", "", address)
        address = address.lower()[:14]
        return address

    # query all device usage info for different scale values
    def query(self, scale, extra):

        usage = self.vue.get_device_list_usage(self.deviceList, None, scale=scale,
                unit=pyemvue.enums.Unit.KWH.value)

        self.update_devices(usage, scale)

        # Update outlet/charger status
        if extra:
            self.query_device_status()

    def update_devices(self, usage, scale):
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
                address = self.makeValidAddress(address)

                LOGGER.debug('Updating child node {}'.format(address))
                try:
                    node = self.polyglot.getNode(address)
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
                        LOGGER.info('Node {} is missing, attempting to add.'.format(address))
                        # Add it?
                        name = channel.name
                        if name == '' or name == None:
                            name = 'channel_' + str(channel.channel_num)
                        child = vueChannel.VueChannel(self.polyglot, str(gid), address, name)
                        self.polyglot.addNode(child)

                except Exception as e:
                    LOGGER.error('Update of node {} failed for scale {} :: {}'.format(address, scale, e))

                # recurse into nested devices
                if channel.nested_devices:
                    self.update_devices(channel.nested_devices, scale)

    def update_outlets(self, outlets):
        for outlet in outlets:
            try:
                node = self.polyglot.getNode(str(outlet.device_gid))
                if node:
                    LOGGER.debug('Updating status to {}'.format(outlet.outlet_on))
                    node.update_state(outlet.outlet_on)
                else:
                    LOGGER.error('Node {} (outlet) is missing!'.format(outlet.device_gid))
            except Exception as e:
                LOGGER.error('Failed to update {}:: {}'.format(outlet.device_gid, e))

    def update_chargers(self, chargers):
        for charger in chargers:
            try:
                node = self.polyglot.getNode(str(charger.device_gid))
                if node:
                    LOGGER.debug('Updating status to {}'.format(charger.charger_on))
                    node.update_state(charger.charger_on)
                    node.update_rate(charger.charging_rate)
                    node.update_max_rate(charger.mac_charging_rate)
                else:
                    LOGGER.error('Node {} (charger) is missing!'.format(charger.device_gid))
            except Exception as e:
                LOGGER.error('Failed to update {}:: {}'.format(charger.device_gid, e))


    # if we want to query a single device, can we call this from a node object?
    def query_device(self, gid, scale):
    
        usage = self.vue.get_device_list_usage([gid], None, scale=scale,
                unit=pyemvue.enums.Unit.KWH.value)

        self.update_devices(usage, scale)

    def query_device_status(self):
        outlets, chargers = self.vue.get_devices_status()

        if outlets:
            self.update_outlets(outlets)

        if chargers:
            self.update_chargers(chargers)
