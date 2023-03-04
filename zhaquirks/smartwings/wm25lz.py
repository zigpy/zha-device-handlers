"""Device handler for Smartwings blinds."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    Ota,
    PowerConfiguration,
    Scenes,
)

from zhaquirks import DoublingPowerConfigurationCluster
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
    CMD_GO_UP = 0x0001 #reported as down_close in ZHA commands
    CMD_GO_DOWN = 0x0000 #reported as up_open in ZHA commands
    
    async def command(
        self, command_id, *args, manufacturer=None, expect_reply=True, tsn=None, **kwargs
    ):
        """Override default commands for up and down. they are backwards."""

        if command_id == self.CMD_GO_UP:
            return await super().command(self.CMD_GO_DOWN, *args)
        if command_id == self.CMD_GO_DOWN:
            return await super().command(self.CMD_GO_UP, *args)
        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )

class WM25LBlinds(CustomDevice):
    """Custom device representing Smartwings WM25LZ blinds."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=514
        # device_version=1
        # input_clusters=[0, 1, 3, 4, 5, 32, 258]
        # output_clusters=[3, 25]>
        MODELS_INFO: [
            ("Smartwings", "WM25/L-Z"),
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
                    DoublingPowerConfigurationCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    InvertedWindowCoveringCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }
