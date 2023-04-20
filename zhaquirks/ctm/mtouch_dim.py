"""CTM Lyng mTouch Dim & DimmerPille"""
import zigpy.profiles.zha as zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Ballast
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from zhaquirks.ctm import CTM, CtmDiagnosticsCluster


class CtmOnOffCluster(CustomCluster, OnOff):
    """CTM Lyng custom on/off cluster."""

    async def command(
        self, command_id, *args, manufacturer=None, expect_reply=False, tsn=None
    ):
        """Set expect_reply=False."""

        await super().command(
            command_id, *args, manufacturer=manufacturer, expect_reply=False, tsn=tsn
        )
        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.SUCCESS)


class CtmLyngTouchDim(CustomDevice):
    """CTM Lyng custom device mTouch Dim."""

    signature = {
        MODELS_INFO: [(CTM, "mTouch Dim"), (CTM, "DimmerPille")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=257
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6, 1024, 1030, 4096, 65261]
            # output_clusters=[3, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ballast.cluster_id,
                    LightLink.cluster_id,
                    CtmDiagnosticsCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    CtmOnOffCluster,
                    LevelControl.cluster_id,
                    Ballast.cluster_id,
                    LightLink.cluster_id,
                    CtmDiagnosticsCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }
