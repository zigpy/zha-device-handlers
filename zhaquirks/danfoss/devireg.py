"""Module to handle quirks of DEVI (Danfoss) DEVIreg electric floor heating thermostats.

Currently covers the DEVIreg Display Connect (manufacturer "devi", model "devi_c").

The device only implements SystemMode.Heat. Like the Danfoss TRVs, turning it "off"
is emulated by lowering the setpoint to the minimum setpoint limit (frost
protection); the reported system mode stays Heat.

Manufacturer specific attributes:
    0x0201 - HeaterOn (0x400A): heating relay state, 0 = open, 1 = closed.
        Mirrored into the unimplemented running_state attribute for the HVAC action.
    0x0402 - RoomTemperature (0x4000): the built-in room sensor.
    0x0402 - FloorTemperature (0x4002): the floor sensor.

Broken firmware behavior:
    - The time is never requested by the device, so it is written to the device
      when the thermostat cluster is bound.
    - Firmware before 03.49 clamps a setpoint write that crosses below 15 °C to
      15 °C; 15 °C is written first, followed by the target value after a delay.
"""

import asyncio
from typing import Any, Final

import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster
from zhaquirks.danfoss.thermostat import DanfossTimeCluster

DANFOSS_MANUFACTURER_CODE = 0x1246

# Firmware before 03.49 clamps setpoint writes crossing below this raw value (15 °C)
SETPOINT_CLAMP_LIMIT = 1500
SETPOINT_CLAMP_SETTLE_DELAY = 3  # seconds

system_mode = Thermostat.AttributeDefs.system_mode
occupied_heating_setpoint = Thermostat.AttributeDefs.occupied_heating_setpoint
min_heat_setpoint_limit = Thermostat.AttributeDefs.min_heat_setpoint_limit
abs_min_heat_setpoint_limit = Thermostat.AttributeDefs.abs_min_heat_setpoint_limit
running_state = Thermostat.AttributeDefs.running_state


class DeviThermostatCluster(CustomCluster, Thermostat):
    """DEVI thermostat cluster with the manufacturer-specific relay state."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        heater_on: Final = ZCLAttributeDef(
            id=0x400A,
            type=t.uint8_t,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        # Derive the unimplemented running_state from the relay state
        if attrid == self.AttributeDefs.heater_on.id:
            self._update_attribute(
                running_state.id,
                self.RunningState.Heat_State_On if value else self.RunningState.Idle,
            )

    async def read_attributes_raw(self, attributes, manufacturer=None, **kwargs):
        """Serve the emulated running_state locally.

        The device would answer UNSUPPORTED_ATTRIBUTE, marking the attribute as
        unsupported and hiding the mirrored value.
        """
        if running_state.id not in attributes:
            return await super().read_attributes_raw(
                attributes, manufacturer=manufacturer, **kwargs
            )

        record = foundation.ReadAttributeRecord(
            running_state.id, foundation.Status.SUCCESS, foundation.TypeValue()
        )
        value = self._attr_cache.get(running_state.id)
        if value is None:
            value = (
                self.RunningState.Heat_State_On
                if self._attr_cache.get(self.AttributeDefs.heater_on.id)
                else self.RunningState.Idle
            )
        record.value.value = self.RunningState(value)
        succeeded = [record]

        attrs_to_read = [attr for attr in attributes if attr != running_state.id]
        if not attrs_to_read:
            return [succeeded]

        results = await super().read_attributes_raw(
            attrs_to_read, manufacturer=manufacturer, **kwargs
        )
        if not isinstance(results[0], list):
            for attrid in attrs_to_read:
                succeeded.append(  # noqa: PERF401
                    foundation.ReadAttributeRecord(
                        attrid,
                        results[0],
                        foundation.TypeValue(),
                    )
                )
        else:
            succeeded.extend(results[0])
        return [succeeded]

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Emulate the unsupported Off system mode and avoid the setpoint clamp.

        The device only implements Heat; Off is emulated by lowering the setpoint
        to the minimum setpoint limit (frost protection).
        """
        attributes = dict(attributes)

        if attributes.get(system_mode.name) == self.SystemMode.Off:
            attributes[system_mode.name] = self.SystemMode.Heat
            attributes[occupied_heating_setpoint.name] = self.get(
                min_heat_setpoint_limit.name,
                self.get(abs_min_heat_setpoint_limit.name, 500),
            )

        setpoint = attributes.get(occupied_heating_setpoint.name)
        current = self.get(occupied_heating_setpoint.name)
        if (
            setpoint is not None
            and setpoint < SETPOINT_CLAMP_LIMIT
            and (current is None or current >= SETPOINT_CLAMP_LIMIT)
        ):
            # Only writes crossing below 15 °C are clamped
            await super().write_attributes(
                {occupied_heating_setpoint.name: SETPOINT_CLAMP_LIMIT},
                manufacturer=manufacturer,
                **kwargs,
            )
            await asyncio.sleep(SETPOINT_CLAMP_SETTLE_DELAY)

        return await super().write_attributes(
            attributes, manufacturer=manufacturer, **kwargs
        )

    async def bind(self):
        """Write the time after binding; the device never requests it on its own."""
        result = await super().bind()
        await self.endpoint.time.write_time()
        return result


class DeviTemperatureMeasurementCluster(CustomCluster, TemperatureMeasurement):
    """DEVI temperature measurement cluster with room and floor sensor attributes.

    The device's standard ``measured_value`` attribute is not usable (never reports a
    valid value); room/floor temperatures are exposed via manufacturer-specific
    attributes instead.
    """

    class AttributeDefs(TemperatureMeasurement.AttributeDefs):
        """Attribute definitions."""

        room_temperature: Final = ZCLAttributeDef(
            id=0x4000,
            type=t.int16s,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        )
        floor_temperature: Final = ZCLAttributeDef(
            id=0x4002,
            type=t.int16s,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        )


(
    QuirkBuilder("devi", "devi_c")
    .friendly_name(model="DEVIreg Display Connect", manufacturer="DEVI")
    .replaces(DeviThermostatCluster)
    .replaces(DeviTemperatureMeasurementCluster)
    .replaces(DanfossTimeCluster)
    .binary_sensor(
        attribute_name=DeviThermostatCluster.AttributeDefs.heater_on.name,
        cluster_id=Thermostat.cluster_id,
        device_class=BinarySensorDeviceClass.RUNNING,
        reporting_config=ReportingConfig(
            min_interval=0, max_interval=3600, reportable_change=1
        ),
        translation_key="heat_required",
        fallback_name="Heat required",
    )
    .sensor(
        attribute_name=DeviTemperatureMeasurementCluster.AttributeDefs.room_temperature.name,
        cluster_id=TemperatureMeasurement.cluster_id,
        divisor=100,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        reporting_config=ReportingConfig(
            min_interval=60, max_interval=3600, reportable_change=10
        ),
        translation_key="local_temperature",
        fallback_name="Local temperature",
    )
    .sensor(
        attribute_name=DeviTemperatureMeasurementCluster.AttributeDefs.floor_temperature.name,
        cluster_id=TemperatureMeasurement.cluster_id,
        divisor=100,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        reporting_config=ReportingConfig(
            min_interval=60, max_interval=3600, reportable_change=10
        ),
        translation_key="local_temperature_floor",
        fallback_name="Floor temperature",
    )
    # measured_value never reports a valid value; prevent the default temperature
    # entity. Matches the ZHA-native entity's legacy unique_id "{ieee}-1-1026".
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=TemperatureMeasurement.cluster_id,
        unique_id_suffix=str(TemperatureMeasurement.cluster_id),
    )
    .add_to_registry()
)
