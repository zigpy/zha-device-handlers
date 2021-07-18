"""Device handler for Yooksmart D10110 roller blinds."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
    Scenes,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class InvertedWindowCoveringCluster(CustomCluster, WindowCovering):
    """WindowCovering cluster implementation.

    This implementation inverts the reported covering percent for non standard
    devices that don't follow the reporting spec.
    """

    cluster_id = WindowCovering.cluster_id
    CURRENT_POSITION_LIFT_PERCENTAGE = 0x0008

    def _update_attribute(self, attrid, value):
        if attrid == self.CURRENT_POSITION_LIFT_PERCENTAGE:
            value = 100 - value
        super()._update_attribute(attrid, value)


class D10110Blinds(CustomDevice):
    """Custom device representing Yooksmart D10110 roller blinds."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=514
        # device_version=1
        # input_clusters=[0, 1, 3, 4, 5, 32, 258]
        # output_clusters=[3, 25]>
        MODELS_INFO: [
            ("yooksmart", "D10110"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    PollControl.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    PollControl.cluster_id,
                    InvertedWindowCoveringCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }
