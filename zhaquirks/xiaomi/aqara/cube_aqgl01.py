"""Xiaomi aqara magic cube device."""
import logging

import homeassistant.components.zha.const as zha_const
from zigpy import quirks
from zigpy.profiles import zha
from zigpy.quirks.xiaomi import AqaraMagicCubeSensor
from zigpy.zcl.clusters.general import (
    AnalogInput, Groups, Identify, MultistateInput, Ota, Scenes)

from zhaquirks import CustomCluster
from zhaquirks.xiaomi import (
    BasicCluster, PowerConfigurationCluster, TemperatureMeasurementCluster,
    XiaomiCustomDevice)

XIAOMI_SENSORS = 0x5F01  # decimal = 24321 ? sensors
XIAOMI_MEASUREMENTS = 0x5F02  # decimal = 24322 ? multistate measurements
XIAOMI_ANALOG = 0x5F03  # decimal = 24323 ? analog input

XIAOMI_SENSORS_REPLACEMENT = 0x6F01
XIAOMI_MEASUREMENTS_REPLACEMENT = 0x6F02
XIAOMI_ANALOG_REPLACEMENT = 0x6F03

STATUS_TYPE_ATTR = 0x0055  # decimal = 85

SHAKE_VALUE = 0
DROP_VALUE = 3
SLIDE_VALUE = 261

KNOCK_1_VALUE = 512  # aqara skyside
KNOCK_2_VALUE = 513  # aqara facing me 90 right
KNOCK_3_VALUE = 514  # aqara facing me upside down
KNOCK_4_VALUE = 515  # aqara tableside
KNOCK_5_VALUE = 516  # aqara facing me 90 left
KNOCK_6_VALUE = 517  # aqara facing me upright

SLIDE_1_VALUE = 256  # aqara skyside
SLIDE_2_VALUE = 257  # aqara facing me 90 right
SLIDE_3_VALUE = 258  # aqara facing me upside down
SLIDE_4_VALUE = 259  # aqara tableside
SLIDE_5_VALUE = 260  # aqara facing me 90 left
SLIDE_6_VALUE = 261  # aqara facing me upright

FLIP_BEGIN = 50
FLIP_END = 180

MOVEMENT_TYPE = {
    SHAKE_VALUE: "shake",
    DROP_VALUE: "drop",
    SLIDE_1_VALUE: 'slide',
    SLIDE_2_VALUE: 'slide',
    SLIDE_3_VALUE: 'slide',
    SLIDE_4_VALUE: 'slide',
    SLIDE_5_VALUE: 'slide',
    SLIDE_6_VALUE: 'slide',
    KNOCK_1_VALUE: 'knock',
    KNOCK_2_VALUE: 'knock',
    KNOCK_3_VALUE: 'knock',
    KNOCK_4_VALUE: 'knock',
    KNOCK_5_VALUE: 'knock',
    KNOCK_6_VALUE: 'knock',
}

MOVEMENT_TYPE_DESCRIPTION = {
    SHAKE_VALUE: "shake",
    DROP_VALUE: "drop",
    SLIDE_1_VALUE: 'aqara logo on top',
    SLIDE_2_VALUE: 'aqara logo facing user rotated 90 degrees right',
    SLIDE_3_VALUE: 'aqara logo facing user upside down',
    SLIDE_4_VALUE: 'arara logo on bottom',
    SLIDE_5_VALUE: 'aqara logo facing user rotated 90 degrees left',
    SLIDE_6_VALUE: 'aqara logo facing user upright',
    KNOCK_1_VALUE: 'aqara logo on top',
    KNOCK_2_VALUE: 'aqara logo facing user rotated 90 degrees right',
    KNOCK_3_VALUE: 'aqara logo facing user upside down',
    KNOCK_4_VALUE: 'arara logo on bottom',
    KNOCK_5_VALUE: 'aqara logo facing user rotated 90 degrees left',
    KNOCK_6_VALUE: 'aqara logo facing user upright',
}

SIDES = {
    SLIDE_1_VALUE: 1,
    SLIDE_2_VALUE: 2,
    SLIDE_3_VALUE: 3,
    SLIDE_4_VALUE: 4,
    SLIDE_5_VALUE: 5,
    SLIDE_6_VALUE: 6,
    KNOCK_1_VALUE: 1,
    KNOCK_2_VALUE: 2,
    KNOCK_3_VALUE: 3,
    KNOCK_4_VALUE: 4,
    KNOCK_5_VALUE: 5,
    KNOCK_6_VALUE: 6,
}

ROTATE_RIGHT = 'rotate_right'
ROTATE_LEFT = 'rotate_left'

_LOGGER = logging.getLogger(__name__)

zha_const.SINGLE_INPUT_CLUSTER_DEVICE_CLASS.update({
    MultistateInput: 'sensor',
    AnalogInput: 'sensor'
})


def extend_dict(dictionary, value, ranges):
    """Extend a dict."""
    for item in ranges:
        dictionary[item] = value


extend_dict(MOVEMENT_TYPE, 'flip', range(FLIP_BEGIN, FLIP_END))

#  remove the zigpy version of this device handler
if AqaraMagicCubeSensor in quirks._DEVICE_REGISTRY:
    quirks._DEVICE_REGISTRY.remove(AqaraMagicCubeSensor)


class CubeAQGL01(XiaomiCustomDevice):
    """Aqara magic cube device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 9
        super().__init__(*args, **kwargs)

    class MultistateInputCluster(CustomCluster, MultistateInput):
        """Multistate input cluster."""

        cluster_id = MultistateInput.cluster_id

        def __init__(self, *args, **kwargs):
            """Init."""
            self._current_state = {}
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)
            if attrid == STATUS_TYPE_ATTR:
                self._current_state[STATUS_TYPE_ATTR] = action = \
                    MOVEMENT_TYPE.get(value)
                event_args = {
                    'value': value
                }
                if action is not None:

                    if action in ('slide', 'knock'):
                        event_args['description'] = MOVEMENT_TYPE_DESCRIPTION[
                            value
                        ]
                        event_args['activated_face'] = SIDES[value]

                    if action == 'flip':
                        if value > 108:
                            event_args['flip_degrees'] = 180
                        else:
                            event_args['flip_degrees'] = 90
                        event_args['activated_face'] = (value % 8) + 1

                    self.listener_event(
                        'zha_send_event',
                        self,
                        action,
                        event_args
                    )

                # show something in the sensor in HA
                super()._update_attribute(
                    0,
                    action
                )

    class AnalogInputCluster(CustomCluster, AnalogInput):
        """Analog input cluster."""

        cluster_id = AnalogInput.cluster_id

        def __init__(self, *args, **kwargs):
            """Init."""
            self._current_state = {}
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)
            if attrid == STATUS_TYPE_ATTR:
                if value > 0:
                    self._current_state[STATUS_TYPE_ATTR] = ROTATE_RIGHT
                else:
                    self._current_state[STATUS_TYPE_ATTR] = ROTATE_LEFT
                # show something in the sensor in HA
                super()._update_attribute(
                    0,
                    '{}:{}'.format(
                        self._current_state[STATUS_TYPE_ATTR],
                        value
                    )
                )
                if self._current_state[STATUS_TYPE_ATTR] is not None:
                    self.listener_event(
                        'zha_send_event',
                        self,
                        self._current_state[STATUS_TYPE_ATTR],
                        {
                            'relative_degrees': value
                        }
                    )

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        #  device_version=1
        #  input_clusters=[0, 3, 25, 18]
        #  output_clusters=[0, 4, 3, 5, 25, 18]>
        1: {
            'manufacturer': 'LUMI',
            'model': 'lumi.sensor_cube.aqgl01',
            'profile_id': zha.PROFILE_ID,
            'device_type': XIAOMI_SENSORS,
            'input_clusters': [
                BasicCluster.cluster_id,
                Identify.cluster_id,
                Ota.cluster_id,
                MultistateInput.cluster_id
            ],
            'output_clusters': [
                BasicCluster.cluster_id,
                Groups.cluster_id,
                Identify.cluster_id,
                Scenes.cluster_id,
                Ota.cluster_id,
                MultistateInput.cluster_id
            ],
        },
        #  <SimpleDescriptor endpoint=2 profile=260 device_type=24322
        #  device_version=1
        #  input_clusters=[3, 18]
        #  output_clusters=[4, 3, 5, 18]>
        2: {
            'profile_id': zha.PROFILE_ID,
            'device_type': XIAOMI_MEASUREMENTS,
            'input_clusters': [
                Identify.cluster_id,
                MultistateInput.cluster_id
            ],
            'output_clusters': [
                Groups.cluster_id,
                Identify.cluster_id,
                Scenes.cluster_id,
                MultistateInput.cluster_id
            ],
        },
        #  <SimpleDescriptor endpoint=3 profile=260 device_type=24323
        #  device_version=1
        #  input_clusters=[3, 12]
        #  output_clusters=[4, 3, 5, 12]>
        3: {
            'profile_id': zha.PROFILE_ID,
            'device_type': XIAOMI_ANALOG,
            'input_clusters': [
                Identify.cluster_id,
                AnalogInput.cluster_id
            ],
            'output_clusters': [
                Groups.cluster_id,
                Identify.cluster_id,
                Scenes.cluster_id,
                AnalogInput.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'LUMI',
                'model': 'lumi.sensor_cube.aqgl01',
                'device_type': XIAOMI_SENSORS_REPLACEMENT,
                'input_clusters': [
                    BasicCluster,
                    PowerConfigurationCluster,
                    TemperatureMeasurementCluster,
                    Identify.cluster_id,
                    Ota.cluster_id
                ],
                'output_clusters': [
                    BasicCluster.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    MultistateInput.cluster_id
                ],
            },
            2: {
                'manufacturer': 'LUMI',
                'model': 'lumi.sensor_cube.aqgl01',
                'device_type': XIAOMI_MEASUREMENTS_REPLACEMENT,
                'input_clusters': [
                    Identify.cluster_id,
                    MultistateInputCluster
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    MultistateInput.cluster_id
                ],
            },
            3: {
                'manufacturer': 'LUMI',
                'model': 'lumi.sensor_cube.aqgl01',
                'device_type': XIAOMI_ANALOG_REPLACEMENT,
                'input_clusters': [
                    Identify.cluster_id,
                    AnalogInputCluster
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    AnalogInput.cluster_id
                ],
            }
        },
    }
