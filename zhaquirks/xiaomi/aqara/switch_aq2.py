"""Xiaomi aqara button sensor."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Groups, OnOff

from zhaquirks.xiaomi import (
    BasicCluster, PowerConfigurationCluster, TemperatureMeasurementCluster,
    XiaomiCustomDevice)

BUTTON_DEVICE_TYPE = 0x5F01
XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)


class SwitchAQ2(XiaomiCustomDevice):
    """Aqara button device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        # device_version=1
        # input_clusters=[0, 6, 65535]
        # output_clusters=[0, 4, 65535]>
        1: {
            'manufacturer': 'LUMI',
            'model': 'lumi.sensor_switch.aq2',
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
                'manufacturer': 'LUMI',
                'model': 'lumi.sensor_switch.aq2',
                'device_type': zha.DeviceType.REMOTE_CONTROL,
                'input_clusters': [
                    BasicCluster,
                    PowerConfigurationCluster,
                    TemperatureMeasurementCluster,
                    XIAOMI_CLUSTER_ID
                ],
                'output_clusters': [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    XIAOMI_CLUSTER_ID,
                    OnOff.cluster_id,
                ],
            }
        },
    }
