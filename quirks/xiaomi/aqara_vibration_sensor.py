import logging

from zigpy.quirks import CustomCluster
from zigpy.profiles import PROFILES, zha
from zigpy.zcl.clusters.general import Basic, Groups, PowerConfiguration,\
    Identify, Ota, Scenes, MultistateInput
from zigpy.zcl.clusters.closures import DoorLock
from quirks.xiaomi import BasicCluster, PowerConfigurationCluster,\
    TemperatureMeasurementCluster, XiaomiCustomDevice
from quirks import Bus

VIBE_DEVICE_TYPE = 0x5F02  # decimal = 24322
RECENT_ACTIVITY_LEVEL_ATTR = 0x0505  # decimal = 1285
ACCELEROMETER_ATTR = 0x0508  # decimal = 1288
STATUS_TYPE_ATTR = 0x0055  # decimal = 85
ROTATION_DEGREES_ATTR = 0x0503  # decimal = 1283
MEASUREMENT_TYPE = {
    0: "Stationary",
    1: "Vibration",
    2: "Tilt",
    3: "Drop"
}

_LOGGER = logging.getLogger(__name__)

PROFILES[zha.PROFILE_ID].CLUSTERS[zha.DeviceType.DOOR_LOCK] = (
    [
        Basic.cluster_id,
        PowerConfiguration.cluster_id,
        Identify.cluster_id,
        Ota.cluster_id,
        DoorLock.cluster_id
    ],
    [
        Basic.cluster_id,
        Identify.cluster_id,
        Groups.cluster_id,
        Scenes.cluster_id,
        Ota.cluster_id,
        DoorLock.cluster_id
    ]
)

PROFILES[zha.PROFILE_ID].CLUSTERS[VIBE_DEVICE_TYPE] = (
    [
        Identify.cluster_id,
        MultistateInput.cluster_id
    ],
    [
        Identify.cluster_id,
        Groups.cluster_id,
        Scenes.cluster_id,
        MultistateInput.cluster_id
    ]
)


class AqaraVibrationSensor(XiaomiCustomDevice):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class MultistateInputCluster(CustomCluster, MultistateInput):
        cluster_id = DoorLock.cluster_id

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._currentState = {}

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)
            _LOGGER.debug(
                "%s - Attribute report. attribute_id: [%s] value: [%s]",
                self.endpoint.device._ieee,
                attrid,
                value
            )
            if attrid == STATUS_TYPE_ATTR:
                _LOGGER.debug(
                    "%s - Status type report. attribute_id: [%s] value: [%s]",
                    self.endpoint.device._ieee,
                    attrid,
                    MEASUREMENT_TYPE.get(value)
                )
                self._currentState[STATUS_TYPE_ATTR] = MEASUREMENT_TYPE.get(
                    value
                )

    signature = {
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.DOOR_LOCK,
            'input_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Ota.cluster_id,
                DoorLock.cluster_id
            ],
            'output_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                Ota.cluster_id,
                DoorLock.cluster_id
            ],
        },
        2: {
            'profile_id': zha.PROFILE_ID,
            'device_type': VIBE_DEVICE_TYPE,
            'input_clusters': [
                Identify.cluster_id,
                MultistateInput.cluster_id
            ],
            'output_clusters': [
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                MultistateInput.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'input_clusters': [
                    BasicCluster,
                    PowerConfigurationCluster,
                    TemperatureMeasurementCluster,
                    Identify.cluster_id,
                    MultistateInputCluster
                ],
            }
        },
    }
