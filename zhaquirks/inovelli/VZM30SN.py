"""VZM30-SN Smart On/Off Switch."""

from zigpy.profiles import zha

from zhaquirks.inovelli import INOVELLI_AUTOMATION_TRIGGERS, InovelliVZM30SNCluster
from zhaquirks.inovelli.builder import InovelliQuirkBuilder

(
    InovelliQuirkBuilder("Inovelli", "VZM30-SN")
    .replaces_endpoint(1, device_type=zha.DeviceType.DIMMABLE_LIGHT)
    .replace_cluster_occurrences(InovelliVZM30SNCluster)
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
    .inovelli_relay_click_in_on_off_mode()
    .inovelli_disable_clear_notifications_double_tap()
    # select entities
    .inovelli_output_mode()
    .inovelli_led_scaling_mode()
    .inovelli_increased_non_neutral_output()
    # sensor entities
    .inovelli_internal_temperature()
    .inovelli_overheated()
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
    .add_to_registry()
)
