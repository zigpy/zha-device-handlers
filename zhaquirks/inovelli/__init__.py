"""Module for Inovelli quirks implementations."""

import logging
from typing import Any, Optional, Union

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    ZCLAttributeDef,
    ZCLCommandDef,
    ZCLHeader,
)

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

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        dimming_speed_up_remote = ZCLAttributeDef(
            id=0x0001,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        ramp_rate_off_to_on_remote = ZCLAttributeDef(
            id=0x0003,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        dimming_speed_down_remote = ZCLAttributeDef(
            id=0x0005,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        ramp_rate_on_to_off_remote = ZCLAttributeDef(
            id=0x0007,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        minimum_level = ZCLAttributeDef(
            id=0x0009,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        maximum_level = ZCLAttributeDef(
            id=0x000A,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        auto_off_timer = ZCLAttributeDef(
            id=0x000C,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        default_level_remote = ZCLAttributeDef(
            id=0x000E,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        state_after_power_restored = ZCLAttributeDef(
            id=0x000F,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        power_type = ZCLAttributeDef(
            id=0x0015,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        internal_temp_monitor = ZCLAttributeDef(
            id=0x0020,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        overheated = ZCLAttributeDef(
            id=0x0021,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        smart_bulb_mode = ZCLAttributeDef(
            id=0x0034,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        led_color_when_on = ZCLAttributeDef(
            id=0x005F,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_intensity_when_on = ZCLAttributeDef(
            id=0x0061,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        remote_protection = ZCLAttributeDef(
            id=0x0101,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        output_mode = ZCLAttributeDef(
            id=0x0102,
            type=t.Bool,
            is_manufacturer_specific=True,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        button_event = ZCLCommandDef(
            id=0x00,
            schema={"button_pressed": t.uint8_t, "press_type": t.uint8_t},
            is_manufacturer_specific=True,
        )
        led_effect = ZCLCommandDef(
            id=0x01,
            schema={
                "led_effect": t.uint8_t,
                "led_color": t.uint8_t,
                "led_level": t.uint8_t,
                "led_duration": t.uint8_t,
            },
            is_manufacturer_specific=True,
        )
        reset_energy_meter = ZCLCommandDef(
            id=0x02,
            schema={},
            is_manufacturer_specific=True,
        )
        individual_led_effect = ZCLCommandDef(
            id=0x03,
            schema={
                "led_number": t.uint8_t,
                "led_effect": t.uint8_t,
                "led_color": t.uint8_t,
                "led_level": t.uint8_t,
                "led_duration": t.uint8_t,
            },
            is_manufacturer_specific=True,
        )
        led_effect_complete = ZCLCommandDef(
            id=0x24,
            schema={
                "notification_type": t.uint8_t,
            },
            is_manufacturer_specific=True,
        )

    def handle_cluster_request(
        self,
        hdr: ZCLHeader,
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
        if hdr.command_id == self.ServerCommandDefs.button_event.id:
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
        if hdr.command_id == self.ServerCommandDefs.led_effect_complete.id:
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


class InovelliVZM30SNCluster(InovelliCluster):
    """Inovelli VZM30-SN custom cluster."""

    name = "InovelliVZM30SNCluster"

    class AttributeDefs(InovelliCluster.AttributeDefs):
        """Attribute definitions."""

        dimming_speed_up_local = ZCLAttributeDef(
            id=0x0002,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        ramp_rate_off_to_on_local = ZCLAttributeDef(
            id=0x0004,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        dimming_speed_down_local = ZCLAttributeDef(
            id=0x0006,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        ramp_rate_on_to_off_local = ZCLAttributeDef(
            id=0x0008,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        invert_switch = ZCLAttributeDef(
            id=0x000B,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        default_level_local = ZCLAttributeDef(
            id=0x000D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        load_level_indicator_timeout = ZCLAttributeDef(
            id=0x0011,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        active_power_reports = ZCLAttributeDef(
            id=0x0012,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        periodic_power_and_energy_reports = ZCLAttributeDef(
            id=0x0013,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        active_energy_reports = ZCLAttributeDef(
            id=0x0014,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        switch_type = ZCLAttributeDef(
            id=0x0016,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        increased_non_neutral_output = ZCLAttributeDef(
            id=0x0019,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        leading_or_trailing_edge = ZCLAttributeDef(
            id=0x001A,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        button_delay = ZCLAttributeDef(
            id=0x0032,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        device_bind_number = ZCLAttributeDef(
            id=0x0033,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        double_tap_up_enabled = ZCLAttributeDef(
            id=0x0035,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        double_tap_down_enabled = ZCLAttributeDef(
            id=0x0036,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        double_tap_up_level = ZCLAttributeDef(
            id=0x0037,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        double_tap_down_level = ZCLAttributeDef(
            id=0x0038,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_color_when_on = ZCLAttributeDef(
            id=0x003C,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_color_when_off = ZCLAttributeDef(
            id=0x003D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_intensity_when_on = ZCLAttributeDef(
            id=0x003E,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_intensity_when_off = ZCLAttributeDef(
            id=0x003F,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_color_when_on = ZCLAttributeDef(
            id=0x0041,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_color_when_off = ZCLAttributeDef(
            id=0x0042,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0043,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0044,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_color_when_on = ZCLAttributeDef(
            id=0x0046,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_color_when_off = ZCLAttributeDef(
            id=0x0047,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0048,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0049,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_color_when_on = ZCLAttributeDef(
            id=0x004B,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_color_when_off = ZCLAttributeDef(
            id=0x004C,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_intensity_when_on = ZCLAttributeDef(
            id=0x004D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_intensity_when_off = ZCLAttributeDef(
            id=0x004E,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_color_when_on = ZCLAttributeDef(
            id=0x0050,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_color_when_off = ZCLAttributeDef(
            id=0x0051,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0052,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0053,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_color_when_on = ZCLAttributeDef(
            id=0x0055,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_color_when_off = ZCLAttributeDef(
            id=0x0056,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0057,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0058,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_color_when_on = ZCLAttributeDef(
            id=0x005A,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_color_when_off = ZCLAttributeDef(
            id=0x005B,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_intensity_when_on = ZCLAttributeDef(
            id=0x005C,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_intensity_when_off = ZCLAttributeDef(
            id=0x005D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_color_when_off = ZCLAttributeDef(
            id=0x0060,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_intensity_when_off = ZCLAttributeDef(
            id=0x0062,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_scaling_mode = ZCLAttributeDef(
            id=0x0064,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        fan_single_tap_behavior = ZCLAttributeDef(
            id=0x0078,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        fan_timer_display = ZCLAttributeDef(
            id=0x0079,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        aux_switch_scenes = ZCLAttributeDef(
            id=0x007B,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        binding_off_to_on_sync_level = ZCLAttributeDef(
            id=0x007D,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        fan_module_binding_control = ZCLAttributeDef(
            id=0x0082,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        low_for_bound_control = ZCLAttributeDef(
            id=0x0083,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        medium_for_bound_control = ZCLAttributeDef(
            id=0x0084,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        high_for_bound_control = ZCLAttributeDef(
            id=0x0085,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_color_for_bound_control = ZCLAttributeDef(
            id=0x0086,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        local_protection = ZCLAttributeDef(
            id=0x0100,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        on_off_led_mode = ZCLAttributeDef(
            id=0x0103,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        firmware_progress_led = ZCLAttributeDef(
            id=0x0104,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        relay_click_in_on_off_mode = ZCLAttributeDef(
            id=0x0105,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        disable_clear_notifications_double_tap = ZCLAttributeDef(
            id=0x0106,
            type=t.Bool,
            is_manufacturer_specific=True,
        )


class InovelliVZM31SNCluster(InovelliCluster):
    """Inovelli VZM31-SN custom cluster."""

    name = "InovelliVZM31SNCluster"

    class AttributeDefs(InovelliCluster.AttributeDefs):
        """Attribute definitions."""

        dimming_speed_up_local = ZCLAttributeDef(
            id=0x0002,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        ramp_rate_off_to_on_local = ZCLAttributeDef(
            id=0x0004,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        dimming_speed_down_local = ZCLAttributeDef(
            id=0x0006,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        ramp_rate_on_to_off_local = ZCLAttributeDef(
            id=0x0008,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        invert_switch = ZCLAttributeDef(
            id=0x000B,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        default_level_local = ZCLAttributeDef(
            id=0x000D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        load_level_indicator_timeout = ZCLAttributeDef(
            id=0x0011,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        active_power_reports = ZCLAttributeDef(
            id=0x0012,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        periodic_power_and_energy_reports = ZCLAttributeDef(
            id=0x0013,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        active_energy_reports = ZCLAttributeDef(
            id=0x0014,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        switch_type = ZCLAttributeDef(
            id=0x0016,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        quick_start_time = ZCLAttributeDef(
            id=0x0017,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        quick_start_level = ZCLAttributeDef(
            id=0x0018,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        increased_non_neutral_output = ZCLAttributeDef(
            id=0x0019,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        leading_or_trailing_edge = ZCLAttributeDef(
            id=0x001A,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        button_delay = ZCLAttributeDef(
            id=0x0032,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        device_bind_number = ZCLAttributeDef(
            id=0x0033,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        double_tap_up_enabled = ZCLAttributeDef(
            id=0x0035,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        double_tap_down_enabled = ZCLAttributeDef(
            id=0x0036,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        double_tap_up_level = ZCLAttributeDef(
            id=0x0037,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        double_tap_down_level = ZCLAttributeDef(
            id=0x0038,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_color_when_on = ZCLAttributeDef(
            id=0x003C,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_color_when_off = ZCLAttributeDef(
            id=0x003D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_intensity_when_on = ZCLAttributeDef(
            id=0x003E,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_intensity_when_off = ZCLAttributeDef(
            id=0x003F,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_color_when_on = ZCLAttributeDef(
            id=0x0041,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_color_when_off = ZCLAttributeDef(
            id=0x0042,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0043,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0044,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_color_when_on = ZCLAttributeDef(
            id=0x0046,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_color_when_off = ZCLAttributeDef(
            id=0x0047,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0048,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0049,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_color_when_on = ZCLAttributeDef(
            id=0x004B,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_color_when_off = ZCLAttributeDef(
            id=0x004C,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_intensity_when_on = ZCLAttributeDef(
            id=0x004D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_intensity_when_off = ZCLAttributeDef(
            id=0x004E,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_color_when_on = ZCLAttributeDef(
            id=0x0050,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_color_when_off = ZCLAttributeDef(
            id=0x0051,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0052,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0053,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_color_when_on = ZCLAttributeDef(
            id=0x0055,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_color_when_off = ZCLAttributeDef(
            id=0x0056,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0057,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0058,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_color_when_on = ZCLAttributeDef(
            id=0x005A,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_color_when_off = ZCLAttributeDef(
            id=0x005B,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_intensity_when_on = ZCLAttributeDef(
            id=0x005C,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_intensity_when_off = ZCLAttributeDef(
            id=0x005D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_color_when_off = ZCLAttributeDef(
            id=0x0060,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_intensity_when_off = ZCLAttributeDef(
            id=0x0062,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_scaling_mode = ZCLAttributeDef(
            id=0x0064,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        fan_single_tap_behavior = ZCLAttributeDef(
            id=0x0078,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        fan_timer_display = ZCLAttributeDef(
            id=0x0079,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        aux_switch_scenes = ZCLAttributeDef(
            id=0x007B,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        binding_off_to_on_sync_level = ZCLAttributeDef(
            id=0x007D,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        fan_module_binding_control = ZCLAttributeDef(
            id=0x0082,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        low_for_bound_control = ZCLAttributeDef(
            id=0x0083,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        medium_for_bound_control = ZCLAttributeDef(
            id=0x0084,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        high_for_bound_control = ZCLAttributeDef(
            id=0x0085,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_color_for_bound_control = ZCLAttributeDef(
            id=0x0086,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        local_protection = ZCLAttributeDef(
            id=0x0100,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        on_off_led_mode = ZCLAttributeDef(
            id=0x0103,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        firmware_progress_led = ZCLAttributeDef(
            id=0x0104,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        relay_click_in_on_off_mode = ZCLAttributeDef(
            id=0x0105,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        disable_clear_notifications_double_tap = ZCLAttributeDef(
            id=0x0106,
            type=t.Bool,
            is_manufacturer_specific=True,
        )


class InovelliVZM32SNCluster(InovelliCluster):
    """Inovelli VZM32-SN custom cluster."""

    name = "InovelliVZM32SNCluster"

    class AttributeDefs(InovelliCluster.AttributeDefs):
        """Attribute definitions."""

        dimming_speed_up_local = ZCLAttributeDef(
            id=0x0002,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        ramp_rate_off_to_on_local = ZCLAttributeDef(
            id=0x0004,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        dimming_speed_down_local = ZCLAttributeDef(
            id=0x0006,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        ramp_rate_on_to_off_local = ZCLAttributeDef(
            id=0x0008,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        invert_switch = ZCLAttributeDef(
            id=0x000B,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        default_level_local = ZCLAttributeDef(
            id=0x000D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        load_level_indicator_timeout = ZCLAttributeDef(
            id=0x0011,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        active_power_reports = ZCLAttributeDef(
            id=0x0012,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        periodic_power_and_energy_reports = ZCLAttributeDef(
            id=0x0013,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        active_energy_reports = ZCLAttributeDef(
            id=0x0014,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        switch_type = ZCLAttributeDef(
            id=0x0016,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        increased_non_neutral_output = ZCLAttributeDef(
            id=0x0019,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        leading_or_trailing_edge = ZCLAttributeDef(
            id=0x001A,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        button_delay = ZCLAttributeDef(
            id=0x0032,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        device_bind_number = ZCLAttributeDef(
            id=0x0033,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        double_tap_up_enabled = ZCLAttributeDef(
            id=0x0035,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        double_tap_down_enabled = ZCLAttributeDef(
            id=0x0036,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        double_tap_up_level = ZCLAttributeDef(
            id=0x0037,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        double_tap_down_level = ZCLAttributeDef(
            id=0x0038,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_color_when_on = ZCLAttributeDef(
            id=0x003C,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_color_when_off = ZCLAttributeDef(
            id=0x003D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_intensity_when_on = ZCLAttributeDef(
            id=0x003E,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_intensity_when_off = ZCLAttributeDef(
            id=0x003F,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_color_when_on = ZCLAttributeDef(
            id=0x0041,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_color_when_off = ZCLAttributeDef(
            id=0x0042,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0043,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0044,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_color_when_on = ZCLAttributeDef(
            id=0x0046,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_color_when_off = ZCLAttributeDef(
            id=0x0047,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0048,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0049,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_color_when_on = ZCLAttributeDef(
            id=0x004B,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_color_when_off = ZCLAttributeDef(
            id=0x004C,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_intensity_when_on = ZCLAttributeDef(
            id=0x004D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_intensity_when_off = ZCLAttributeDef(
            id=0x004E,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_color_when_on = ZCLAttributeDef(
            id=0x0050,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_color_when_off = ZCLAttributeDef(
            id=0x0051,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0052,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0053,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_color_when_on = ZCLAttributeDef(
            id=0x0055,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_color_when_off = ZCLAttributeDef(
            id=0x0056,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0057,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0058,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_color_when_on = ZCLAttributeDef(
            id=0x005A,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_color_when_off = ZCLAttributeDef(
            id=0x005B,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_intensity_when_on = ZCLAttributeDef(
            id=0x005C,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_intensity_when_off = ZCLAttributeDef(
            id=0x005D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_color_when_off = ZCLAttributeDef(
            id=0x0060,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_intensity_when_off = ZCLAttributeDef(
            id=0x0062,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_scaling_mode = ZCLAttributeDef(
            id=0x0064,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        light_on_presence_behavior = ZCLAttributeDef(
            id=0x006E,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        mmwave_room_size_preset = ZCLAttributeDef(
            id=0x0075,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        fan_single_tap_behavior = ZCLAttributeDef(
            id=0x0078,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        fan_timer_display = ZCLAttributeDef(
            id=0x0079,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        aux_switch_scenes = ZCLAttributeDef(
            id=0x007B,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        binding_off_to_on_sync_level = ZCLAttributeDef(
            id=0x007D,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        fan_module_binding_control = ZCLAttributeDef(
            id=0x0082,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        low_for_bound_control = ZCLAttributeDef(
            id=0x0083,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        medium_for_bound_control = ZCLAttributeDef(
            id=0x0084,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        high_for_bound_control = ZCLAttributeDef(
            id=0x0085,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_color_for_bound_control = ZCLAttributeDef(
            id=0x0086,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        local_protection = ZCLAttributeDef(
            id=0x0100,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        on_off_led_mode = ZCLAttributeDef(
            id=0x0103,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        firmware_progress_led = ZCLAttributeDef(
            id=0x0104,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        relay_click_in_on_off_mode = ZCLAttributeDef(
            id=0x0105,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        disable_clear_notifications_double_tap = ZCLAttributeDef(
            id=0x0106,
            type=t.Bool,
            is_manufacturer_specific=True,
        )


class InovelliVZM35SNCluster(InovelliCluster):
    """Inovelli VZM35-SN custom cluster."""

    name = "InovelliVZM35SNCluster"

    class AttributeDefs(InovelliCluster.AttributeDefs):
        """Attribute definitions."""

        dimming_speed_up_local = ZCLAttributeDef(
            id=0x0002,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        ramp_rate_off_to_on_local = ZCLAttributeDef(
            id=0x0004,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        dimming_speed_down_local = ZCLAttributeDef(
            id=0x0006,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        ramp_rate_on_to_off_local = ZCLAttributeDef(
            id=0x0008,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        invert_switch = ZCLAttributeDef(
            id=0x000B,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        default_level_local = ZCLAttributeDef(
            id=0x000D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        load_level_indicator_timeout = ZCLAttributeDef(
            id=0x0011,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        switch_type = ZCLAttributeDef(
            id=0x0016,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        quick_start_time = ZCLAttributeDef(
            id=0x0017,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        non_neutral_aux_med_gear_learn_value = ZCLAttributeDef(
            id=0x001E,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        non_neutral_aux_low_gear_learn_value = ZCLAttributeDef(
            id=0x001F,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        button_delay = ZCLAttributeDef(
            id=0x0032,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        device_bind_number = ZCLAttributeDef(
            id=0x0033,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        smart_fan_mode = ZCLAttributeDef(
            id=0x0034,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        double_tap_up_enabled = ZCLAttributeDef(
            id=0x0035,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        double_tap_down_enabled = ZCLAttributeDef(
            id=0x0036,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        double_tap_up_level = ZCLAttributeDef(
            id=0x0037,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        double_tap_down_level = ZCLAttributeDef(
            id=0x0038,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_color_when_on = ZCLAttributeDef(
            id=0x003C,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_color_when_off = ZCLAttributeDef(
            id=0x003D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_intensity_when_on = ZCLAttributeDef(
            id=0x003E,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led1_strip_intensity_when_off = ZCLAttributeDef(
            id=0x003F,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_color_when_on = ZCLAttributeDef(
            id=0x0041,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_color_when_off = ZCLAttributeDef(
            id=0x0042,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0043,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led2_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0044,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_color_when_on = ZCLAttributeDef(
            id=0x0046,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_color_when_off = ZCLAttributeDef(
            id=0x0047,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0048,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led3_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0049,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_color_when_on = ZCLAttributeDef(
            id=0x004B,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_color_when_off = ZCLAttributeDef(
            id=0x004C,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_intensity_when_on = ZCLAttributeDef(
            id=0x004D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led4_strip_intensity_when_off = ZCLAttributeDef(
            id=0x004E,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_color_when_on = ZCLAttributeDef(
            id=0x0050,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_color_when_off = ZCLAttributeDef(
            id=0x0051,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0052,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led5_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0053,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_color_when_on = ZCLAttributeDef(
            id=0x0055,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_color_when_off = ZCLAttributeDef(
            id=0x0056,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_intensity_when_on = ZCLAttributeDef(
            id=0x0057,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led6_strip_intensity_when_off = ZCLAttributeDef(
            id=0x0058,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_color_when_on = ZCLAttributeDef(
            id=0x005A,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_color_when_off = ZCLAttributeDef(
            id=0x005B,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_intensity_when_on = ZCLAttributeDef(
            id=0x005C,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        default_led7_strip_intensity_when_off = ZCLAttributeDef(
            id=0x005D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_color_when_off = ZCLAttributeDef(
            id=0x0060,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_intensity_when_off = ZCLAttributeDef(
            id=0x0062,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        fan_single_tap_behavior = ZCLAttributeDef(
            id=0x0078,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        fan_timer_display = ZCLAttributeDef(
            id=0x0079,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        aux_switch_scenes = ZCLAttributeDef(
            id=0x007B,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        fan_breeze_mode = ZCLAttributeDef(
            id=0x0081,
            type=t.uint32_t,
            is_manufacturer_specific=True,
        )
        fan_module_binding_control = ZCLAttributeDef(
            id=0x0082,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        low_for_bound_control = ZCLAttributeDef(
            id=0x0083,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        medium_for_bound_control = ZCLAttributeDef(
            id=0x0084,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        high_for_bound_control = ZCLAttributeDef(
            id=0x0085,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        led_color_for_bound_control = ZCLAttributeDef(
            id=0x0086,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        local_protection = ZCLAttributeDef(
            id=0x0100,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        on_off_led_mode = ZCLAttributeDef(
            id=0x0103,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        firmware_progress_led = ZCLAttributeDef(
            id=0x0104,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        disable_clear_notifications_double_tap = ZCLAttributeDef(
            id=0x0106,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        smart_fan_led_display_levels = ZCLAttributeDef(
            id=0x0107,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


class InovelliVZM36LightCluster(InovelliCluster):
    """Inovelli VZM36 Light custom cluster."""

    name = "InovelliVZM36LightCluster"

    class AttributeDefs(InovelliCluster.AttributeDefs):
        """Attribute definitions."""

        quick_start_time = ZCLAttributeDef(
            id=0x0017,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        quick_start_level = ZCLAttributeDef(
            id=0x0018,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        increased_non_neutral_output = ZCLAttributeDef(
            id=0x0019,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        leading_or_trailing_edge = ZCLAttributeDef(
            id=0x001A,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


class InovelliVZM36FanCluster(InovelliCluster):
    """Inovelli VZM36 Fan custom cluster."""

    name = "InovelliVZM36FanCluster"

    class AttributeDefs(InovelliCluster.AttributeDefs):
        """Attribute definitions."""

        quick_start_time = ZCLAttributeDef(
            id=0x0017,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        smart_fan_mode = ZCLAttributeDef(
            id=0x0034,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        breeze_mode = ZCLAttributeDef(
            id=0x0081,
            type=t.uint32_t,
            is_manufacturer_specific=True,
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
