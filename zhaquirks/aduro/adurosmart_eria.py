"""ADUROSMART Eria SceneSwitch 81847 device."""

from __future__ import annotations

from typing import Any

from zigpy.profiles.zha import DeviceType
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.typing import AddressingMode
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    COMMAND,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFCCC  # decimal = 64716


class AduroSmartCluster(CustomCluster, ManufacturerSpecificCluster):
    """Custom cluster for handling unknown cluster command 0xFCCC."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: AddressingMode | None = None,
    ):
        """Handle incoming cluster commands."""
        if hdr.command_id == 0x00:
            button = None
            press_type = SHORT_PRESS

            if args == b"\x00\x00\x00":
                button = BUTTON_1
            elif args == b"\x00\x01\x00":
                button = BUTTON_2
            elif args == b"\x00\x02\x00":
                button = BUTTON_3
            elif args == b"\x00\x03\x00":
                button = BUTTON_4
            elif args == b"\x01\x00\x00":
                button = BUTTON_1
                press_type = LONG_PRESS
            elif args == b"\x01\x01\x00":
                button = BUTTON_2
                press_type = LONG_PRESS
            elif args == b"\x01\x02\x00":
                button = BUTTON_3
                press_type = LONG_PRESS
            elif args == b"\x01\x03\x00":
                button = BUTTON_4
                press_type = LONG_PRESS

            event_args = {
                BUTTON: button,
                PRESS_TYPE: press_type,
            }

            if button is None:
                self.debug("Unknown args for cluster command 0: %s", args)
                return

            action = f"{button}_{press_type}"
            self.listener_event(ZHA_SEND_EVENT, action, event_args)

            return

        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


class AduroSmartCSC(CustomDevice):
    """ADUROSMART Eria SceneSwitch 81847 device."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID

    # <SimpleDescriptor endpoint=1 profile=49246 device_type=2064
    # device_version=2
    # input_clusters=[ 0, 1, 3, 4, 5, 6, 8, 768, 4096, 64716 ]
    # output_clusters=[ 0, 3, 4, 5, 6, 8, 768, 4096, 64716 ]>
    signature = {
        MODELS_INFO: [("AduroSmart Eria", "ADUROLIGHT_CSC")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0xC05E,
                DEVICE_TYPE: DeviceType.COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    AduroSmartCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    AduroSmartCluster.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: 0xC05E,
                DEVICE_TYPE: 0x03F2,
                INPUT_CLUSTERS: [LightLink.cluster_id],
                OUTPUT_CLUSTERS: [LightLink.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0xC05E,
                DEVICE_TYPE: DeviceType.COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    AduroSmartCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    AduroSmartCluster,
                ],
            },
            2: {
                PROFILE_ID: 0xC05E,
                DEVICE_TYPE: 0x03F2,
                INPUT_CLUSTERS: [LightLink.cluster_id],
                OUTPUT_CLUSTERS: [LightLink.cluster_id],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{SHORT_PRESS}"},
        (SHORT_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{SHORT_PRESS}"},
        (SHORT_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{SHORT_PRESS}"},
        (SHORT_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_{SHORT_PRESS}"},
        (LONG_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{LONG_PRESS}"},
        (LONG_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{LONG_PRESS}"},
        (LONG_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{LONG_PRESS}"},
        (LONG_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_{LONG_PRESS}"},
    }
