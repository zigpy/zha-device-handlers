"""Smart vent quirk."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    Scenes,
)
from zigpy.zcl.clusters.measurement import PressureMeasurement, TemperatureMeasurement

from .. import DoublingPowerConfigurationCluster
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

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
        MODELS_INFO: [
            ("Keen Home Inc", "SV01-410-MP-1.0"),
            ("Keen Home Inc", "SV01-410-MP-1.1"),
            ("Keen Home Inc", "SV01-410-MP-1.4"),
            ("Keen Home Inc", "SV01-410-MP-1.5"),
            ("Keen Home Inc", "SV02-410-MP-1.3"),
            ("Keen Home Inc", "SV01-412-MP-1.0"),
            ("Keen Home Inc", "SV01-610-MP-1.0"),
            ("Keen Home Inc", "SV02-610-MP-1.3"),
            ("Keen Home Inc", "SV01-612-MP-1.0"),
            ("Keen Home Inc", "SV02-612-MP-1.3"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROLLABLE_OUTPUT,
                INPUT_CLUSTERS: [
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
                    KEEN2_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                INPUT_CLUSTERS: [
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
                    KEEN2_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
