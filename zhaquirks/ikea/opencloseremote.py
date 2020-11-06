"""Device handler for IKEA of Sweden TRADFRI remote control."""
from typing import List

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Alarms,
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.lightlink import LightLink

from . import IKEA
from .. import DoublingPowerConfigurationCluster
from ..const import (
    ARGS,
    CLOSE,
    COMMAND,
    COMMAND_STOP,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_RELEASE,
    MODELS_INFO,
    OPEN,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)

COMMAND_CLOSE = "down_close"
COMMAND_STOP_OPENING = "stop_opening"
COMMAND_STOP_CLOSING = "stop_closing"
COMMAND_OPEN = "up_open"
IKEA_CLUSTER_ID = 0xFC7C  # decimal = 64636


class IkeaWindowCovering(CustomCluster, WindowCovering):
    """Ikea Window covering cluster."""

    def __init__(self, *args, **kwargs):
        """Initialize instance."""
        super().__init__(*args, **kwargs)
        self._is_closing = None

    def handle_cluster_request(
        self, tsn: int, command_id: int, args: List[int]
    ) -> None:
        """Handle cluster specific commands.

        We just want to keep track of direction, to associate it with the stop command.
        """

        cmd_name = self.server_commands.get(command_id, [command_id])[0]
        if cmd_name == COMMAND_OPEN:
            self._is_closing = False
        elif cmd_name == COMMAND_CLOSE:
            self._is_closing = True
        elif cmd_name == COMMAND_STOP:
            action = COMMAND_STOP_CLOSING if self._is_closing else COMMAND_STOP_OPENING
            self.listener_event(ZHA_SEND_EVENT, action, [])


class IkeaTradfriOpenCloseRemote(CustomDevice):
    """Custom device representing IKEA of Sweden TRADFRI remote control."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=515
        # device_version=1
        # input_clusters=[0, 1, 3, 9, 32, 4096, 64636]
        # output_clusters=[3, 4, 6, 8, 25, 258, 4096]>
        MODELS_INFO: [
            ("\x02KE", "TRADFRI open/close remote"),
            (IKEA, "TRADFRI open/close remote"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    IKEA_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        },
    }

    replacement = {
        MODELS_INFO: [(IKEA, "TRADFRI open/close remote")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DoublingPowerConfigurationCluster,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    IKEA_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    IkeaWindowCovering,
                    LightLink.cluster_id,
                ],
            }
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, OPEN): {COMMAND: COMMAND_OPEN, ARGS: []},
        (LONG_RELEASE, OPEN): {COMMAND: COMMAND_STOP_OPENING, ARGS: []},
        (SHORT_PRESS, CLOSE): {COMMAND: COMMAND_CLOSE, ARGS: []},
        (LONG_RELEASE, CLOSE): {COMMAND: COMMAND_STOP_CLOSING, ARGS: []},
    }
