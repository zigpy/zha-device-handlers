"""Xiaomi aqara double key switch device."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    AnalogInput, Basic, Groups, Identify, MultistateInput, Ota, Scenes)

from zhaquirks import CustomCluster
from zhaquirks.xiaomi import (
    BasicCluster, PowerConfigurationCluster, TemperatureMeasurementCluster,
    XiaomiCustomDevice)

XIAOMI_DEVICE_TYPE = 0x5F01
XIAOMI_DEVICE_TYPE2 = 0x5F02
XIAOMI_DEVICE_TYPE3 = 0x5F03
XIAOMI_CLUSTER_ID = 0xFFFF
STATUS_TYPE_ATTR = 0x0055  # decimal = 85

PRESS_TYPE = {
    0: 'long press',
    1: 'single',
    2: 'double'
}

ENDPOINTS = {
    1: 'left',
    2: 'right',
    3: 'both'
}

_LOGGER = logging.getLogger(__name__)


class RemoteB286ACN01(XiaomiCustomDevice):
    """Aqara double key switch device."""

    class MultistateInputCluster(CustomCluster, MultistateInput):
        """Multistate input cluster."""

        cluster_id = MultistateInput.cluster_id

        def __init__(self, *args, **kwargs):
            """Init."""
            self._current_state = None
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)
            if attrid == STATUS_TYPE_ATTR:
                self._current_state = PRESS_TYPE.get(value)
                button = ENDPOINTS.get(self.endpoint.endpoint_id)
                event_args = {
                    'button': button,
                    'press_type': self._current_state,
                    'attr_id': attrid,
                    'value': value
                }
                action = "{}_{}".format(button, self._current_state)
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
        # input_clusters=[0, 3, 25, 65535, 18]
        # output_clusters=[0, 4, 3, 5, 25, 65535, 18]>
        1: {
            'manufacturer': 'LUMI',
            'model': 'lumi.remote.b286acn01',
            'profile_id': zha.PROFILE_ID,
            'device_type': XIAOMI_DEVICE_TYPE,
            'input_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Ota.cluster_id,
                XIAOMI_CLUSTER_ID,
                MultistateInputCluster.cluster_id
            ],
            'output_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                Ota.cluster_id,
                XIAOMI_CLUSTER_ID,
                MultistateInputCluster.cluster_id
            ],
        },
        # <SimpleDescriptor endpoint=2 profile=260 device_type=24322
        # device_version=1
        # input_clusters=[3, 18]
        # output_clusters=[4, 3, 5, 18]>
        2: {
            'profile_id': zha.PROFILE_ID,
            'device_type': XIAOMI_DEVICE_TYPE2,
            'input_clusters': [
                Identify.cluster_id,
                MultistateInputCluster.cluster_id
            ],
            'output_clusters': [
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                MultistateInputCluster.cluster_id
            ],
        },
        # <SimpleDescriptor endpoint=3 profile=260 device_type=24323
        # device_version=1
        # input_clusters=[3, 12]
        # output_clusters=[4, 3, 5, 12]>
        3: {
            'profile_id': zha.PROFILE_ID,
            'device_type': XIAOMI_DEVICE_TYPE3,
            'input_clusters': [
                Identify.cluster_id,
                AnalogInput.cluster_id
            ],
            'output_clusters': [
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                AnalogInput.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'LUMI',
                'model': 'lumi.remote.b286acn01',
                'device_type': XIAOMI_DEVICE_TYPE,
                'input_clusters': [
                    BasicCluster,
                    PowerConfigurationCluster,
                    TemperatureMeasurementCluster,
                    Identify.cluster_id,
                    Ota.cluster_id,
                    XIAOMI_CLUSTER_ID,
                    MultistateInputCluster
                ],
                'output_clusters': [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    XIAOMI_CLUSTER_ID,
                    MultistateInputCluster
                ],
            },
            2: {
                'manufacturer': 'LUMI',
                'model': 'lumi.remote.b286acn01',
                'device_type': XIAOMI_DEVICE_TYPE2,
                'input_clusters': [
                    Identify.cluster_id,
                    MultistateInputCluster
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MultistateInputCluster
                ],
            },
            3: {
                'manufacturer': 'LUMI',
                'model': 'lumi.remote.b286acn01',
                'device_type': XIAOMI_DEVICE_TYPE3,
                'input_clusters': [
                    Identify.cluster_id,
                    MultistateInputCluster
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    AnalogInput.cluster_id,
                    MultistateInputCluster
                ],
            }
        },
    }
