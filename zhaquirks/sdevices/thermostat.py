"""SDevices SBDV-00205 smart thermostat.

ZHA exposes the standard Thermostat cluster as a native ``climate`` entity and
the wired floor sensor as a native temperature sensor. This quirk adds the
SDevices configuration, metering, protection and diagnostic attributes.

The weekly schedule uses the standard Thermostat ``Set/Get/Clear Weekly
Schedule`` commands. ZHA has no editable text entity for quirks v2 yet, so the
seven schedules are exposed as local CharacterString attributes. They can be
inspected and written from "Manage Zigbee device" using the Zigbee2MQTT format::

    06:00/20 08:00/17.5 18:00/21

Each day supports up to ten heat-setpoint transitions.
"""

from __future__ import annotations

import re
from typing import Any, Final

import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import DeviceTemperature
from zigpy.zcl.clusters.hvac import SeqDayOfWeek, Thermostat, UserInterface
from zigpy.zcl.foundation import Status, ZCLAttributeDef

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster
from zhaquirks.sdevices import (
    SDEVICES,
    SDEVICES_MFR_CODE,
    SDevicesCluster,
    SDevicesDeviceTemperatureCluster,
    SDevicesDiagnosticCluster,
    SDevicesReportingCluster,
    _SDevicesFirmwareReportingMixin,
)

_MAX_DAILY_TRANSITIONS = 10
_READ_ON_STARTUP = {"attribute_initialized_from_cache": False}
_TRANSITION_RE = re.compile(
    r"^(?P<hour>0[0-9]|1[0-9]|2[0-3]):(?P<minute>[0-5][0-9])/"
    r"(?P<temperature>[0-9]+(?:\.5)?)$"
)


class SensorMode(t.enum8):
    """Active temperature sensor."""

    Local = 0x00
    Remote = 0x01
    Combined = 0x02


class OutputMode(t.enum8):
    """Relay drive logic."""

    Normal = 0x00
    Inverted = 0x01


class LocalSensorType(t.enum8):
    """Wired NTC sensor resistance in kOhm."""

    k4_7 = 0x00
    k6_8 = 0x01
    k10 = 0x02
    k12 = 0x03
    k15 = 0x04
    k33 = 0x05
    k47 = 0x06


class SDevicesProgrammingOperationMode(t.enum8):
    """Programming modes supported by SBDV-00205."""

    Simple = Thermostat.ProgrammingOperationMode.Simple
    Schedule_programming_mode = (
        Thermostat.ProgrammingOperationMode.Schedule_programming_mode
    )


class SDevicesThermostatProprietaryCluster(SDevicesReportingCluster):
    """Thermostat-specific 0xFCCF cluster with the v2 emergency bitmap."""

    class AttributeDefs(SDevicesCluster.AttributeDefs):
        """Synthetic views of the thermostat emergency flags."""

        emergency_no_load: Final = ZCLAttributeDef(id=0x3201, type=t.Bool, access="r")
        emergency_no_data: Final = ZCLAttributeDef(id=0x3202, type=t.Bool, access="r")
        emergency_wrong_data: Final = ZCLAttributeDef(
            id=0x3203, type=t.Bool, access="r"
        )

    _EMERGENCY_V2_BITS: Final = {
        SDevicesCluster.AttributeDefs.emergency_overcurrent.id: 0x04,
        SDevicesCluster.AttributeDefs.emergency_overheat.id: 0x08,
        AttributeDefs.emergency_no_load.id: 0x10,
        AttributeDefs.emergency_no_data.id: 0x20,
        AttributeDefs.emergency_wrong_data.id: 0x40,
    }

    def _update_attribute(self, attrid, value):
        """Split the thermostat bitmap without applying the socket layout."""
        CustomCluster._update_attribute(self, attrid, value)
        if (
            attrid == SDevicesCluster.AttributeDefs.emergency_shutoff_state.id
            and value is not None
        ):
            for flag_id, bit in self._EMERGENCY_V2_BITS.items():
                CustomCluster._update_attribute(self, flag_id, bool(value & bit))


_SENSOR_ERROR_BITS: Final = {
    0x4121: 0x01,
    0x4122: 0x02,
    0x4123: 0x04,
}
_EVENT_STATUS_BITS: Final = {
    0x4131: 0x01,
    0x4132: 0x02,
    0x4133: 0x04,
    0x4134: 0x08,
}


class SDevicesThermostatCluster(
    _SDevicesFirmwareReportingMixin, CustomCluster, Thermostat
):
    """Thermostat cluster with local, human-readable weekly schedules."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """SDevices attributes and local schedule views."""

        remote_temperature: Final = ZCLAttributeDef(
            id=0x4001,
            type=t.int16s,
            access="rwp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        remote_temperature_calibration: Final = ZCLAttributeDef(
            id=0x4002,
            type=t.int8s,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        sensor_mode: Final = ZCLAttributeDef(
            id=0x4003,
            type=SensorMode,
            access="rwp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        open_window_enabled: Final = ZCLAttributeDef(
            id=0x4005,
            type=t.Bool,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        heating_hysteresis: Final = ZCLAttributeDef(
            id=0x4019,
            type=t.int8s,
            access="rwp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        min_local_temperature_limit: Final = ZCLAttributeDef(
            id=0x40F0,
            type=t.int16s,
            access="rwp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        max_local_temperature_limit: Final = ZCLAttributeDef(
            id=0x40F1,
            type=t.int16s,
            access="rwp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        output_mode: Final = ZCLAttributeDef(
            id=0x4100,
            type=OutputMode,
            access="rwp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        local_sensor_type: Final = ZCLAttributeDef(
            id=0x4101,
            type=LocalSensorType,
            access="rwp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        sensor_error: Final = ZCLAttributeDef(
            id=0x4102,
            type=t.bitmap16,
            access="rp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        event_status: Final = ZCLAttributeDef(
            id=0x4103,
            type=t.bitmap16,
            access="rp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        remote_sensor_timeout: Final = ZCLAttributeDef(
            id=0x4203,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        sensor_error_remote_disconnected: Final = ZCLAttributeDef(
            id=0x4121, type=t.Bool, access="r"
        )
        sensor_error_local_disconnected: Final = ZCLAttributeDef(
            id=0x4122, type=t.Bool, access="r"
        )
        sensor_error_short_circuit: Final = ZCLAttributeDef(
            id=0x4123, type=t.Bool, access="r"
        )
        status_heat_inefficient: Final = ZCLAttributeDef(
            id=0x4131, type=t.Bool, access="r"
        )
        status_antifrost: Final = ZCLAttributeDef(id=0x4132, type=t.Bool, access="r")
        status_open_window: Final = ZCLAttributeDef(id=0x4133, type=t.Bool, access="r")
        status_invalid_time: Final = ZCLAttributeDef(id=0x4134, type=t.Bool, access="r")

        schedule_monday: Final = ZCLAttributeDef(
            id=0xF100, type=t.CharacterString, access="rw"
        )
        schedule_tuesday: Final = ZCLAttributeDef(
            id=0xF101, type=t.CharacterString, access="rw"
        )
        schedule_wednesday: Final = ZCLAttributeDef(
            id=0xF102, type=t.CharacterString, access="rw"
        )
        schedule_thursday: Final = ZCLAttributeDef(
            id=0xF103, type=t.CharacterString, access="rw"
        )
        schedule_friday: Final = ZCLAttributeDef(
            id=0xF104, type=t.CharacterString, access="rw"
        )
        schedule_saturday: Final = ZCLAttributeDef(
            id=0xF105, type=t.CharacterString, access="rw"
        )
        schedule_sunday: Final = ZCLAttributeDef(
            id=0xF106, type=t.CharacterString, access="rw"
        )

    _SCHEDULE_ATTR_TO_DAY: Final = {
        AttributeDefs.schedule_monday.id: Thermostat.SeqDayOfWeek.Monday,
        AttributeDefs.schedule_tuesday.id: Thermostat.SeqDayOfWeek.Tuesday,
        AttributeDefs.schedule_wednesday.id: Thermostat.SeqDayOfWeek.Wednesday,
        AttributeDefs.schedule_thursday.id: Thermostat.SeqDayOfWeek.Thursday,
        AttributeDefs.schedule_friday.id: Thermostat.SeqDayOfWeek.Friday,
        AttributeDefs.schedule_saturday.id: Thermostat.SeqDayOfWeek.Saturday,
        AttributeDefs.schedule_sunday.id: Thermostat.SeqDayOfWeek.Sunday,
    }
    _DAY_TO_SCHEDULE_ATTR: Final = {
        day: attr_id for attr_id, day in _SCHEDULE_ATTR_TO_DAY.items()
    }

    def _update_attribute(self, attrid, value):
        """Split sensor and event status bitmaps into local Boolean views."""
        super()._update_attribute(attrid, value)
        if value is None:
            return
        if attrid == self.AttributeDefs.sensor_error.id:
            bits = _SENSOR_ERROR_BITS
        elif attrid == self.AttributeDefs.event_status.id:
            bits = _EVENT_STATUS_BITS
        else:
            return
        for flag_id, bit in bits.items():
            super()._update_attribute(flag_id, bool(value & bit))

    @staticmethod
    def _parse_schedule(value: str) -> tuple[tuple[int, int], ...]:
        """Parse and normalize ``HH:MM/temperature`` transitions."""
        if not isinstance(value, str):
            raise TypeError("Schedule must be a string")

        raw_transitions = value.split()
        if len(raw_transitions) > _MAX_DAILY_TRANSITIONS:
            raise ValueError("A day must have no more than 10 transitions")

        transitions: list[tuple[int, int]] = []
        for transition in raw_transitions:
            match = _TRANSITION_RE.fullmatch(transition)
            if match is None:
                raise ValueError(
                    "Transitions must use HH:MM/temperature format "
                    f"(for example 12:00/15.5), got: {transition}"
                )

            transition_time = int(match["hour"]) * 60 + int(match["minute"])
            heat_setpoint = round(float(match["temperature"]) * 100)
            if not 0 <= heat_setpoint <= 5000:
                raise ValueError("Schedule temperatures must be between 0 and 50 °C")
            transitions.append((transition_time, heat_setpoint))

        return tuple(sorted(transitions))

    @staticmethod
    def _format_schedule(values: list[int], count: int) -> str:
        """Format the heat-only transition list returned by the device."""
        if len(values) != count * 2:
            raise ValueError(
                f"Expected {count * 2} schedule values, received {len(values)}"
            )

        transitions = []
        for index in range(0, len(values), 2):
            transition_time, heat_setpoint = values[index : index + 2]
            hours, minutes = divmod(transition_time, 60)
            temperature = f"{heat_setpoint / 100:g}"
            transitions.append(f"{hours:02d}:{minutes:02d}/{temperature}")
        return " ".join(sorted(transitions))

    async def refresh_weekly_schedule(
        self,
        days: tuple[SeqDayOfWeek, ...] | None = None,
    ) -> None:
        """Request the schedule for every supplied day from the thermostat."""
        if days is None:
            days = tuple(self._DAY_TO_SCHEDULE_ATTR)
        for day in days:
            await self.command(
                self.ServerCommandDefs.get_weekly_schedule.id,
                day,
                self.SeqMode.Heat,
                expect_reply=False,
            )

    async def apply_custom_configuration(self, *args, **kwargs) -> None:
        """Bind reports and populate the seven local schedule attributes."""
        await self.bind()
        await self.refresh_weekly_schedule()

    async def read_attributes(
        self,
        attributes: list[int | str | ZCLAttributeDef],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> Any:
        """Serve synthetic schedules locally and request fresh device values."""
        schedule_attributes: list[
            tuple[int | str | ZCLAttributeDef, ZCLAttributeDef]
        ] = []
        regular_attributes: list[int | str | ZCLAttributeDef] = []
        for attr in attributes:
            attr_def = self.find_attribute(attr, manufacturer_code=manufacturer)
            if attr_def.id in self._SCHEDULE_ATTR_TO_DAY:
                schedule_attributes.append((attr, attr_def))
            else:
                regular_attributes.append(attr)

        if regular_attributes:
            success, failure = await super().read_attributes(
                regular_attributes,
                allow_cache=allow_cache,
                only_cache=only_cache,
                manufacturer=manufacturer,
                **kwargs,
            )
        else:
            success, failure = {}, {}

        if schedule_attributes and not only_cache:
            await self.refresh_weekly_schedule(
                tuple(
                    self._SCHEDULE_ATTR_TO_DAY[attr_def.id]
                    for _, attr_def in schedule_attributes
                )
            )
        success.update(
            {
                requested_attr: self.get(attr_def.id)
                for requested_attr, attr_def in schedule_attributes
            }
        )
        return success, failure

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Translate local schedule writes into Set Weekly Schedule commands."""
        schedule_updates: list[
            tuple[ZCLAttributeDef, SeqDayOfWeek, str, tuple[tuple[int, int], ...]]
        ] = []
        regular_attributes: dict[str | int | ZCLAttributeDef, Any] = {}

        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr, manufacturer_code=manufacturer)
            day = self._SCHEDULE_ATTR_TO_DAY.get(attr_def.id)
            if day is None:
                regular_attributes[attr] = value
                continue
            schedule_updates.append((attr_def, day, value, self._parse_schedule(value)))

        results: list[foundation.WriteAttributesStatusRecord] = []
        if regular_attributes:
            regular_results = await super().write_attributes(
                regular_attributes, manufacturer=manufacturer, **kwargs
            )
            results.extend(regular_results[0])

        grouped: dict[tuple[tuple[int, int], ...], SeqDayOfWeek] = {}
        for _, day, _, transitions in schedule_updates:
            grouped[transitions] = (
                grouped.get(transitions, Thermostat.SeqDayOfWeek(0)) | day
            )

        for transitions, days in grouped.items():
            values = [item for transition in transitions for item in transition]
            await self.command(
                self.ServerCommandDefs.set_weekly_schedule.id,
                len(transitions),
                days,
                self.SeqMode.Heat,
                values,
                expect_reply=False,
            )

        for attr_def, _, value, _ in schedule_updates:
            self.update_attribute(attr_def.id, value)
            results.append(
                foundation.WriteAttributesStatusRecord(
                    status=Status.SUCCESS,
                    attrid=attr_def.id,
                )
            )

        if schedule_updates:
            await self.refresh_weekly_schedule(
                tuple(day for _, day, _, _ in schedule_updates)
            )

        return [results]

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Any,
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Turn Get Weekly Schedule responses into the local day attributes."""
        if (
            hdr.command_id != self.ClientCommandDefs.get_weekly_schedule_response.id
            or not hasattr(args, "day_of_week_for_sequence")
        ):
            return super().handle_cluster_request(
                hdr, args, dst_addressing=dst_addressing
            )

        if args.mode_for_sequence != self.SeqMode.Heat:
            self.warning(
                "Ignoring unsupported weekly schedule mode: %s",
                args.mode_for_sequence,
            )
            return

        try:
            schedule = self._format_schedule(
                list(args.values), int(args.num_transitions_for_sequence)
            )
        except ValueError as exc:
            self.warning("Ignoring malformed weekly schedule response: %s", exc)
            return

        for day, attr_id in self._DAY_TO_SCHEDULE_ATTR.items():
            if args.day_of_week_for_sequence & day:
                self.update_attribute(attr_id, schedule)


class SDevicesUserInterfaceCluster(
    _SDevicesFirmwareReportingMixin, CustomCluster, UserInterface
):
    """Thermostat User Interface cluster with display brightness settings."""

    class AttributeDefs(UserInterface.AttributeDefs):
        """SDevices display brightness attributes."""

        brightness_operations_mode: Final = ZCLAttributeDef(
            id=0x2001,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        brightness_steady_mode: Final = ZCLAttributeDef(
            id=0x2002,
            type=t.uint16_t,
            access="rwp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        brightness_night_mode: Final = ZCLAttributeDef(
            id=0x2003,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )


_EMERGENCY_FLAGS = (
    ("emergency_overcurrent", "Emergency overcurrent"),
    ("emergency_overheat", "Emergency overheat"),
    ("emergency_no_load", "Emergency no load"),
    ("emergency_no_data", "Emergency no data"),
    ("emergency_wrong_data", "Emergency wrong data"),
)
_SENSOR_ERROR_FLAGS = (
    ("sensor_error_remote_disconnected", "Sensor error remote disconnected"),
    ("sensor_error_local_disconnected", "Sensor error local disconnected"),
    ("sensor_error_short_circuit", "Sensor error short circuit"),
)
_EVENT_STATUS_FLAGS = (
    ("status_heat_inefficient", "Heating inefficient"),
    ("status_antifrost", "Antifrost mode"),
    ("status_open_window", "Open window mode"),
    ("status_invalid_time", "Invalid time"),
)


def _add_metering(qb: QuirkBuilder) -> QuirkBuilder:
    """Add electricity metering while retaining firmware reporting defaults."""
    return (
        qb.sensor(
            attribute_name="rms_voltage_mv",
            cluster_id=SDevicesCluster.cluster_id,
            divisor=1000,
            suggested_display_precision=1,
            unit=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            **_READ_ON_STARTUP,
            fallback_name="Voltage",
        )
        .sensor(
            attribute_name="rms_current_ma",
            cluster_id=SDevicesCluster.cluster_id,
            divisor=1000,
            suggested_display_precision=3,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            **_READ_ON_STARTUP,
            fallback_name="Current",
        )
        .sensor(
            attribute_name="active_power_mw",
            cluster_id=SDevicesCluster.cluster_id,
            divisor=1000,
            suggested_display_precision=1,
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            **_READ_ON_STARTUP,
            fallback_name="Power",
        )
    )


def _add_diagnostics(qb: QuirkBuilder) -> QuirkBuilder:
    """Add supported SDevices diagnostic counters."""
    for attribute_name, unit, translation_key, fallback_name in (
        ("sdevices_uptime_s", UnitOfTime.SECONDS, "uptime", "Uptime"),
        ("number_of_resets", None, "resets_count", "Resets count"),
        ("sdevices_button1_clicks", None, "button_clicks_1", "Button 1 clicks"),
        ("sdevices_button2_clicks", None, "button_clicks_2", "Button 2 clicks"),
        ("sdevices_button3_clicks", None, "button_clicks_3", "Button 3 clicks"),
        ("sdevices_relay1_switches", None, "relay_switches_1", "Relay 1 switches"),
    ):
        qb = qb.sensor(
            attribute_name=attribute_name,
            cluster_id=SDevicesDiagnosticCluster.cluster_id,
            unit=unit,
            entity_type=EntityType.DIAGNOSTIC,
            **_READ_ON_STARTUP,
            translation_key=translation_key,
            fallback_name=fallback_name,
        )
    return qb


def _add_protection(qb: QuirkBuilder) -> QuirkBuilder:
    """Add thermostat protection thresholds and decoded emergency flags."""
    qb = (
        qb.number(
            attribute_name="upper_current_threshold",
            cluster_id=SDevicesCluster.cluster_id,
            min_value=0.1,
            max_value=16,
            step=0.1,
            multiplier=0.001,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=NumberDeviceClass.CURRENT,
            entity_type=EntityType.CONFIG,
            **_READ_ON_STARTUP,
            translation_key="upper_current_threshold",
            fallback_name="Upper current threshold",
        )
        .number(
            attribute_name="upper_temp_threshold",
            cluster_id=SDevicesCluster.cluster_id,
            min_value=10,
            max_value=85,
            step=1,
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_type=EntityType.CONFIG,
            **_READ_ON_STARTUP,
            translation_key="temperature_threshold",
            fallback_name="Overtemperature threshold",
        )
        .sensor(
            attribute_name="emergency_shutoff_state",
            cluster_id=SDevicesCluster.cluster_id,
            entity_type=EntityType.DIAGNOSTIC,
            initially_disabled=True,
            **_READ_ON_STARTUP,
            translation_key="emergency_shutoff_state",
            fallback_name="Emergency shutoff state",
        )
    )
    for attribute_name, fallback_name in _EMERGENCY_FLAGS:
        qb = qb.binary_sensor(
            attribute_name=attribute_name,
            cluster_id=SDevicesCluster.cluster_id,
            entity_type=EntityType.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            translation_key=attribute_name,
            fallback_name=fallback_name,
        )
    return qb


def _add_thermostat_diagnostics(qb: QuirkBuilder) -> QuirkBuilder:
    """Add raw status bitmaps and their decoded per-flag sensors."""
    qb = qb.sensor(
        attribute_name="sensor_error",
        cluster_id=Thermostat.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        **_READ_ON_STARTUP,
        translation_key="sensor_error",
        fallback_name="Sensor error",
    ).sensor(
        attribute_name="event_status",
        cluster_id=Thermostat.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        **_READ_ON_STARTUP,
        translation_key="event_status",
        fallback_name="Event status",
    )
    for attribute_name, fallback_name in _SENSOR_ERROR_FLAGS + _EVENT_STATUS_FLAGS:
        qb = qb.binary_sensor(
            attribute_name=attribute_name,
            cluster_id=Thermostat.cluster_id,
            entity_type=EntityType.DIAGNOSTIC,
            device_class=(
                BinarySensorDeviceClass.PROBLEM
                if attribute_name.startswith("sensor_error")
                else None
            ),
            translation_key=attribute_name,
            fallback_name=fallback_name,
        )
    return qb


def _add_thermostat_config(qb: QuirkBuilder) -> QuirkBuilder:
    """Add the SDevices thermostat configuration entities."""
    return (
        qb.enum(
            attribute_name="sensor_mode",
            enum_class=SensorMode,
            cluster_id=Thermostat.cluster_id,
            entity_type=EntityType.CONFIG,
            **_READ_ON_STARTUP,
            translation_key="sensor_mode",
            fallback_name="Sensor mode",
        )
        .enum(
            attribute_name="output_mode",
            enum_class=OutputMode,
            cluster_id=Thermostat.cluster_id,
            entity_type=EntityType.CONFIG,
            **_READ_ON_STARTUP,
            translation_key="output_mode",
            fallback_name="Output mode",
        )
        .enum(
            attribute_name="local_sensor_type",
            enum_class=LocalSensorType,
            cluster_id=Thermostat.cluster_id,
            entity_type=EntityType.CONFIG,
            **_READ_ON_STARTUP,
            translation_key="local_sensor_type",
            fallback_name="Local sensor type",
        )
        .number(
            attribute_name="heating_hysteresis",
            cluster_id=Thermostat.cluster_id,
            min_value=1.0,
            max_value=10.0,
            step=0.1,
            multiplier=0.1,
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_type=EntityType.CONFIG,
            **_READ_ON_STARTUP,
            translation_key="heating_hysteresis",
            fallback_name="Heating hysteresis",
        )
        .number(
            attribute_name="min_local_temperature_limit",
            cluster_id=Thermostat.cluster_id,
            min_value=1.0,
            max_value=35.0,
            step=0.01,
            multiplier=0.01,
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_type=EntityType.CONFIG,
            **_READ_ON_STARTUP,
            translation_key="min_local_temperature_limit",
            fallback_name="Min local temperature limit",
        )
        .number(
            attribute_name="max_local_temperature_limit",
            cluster_id=Thermostat.cluster_id,
            min_value=5.0,
            max_value=50.0,
            step=0.01,
            multiplier=0.01,
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_type=EntityType.CONFIG,
            **_READ_ON_STARTUP,
            translation_key="max_local_temperature_limit",
            fallback_name="Max local temperature limit",
        )
        .number(
            attribute_name="remote_temperature_calibration",
            cluster_id=Thermostat.cluster_id,
            min_value=-2.5,
            max_value=2.5,
            step=0.1,
            multiplier=0.1,
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_type=EntityType.CONFIG,
            **_READ_ON_STARTUP,
            translation_key="remote_temperature_calibration",
            fallback_name="Remote temperature calibration",
        )
        .number(
            attribute_name="remote_sensor_timeout",
            cluster_id=Thermostat.cluster_id,
            min_value=1,
            max_value=65535,
            step=1,
            unit=UnitOfTime.SECONDS,
            entity_type=EntityType.CONFIG,
            **_READ_ON_STARTUP,
            translation_key="remote_sensor_timeout",
            fallback_name="Remote sensor timeout",
        )
        .switch(
            attribute_name="open_window_enabled",
            cluster_id=Thermostat.cluster_id,
            entity_type=EntityType.CONFIG,
            **_READ_ON_STARTUP,
            translation_key="open_window_enabled",
            fallback_name="Open window detection",
        )
        .sensor(
            attribute_name=Thermostat.AttributeDefs.abs_min_heat_setpoint_limit.name,
            cluster_id=Thermostat.cluster_id,
            divisor=100,
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_type=EntityType.DIAGNOSTIC,
            **_READ_ON_STARTUP,
            translation_key="abs_min_heat_setpoint_limit",
            fallback_name="Abs min heat setpoint limit",
        )
        .sensor(
            attribute_name=Thermostat.AttributeDefs.abs_max_heat_setpoint_limit.name,
            cluster_id=Thermostat.cluster_id,
            divisor=100,
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_type=EntityType.DIAGNOSTIC,
            **_READ_ON_STARTUP,
            translation_key="abs_max_heat_setpoint_limit",
            fallback_name="Abs max heat setpoint limit",
        )
        .number(
            attribute_name="remote_temperature",
            cluster_id=Thermostat.cluster_id,
            min_value=-273.15,
            max_value=327.67,
            step=0.01,
            multiplier=0.01,
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_type=EntityType.CONFIG,
            initially_disabled=True,
            **_READ_ON_STARTUP,
            translation_key="remote_temperature",
            fallback_name="Remote temperature",
        )
    )


def _add_ui_config(qb: QuirkBuilder) -> QuirkBuilder:
    """Add display brightness controls."""
    for attribute_name, translation_key, fallback_name in (
        (
            "brightness_operations_mode",
            "brightness_operations_mode",
            "Brightness (active)",
        ),
        ("brightness_steady_mode", "brightness_steady_mode", "Brightness (steady)"),
        ("brightness_night_mode", "brightness_night_mode", "Brightness (night)"),
    ):
        qb = qb.number(
            attribute_name=attribute_name,
            cluster_id=UserInterface.cluster_id,
            min_value=0,
            max_value=1000,
            step=1,
            entity_type=EntityType.CONFIG,
            **_READ_ON_STARTUP,
            translation_key=translation_key,
            fallback_name=fallback_name,
        )
    return qb


def _build_thermostat(manufacturer: str, model: str) -> QuirkBuilder:
    """Build the complete SBDV-00205 quirk."""
    qb = (
        QuirkBuilder(manufacturer, model)
        .replaces(SDevicesThermostatCluster)
        .replaces(SDevicesUserInterfaceCluster)
        .prevent_default_entity_creation(
            endpoint_id=1,
            cluster_id=UserInterface.cluster_id,
            function=lambda entity: entity.translation_key == "keypad_lockout",
        )
        .switch(
            attribute_name=UserInterface.AttributeDefs.keypad_lockout.name,
            cluster_id=UserInterface.cluster_id,
            off_value=0,
            on_value=1,
            entity_type=EntityType.CONFIG,
            translation_key="child_lock",
            fallback_name="Child lock",
        )
        .replaces(SDevicesThermostatProprietaryCluster)
        .replaces(SDevicesDiagnosticCluster)
        .replaces(SDevicesDeviceTemperatureCluster)
        .prevent_default_entity_creation(
            endpoint_id=1,
            cluster_id=DeviceTemperature.cluster_id,
            function=lambda entity: entity.__class__.__name__ == "DeviceTemperature",
        )
        .sensor(
            attribute_name=DeviceTemperature.AttributeDefs.current_temperature.name,
            cluster_id=DeviceTemperature.cluster_id,
            endpoint_id=1,
            divisor=1,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            unit=UnitOfTemperature.CELSIUS,
            entity_type=EntityType.DIAGNOSTIC,
            unique_id_suffix=str(DeviceTemperature.cluster_id),
            **_READ_ON_STARTUP,
            translation_key="device_temperature",
            fallback_name="Device temperature",
        )
        .enum(
            attribute_name=Thermostat.AttributeDefs.programing_oper_mode.name,
            enum_class=SDevicesProgrammingOperationMode,
            cluster_id=Thermostat.cluster_id,
            entity_type=EntityType.CONFIG,
            **_READ_ON_STARTUP,
            translation_key="programming_operation_mode",
            fallback_name="Programming operation mode",
        )
        .command_button(
            command_name=Thermostat.ServerCommandDefs.clear_weekly_schedule.name,
            cluster_id=Thermostat.cluster_id,
            entity_type=EntityType.CONFIG,
            translation_key="sdevices_clear_weekly_schedule",
            fallback_name=(
                "Clear weekly schedule (configure via SDevices Thermostat "
                "attributes schedule_monday through schedule_sunday, "
                "format HH:MM/temperature)"
            ),
        )
    )
    qb = _add_metering(qb)
    qb = _add_protection(qb)
    qb = _add_thermostat_diagnostics(qb)
    qb = _add_thermostat_config(qb)
    qb = _add_ui_config(qb)
    return _add_diagnostics(qb)


_thermostat = _build_thermostat(SDEVICES, "SBDV-00205")

_thermostat.add_to_registry()
