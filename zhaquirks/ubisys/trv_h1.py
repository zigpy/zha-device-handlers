"""Ubisys Thermostatic Radiator Valve H1."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import BinarySensorDeviceClass, NumberDeviceClass, QuirkBuilder
from zigpy.quirks.v2.homeassistant import (
    PERCENTAGE,
    EntityType,
    UnitOfTemperature,
    UnitOfTime,
)
import zigpy.types as t
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeAccess, ZCLAttributeDef


class ThermostatCluster(CustomCluster, Thermostat):
    """ubisys H1 thermostat cluster."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """ubisys H1 thermostat manufacturer-specific attributes."""

        temperature_offset: Final = ZCLAttributeDef(
            id=0x0010,
            type=t.int8s,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        # not exposed
        default_occupied_heating_setpoint = ZCLAttributeDef(
            id=0x0011,
            type=t.int16s,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        # not exposed
        vacation_mode = ZCLAttributeDef(
            id=0x0012,
            type=t.Bool,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        remote_temperature = ZCLAttributeDef(
            id=0x0013,
            type=t.int16s,
            access=ZCLAttributeAccess.Read,
            manufacturer_code=0x10F2,
        )

        remote_temperature_valid_duration = ZCLAttributeDef(
            id=0x0014,
            type=t.uint16_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        detect_open_window = ZCLAttributeDef(
            id=0x0015,
            type=t.bitmap8,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        open_window_state = ZCLAttributeDef(
            id=0x0016,
            type=t.bitmap8,
            access=ZCLAttributeAccess.Read,
            manufacturer_code=0x10F2,
        )

        open_window_sensitivity = ZCLAttributeDef(
            id=0x0017,
            type=t.uint16_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        open_window_detection_period = ZCLAttributeDef(
            id=0x0018,
            type=t.uint16_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        open_window_timeout = ZCLAttributeDef(
            id=0x0019,
            type=t.uint16_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        # not exposed
        heating_demand_lower_bound = ZCLAttributeDef(
            id=0x001A,
            type=t.uint8_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        # not exposed
        heating_demand_upper_bound = ZCLAttributeDef(
            id=0x001B,
            type=t.uint8_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        season = ZCLAttributeDef(
            id=0x001C,
            type=t.Bool,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        backup_heating_demand: Final = ZCLAttributeDef(
            id=0x001D,
            type=t.uint8_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        alternate_backup_heating_demand = ZCLAttributeDef(
            id=0x001E,
            type=t.uint8_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        proportional_gain = ZCLAttributeDef(
            id=0x0020,
            type=t.int16s,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        proportional_shift = ZCLAttributeDef(
            id=0x0021,
            type=t.int8s,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )

        integral_factor = ZCLAttributeDef(
            id=0x0022,
            type=t.int16s,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            manufacturer_code=0x10F2,
        )


(
    QuirkBuilder("ubisys", "H1")
    .firmware_version_filter(min_version=0x0170044D)
    .replaces(ThermostatCluster)
    .number(
        ThermostatCluster.AttributeDefs.temperature_offset.name,
        ThermostatCluster.cluster_id,
        min_value=-10,
        max_value=10,
        step=1,
        mode="box",
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    .switch(
        ThermostatCluster.AttributeDefs.detect_open_window.name,
        ThermostatCluster.cluster_id,
        translation_key="window_detection",
        fallback_name="Open window detection",
    )
    .binary_sensor(
        ThermostatCluster.AttributeDefs.open_window_state.name,
        ThermostatCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.WINDOW,
        translation_key="open_window_detection_status",
        fallback_name="Open window detection status",
    )
    .number(
        ThermostatCluster.AttributeDefs.open_window_sensitivity.name,
        ThermostatCluster.cluster_id,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        step=0.5,
        translation_key="open_window_detection_threshold",
        fallback_name="Open window detection threshold",
    )
    .number(
        ThermostatCluster.AttributeDefs.open_window_detection_period.name,
        ThermostatCluster.cluster_id,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        mode="box",
        translation_key="open_window_event_duration",
        fallback_name="Open window event duration",
    )
    .number(
        ThermostatCluster.AttributeDefs.open_window_timeout.name,
        ThermostatCluster.cluster_id,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        multiplier=1 / 60,
        mode="box",
        translation_key="open_window_detection_guard_period",
        fallback_name="Open window detection guard period",
    )
    .switch(
        ThermostatCluster.AttributeDefs.season.name,
        ThermostatCluster.cluster_id,
        initially_disabled=True,
        translation_key="summer_mode",
        fallback_name="Summer mode",
    )
    .number(
        ThermostatCluster.AttributeDefs.backup_heating_demand.name,
        ThermostatCluster.cluster_id,
        min_value=0,
        max_value=100,
        unit=PERCENTAGE,
        initially_disabled=True,
        translation_key="winter_backup_heating_demand",
        fallback_name="Winter backup heating demand",
    )
    .number(
        ThermostatCluster.AttributeDefs.alternate_backup_heating_demand.name,
        ThermostatCluster.cluster_id,
        min_value=0,
        max_value=100,
        unit=PERCENTAGE,
        initially_disabled=True,
        translation_key="summer_backup_heating_demand",
        fallback_name="Summer backup heating demand",
    )
    .number(
        ThermostatCluster.AttributeDefs.proportional_gain.name,
        ThermostatCluster.cluster_id,
        initially_disabled=True,
        translation_key="proportional_gain",
        fallback_name="Proportional gain (Kp)",
    )
    .number(
        ThermostatCluster.AttributeDefs.proportional_shift.name,
        ThermostatCluster.cluster_id,
        initially_disabled=True,
        translation_key="proportional_shift",
        fallback_name="Proportional shift (N)",
    )
    .number(
        ThermostatCluster.AttributeDefs.integral_factor.name,
        ThermostatCluster.cluster_id,
        initially_disabled=True,
        translation_key="integral_factor",
        fallback_name="Integral factor",
    )
    .add_to_registry()
)
