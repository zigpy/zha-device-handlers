import logging

from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.profiles import PROFILES, zha
from zigpy.zcl.clusters.general import Basic, Groups, OnOff, PowerConfiguration
from zigpy.util import ListenableMixin

BUTTON_DEVICE_TYPE = 0x5F01
XIAOMI_ATTRIBUTE = 0xFF01
XIAOMI_CLUSTER_ID = 0xFFFF

BATTERY_REPORTED = 'battery_reported'
BATTERY_LEVEL = 'battery_level'
BATTERY_VOLTAGE_MV = 'battery_voltage_mV'
XIAOMI_ATTR_4 = 'X-attrib-4'
XIAOMI_ATTR_5 = 'X-attrib-5'
XIAOMI_ATTR_6 = 'X-attrib-6'
PATH = 'path'
BATTERY_PERCENTAGE_REMAINING = 0x0021

_LOGGER = logging.getLogger(__name__)

# This registers a device that Xiaomi didn't follow the spec on.
# Translated: For device type: 0x5F01 in the ZHA zigbee profile
# the input clusters are: [0x0000, 0x0006, 0xFFFF] and the output
# clusters are: [0x0000, 0x0004, 0xFFFF]. The goal is to read this
# from a configuration file in the future
PROFILES[zha.PROFILE_ID].CLUSTERS[BUTTON_DEVICE_TYPE] = (
    [Basic.cluster_id, OnOff.cluster_id, XIAOMI_CLUSTER_ID],
    [Basic.cluster_id, Groups.cluster_id, XIAOMI_CLUSTER_ID]
    )


class AqaraButton(CustomDevice, ListenableMixin):
    _listeners = {}

    class BasicCluster(CustomCluster, Basic):
        cluster_id = Basic.cluster_id

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)
            if attrid == XIAOMI_ATTRIBUTE:
                attributes = self._parse_attributes(value)
                _LOGGER.debug(
                    "%s - Received attribute report. attribute_id: [%s] value: [%s]",
                    self.endpoint.device._ieee,
                    attrid,
                    attributes
                    )
                if BATTERY_LEVEL in attributes:
                    self.endpoint.device.listener_event(
                        BATTERY_REPORTED,
                        attributes[BATTERY_LEVEL]
                        )

        def _parse_attributes(self, value):
            """ parse non standard atrributes."""
            import zigpy.types as t
            from zigpy.zcl import foundation as f
            attributes = {}
            attribute_names = {
                4: XIAOMI_ATTR_4,
                1: BATTERY_VOLTAGE_MV,
                5: XIAOMI_ATTR_5,
                6: XIAOMI_ATTR_6,
                10: PATH
            }
            result = {}
            while value:
                skey = int(value[0])
                svalue, value = f.TypeValue.deserialize(value[1:])
                result[skey] = svalue.value
            for item, value in result.items():
                key = attribute_names[item] \
                    if item in attribute_names else "0xff01-" + str(item)
                attributes[key] = value
            if BATTERY_VOLTAGE_MV in attributes:
                attributes[BATTERY_LEVEL] = int(
                    self._calculate_remaining_battery_percentage(
                        attributes[BATTERY_VOLTAGE_MV]
                        )
                    )
            return attributes

        def _calculate_remaining_battery_percentage(self, voltage):
            """calculate percentage."""
            min_voltage = 2500
            max_voltage = 3000
            percent = (voltage - min_voltage) / (max_voltage - min_voltage) * 100
            if percent > 100:
                percent = 100
            return percent

    class PowerConfigurationCluster(CustomCluster, PowerConfiguration):
        cluster_id = PowerConfiguration.cluster_id

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.endpoint.device.add_listener(self)

        def battery_reported(self, voltage):
            self._update_attribute(BATTERY_PERCENTAGE_REMAINING, voltage)

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        # device_version=1 input_clusters=[0, 6, 65535]
        # output_clusters=[0, 4, 65535]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': BUTTON_DEVICE_TYPE,
            'input_clusters': [
                Basic.cluster_id,
                OnOff.cluster_id,
                XIAOMI_CLUSTER_ID
               ],
            'output_clusters': [
                Basic.cluster_id,
                Groups.cluster_id,
                XIAOMI_CLUSTER_ID
                ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'input_clusters': [
                    BasicCluster,
                    PowerConfigurationCluster,
                    OnOff.cluster_id,
                    XIAOMI_CLUSTER_ID
                    ],
            }
        },
    }
