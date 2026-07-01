"""Signify RDM002 device."""

import logging
from typing import Any

from zigpy.profiles import zha
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

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    CLUSTER_ID,
    COMMAND,
    COMMAND_STEP_ON_OFF,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PARAMS,
    PROFILE_ID,
    SHORT_PRESS,
)
from zhaquirks.philips import (
    PHILIPS,
    SIGNIFY,
    Button,
    PhilipsBasicCluster,
    PhilipsRemoteCluster,
)

_LOGGER = logging.getLogger(__name__)

DIAL_TRIGGERS = {
    (SHORT_PRESS, DIM_UP): {
        COMMAND: COMMAND_STEP_ON_OFF,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 0},
    },
    (SHORT_PRESS, DIM_DOWN): {
        COMMAND: COMMAND_STEP_ON_OFF,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 1},
    },
}


class PhilipsRdm002RemoteCluster(PhilipsRemoteCluster):
    """Philips remote cluster for RDM002."""

    BUTTONS = {
        1: Button(BUTTON_1),
        2: Button(BUTTON_2),
        3: Button(BUTTON_3),
        4: Button(BUTTON_4),
    }


class PhilipsRdm002LevelControl(CustomCluster, LevelControl):
    """Philips RDM002 LevelControl cluster."""

    def listener_event(self, method_name: str, *args) -> list[Any | None]:
        """Blackhole requests with transition_time=8, which originate from button long-presses."""

        # example args we want to mute:
        # [(224, 6, step_with_on_off(step_mode=<StepMode.Down: 1>, step_size=255, transition_time=8))]
        # transition_time=8 when step command is sent for long-press of button 1.
        # transition_time=4 when dial is rotated.
        if (
            method_name == "cluster_command"
            and len(args) > 2
            and len(args[2]) > 2
            and args[2][2] == 8
        ):
            _LOGGER.debug(
                "%s::listener_event - muting level control method: %s - args: [%s]",
                self.__class__.__name__,
                method_name,
                args,
            )
            return []

        return super().listener_event(method_name, *args)


class PhilipsRDM002(CustomDevice):
    """Philips RDM002 device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=2096
        #  device_version=1
        #  input_clusters=[0, 1, 3, 64512, 4096]
        #  output_clusters=[25, 0, 3, 4, 6, 8, 5, 4096]>
        MODELS_INFO: [(PHILIPS, "RDM002"), (SIGNIFY, "RDM002")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PhilipsRdm002RemoteCluster.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    PhilipsBasicCluster,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PhilipsRdm002RemoteCluster,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    PhilipsRdm002LevelControl,
                    Scenes.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = (
        PhilipsRdm002RemoteCluster.generate_device_automation_triggers(DIAL_TRIGGERS)
    )
