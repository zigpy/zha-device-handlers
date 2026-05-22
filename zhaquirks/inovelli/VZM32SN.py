"""VZM32-SN MMwave Switch/Dimmer Module with explicit entity declarations."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType
import zigpy.types as t

from zhaquirks.inovelli import (
    INOVELLI_AUTOMATION_TRIGGERS,
    InovelliVZM32SNCluster,
    InovelliVZM32SNMMWaveCluster,
)


class InovelliOutputMode(t.enum1):
    """Inovelli output mode."""

    Dimmer = 0x00
    OnOff = 0x01


class InovelliLedScalingMode(t.enum1):
    """Inovelli LED scaling mode."""

    VZM31SN = 0x00
    LZW31SN = 0x01


class InovelliNonNeutralOutput(t.enum1):
    """Inovelli non-neutral output selection."""

    Low = 0x00
    High = 0x01


class InovelliVZM32SwitchType(t.enum8):
    """Inovelli VZM32-SN switch type."""

    Single_Pole = 0x00
    Three_Way_AUX = 0x01


class InovelliMmwaveRoomSizePreset(t.enum8):
    """Inovelli mmWave room size preset."""

    Custom = 0x00
    X_Small = 0x01
    Small = 0x02
    Medium = 0x03
    Large = 0x04
    X_Large = 0x05


class InovelliLightOnPresenceBehavior(t.enum8):
    """Inovelli light on presence behavior."""

    Disabled = 0x00
    On_When_Occupied_Off_When_Unoccupied = 0x01
    Off_When_Vacant = 0x02
    On_When_Occupied = 0x03
    On_When_Vacant_Off_When_Occupied = 0x04
    On_When_Vacant = 0x05
    Off_When_Occupied = 0x06


class InovelliMmwaveSensitivity(t.enum8):
    """Inovelli mmWave sensitivity."""

    Low = 0x00
    Medium = 0x01
    High = 0x02


class InovelliMmwaveTargetSpeed(t.enum8):
    """Inovelli mmWave target speed."""

    Low = 0x00
    Medium = 0x01
    Fast = 0x02


(
    QuirkBuilder("Inovelli", "VZM32-SN")
    .replaces_endpoint(1, device_type=zha.DeviceType.DIMMABLE_LIGHT)
    .replace_cluster_occurrences(InovelliVZM32SNMMWaveCluster)
    .replace_cluster_occurrences(InovelliVZM32SNCluster)
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
    # Number entities for VZM32SN cluster
    .number(
        InovelliVZM32SNCluster.AttributeDefs.dimming_speed_up_local.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=0,
        max_value=126,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="dimming_speed_up_local",
        fallback_name="Local dimming up speed",
    )
    .number(
        InovelliVZM32SNCluster.AttributeDefs.ramp_rate_off_to_on_local.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=0,
        max_value=127,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="ramp_rate_off_to_on_local",
        fallback_name="Local ramp rate off to on",
    )
    .number(
        InovelliVZM32SNCluster.AttributeDefs.dimming_speed_down_local.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=0,
        max_value=127,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="dimming_speed_down_local",
        fallback_name="Local dimming down speed",
    )
    .number(
        InovelliVZM32SNCluster.AttributeDefs.ramp_rate_on_to_off_local.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=0,
        max_value=127,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="ramp_rate_on_to_off_local",
        fallback_name="Local ramp rate on to off",
    )
    .number(
        InovelliVZM32SNCluster.AttributeDefs.default_level_local.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=1,
        max_value=254,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="default_level_local",
        fallback_name="Local default dimming level",
    )
    .number(
        InovelliVZM32SNCluster.AttributeDefs.load_level_indicator_timeout.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=0,
        max_value=11,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="load_level_indicator_timeout",
        fallback_name="Load level indicator timeout",
    )
    .number(
        InovelliVZM32SNCluster.AttributeDefs.button_delay.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=0,
        max_value=9,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="button_delay",
        fallback_name="Button delay",
    )
    .number(
        InovelliVZM32SNCluster.AttributeDefs.double_tap_up_level.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=2,
        max_value=254,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="double_tap_up_level",
        fallback_name="Double tap up level",
    )
    .number(
        InovelliVZM32SNCluster.AttributeDefs.double_tap_down_level.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=0,
        max_value=254,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="double_tap_down_level",
        fallback_name="Double tap down level",
    )
    # LED color and intensity sliders
    .number(
        InovelliVZM32SNCluster.AttributeDefs.led_color_when_on.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=0,
        max_value=255,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="led_color_when_on",
        fallback_name="Default all LED on color",
    )
    .number(
        InovelliVZM32SNCluster.AttributeDefs.led_color_when_off.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=0,
        max_value=255,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="led_color_when_off",
        fallback_name="Default all LED off color",
    )
    .number(
        InovelliVZM32SNCluster.AttributeDefs.led_intensity_when_on.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="led_intensity_when_on",
        fallback_name="Default all LED on intensity",
    )
    .number(
        InovelliVZM32SNCluster.AttributeDefs.led_intensity_when_off.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="led_intensity_when_off",
        fallback_name="Default all LED off intensity",
    )
    # Auto-off timer
    .number(
        InovelliVZM32SNCluster.AttributeDefs.auto_off_timer.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=0,
        max_value=32767,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="auto_off_timer",
        fallback_name="Automatic switch shutoff timer",
    )
    # Min/max levels
    .number(
        InovelliVZM32SNCluster.AttributeDefs.minimum_level.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=1,
        max_value=254,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="minimum_level",
        fallback_name="Minimum load dimming level",
    )
    .number(
        InovelliVZM32SNCluster.AttributeDefs.maximum_level.name,
        InovelliVZM32SNCluster.cluster_id,
        min_value=2,
        max_value=255,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="maximum_level",
        fallback_name="Maximum load dimming level",
    )
    .enum(
        InovelliVZM32SNCluster.AttributeDefs.mmwave_room_size_preset.name,
        InovelliMmwaveRoomSizePreset,
        InovelliVZM32SNCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="mmwave_room_size_preset",
        fallback_name="mmWave room size preset",
    )
    .enum(
        InovelliVZM32SNCluster.AttributeDefs.light_on_presence_behavior.name,
        InovelliLightOnPresenceBehavior,
        InovelliVZM32SNCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="light_on_presence_behavior",
        fallback_name="Light on presence behavior",
    )
    .enum(
        InovelliVZM32SNCluster.AttributeDefs.switch_type.name,
        InovelliVZM32SwitchType,
        InovelliVZM32SNCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="switch_type",
        fallback_name="Switch type",
    )
    # Switch entities for VZM32SN cluster
    .switch(
        InovelliVZM32SNCluster.AttributeDefs.invert_switch.name,
        InovelliVZM32SNCluster.cluster_id,
        off_value=0,
        on_value=1,
        entity_type=EntityType.CONFIG,
        translation_key="invert_switch",
        fallback_name="Invert switch",
    )
    .switch(
        InovelliVZM32SNCluster.AttributeDefs.smart_bulb_mode.name,
        InovelliVZM32SNCluster.cluster_id,
        off_value=0,
        on_value=1,
        entity_type=EntityType.CONFIG,
        translation_key="smart_bulb_mode",
        fallback_name="Smart bulb mode",
    )
    .switch(
        InovelliVZM32SNCluster.AttributeDefs.double_tap_up_enabled.name,
        InovelliVZM32SNCluster.cluster_id,
        off_value=0,
        on_value=1,
        entity_type=EntityType.CONFIG,
        translation_key="double_tap_up_enabled",
        fallback_name="Double tap up enabled",
    )
    .switch(
        InovelliVZM32SNCluster.AttributeDefs.double_tap_down_enabled.name,
        InovelliVZM32SNCluster.cluster_id,
        off_value=0,
        on_value=1,
        entity_type=EntityType.CONFIG,
        translation_key="double_tap_down_enabled",
        fallback_name="Double tap down enabled",
    )
    .switch(
        InovelliVZM32SNCluster.AttributeDefs.aux_switch_scenes.name,
        InovelliVZM32SNCluster.cluster_id,
        off_value=0,
        on_value=1,
        entity_type=EntityType.CONFIG,
        translation_key="aux_switch_scenes",
        fallback_name="Aux switch scenes",
    )
    .switch(
        InovelliVZM32SNCluster.AttributeDefs.binding_off_to_on_sync_level.name,
        InovelliVZM32SNCluster.cluster_id,
        off_value=0,
        on_value=1,
        entity_type=EntityType.CONFIG,
        translation_key="binding_off_to_on_sync_level",
        fallback_name="Binding off to on sync level",
    )
    .switch(
        InovelliVZM32SNCluster.AttributeDefs.local_protection.name,
        InovelliVZM32SNCluster.cluster_id,
        off_value=0,
        on_value=1,
        entity_type=EntityType.CONFIG,
        translation_key="local_protection",
        fallback_name="Local protection",
    )
    .switch(
        InovelliVZM32SNCluster.AttributeDefs.remote_protection.name,
        InovelliVZM32SNCluster.cluster_id,
        off_value=0,
        on_value=1,
        entity_type=EntityType.CONFIG,
        translation_key="remote_protection",
        fallback_name="Remote protection",
    )
    .switch(
        InovelliVZM32SNCluster.AttributeDefs.on_off_led_mode.name,
        InovelliVZM32SNCluster.cluster_id,
        off_value=0,
        on_value=1,
        entity_type=EntityType.CONFIG,
        translation_key="on_off_led_mode",
        fallback_name="Only 1 LED mode",
    )
    .switch(
        InovelliVZM32SNCluster.AttributeDefs.firmware_progress_led.name,
        InovelliVZM32SNCluster.cluster_id,
        off_value=0,
        on_value=1,
        entity_type=EntityType.CONFIG,
        translation_key="firmware_progress_led",
        fallback_name="Firmware progress LED",
    )
    .switch(
        InovelliVZM32SNCluster.AttributeDefs.disable_clear_notifications_double_tap.name,
        InovelliVZM32SNCluster.cluster_id,
        off_value=0,
        on_value=1,
        entity_type=EntityType.CONFIG,
        translation_key="disable_clear_notifications_double_tap",
        fallback_name="Disable config 2x tap to clear notifications",
    )
    .enum(
        InovelliVZM32SNCluster.AttributeDefs.output_mode.name,
        InovelliOutputMode,
        InovelliVZM32SNCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="output_mode",
        fallback_name="Output mode",
    )
    .enum(
        InovelliVZM32SNCluster.AttributeDefs.increased_non_neutral_output.name,
        InovelliNonNeutralOutput,
        InovelliVZM32SNCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="increased_non_neutral_output",
        fallback_name="Non neutral output",
    )
    .enum(
        InovelliVZM32SNCluster.AttributeDefs.led_scaling_mode.name,
        InovelliLedScalingMode,
        InovelliVZM32SNCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="led_scaling_mode",
        fallback_name="LED scaling mode",
    )
    # MMWave cluster entities
    .number(
        InovelliVZM32SNMMWaveCluster.AttributeDefs.mmwave_height_minimum_floor.name,
        InovelliVZM32SNMMWaveCluster.cluster_id,
        min_value=-600,
        max_value=600,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="mmwave_height_minimum_floor",
        fallback_name="mmWave height minimum (floor)",
    )
    .number(
        InovelliVZM32SNMMWaveCluster.AttributeDefs.mmwave_height_maximum_ceiling.name,
        InovelliVZM32SNMMWaveCluster.cluster_id,
        min_value=-600,
        max_value=600,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="mmwave_height_maximum_ceiling",
        fallback_name="mmWave height maximum (ceiling)",
    )
    .number(
        InovelliVZM32SNMMWaveCluster.AttributeDefs.mmwave_width_minimum_left.name,
        InovelliVZM32SNMMWaveCluster.cluster_id,
        min_value=-600,
        max_value=600,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="mmwave_width_minimum_left",
        fallback_name="mmWave width minimum (left)",
    )
    .number(
        InovelliVZM32SNMMWaveCluster.AttributeDefs.mmwave_width_maximum_right.name,
        InovelliVZM32SNMMWaveCluster.cluster_id,
        min_value=-600,
        max_value=600,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="mmwave_width_maximum_right",
        fallback_name="mmWave width maximum (right)",
    )
    .number(
        InovelliVZM32SNMMWaveCluster.AttributeDefs.mmwave_depth_minimum_near.name,
        InovelliVZM32SNMMWaveCluster.cluster_id,
        min_value=0,
        max_value=600,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="mmwave_depth_minimum_near",
        fallback_name="mmWave depth minimum (near)",
    )
    .number(
        InovelliVZM32SNMMWaveCluster.AttributeDefs.mmwave_depth_maximum_far.name,
        InovelliVZM32SNMMWaveCluster.cluster_id,
        min_value=0,
        max_value=600,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="mmwave_depth_maximum_far",
        fallback_name="mmWave depth maximum (far)",
    )
    .enum(
        InovelliVZM32SNMMWaveCluster.AttributeDefs.mmwave_detect_sensitivity.name,
        InovelliMmwaveSensitivity,
        InovelliVZM32SNMMWaveCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="mmwave_detect_sensitivity",
        fallback_name="mmWave sensitivity",
    )
    .enum(
        InovelliVZM32SNMMWaveCluster.AttributeDefs.mmwave_detect_trigger.name,
        InovelliMmwaveTargetSpeed,
        InovelliVZM32SNMMWaveCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="mmwave_detect_trigger",
        fallback_name="mmWave target speed",
    )
    .number(
        InovelliVZM32SNMMWaveCluster.AttributeDefs.mmwave_hold_time.name,
        InovelliVZM32SNMMWaveCluster.cluster_id,
        min_value=0,
        max_value=4294967295,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="mmwave_hold_time",
        fallback_name="mmWave hold time",
    )
    .add_to_registry()
)
