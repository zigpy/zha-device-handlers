"""Module for Inovelli quirks implementations."""

import logging
from typing import Any, Optional, Union

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
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

LED_NOTIFICATION_TYPES = {
    0: "LED_1",
    1: "LED_2",
    2: "LED_3",
    3: "LED_4",
    4: "LED_5",
    5: "LED_6",
    6: "LED_7",
    16: "ALL_LEDS",
    255: "CONFIG_BUTTON_DOUBLE_PRESS",
}

# Buttons
# 1 - down button
# 2 - up button
# 3 - config button
# 4 - aux down button
# 5 - aux up button
# 6 - aux config button

BUTTONS = {1: BUTTON_1, 2: BUTTON_2, 3: BUTTON_3, 4: BUTTON_4, 5: BUTTON_5, 6: BUTTON_6}
ON = "Up"
OFF = "Down"
CONFIG = "Config"
AUX_ON = "Aux up"
AUX_OFF = "Aux down"
AUX_CONFIG = "Aux config"

NOTIFICATION_TYPE = "notification_type"


class InovelliCluster(CustomCluster):
    """Inovelli base cluster."""

    cluster_id = 0xFC31
    ep_attribute = "inovelli_vzm31sn_cluster"

    attributes = {
        0x0001: ("dimming_speed_up_remote", t.uint8_t, True),
        0x0003: ("ramp_rate_off_to_on_remote", t.uint8_t, True),
        0x0005: ("dimming_speed_down_remote", t.uint8_t, True),
        0x0007: ("ramp_rate_on_to_off_remote", t.uint8_t, True),
        0x0009: ("minimum_level", t.uint8_t, True),
        0x000A: ("maximum_level", t.uint8_t, True),
        0x000C: ("auto_off_timer", t.uint16_t, True),
        0x000E: ("default_level_remote", t.uint8_t, True),
        0x000F: ("state_after_power_restored", t.uint8_t, True),
        0x0015: ("power_type", t.uint8_t, True),
        0x0020: ("internal_temp_monitor", t.uint8_t, True),
        0x0021: ("overheated", t.Bool, True),
        0x0034: ("smart_bulb_mode", t.Bool, True),
        0x005F: ("led_color_when_on", t.uint8_t, True),
        0x0061: ("led_intensity_when_on", t.uint8_t, True),
        0x0101: ("remote_protection", t.Bool, True),
        0x0102: ("output_mode", t.Bool, True),
    }

    server_commands = {
        0x00: foundation.ZCLCommandDef(
            "button_event",
            {"button_pressed": t.uint8_t, "press_type": t.uint8_t},
            direction=foundation.Direction.Client_to_Server,
            is_manufacturer_specific=True,
        ),
        0x01: foundation.ZCLCommandDef(
            "led_effect",
            {
                "led_effect": t.uint8_t,
                "led_color": t.uint8_t,
                "led_level": t.uint8_t,
                "led_duration": t.uint8_t,
            },
            direction=foundation.Direction.Client_to_Server,
            is_manufacturer_specific=True,
        ),
        0x02: foundation.ZCLCommandDef(
            "reset_energy_meter",
            {},
            direction=foundation.Direction.Client_to_Server,
            is_manufacturer_specific=True,
        ),
        0x03: foundation.ZCLCommandDef(
            "individual_led_effect",
            {
                "led_number": t.uint8_t,
                "led_effect": t.uint8_t,
                "led_color": t.uint8_t,
                "led_level": t.uint8_t,
                "led_duration": t.uint8_t,
            },
            direction=foundation.Direction.Client_to_Server,
            is_manufacturer_specific=True,
        ),
        0x24: foundation.ZCLCommandDef(
            "led_effect_complete",
            {
                "notification_type": t.uint8_t,
            },
            direction=foundation.Direction.Client_to_Server,
            is_manufacturer_specific=True,
        ),
    }

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
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
        if hdr.command_id == self.commands_by_name["button_event"].id:
            button = BUTTONS[args.button_pressed]
            press_type = PRESS_TYPES[args.press_type]
            action = f"{button}_{press_type}"
            event_args = {
                BUTTON: button,
                PRESS_TYPE: press_type,
                COMMAND_ID: hdr.command_id,
            }
            self.listener_event(ZHA_SEND_EVENT, action, event_args)
            return
        if hdr.command_id == self.commands_by_name["led_effect_complete"].id:
            notification_type = LED_NOTIFICATION_TYPES.get(
                args.notification_type, "unknown"
            )
            action = f"led_effect_complete_{notification_type}"
            event_args = {
                NOTIFICATION_TYPE: notification_type,
                COMMAND_ID: hdr.command_id,
            }
            self.listener_event(ZHA_SEND_EVENT, action, event_args)
            return


class InovelliVZM31SNCluster(InovelliCluster):
    """Inovelli VZM31-SN custom cluster."""

    name = "InovelliVZM31SNCluster"

    attributes = InovelliCluster.attributes.copy()
    attributes.update(
        {
            0x0002: ("dimming_speed_up_local", t.uint8_t, True),
            0x0004: ("ramp_rate_off_to_on_local", t.uint8_t, True),
            0x0006: ("dimming_speed_down_local", t.uint8_t, True),
            0x0008: ("ramp_rate_on_to_off_local", t.uint8_t, True),
            0x000B: ("invert_switch", t.Bool, True),
            0x000D: ("default_level_local", t.uint8_t, True),
            0x0011: ("load_level_indicator_timeout", t.uint8_t, True),
            0x0012: ("active_power_reports", t.uint8_t, True),
            0x0013: ("periodic_power_and_energy_reports", t.uint8_t, True),
            0x0014: ("active_energy_reports", t.uint16_t, True),
            0x0016: ("switch_type", t.uint8_t, True),
            0x0019: ("increased_non_neutral_output", t.Bool, True),
            0x001A: ("leading_or_trailing_edge", t.Bool, True),
            0x0032: ("button_delay", t.uint8_t, True),
            0x0033: ("device_bind_number", t.uint8_t, True),
            0x0035: ("double_tap_up_enabled", t.Bool, True),
            0x0036: ("double_tap_down_enabled", t.Bool, True),
            0x0037: ("double_tap_up_level", t.uint8_t, True),
            0x0038: ("double_tap_down_level", t.uint8_t, True),
            0x003C: ("default_led1_strip_color_when_on", t.uint8_t, True),
            0x003D: ("default_led1_strip_color_when_off", t.uint8_t, True),
            0x003E: ("default_led1_strip_intensity_when_on", t.uint8_t, True),
            0x003F: ("default_led1_strip_intensity_when_off", t.uint8_t, True),
            0x0041: ("default_led2_strip_color_when_on", t.uint8_t, True),
            0x0042: ("default_led2_strip_color_when_off", t.uint8_t, True),
            0x0043: ("default_led2_strip_intensity_when_on", t.uint8_t, True),
            0x0044: ("default_led2_strip_intensity_when_off", t.uint8_t, True),
            0x0046: ("default_led3_strip_color_when_on", t.uint8_t, True),
            0x0047: ("default_led3_strip_color_when_off", t.uint8_t, True),
            0x0048: ("default_led3_strip_intensity_when_on", t.uint8_t, True),
            0x0049: ("default_led3_strip_intensity_when_off", t.uint8_t, True),
            0x004B: ("default_led4_strip_color_when_on", t.uint8_t, True),
            0x004C: ("default_led4_strip_color_when_off", t.uint8_t, True),
            0x004D: ("default_led4_strip_intensity_when_on", t.uint8_t, True),
            0x004E: ("default_led4_strip_intensity_when_off", t.uint8_t, True),
            0x0050: ("default_led5_strip_color_when_on", t.uint8_t, True),
            0x0051: ("default_led5_strip_color_when_off", t.uint8_t, True),
            0x0052: ("default_led5_strip_intensity_when_on", t.uint8_t, True),
            0x0053: ("default_led5_strip_intensity_when_off", t.uint8_t, True),
            0x0055: ("default_led6_strip_color_when_on", t.uint8_t, True),
            0x0056: ("default_led6_strip_color_when_off", t.uint8_t, True),
            0x0057: ("default_led6_strip_intensity_when_on", t.uint8_t, True),
            0x0058: ("default_led6_strip_intensity_when_off", t.uint8_t, True),
            0x005A: ("default_led7_strip_color_when_on", t.uint8_t, True),
            0x005B: ("default_led7_strip_color_when_off", t.uint8_t, True),
            0x005C: ("default_led7_strip_intensity_when_on", t.uint8_t, True),
            0x005D: ("default_led7_strip_intensity_when_off", t.uint8_t, True),
            0x0060: ("led_color_when_off", t.uint8_t, True),
            0x0062: ("led_intensity_when_off", t.uint8_t, True),
            0x0064: ("led_scaling_mode", t.Bool, True),
            0x0078: ("fan_single_tap_behavior", t.uint8_t, True),
            0x0079: ("fan_timer_display", t.Bool, True),
            0x007B: ("aux_switch_scenes", t.Bool, True),
            0x007D: ("binding_off_to_on_sync_level", t.Bool, True),
            0x0082: ("fan_module_binding_control", t.uint8_t, True),
            0x0083: ("low_for_bound_control", t.uint8_t, True),
            0x0084: ("medium_for_bound_control", t.uint8_t, True),
            0x0085: ("high_for_bound_control", t.uint8_t, True),
            0x0086: ("led_color_for_bound_control", t.uint8_t, True),
            0x0100: ("local_protection", t.Bool, True),
            0x0103: ("on_off_led_mode", t.Bool, True),
            0x0104: ("firmware_progress_led", t.Bool, True),
            0x0105: ("relay_click_in_on_off_mode", t.Bool, True),
            0x0106: ("disable_clear_notifications_double_tap", t.Bool, True),
        }
    )


class InovelliVZM35SNCluster(InovelliCluster):
    """Inovelli VZM35-SN custom cluster."""

    name = "InovelliVZM35SNCluster"

    attributes = InovelliCluster.attributes.copy()
    attributes.update(
        {
            0x0002: ("dimming_speed_up_local", t.uint8_t, True),
            0x0004: ("ramp_rate_off_to_on_local", t.uint8_t, True),
            0x0006: ("dimming_speed_down_local", t.uint8_t, True),
            0x0008: ("ramp_rate_on_to_off_local", t.uint8_t, True),
            0x000B: ("invert_switch", t.Bool, True),
            0x000D: ("default_level_local", t.uint8_t, True),
            0x0011: ("load_level_indicator_timeout", t.uint8_t, True),
            0x0016: ("switch_type", t.uint8_t, True),
            0x0017: ("quick_start_time", t.uint8_t, True),
            0x001E: ("non_neutral_aux_med_gear_learn_value", t.uint8_t, True),
            0x001F: ("non_neutral_aux_low_gear_learn_value", t.uint8_t, True),
            0x0032: ("button_delay", t.uint8_t, True),
            0x0033: ("device_bind_number", t.uint8_t, True),
            0x0034: ("smart_fan_mode", t.Bool, True),
            0x0035: ("double_tap_up_enabled", t.Bool, True),
            0x0036: ("double_tap_down_enabled", t.Bool, True),
            0x0037: ("double_tap_up_level", t.uint8_t, True),
            0x0038: ("double_tap_down_level", t.uint8_t, True),
            0x003C: ("default_led1_strip_color_when_on", t.uint8_t, True),
            0x003D: ("default_led1_strip_color_when_off", t.uint8_t, True),
            0x003E: ("default_led1_strip_intensity_when_on", t.uint8_t, True),
            0x003F: ("default_led1_strip_intensity_when_off", t.uint8_t, True),
            0x0041: ("default_led2_strip_color_when_on", t.uint8_t, True),
            0x0042: ("default_led2_strip_color_when_off", t.uint8_t, True),
            0x0043: ("default_led2_strip_intensity_when_on", t.uint8_t, True),
            0x0044: ("default_led2_strip_intensity_when_off", t.uint8_t, True),
            0x0046: ("default_led3_strip_color_when_on", t.uint8_t, True),
            0x0047: ("default_led3_strip_color_when_off", t.uint8_t, True),
            0x0048: ("default_led3_strip_intensity_when_on", t.uint8_t, True),
            0x0049: ("default_led3_strip_intensity_when_off", t.uint8_t, True),
            0x004B: ("default_led4_strip_color_when_on", t.uint8_t, True),
            0x004C: ("default_led4_strip_color_when_off", t.uint8_t, True),
            0x004D: ("default_led4_strip_intensity_when_on", t.uint8_t, True),
            0x004E: ("default_led4_strip_intensity_when_off", t.uint8_t, True),
            0x0050: ("default_led5_strip_color_when_on", t.uint8_t, True),
            0x0051: ("default_led5_strip_color_when_off", t.uint8_t, True),
            0x0052: ("default_led5_strip_intensity_when_on", t.uint8_t, True),
            0x0053: ("default_led5_strip_intensity_when_off", t.uint8_t, True),
            0x0055: ("default_led6_strip_color_when_on", t.uint8_t, True),
            0x0056: ("default_led6_strip_color_when_off", t.uint8_t, True),
            0x0057: ("default_led6_strip_intensity_when_on", t.uint8_t, True),
            0x0058: ("default_led6_strip_intensity_when_off", t.uint8_t, True),
            0x005A: ("default_led7_strip_color_when_on", t.uint8_t, True),
            0x005B: ("default_led7_strip_color_when_off", t.uint8_t, True),
            0x005C: ("default_led7_strip_intensity_when_on", t.uint8_t, True),
            0x005D: ("default_led7_strip_intensity_when_off", t.uint8_t, True),
            0x0060: ("led_color_when_off", t.uint8_t, True),
            0x0062: ("led_intensity_when_off", t.uint8_t, True),
            0x0078: ("fan_single_tap_behavior", t.uint8_t, True),
            0x0079: ("fan_timer_display", t.Bool, True),
            0x007B: ("aux_switch_scenes", t.Bool, True),
            0x0081: ("fan_breeze_mode", t.uint32_t, True),
            0x0082: ("fan_module_binding_control", t.uint8_t, True),
            0x0083: ("low_for_bound_control", t.uint8_t, True),
            0x0084: ("medium_for_bound_control", t.uint8_t, True),
            0x0085: ("high_for_bound_control", t.uint8_t, True),
            0x0086: ("led_color_for_bound_control", t.uint8_t, True),
            0x0100: ("local_protection", t.Bool, True),
            0x0103: ("on_off_led_mode", t.Bool, True),
            0x0104: ("firmware_progress_led", t.Bool, True),
            0x0106: ("disable_clear_notifications_double_tap", t.Bool, True),
            0x0107: ("smart_fan_led_display_levels", t.uint8_t, True),
        }
    )


class InovelliVZM36LightCluster(InovelliCluster):
    """Inovelli VZM36 Light custom cluster."""

    name = "InovelliVZM36LightCluster"

    attributes = InovelliCluster.attributes.copy()
    attributes.update(
        {
            0x0017: ("quick_start_time", t.uint8_t, True),
            0x0018: ("quick_start_level", t.uint8_t, True),
            0x0019: ("increased_non_neutral_output", t.Bool, True),
        }
    )


class InovelliVZM36FanCluster(InovelliCluster):
    """Inovelli VZM36 Fan custom cluster."""

    name = "InovelliVZM36FanCluster"

    attributes = InovelliCluster.attributes.copy()
    attributes.update(
        {
            0x0017: ("quick_start_time", t.uint8_t, True),
            0x0034: ("smart_fan_mode", t.Bool, True),
            0x0081: ("breeze_mode", t.uint32_t, True),
        }
    )


INOVELLI_AUTOMATION_TRIGGERS = {
    (COMMAND_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_PRESS}"},
    (COMMAND_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_PRESS}"},
    (COMMAND_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_PRESS}"},
    (COMMAND_PRESS, AUX_ON): {COMMAND: f"{BUTTON_5}_{COMMAND_PRESS}"},
    (COMMAND_PRESS, AUX_OFF): {COMMAND: f"{BUTTON_4}_{COMMAND_PRESS}"},
    (COMMAND_PRESS, AUX_CONFIG): {COMMAND: f"{BUTTON_6}_{COMMAND_PRESS}"},
    (COMMAND_HOLD, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_HOLD}"},
    (COMMAND_HOLD, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_HOLD}"},
    (COMMAND_HOLD, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_HOLD}"},
    (COMMAND_HOLD, AUX_ON): {COMMAND: f"{BUTTON_5}_{COMMAND_HOLD}"},
    (COMMAND_HOLD, AUX_OFF): {COMMAND: f"{BUTTON_4}_{COMMAND_HOLD}"},
    (COMMAND_HOLD, AUX_CONFIG): {COMMAND: f"{BUTTON_6}_{COMMAND_HOLD}"},
    (DOUBLE_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_DOUBLE}"},
    (DOUBLE_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_DOUBLE}"},
    (DOUBLE_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_DOUBLE}"},
    (DOUBLE_PRESS, AUX_ON): {COMMAND: f"{BUTTON_5}_{COMMAND_DOUBLE}"},
    (DOUBLE_PRESS, AUX_CONFIG): {COMMAND: f"{BUTTON_6}_{COMMAND_DOUBLE}"},
    (DOUBLE_PRESS, AUX_OFF): {COMMAND: f"{BUTTON_4}_{COMMAND_DOUBLE}"},
    (TRIPLE_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_TRIPLE}"},
    (TRIPLE_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_TRIPLE}"},
    (TRIPLE_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_TRIPLE}"},
    (TRIPLE_PRESS, AUX_ON): {COMMAND: f"{BUTTON_5}_{COMMAND_TRIPLE}"},
    (TRIPLE_PRESS, AUX_CONFIG): {COMMAND: f"{BUTTON_6}_{COMMAND_TRIPLE}"},
    (TRIPLE_PRESS, AUX_OFF): {COMMAND: f"{BUTTON_4}_{COMMAND_TRIPLE}"},
    (QUADRUPLE_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_QUAD}"},
    (QUADRUPLE_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_QUAD}"},
    (QUADRUPLE_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_QUAD}"},
    (QUADRUPLE_PRESS, AUX_ON): {COMMAND: f"{BUTTON_5}_{COMMAND_QUAD}"},
    (QUADRUPLE_PRESS, AUX_CONFIG): {COMMAND: f"{BUTTON_6}_{COMMAND_QUAD}"},
    (QUADRUPLE_PRESS, AUX_OFF): {COMMAND: f"{BUTTON_4}_{COMMAND_QUAD}"},
    (QUINTUPLE_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_QUINTUPLE}"},
    (QUINTUPLE_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_QUINTUPLE}"},
    (QUINTUPLE_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_QUINTUPLE}"},
    (QUINTUPLE_PRESS, AUX_ON): {COMMAND: f"{BUTTON_5}_{COMMAND_QUINTUPLE}"},
    (QUINTUPLE_PRESS, AUX_OFF): {COMMAND: f"{BUTTON_4}_{COMMAND_QUINTUPLE}"},
    (QUINTUPLE_PRESS, AUX_CONFIG): {COMMAND: f"{BUTTON_6}_{COMMAND_QUINTUPLE}"},
    (COMMAND_RELEASE, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_RELEASE}"},
    (COMMAND_RELEASE, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_RELEASE}"},
    (COMMAND_RELEASE, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_RELEASE}"},
    (COMMAND_RELEASE, AUX_ON): {COMMAND: f"{BUTTON_5}_{COMMAND_RELEASE}"},
    (COMMAND_RELEASE, AUX_OFF): {COMMAND: f"{BUTTON_4}_{COMMAND_RELEASE}"},
    (COMMAND_RELEASE, AUX_CONFIG): {COMMAND: f"{BUTTON_6}_{COMMAND_RELEASE}"},
}
