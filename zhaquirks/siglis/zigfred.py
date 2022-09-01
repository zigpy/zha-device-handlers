"""zigfred device handler."""
import logging
from typing import Any, List, Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    COMMAND,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)

_LOGGER = logging.getLogger(__name__)

# Siglis zigfred specific clusters
SIGLIS_MANUFACTURER_CODE = 0x129C
ZIGFRED_CLUSTER_ID = 0xFC42
ZIGFRED_CLUSTER_BUTTONS_ATTRIBUTE_ID = 0x0008
ZIGFRED_CLUSTER_COMMAND_BUTTON_EVENT = 0x02


# Siglis zigfred cluster implementation
class ZigfredCluster(CustomCluster):
    """Siglis manufacturer specific cluster for zigfred."""

    name = "Siglis Manufacturer Specific"
    cluster_id = ZIGFRED_CLUSTER_ID
    buttons_attribute_id = ZIGFRED_CLUSTER_BUTTONS_ATTRIBUTE_ID

    server_commands = {
        ZIGFRED_CLUSTER_COMMAND_BUTTON_EVENT: foundation.ZCLCommandDef(
            "button_event",
            {"param1": t.uint32_t},
            is_reply=False,
            is_manufacturer_specific=True,
        ),
    }

    def _process_button_event(self, value: t.uint32_t):
        button_lookup = {
            0: BUTTON_1,
            1: BUTTON_2,
            2: BUTTON_3,
            3: BUTTON_4,
        }

        press_type_lookup = {
            0: LONG_RELEASE,
            1: SHORT_PRESS,
            2: DOUBLE_PRESS,
            3: LONG_PRESS,
        }

        button = value & 0xFF
        press_type = (value >> 8) & 0xFF

        button = button_lookup[button]
        press_type = press_type_lookup[press_type]

        action = f"{button}_{press_type}"

        event_args = {
            BUTTON: button,
            PRESS_TYPE: press_type,
        }

        _LOGGER.info(f"Got button press on zigfred cluster: {action}")

        if button and press_type:
            self.listener_event(ZHA_SEND_EVENT, action, event_args)

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ) -> None:
        """Handle cluster specific commands."""
        if hdr.command_id == ZIGFRED_CLUSTER_COMMAND_BUTTON_EVENT:
            self._process_button_event(args[0])


class ZigfredUno(CustomDevice):
    """zigfred uno device handler."""

    def __init__(self, *args, **kwargs):
        """Init."""
        _LOGGER.info("Initializing zigfred uno")
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [("Siglis", "zigfred uno")],
        ENDPOINTS: {
            5: {
                # Front Module LED
                # SizePrefixedSimpleDescriptor(endpoint=5,
                # profile=260, device_type=258,
                # device_version=1,
                # input_clusters=[0, 3, 4, 5, 6, 8, 768, 837],
                # output_clusters=[])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    ZigfredCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                # Relay
                # SizePrefixedSimpleDescriptor(endpoint=6,
                # profile=260, device_type=256,
                # device_version=1,
                # input_clusters=[0, 3, 4, 5, 6],
                # output_clusters=[])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                # Relay
                # SizePrefixedSimpleDescriptor(endpoint=7,
                # profile=260, device_type=257,
                # device_version=1,
                # input_clusters=[0, 3, 5, 4, 6, 8],
                # output_clusters=[])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                # SizePrefixedSimpleDescriptor(endpoint=242,
                # profile=41440, device_type=97,
                # device_version=0,
                # input_clusters=[],
                # output_clusters=[33])
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    ZigfredCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{SHORT_PRESS}"},
        (SHORT_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{SHORT_PRESS}"},
        (SHORT_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{SHORT_PRESS}"},
        (SHORT_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_{SHORT_PRESS}"},
        (DOUBLE_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{DOUBLE_PRESS}"},
        (DOUBLE_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{DOUBLE_PRESS}"},
        (DOUBLE_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{DOUBLE_PRESS}"},
        (DOUBLE_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_{DOUBLE_PRESS}"},
        (LONG_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{LONG_PRESS}"},
        (LONG_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{LONG_PRESS}"},
        (LONG_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{LONG_PRESS}"},
        (LONG_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_{LONG_PRESS}"},
        (LONG_RELEASE, BUTTON_1): {COMMAND: f"{BUTTON_1}_{LONG_RELEASE}"},
        (LONG_RELEASE, BUTTON_2): {COMMAND: f"{BUTTON_2}_{LONG_RELEASE}"},
        (LONG_RELEASE, BUTTON_3): {COMMAND: f"{BUTTON_3}_{LONG_RELEASE}"},
        (LONG_RELEASE, BUTTON_4): {COMMAND: f"{BUTTON_4}_{LONG_RELEASE}"},
    }


class ZigfredPlus(CustomDevice):
    """zigfred plus device handler."""

    def __init__(self, *args, **kwargs):
        """Init."""
        _LOGGER.info("Initializing zigfred plus")
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [("Siglis", "zigfred plus")],
        ENDPOINTS: {
            5: {
                # Front Module LED
                # SizePrefixedSimpleDescriptor(endpoint=5,
                # profile=260, device_type=258,
                # device_version=1,
                # input_clusters=[0, 3, 4, 5, 6, 8, 768, 837],
                # output_clusters=[])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    ZigfredCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                # Dimmable Light 1
                # SizePrefixedSimpleDescriptor(endpoint=7,
                # profile=260, device_type=257,
                # device_version=1,
                # input_clusters=[0, 3, 5, 4, 6, 8],
                # output_clusters=[])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            8: {
                # Dimmable Light 2
                # SizePrefixedSimpleDescriptor(endpoint=8,
                # profile=260, device_type=257,
                # device_version=1,
                # input_clusters=[0, 3, 5, 4, 6, 8],
                # output_clusters=[])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            9: {
                # Dimmable Light 3
                # SizePrefixedSimpleDescriptor(endpoint=9,
                # profile=260, device_type=257,
                # device_version=1,
                # input_clusters=[0, 3, 5, 4, 6, 8],
                # output_clusters=[])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            10: {
                # Dimmable Light 4
                # SizePrefixedSimpleDescriptor(endpoint=10,
                # profile=260, device_type=257,
                # device_version=1,
                # input_clusters=[0, 3, 5, 4, 6, 8],
                # output_clusters=[])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            11: {
                # Window Cover 1
                # SizePrefixedSimpleDescriptor(endpoint=11,
                # profile=260, device_type=514,
                # device_version=1,
                # input_clusters=[0, 3, 5, 4, 258],
                # output_clusters=[])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            12: {
                # Window Cover 1
                # SizePrefixedSimpleDescriptor(endpoint=12,
                # profile=260, device_type=514,
                # device_version=1,
                # input_clusters=[0, 3, 5, 4, 258],
                # output_clusters=[])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                # SizePrefixedSimpleDescriptor(endpoint=242,
                # profile=41440, device_type=97,
                # device_version=0,
                # input_clusters=[],
                # output_clusters=[33])
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    ZigfredCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
            },
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
            },
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
            },
            10: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
            },
            11: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    WindowCovering.cluster_id,
                ],
            },
            12: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    WindowCovering.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{SHORT_PRESS}"},
        (SHORT_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{SHORT_PRESS}"},
        (SHORT_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{SHORT_PRESS}"},
        (SHORT_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_{SHORT_PRESS}"},
        (DOUBLE_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{DOUBLE_PRESS}"},
        (DOUBLE_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{DOUBLE_PRESS}"},
        (DOUBLE_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{DOUBLE_PRESS}"},
        (DOUBLE_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_{DOUBLE_PRESS}"},
        (LONG_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{LONG_PRESS}"},
        (LONG_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{LONG_PRESS}"},
        (LONG_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{LONG_PRESS}"},
        (LONG_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_{LONG_PRESS}"},
        (LONG_RELEASE, BUTTON_1): {COMMAND: f"{BUTTON_1}_{LONG_RELEASE}"},
        (LONG_RELEASE, BUTTON_2): {COMMAND: f"{BUTTON_2}_{LONG_RELEASE}"},
        (LONG_RELEASE, BUTTON_3): {COMMAND: f"{BUTTON_3}_{LONG_RELEASE}"},
        (LONG_RELEASE, BUTTON_4): {COMMAND: f"{BUTTON_4}_{LONG_RELEASE}"},
    }
