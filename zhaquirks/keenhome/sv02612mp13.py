"""Smart vent quirk."""
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic, Identify, Groups, Scenes, OnOff, LevelControl, Ota, PollControl
)
from zigpy.zcl.clusters.measurement import (
    TemperatureMeasurement, PressureMeasurement
)
from zigpy.quirks import CustomDevice
from .. import DoublingPowerConfigurationCluster

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821
KEEN1_CLUSTER_ID = 0xFC01  # decimal = 64513
KEEN2_CLUSTER_ID = 0xFC02  # decimal = 64514


class KeenHomeSmartVent(CustomDevice):
    """Custom device representing Keen Home Smart Vent."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=3
        # device_version=0
        # input_clusters=[
        #   0, 1, 3, 4, 5, 6, 8, 32, 1026, 1027, 2821, 64513, 64514]
        # output_clusters=[25]>
        'models_info': [
            ('Keen Home Inc', 'SV02-612-MP-1.3')
        ],
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'device_type': zha.DeviceType.LEVEL_CONTROLLABLE_OUTPUT,
                'input_clusters': [
                    Basic.cluster_id,
                    DoublingPowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    PressureMeasurement.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    KEEN1_CLUSTER_ID,
                    KEEN2_CLUSTER_ID
                ],
                'output_clusters': [
                    Ota.cluster_id
                ],
            },
        }
    }

    replacement = {
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'input_clusters': [
                    Basic.cluster_id,
                    DoublingPowerConfigurationCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    PressureMeasurement.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    KEEN1_CLUSTER_ID,
                    KEEN2_CLUSTER_ID
                ],
                'output_clusters': [
                    Ota.cluster_id
                ],
            }
        },
    }
