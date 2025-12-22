"""Ubisys H1 - Zigbee Thermostatic Radiator Valve."""

import dataclasses
from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import NumberDeviceClass, QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature, UnitOfTime
import zigpy.types as t
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import Attribute, ZCLAttributeAccess, ZCLAttributeDef


@dataclasses.dataclass(frozen=True)
class RemappableZCLAttributeDef(ZCLAttributeDef):
    """ZCL Attribute Definition with rewritten attribute ID."""

    actual_id: t.uint16_t | None = None


class RemappleAttributesCustomCluster(CustomCluster):
    """Custom Cluster that rewrites attribute IDs when using RemappableZCLAttributeDef."""

    async def _write_attributes(
        self,
        attributes: list[Attribute],
        *args,
        manufacturer: int | t.uint16_t | None = None,
        **kwargs,
    ):
        remapped_ids = {}
        generic_attributes = []
        specific_attributes = []
        for a in attributes:
            if not isinstance(self.attributes[a.attrid], RemappableZCLAttributeDef):
                generic_attributes.append(a)
            else:
                actual_id = self.attributes[a.attrid].actual_id
                remapped_ids[actual_id] = a.attrid
                a.attrid = actual_id
                specific_attributes.append(a)

        result_generic = (
            await super()._write_attributes(
                generic_attributes,
                *args,
                manufacturer=manufacturer,
                **kwargs,
            )
            if len(generic_attributes) > 0
            else None
        )

        result_specific = (
            await super()._write_attributes(
                specific_attributes,
                *args,
                manufacturer=self.manufacturer_id_override,
                **kwargs,
            )
            if len(specific_attributes) > 0
            else None
        )

        status_records = []
        if result_generic:
            status_records.extend(result_generic.status_records)

        if result_specific:
            status_records.extend(result_specific.status_records)

            # Manually trigger attribute read as the H1 does not report change
            await self.read_attributes(
                [remapped_ids[a.attrid] for a in specific_attributes],
                manufacturer=self.manufacturer_id_override,
            )

        return (status_records,)

    async def _read_attributes(
        self,
        attribute_ids: list[t.uint16_t],
        *args,
        manufacturer: int | t.uint16_t | None = None,
        **kwargs,
    ):
        remapped_ids = {}
        generic_attributes = []
        specific_attributes = []
        for a in attribute_ids:
            if not isinstance(self.attributes[a], RemappableZCLAttributeDef):
                generic_attributes.append(a)
            else:
                actual_id = self.attributes[a].actual_id
                remapped_ids[actual_id] = a
                specific_attributes.append(t.uint16_t(actual_id))

        result_generic = (
            await super()._read_attributes(
                generic_attributes,
                *args,
                manufacturer=manufacturer,
                **kwargs,
            )
            if len(generic_attributes) > 0
            else ([],)
        )

        result_specific = (
            await super()._read_attributes(
                specific_attributes,
                *args,
                manufacturer=self.manufacturer_id_override,
                **kwargs,
            )
            if len(specific_attributes) > 0
            else ([],)
        )

        for a in result_specific[0]:
            a.attrid = t.uint16_t(remapped_ids[a.attrid])

        return ([*result_generic[0], *result_specific[0]],)


class ThermostatCluster(RemappleAttributesCustomCluster, Thermostat):
    """ubisys H1 thermostat cluster."""

    manufacturer_id_override = t.uint16_t(0x10F2)

    class AttributeDefs(Thermostat.AttributeDefs):
        """ubisys H1 thermostat manufacturer-specific attributes."""

        temperature_offset: Final = RemappableZCLAttributeDef(
            id=t.uint16_t(0x4010),
            actual_id=t.uint16_t(0x0010),
            type=t.int8s,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        # not exposed
        default_occupied_heating_setpoint = RemappableZCLAttributeDef(
            id=t.uint16_t(0x4011),
            actual_id=t.uint16_t(0x0011),
            type=t.int16s,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        # not exposed
        vacation_mode = RemappableZCLAttributeDef(
            id=t.uint16_t(0x4012),
            actual_id=t.uint16_t(0x0012),
            type=t.Bool,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        remote_temperature = RemappableZCLAttributeDef(
            id=t.uint16_t(0x4013),
            actual_id=t.uint16_t(0x0013),
            type=t.int16s,
            access=ZCLAttributeAccess.Read,
            is_manufacturer_specific=True,
        )

        remote_temperature_valid_duration = RemappableZCLAttributeDef(
            id=t.uint16_t(0x4014),
            actual_id=t.uint16_t(0x0014),
            type=t.uint16_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        detect_open_window = RemappableZCLAttributeDef(
            id=t.uint16_t(0x4015),
            actual_id=t.uint16_t(0x0015),
            type=t.bitmap8,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        open_window_state = RemappableZCLAttributeDef(
            id=t.uint16_t(0x4016),
            actual_id=t.uint16_t(0x0016),
            type=t.bitmap8,
            access=ZCLAttributeAccess.Read,
            is_manufacturer_specific=True,
        )

        open_window_sensitivity = RemappableZCLAttributeDef(
            id=t.uint16_t(0x4017),
            actual_id=t.uint16_t(0x0017),
            type=t.uint16_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        open_window_detection_period = RemappableZCLAttributeDef(
            id=t.uint16_t(0x4018),
            actual_id=t.uint16_t(0x0018),
            type=t.uint16_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        open_window_timeout = RemappableZCLAttributeDef(
            id=t.uint16_t(0x4019),
            actual_id=t.uint16_t(0x0019),
            type=t.uint16_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        # not exposed
        heating_demand_lower_bound = RemappableZCLAttributeDef(
            id=t.uint16_t(0x401A),
            actual_id=t.uint16_t(0x001A),
            type=t.uint8_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        # not exposed
        heating_demand_upper_bound = RemappableZCLAttributeDef(
            id=t.uint16_t(0x401B),
            actual_id=t.uint16_t(0x001B),
            type=t.uint8_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        season = RemappableZCLAttributeDef(
            id=t.uint16_t(0x401C),
            actual_id=t.uint16_t(0x001C),
            type=t.Bool,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        backup_heating_demand: Final = RemappableZCLAttributeDef(
            id=t.uint16_t(0x401D),
            actual_id=t.uint16_t(0x001D),
            type=t.uint8_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        alternate_backup_heating_demand = RemappableZCLAttributeDef(
            id=t.uint16_t(0x401E),
            actual_id=t.uint16_t(0x001E),
            type=t.uint8_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        proportional_gain = RemappableZCLAttributeDef(
            id=t.uint16_t(0x4020),
            actual_id=t.uint16_t(0x0020),
            type=t.int16s,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        proportional_shift = RemappableZCLAttributeDef(
            id=t.uint16_t(0x4021),
            actual_id=t.uint16_t(0x0021),
            type=t.int8s,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
        )

        integral_factor = RemappableZCLAttributeDef(
            id=t.uint16_t(0x4022),
            actual_id=t.uint16_t(0x0022),
            type=t.int16s,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Write,
            is_manufacturer_specific=True,
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
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="temperature_offset",
        fallback_name="Temperature offset",
    )
    .number(
        ThermostatCluster.AttributeDefs.remote_temperature.name,
        ThermostatCluster.cluster_id,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="external_temperature_sensor_value",
        fallback_name="External temperature sensor value",
    )
    .number(
        ThermostatCluster.AttributeDefs.remote_temperature_valid_duration.name,
        ThermostatCluster.cluster_id,
        unit=UnitOfTime.MINUTES,
        multiplier=1 / 60,
        translation_key="external_temperature_sensor_valid_duration",
        fallback_name="External temperature sensor valid duration",
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
        translation_key="open_window_detection_status",
        fallback_name="Open window detection status",
    )
    .number(
        ThermostatCluster.AttributeDefs.open_window_sensitivity.name,
        ThermostatCluster.cluster_id,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="open_window_detection_threshold",
        fallback_name="Open window detection threshold",
    )
    .number(
        ThermostatCluster.AttributeDefs.open_window_detection_period.name,
        ThermostatCluster.cluster_id,
        unit=UnitOfTime.MINUTES,
        translation_key="open_window_event_duration",
        fallback_name="Open window event duration",
    )
    .number(
        ThermostatCluster.AttributeDefs.open_window_timeout.name,
        ThermostatCluster.cluster_id,
        unit=UnitOfTime.MINUTES,
        multiplier=1 / 60,
        translation_key="open_window_detection_guard_period",
        fallback_name="Open window detection guard period",
    )
    .switch(
        ThermostatCluster.AttributeDefs.season.name,
        ThermostatCluster.cluster_id,
        translation_key="summer_mode",
        fallback_name="Summer Mode",
        initially_disabled=True,
    )
    .number(
        ThermostatCluster.AttributeDefs.backup_heating_demand.name,
        ThermostatCluster.cluster_id,
        min_value=0,
        max_value=100,
        unit=PERCENTAGE,
        translation_key="backup_heating_demand",
        fallback_name="Backup Heating Demand",
        initially_disabled=True,
    )
    .number(
        ThermostatCluster.AttributeDefs.alternate_backup_heating_demand.name,
        ThermostatCluster.cluster_id,
        min_value=0,
        max_value=100,
        unit=PERCENTAGE,
        translation_key="alternate_backup_heating_demand",
        fallback_name="Alternate Backup Heating Demand",
        initially_disabled=True,
    )
    .number(
        ThermostatCluster.AttributeDefs.proportional_gain.name,
        ThermostatCluster.cluster_id,
        translation_key="proportional_gain",
        fallback_name="Proportional Gain (Kp)",
        initially_disabled=True,
    )
    .number(
        ThermostatCluster.AttributeDefs.proportional_shift.name,
        ThermostatCluster.cluster_id,
        translation_key="proportional_shift",
        fallback_name="Proportional Shift (N)",
        initially_disabled=True,
    )
    .number(
        ThermostatCluster.AttributeDefs.integral_factor.name,
        ThermostatCluster.cluster_id,
        translation_key="integral_factor",
        fallback_name="Integral Factor",
        initially_disabled=True,
    )
    .add_to_registry()
)
