"""VZM32-SN MMwave Switch/Dimmer Module."""

from zigpy.profiles import zha

from zhaquirks.inovelli import (
    INOVELLI_AUTOMATION_TRIGGERS,
    InovelliVZM32SNCluster,
    InovelliVZM32SNMMWaveCluster,
)
from zhaquirks.inovelli.builder import InovelliQuirkBuilder

(
    InovelliQuirkBuilder("Inovelli", "VZM32-SN")
    .replaces_endpoint(1, device_type=zha.DeviceType.DIMMABLE_LIGHT)
    .replace_cluster_occurrences(InovelliVZM32SNMMWaveCluster)
    .replace_cluster_occurrences(InovelliVZM32SNCluster)
    # number entities
    .inovelli_remote_dimming_up_speed()
    .inovelli_local_dimming_up_speed()
    .inovelli_remote_dimming_down_speed()
    .inovelli_local_dimming_down_speed()
    .inovelli_remote_ramp_rate_off_to_on()
    .inovelli_local_ramp_rate_off_to_on()
    .inovelli_remote_ramp_rate_on_to_off()
    .inovelli_local_ramp_rate_on_to_off()
    .inovelli_button_delay()
    .inovelli_minimum_load_dimming_level()
    .inovelli_maximum_load_dimming_level()
    .inovelli_auto_shutoff_timer()
    .inovelli_local_default_level()
    .inovelli_remote_default_level()
    .inovelli_startup_default_level()
    .inovelli_load_level_indicator_timeout()
    .inovelli_default_all_led_on_color()
    .inovelli_default_all_led_off_color()
    .inovelli_default_all_led_on_intensity()
    .inovelli_default_all_led_off_intensity()
    .inovelli_double_tap_up_level()
    .inovelli_double_tap_down_level()
    # switch entities
    .inovelli_invert_switch()
    .inovelli_smart_bulb_mode()
    .inovelli_double_tap_up_enabled()
    .inovelli_double_tap_down_enabled()
    .inovelli_aux_switch_scenes()
    .inovelli_binding_off_to_on_sync_level()
    .inovelli_local_protection()
    .inovelli_on_off_led_mode()
    .inovelli_firmware_progress_led()
    .inovelli_disable_clear_notifications_double_tap()
    # select entities
    .inovelli_output_mode()
    .inovelli_led_scaling_mode()
    .inovelli_increased_non_neutral_output()
    # sensor entities
    .inovelli_internal_temperature()
    .inovelli_overheated()
    # VZM32-SN specific entities (0xFC31)
    .inovelli_remote_protection()
    .inovelli_vzm32_switch_type()
    .inovelli_light_on_presence_behavior()
    .inovelli_mmwave_room_size_preset()
    # VZM32-SN mmWave cluster entities (0xFC32)
    .inovelli_mmwave_height_minimum_floor()
    .inovelli_mmwave_height_maximum_ceiling()
    .inovelli_mmwave_width_minimum_left()
    .inovelli_mmwave_width_maximum_right()
    .inovelli_mmwave_depth_minimum_near()
    .inovelli_mmwave_depth_maximum_far()
    .inovelli_mmwave_detect_sensitivity()
    .inovelli_mmwave_detect_trigger()
    .inovelli_mmwave_hold_time()
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
    .add_to_registry()
)
