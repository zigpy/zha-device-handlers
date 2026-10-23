"""VZM36 Canopy Module."""

from zigpy.profiles import zha

from zhaquirks.inovelli import (
    INOVELLI_AUTOMATION_TRIGGERS,
    InovelliVZM36FanCluster,
    InovelliVZM36LightCluster,
)
from zhaquirks.inovelli.builder import InovelliQuirkBuilder

(
    InovelliQuirkBuilder("Inovelli", "VZM36")
    .replaces_endpoint(1, device_type=zha.DeviceType.DIMMABLE_LIGHT)
    .replaces(InovelliVZM36LightCluster)
    .replaces(InovelliVZM36FanCluster, endpoint_id=2)
    # light endpoint (1) entities
    .inovelli_remote_dimming_up_speed()
    .inovelli_remote_dimming_down_speed()
    .inovelli_remote_ramp_rate_off_to_on()
    .inovelli_remote_ramp_rate_on_to_off()
    .inovelli_minimum_load_dimming_level()
    .inovelli_maximum_load_dimming_level()
    .inovelli_auto_shutoff_timer()
    .inovelli_remote_default_level()
    .inovelli_startup_default_level()
    .inovelli_default_all_led_on_color()
    .inovelli_default_all_led_on_intensity()
    .inovelli_smart_bulb_mode()
    .inovelli_output_mode()
    .inovelli_increased_non_neutral_output()
    .inovelli_dimming_mode()
    .inovelli_internal_temperature()
    .inovelli_overheated()
    # fan endpoint (2) entities
    .inovelli_remote_dimming_up_speed(endpoint_id=2)
    .inovelli_remote_dimming_down_speed(endpoint_id=2)
    .inovelli_remote_ramp_rate_off_to_on(endpoint_id=2)
    .inovelli_remote_ramp_rate_on_to_off(endpoint_id=2)
    .inovelli_minimum_load_dimming_level(endpoint_id=2)
    .inovelli_maximum_load_dimming_level(endpoint_id=2)
    .inovelli_auto_shutoff_timer(endpoint_id=2)
    .inovelli_remote_default_level(endpoint_id=2)
    .inovelli_startup_default_level(endpoint_id=2)
    .inovelli_default_all_led_on_color(endpoint_id=2)
    .inovelli_default_all_led_on_intensity(endpoint_id=2)
    .inovelli_smart_bulb_mode(endpoint_id=2)
    .inovelli_output_mode(endpoint_id=2)
    .inovelli_internal_temperature(endpoint_id=2)
    .inovelli_overheated(endpoint_id=2)
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
    .add_to_registry()
)
