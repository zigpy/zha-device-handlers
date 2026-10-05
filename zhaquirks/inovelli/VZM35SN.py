"""VZM35-SN Fan Switch."""

from zigpy.profiles import zha
from zigpy.zcl import ClusterType

from zhaquirks.inovelli import INOVELLI_AUTOMATION_TRIGGERS, InovelliVZM35SNCluster
from zhaquirks.inovelli.builder import InovelliQuirkBuilder

(
    InovelliQuirkBuilder("Inovelli", "VZM35-SN")
    .replaces_endpoint(1, device_type=zha.DeviceType.DIMMABLE_LIGHT)
    .replace_cluster_occurrences(InovelliVZM35SNCluster)
    # ep 3 is missing in zigpy DB for devices paired with an old fw version, add it:
    .replaces_endpoint(3, device_type=zha.DeviceType.DIMMER_SWITCH)
    # these missing clusters are needed for button presses to generate events:
    .replaces(InovelliVZM35SNCluster, endpoint_id=2, cluster_type=ClusterType.Client)
    .replaces(InovelliVZM35SNCluster, endpoint_id=3, cluster_type=ClusterType.Client)
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
    .inovelli_quick_start_time()
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
    .inovelli_smart_fan_mode()
    .inovelli_double_tap_up_enabled()
    .inovelli_double_tap_down_enabled()
    .inovelli_aux_switch_scenes()
    .inovelli_local_protection()
    .inovelli_on_off_led_mode()
    .inovelli_firmware_progress_led()
    .inovelli_disable_clear_notifications_double_tap()
    # select entities
    .inovelli_output_mode()
    .inovelli_fan_switch_type()
    .inovelli_fan_led_scaling_mode()
    # sensor entities
    .inovelli_internal_temperature()
    .inovelli_overheated()
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
    .add_to_registry()
)
