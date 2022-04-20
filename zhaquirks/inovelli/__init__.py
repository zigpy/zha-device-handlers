"""Module for Inovelli quirks implementations."""

import logging
from typing import Any, List, Optional, Union

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster

from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_ID,
    COMMAND_PRESS,
    COMMAND_QUAD,
    COMMAND_RELEASE,
    COMMAND_TRIPLE,
    DOUBLE_PRESS,
    PRESS_TYPE,
    QUADRUPLE_PRESS,
    QUINTUPLE_PRESS,
    TRIPLE_PRESS,
    ZHA_SEND_EVENT,
)

_LOGGER = logging.getLogger(__name__)
INOVELLI_VZM31SN_CLUSTER_ID = 64561

# Press Types
# 0 - pressed
# 1 - released
# 2 - held
# 3 - 2x
# 4 - 3x
# 5 - 4x
# 6 - 5x
COMMAND_QUINTUPLE = "quintuple"
PRESS_TYPES = {
    0: COMMAND_PRESS,
    1: COMMAND_RELEASE,
    2: COMMAND_HOLD,
    3: COMMAND_DOUBLE,
    4: COMMAND_TRIPLE,
    5: COMMAND_QUAD,
    6: COMMAND_QUINTUPLE,
}

# Buttons
# 1 - down button
# 2 - up button
# 3 - config button

BUTTONS = {1: BUTTON_1, 2: BUTTON_2, 3: BUTTON_3}
ON = "Up"
OFF = "Down"
CONFIG = "Config"


class Inovelli_VZM31SN_Cluster(CustomCluster):
    """Inovelli VZM31-SN custom cluster."""

    cluster_id = 0xFC31
    name = "InovelliVZM31SNCluster"
    ep_attribute = "inovelli_vzm31sn_cluster"

    attributes = ManufacturerSpecificCluster.attributes.copy()
    attributes.update(
        {
            0x0001: ("Dimming_Speed_Up_Remote", t.uint8_t),
            0x0002: ("Dimming_Speed_Up_Local", t.uint8_t),
            0x0003: ("Ramp_Rate_Off_to_On_Local", t.uint8_t),
            0x0004: ("Ramp_Rate_Off_to_On_Remote", t.uint8_t),
            0x0005: ("Dimming_Speed_Down_Remote", t.uint8_t),
            0x0006: ("Dimming_Speed_Down_Local", t.uint8_t),
            0x0007: ("Ramp_Rate_On_to_Off_Local", t.uint8_t),
            0x0008: ("Ramp_Rate_On_to_Off_Remote", t.uint8_t),
            0x0009: ("Minimum_Level", t.uint8_t),
            0x000A: ("Maximum_Level", t.uint8_t),
            0x000B: ("Invert_Switch", t.Bool),
            0x000C: ("Auto_Off_Timer", t.uint16_t),
            0x000D: ("Default_Level_Local", t.uint8_t),
            0x000E: ("Default_Level_Remote", t.uint8_t),
            0x000F: ("State_After_Power_Restored", t.uint8_t),
            0x0011: ("Load_Level_Indicator_Timeout", t.uint8_t),
            0x0012: ("Active_Power_Reports", t.uint16_t),
            0x0013: ("Periodic_Power_and_Energy_Reports", t.uint8_t),
            0x0014: ("Active_Energy_Reports", t.uint16_t),
            0x0015: ("Power_Type", t.uint8_t),
            0x0016: ("Switch_Type", t.uint8_t),
            0x0032: ("Button_Delay", t.uint8_t),
            0x0033: ("Device_Bind_Number", t.uint8_t),
            0x003C: ("Default_LED1_Strip_Color_When_On", t.uint8_t),
            0x003D: ("Default_LED1_Strip_Color_When_Off", t.uint8_t),
            0x003E: ("Default_LED1_Strip_Intensity_When_On", t.uint8_t),
            0x003F: ("Default_LED1_Strip_Intensity_When_Off", t.uint8_t),
            0x0041: ("Default_LED2_Strip_Color_When_On", t.uint8_t),
            0x0042: ("Default_LED2_Strip_Color_When_Off", t.uint8_t),
            0x0043: ("Default_LED2_Strip_Intensity_When_On", t.uint8_t),
            0x0044: ("Default_LED2_Strip_Intensity_When_Off", t.uint8_t),
            0x0046: ("Default_LED3_Strip_Color_When_On", t.uint8_t),
            0x0047: ("Default_LED3_Strip_Color_When_Off", t.uint8_t),
            0x0048: ("Default_LED3_Strip_Intensity_When_On", t.uint8_t),
            0x0049: ("Default_LED3_Strip_Intensity_When_Off", t.uint8_t),
            0x004B: ("Default_LED4_Strip_Color_When_On", t.uint8_t),
            0x004C: ("Default_LED4_Strip_Color_When_Off", t.uint8_t),
            0x004D: ("Default_LED4_Strip_Intensity_When_On", t.uint8_t),
            0x004E: ("Default_LED4_Strip_Intensity_When_Off", t.uint8_t),
            0x0050: ("Default_LED5_Strip_Color_When_On", t.uint8_t),
            0x0051: ("Default_LED5_Strip_Color_When_Off", t.uint8_t),
            0x0052: ("Default_LED5_Strip_Intensity_When_On", t.uint8_t),
            0x0053: ("Default_LED5_Strip_Intensity_When_Off", t.uint8_t),
            0x0055: ("Default_LED6_Strip_Color_When_On", t.uint8_t),
            0x0056: ("Default_LED6_Strip_Color_When_Off", t.uint8_t),
            0x0057: ("Default_LED6_Strip_Intensity_When_On", t.uint8_t),
            0x0058: ("Default_LED6_Strip_Intensity_When_Off", t.uint8_t),
            0x005A: ("Default_LED7_Strip_Color_When_On", t.uint8_t),
            0x005B: ("Default_LED7_Strip_Color_When_Off", t.uint8_t),
            0x005C: ("Default_LED7_Strip_Intensity_When_On", t.uint8_t),
            0x005D: ("Default_LED7_Strip_Intensity_When_Off", t.uint8_t),
            0x0034: ("Smart_Bulb_Mode", t.Bool),
            0x0035: ("Double_Tap_Up_for_Full_Brightness", t.Bool),
            0x005F: ("LED_Color_When_On", t.uint8_t),
            0x0060: ("LED_Color_When_Off", t.uint8_t),
            0x0061: ("LED_Intensity_When_On", t.uint8_t),
            0x0062: ("LED_Intensity_When_Off", t.uint8_t),
            0x0100: ("Local_Protection", t.Bool),
            0x0101: ("Remote_Protection", t.Bool),
            0x0102: ("Output_Mode", t.Bool),
            0x0103: ("On_Off_LED_Mode", t.Bool),
            0x0104: ("Firmware_Progress_LED", t.Bool),
        }
    )

    server_commands = {
        0x00: ("button_event", (t.uint8_t, t.uint8_t), False),
        0x01: (
            "led_effect",
            (t.uint8_t, t.uint8_t, t.uint8_t, t.uint8_t),
            False,
        ),  # LED Effect
        0x03: (
            "individual_led_effect",
            (t.uint8_t, t.uint8_t, t.uint8_t, t.uint8_t, t.uint8_t),
            False,
        ),  # individual LED Effect
    }

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle a cluster request."""
        _LOGGER.debug(
            "%s: handle_cluster_request - Command: %s Data: %s",
            self.name,
            hdr.command_id,
            args,
        )
        if hdr.command_id == 0x00:

            button = BUTTONS.get(args[0])
            press_type = PRESS_TYPES.get(args[1])
            action = f"{button}_{press_type}"

            event_args = {
                BUTTON: button,
                PRESS_TYPE: press_type,
                COMMAND_ID: hdr.command_id,
            }

            self.listener_event(ZHA_SEND_EVENT, action, event_args)
            return


INOVELLI_AUTOMATION_TRIGGERS = {
    (COMMAND_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_PRESS}"},
    (COMMAND_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_PRESS}"},
    (COMMAND_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_PRESS}"},
    (COMMAND_HOLD, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_HOLD}"},
    (COMMAND_HOLD, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_HOLD}"},
    (DOUBLE_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_DOUBLE}"},
    (DOUBLE_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_DOUBLE}"},
    (DOUBLE_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_DOUBLE}"},
    (TRIPLE_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_TRIPLE}"},
    (TRIPLE_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_TRIPLE}"},
    (TRIPLE_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_TRIPLE}"},
    (QUADRUPLE_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_QUAD}"},
    (QUADRUPLE_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_QUAD}"},
    (QUADRUPLE_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_QUAD}"},
    (QUINTUPLE_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_QUINTUPLE}"},
    (QUINTUPLE_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_QUINTUPLE}"},
    (QUINTUPLE_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_QUINTUPLE}"},
    (COMMAND_RELEASE, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_RELEASE}"},
    (COMMAND_RELEASE, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_RELEASE}"},
}
