"""Salus SQ610RF / SQ610RFNH Quantum thermostat (iT600)."""

import time
from typing import Any, Final

import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.clusters.measurement import RelativeHumidity
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.builder import QuirkBuilder
from zhaquirks.salus import (
    COMPUTIME,
    IT600_SYNC_INTERVAL,
    SALUS,
    SalusIt600Basic,
    SalusIt600Cluster,
    SalusIt600Ota,
)

THERMOSTAT_ENDPOINT = 9
WIRING_CENTRE_ENDPOINT = 8
WIRING_CENTRE_NUMBER = 1

# Record types the thermostat sends with command 0x31.
RECORD_STATUS = 0x71
RECORD_SETTINGS = 0x72

# The thermostat sends 12.34 °C instead of a reading every few minutes.
PLACEHOLDER_TEMPERATURE = 0x1234

HOLD_TYPE_PERMANENT = 2
HOLD_TYPE_STANDBY = 7
SYSTEM_MODE_COOL = 3
SYSTEM_MODE_HEAT = 4

BATTERY_LEVELS = (0, 10, 25, 50, 75, 100)


def bcd_to_int(data: bytes) -> int:
    """Decode a BCD value; a first digit of 0xB or more encodes a negative one."""
    value = 0
    for byte in data:
        value = value * 100 + (byte >> 4) * 10 + (byte & 0x0F)
    return value if value < 11000 else 11000 - value


def setpoint_to_byte(setpoint: int) -> int:
    """Encode a setpoint in centidegrees as 0.5 °C steps offset by 0x20."""
    return round(setpoint / 50) + 0x20


class SalusSQ610Cluster(SalusIt600Cluster):
    """iT600 cluster of the thermostat.

    Status arrives as record 0x71 (command 0x31) and changes are written with
    B-commands (command 0x32), as the Salus gateway does.
    """

    DEFAULT_DEVICE_NUMBER = 0x20

    class AttributeDefs(BaseAttributeDefs):
        """Local attributes, filled from the thermostat's records."""

        device_number: Final = ZCLAttributeDef(id=0x0000, type=t.uint8_t, access="r")
        child_lock: Final = ZCLAttributeDef(id=0x0001, type=t.Bool, access="rw")

    _handle: int = 0

    async def send_sync_response(self, device_number: int) -> None:
        """Send the sync response and remember the device number."""
        self.update_attribute(self.AttributeDefs.device_number.id, device_number)
        await super().send_sync_response(device_number)

    def handle_it600_command(self, command_id: int, payload: bytes) -> None:
        """Handle records, zone reports and the zone pairing handshake."""
        commands = self.ClientCommandDefs
        if command_id == commands.record.id:
            self._handle_record(payload)
            self._maybe_resend_sync()
        elif command_id == commands.zone_report.id:
            self._handle_zone_report(payload)
        elif command_id == commands.wiring_centre_request.id:
            self._reply(0x86, self._wiring_centre_response(payload))
        elif command_id == commands.zone_pair_request.id:
            self._reply(0x88, bytes.fromhex("00ff0000000000"))
        elif command_id == commands.zone_pair_confirm.id and len(payload) >= 2:
            self._reply(0x84, bytes([0x00, payload[1], 0x00]))
        else:
            super().handle_it600_command(command_id, payload)

    def _reply(self, command_id: int, payload: bytes) -> None:
        self.create_catching_task(self.send_it600_frame(command_id, payload))

    def _maybe_resend_sync(self) -> None:
        """Keep the clock right by resending the sync response once a day."""
        device_number = self.get(self.AttributeDefs.device_number.id)
        if device_number is None:
            return
        if (
            self._last_sync is not None
            and time.monotonic() - self._last_sync < IT600_SYNC_INTERVAL
        ):
            return
        self._last_sync = time.monotonic()
        self.create_catching_task(self.send_sync_response(device_number))

    def _handle_record(self, record: bytes) -> None:
        if not record:
            return
        thermostat = self.endpoint.thermostat
        attrs = Thermostat.AttributeDefs

        if record[0] == RECORD_SETTINGS and len(record) >= 26:
            thermostat.update_attribute(
                attrs.max_heat_setpoint_limit.id, bcd_to_int(record[22:24])
            )
            thermostat.update_attribute(
                attrs.min_heat_setpoint_limit.id, bcd_to_int(record[24:26])
            )
            return

        if record[0] != RECORD_STATUS or len(record) < 50:
            return

        hold_type = record[3]
        cooling = record[15] == SYSTEM_MODE_COOL
        if hold_type == HOLD_TYPE_STANDBY:
            system_mode = Thermostat.SystemMode.Off
        elif cooling:
            system_mode = Thermostat.SystemMode.Cool
        else:
            system_mode = Thermostat.SystemMode.Heat

        if int.from_bytes(record[4:6], "big") != PLACEHOLDER_TEMPERATURE:
            thermostat.update_attribute(
                attrs.local_temperature.id, bcd_to_int(record[4:6])
            )
        # In standby the active setpoint is the frost setpoint; keep the last one.
        if hold_type != HOLD_TYPE_STANDBY:
            setpoint_attr = (
                attrs.occupied_cooling_setpoint
                if cooling
                else attrs.occupied_heating_setpoint
            )
            thermostat.update_attribute(setpoint_attr.id, bcd_to_int(record[9:11]))
        thermostat.update_attribute(attrs.system_mode.id, system_mode)
        thermostat.update_attribute(
            attrs.running_state.id,
            Thermostat.RunningState.Heat_State_On
            if record[17] == 1
            else Thermostat.RunningState.Idle,
        )

        self.update_attribute(self.AttributeDefs.child_lock.id, t.Bool(record[23]))
        self.endpoint.humidity.update_attribute(
            RelativeHumidity.AttributeDefs.measured_value.id,
            bcd_to_int(record[24:25]) * 100,
        )
        if record[49] < len(BATTERY_LEVELS):
            self.endpoint.power.update_attribute(
                PowerConfiguration.AttributeDefs.battery_percentage_remaining.id,
                BATTERY_LEVELS[record[49]] * 2,
            )

    def _handle_zone_report(self, report: bytes) -> None:
        """Parse a zone report, which reaches us when we act as wiring centre.

        Layout: 02 01 <demand> <zone> 00 ff 00 00 00 00 00 ff
                <temperature x100 LE> <setpoint x100 LE> <frost x100 LE>
        """
        if len(report) < 16:
            return
        thermostat = self.endpoint.thermostat
        attrs = Thermostat.AttributeDefs
        thermostat.update_attribute(
            attrs.local_temperature.id, int.from_bytes(report[12:14], "little")
        )
        thermostat.update_attribute(
            attrs.occupied_heating_setpoint.id,
            int.from_bytes(report[14:16], "little"),
        )
        thermostat.update_attribute(
            attrs.running_state.id,
            Thermostat.RunningState.Heat_State_On
            if report[2]
            else Thermostat.RunningState.Idle,
        )

    def _wiring_centre_response(self, payload: bytes) -> bytes:
        """Answer "where is wiring centre N" from the thermostat's zone menu.

        Point it at a KL08RF on the network so the wiring centre drives the
        zone. Without one, point it at the coordinator, which then answers the
        zone pairing itself so the thermostat still reports to us.
        """
        number = payload[0] if payload else WIRING_CENTRE_NUMBER
        nwk = self._find_wiring_centre()
        if nwk is None:
            return b"\x01\x00\x00"
        if number != WIRING_CENTRE_NUMBER:
            return b"\x00\xff\xff"
        return b"\x01" + nwk.to_bytes(2, "little")

    def _find_wiring_centre(self) -> int | None:
        """Return the short address of a wiring centre on the network."""
        for device in self.endpoint.device.application.devices.values():
            if device.nwk == 0x0000:
                continue
            endpoint = device.endpoints.get(WIRING_CENTRE_ENDPOINT)
            if endpoint is not None and (
                self.cluster_id in endpoint.in_clusters
                or self.cluster_id in endpoint.out_clusters
            ):
                return int(device.nwk)
        return None

    async def it600_write(self, command: bytes, *args: int) -> None:
        """Send a B-command (0x32) with a fresh handle.

        Handles 1-127 belong to the gateway; the device uses the others.
        """
        self._handle = self._handle % 0x7F + 1
        await self.send_it600_frame(0x32, bytes([self._handle, *command, *args]))

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        *args,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Write the child lock with B03."""
        for attr, value in attributes.items():
            if self.find_attribute(attr) == self.AttributeDefs.child_lock:
                await self.it600_write(
                    b"B03", 0x00, 0x00, 0x41 if value else 0x42, *bytes(10)
                )
        return await super().write_attributes(attributes, *args, **kwargs)


class SalusThermostat(LocalDataCluster, Thermostat):
    """Thermostat cluster backed by the iT600 records and B-commands."""

    _CONSTANT_ATTRIBUTES = {
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.id: (
            Thermostat.ControlSequenceOfOperation.Heating_Only
        ),
    }
    _DEFAULT_VALUES = {
        Thermostat.AttributeDefs.min_heat_setpoint_limit.id: 500,
        Thermostat.AttributeDefs.max_heat_setpoint_limit.id: 3500,
    }

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        *args,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Send setpoint and system mode writes as B-commands."""
        it600 = self.endpoint.salus_it600
        attrs = self.AttributeDefs
        written = {}
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            if attr_def in (
                attrs.occupied_heating_setpoint,
                attrs.occupied_cooling_setpoint,
            ):
                setpoint = setpoint_to_byte(value)
                command = (
                    b"B34" if attr_def == attrs.occupied_heating_setpoint else b"B33"
                )
                await it600.it600_write(command, setpoint)
                value = (setpoint - 0x20) * 50
            elif attr_def == attrs.system_mode:
                if value == self.SystemMode.Off:
                    await it600.it600_write(b"B20", HOLD_TYPE_STANDBY)
                else:
                    await it600.it600_write(b"B20", HOLD_TYPE_PERMANENT)
                    await it600.it600_write(
                        b"B48",
                        SYSTEM_MODE_COOL
                        if value == self.SystemMode.Cool
                        else SYSTEM_MODE_HEAT,
                    )
            written[attr_def.id] = value
        return await super().write_attributes(written, *args, **kwargs)


class SalusPowerConfiguration(LocalDataCluster, PowerConfiguration):
    """Battery level from the iT600 status record."""


class SalusRelativeHumidity(LocalDataCluster, RelativeHumidity):
    """Humidity from the iT600 status record."""


(
    QuirkBuilder(SALUS, "SQ610RFNH")
    .applies_to(SALUS, "SQ610RF")
    .applies_to(COMPUTIME, "SQ610RFNH")
    .applies_to(COMPUTIME, "SQ610RF")
    .replaces(SalusIt600Basic, endpoint_id=THERMOSTAT_ENDPOINT)
    .replaces(
        SalusIt600Ota, endpoint_id=THERMOSTAT_ENDPOINT, cluster_type=ClusterType.Client
    )
    .replace_cluster_occurrences(SalusSQ610Cluster)
    .adds(SalusThermostat, endpoint_id=THERMOSTAT_ENDPOINT)
    .adds(SalusPowerConfiguration, endpoint_id=THERMOSTAT_ENDPOINT)
    .adds(SalusRelativeHumidity, endpoint_id=THERMOSTAT_ENDPOINT)
    .switch(
        attribute_name=SalusSQ610Cluster.AttributeDefs.child_lock.name,
        cluster_id=SalusSQ610Cluster.cluster_id,
        endpoint_id=THERMOSTAT_ENDPOINT,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .add_to_registry()
)
