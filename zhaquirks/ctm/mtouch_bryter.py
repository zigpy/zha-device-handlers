"""CTM Lyng mTouch Bryter"""
import zigpy.profiles.zha as zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks.const import (
    ALT_SHORT_PRESS,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
    COMMAND_TOGGLE,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PARAMS,
    PROFILE_ID,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.ctm import (
    CTM,
    CTM_MFCODE,
    CtmDiagnosticsCluster,
    CtmGroupConfigCluster,
    CtmPowerConfiguration,
    CtmTemperatureMeasurement,
)

COMMAND_RECALL = "recall"
COMMAND_STORE = "store"
COMMAND_ON_WITH_TIMED_OFF = "on_with_timed_off"
DIMMER_BUTTON = "dimmer_button"


class CtmScenes(CustomCluster, Scenes):
    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        # Set groupID 0x0000, so EZSP coordinator can receive multicast
        await self.endpoint.ctm_group_config.write_attributes(
            {"grpup_id": 0}, manufacturer=CTM_MFCODE
        )
        return result


class CtmLyngMTouchBryter(CustomDevice):
    """Custom device mtouch bryter."""

    signature = {
        MODELS_INFO: [(CTM, "mTouch Bryter")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1026, 65191, 65261]
            # output_clusters=[3, 4, 5, 6, 8, 25, 4096]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    CtmGroupConfigCluster.cluster_id,
                    CtmDiagnosticsCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CtmPowerConfiguration,
                    Identify.cluster_id,
                    CtmTemperatureMeasurement,
                    CtmGroupConfigCluster,
                    CtmDiagnosticsCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    CtmScenes,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {
            COMMAND: COMMAND_RECALL,
            PARAMS: {"scene_id": 1},
        },
        (LONG_RELEASE, BUTTON_1): {
            COMMAND: COMMAND_STORE,
            PARAMS: {"scene_id": 1},
        },
        (SHORT_PRESS, BUTTON_2): {
            COMMAND: COMMAND_RECALL,
            PARAMS: {"scene_id": 2},
        },
        (LONG_RELEASE, BUTTON_2): {
            COMMAND: COMMAND_STORE,
            PARAMS: {"scene_id": 2},
        },
        (SHORT_PRESS, BUTTON_3): {
            COMMAND: COMMAND_RECALL,
            PARAMS: {"scene_id": 3},
        },
        (LONG_RELEASE, BUTTON_3): {
            COMMAND: COMMAND_STORE,
            PARAMS: {"scene_id": 3},
        },
        (SHORT_PRESS, TURN_ON): {
            COMMAND: COMMAND_ON,
        },
        (SHORT_PRESS, TURN_OFF): {
            COMMAND: COMMAND_OFF,
        },
        (ALT_SHORT_PRESS, BUTTON_2): {
            COMMAND: COMMAND_TOGGLE,
        },
        (ALT_SHORT_PRESS, TURN_ON): {
            COMMAND: COMMAND_ON_WITH_TIMED_OFF,
        },
        (LONG_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_MOVE,
            PARAMS: {"move_mode": 1},
        },
        (LONG_PRESS, DIM_UP): {
            COMMAND: COMMAND_MOVE_ON_OFF,
            PARAMS: {"move_mode": 0},
        },
        (LONG_RELEASE, DIMMER_BUTTON): {
            COMMAND: COMMAND_STOP,
        },
    }
