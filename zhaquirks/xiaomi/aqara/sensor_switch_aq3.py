"""Xiaomi aqara button sensor."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, MultistateInput, OnOff

from zhaquirks import CustomCluster
from zhaquirks.xiaomi import (
    BasicCluster, PowerConfigurationCluster, TemperatureMeasurementCluster,
    XiaomiCustomDevice)

BUTTON_DEVICE_TYPE = 0x5F01
STATUS_TYPE_ATTR = 0x0055  # decimal = 85
SINGLE = 1
DOUBLE = 2
HOLD = 16
RELEASE = 17
SHAKE = 18

MOVEMENT_TYPE = {
    SINGLE: 'single',
    DOUBLE: 'double',
    HOLD: 'hold',
    RELEASE: 'release',
    SHAKE: 'shake'
}

_LOGGER = logging.getLogger(__name__)


class SwitchAQ3(XiaomiCustomDevice):
    """Aqara button device."""

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

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        # device_version=1
        # input_clusters=[0, 18, 6, 1]
        # output_clusters=[0]>
        1: {
            'manufacturer': 'LUMI',
            'model': 'lumi.sensor_switch.aq3',
            'profile_id': zha.PROFILE_ID,
            'device_type': BUTTON_DEVICE_TYPE,
            'input_clusters': [
                Basic.cluster_id,
                PowerConfigurationCluster.cluster_id,
                OnOff.cluster_id,
                MultistateInput.cluster_id
            ],
            'output_clusters': [
                Basic.cluster_id,
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'LUMI',
                'model': 'lumi.sensor_switch.aq3',
                'device_type': zha.DeviceType.REMOTE_CONTROL,
                'input_clusters': [
                    BasicCluster,
                    PowerConfigurationCluster,
                    TemperatureMeasurementCluster,
                    MultistateInputCluster
                ],
                'output_clusters': [
                    Basic.cluster_id,
                    OnOff.cluster_id,
                ],
            }
        },
    }
