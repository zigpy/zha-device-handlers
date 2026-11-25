"""Quirk for GLEDOPTO GL-SD-* dimmers."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks import NoReplyMixin
from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legacy import CustomDevice


class LevelControlNoReply(NoReplyMixin, CustomCluster, LevelControl):
    """LevelControl cluster that does not require default responses."""

    void_input_commands = {cmd.id for cmd in LevelControl.commands_by_name.values()}


class GledoptoGlSdDimmer(CustomDevice):
    """Gledopto GL-SD-001 & GL-SD-003P dimmer custom device implementation."""

    signature = {
        MODELS_INFO: [("GLEDOPTO", "GL-SD-001"), ("GLEDOPTO", "GL-SD-003P")],
        ENDPOINTS: {
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
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
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
                    OnOff.cluster_id,
                    LevelControlNoReply,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
        },
    }


# The GL-SD-001P and GL-SD-301P are brightness-only triac dimmers that still announce
# the Color cluster (color_capabilities 0, but a cached color_temperature). Remove it
# so ZHA doesn't show color temperature controls.
(
    QuirkBuilder("GLEDOPTO", "GL-SD-001P")
    .applies_to("GLEDOPTO", "GL-SD-301P")
    .removes(Color.cluster_id, endpoint_id=11)
    .add_to_registry()
)
