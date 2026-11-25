"""Aqara W600 TRV (lumi.airrtc.aeu005 / WT-A03E) ZHA quirk.

The mode path follows the Zigbee2MQTT createW600Thermostat()
reference.  W600 mode is a composite state in Aqara cluster 0xFCC0 and must
not be written to standard Thermostat.system_mode (0x0201/0x001C).  The
setpoint path follows the Z2M reference order: wake an explicitly off
device into heat via ``0xFCC0/0x0271=1`` first, then write the standard
``0x0201/0x0012`` occupied heating setpoint, then arm the manual override
when the schedule is on.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
import logging
import math
import struct
import time
from typing import Any, Final

import zigpy.exceptions
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.helpers import ReportingConfig as ZigpyReportingConfig

from zhaquirks import CustomCluster, LocalDataCluster
from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
)
from zhaquirks.device import CustomZigpyDevice

_LOGGER = logging.getLogger(__name__)

# Device match and vendor code from the W600/WT-A03E ZHA diagnostic snapshot.
AQARA: Final = "Aqara"
MODEL: Final = "lumi.airrtc.aeu005"
AQARA_MANUFACTURER_CODE: Final = 4447  # 0x115F, ZHA/Zigbee2MQTT mapping

# Standard Thermostat cluster (0x0201), ZCL-defined attributes.
ATTR_OCCUPIED_HEATING_SETPOINT: Final = 0x0012
ATTR_CTRL_SEQUENCE_OF_OPER: Final = 0x001B
ATTR_SYSTEM_MODE: Final = 0x001C
ATTR_TEMP_SETPOINT_HOLD: Final = 0x0023
ATTR_TEMP_SETPOINT_HOLD_DURATION: Final = 0x0024
ATTR_RUNNING_STATE: Final = 0x0029

# Standard ZCL enum/map values.  0x02 means Heating Only and is the
# capability value that removes cooling modes from the ZHA climate entity.
SYS_OFF: Final = 0x00
SYS_AUTO: Final = 0x01
SYS_HEAT: Final = 0x04
CTRL_SEQ_HEATING_ONLY: Final = 0x02
RUNSTATE_HEAT_ON: Final = 0x0001
RUNSTATE_IDLE: Final = 0x0000

# Protocol reference (attributes, presets and external sensor framing):
# https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/src/lib/lumi.ts
# WT-A03E Zigbee2MQTT mapping:
# https://www.zigbee2mqtt.io/devices/WT-A03E.html
# Device-support context:
# https://github.com/zigpy/zha-device-handlers/issues/4518
# Attribute IDs/types are also present in the anonymized W600 ZHA diagnostic
# snapshot attached to the device support request.
# The mode attributes 0x0271/0x027D and valve 0x0360 were also exercised on
# a real W600. Current Zigbee2MQTT models valve position as float percent.
ATTR_THERMOSTAT_ENABLED: Final = 0x0271
ATTR_CALIBRATE: Final = 0x0270
ATTR_WINDOW_DETECTION: Final = 0x0273
# Configures abnormal-control notifications; the actual alarm is in heartbeat 9C.
ATTR_TEMPERATURE_CONTROL_ABNORMAL_NOTIFICATION: Final = 0x0274
ATTR_CHILD_LOCK: Final = 0x0277
ATTR_ANTI_FREEZE_TEMPERATURE: Final = 0x0279
ATTR_CALIBRATED: Final = 0x027B
ATTR_SCHEDULE_ENABLED: Final = 0x027D
ATTR_DEVICE_STATE_AUX: Final = 0x0310
ATTR_DEVICE_STATE: Final = 0x0311
ATTR_DISPLAY_FLIP: Final = 0x0330
ATTR_VALVE_POSITION_RAW: Final = 0x0360
ATTR_HEARTBEAT: Final = 0x00F7
ATTR_PRESET_TEMPERATURE_TABLE: Final = 0x0317
ATTR_TEMPERATURE_SOURCE: Final = 0x0280
ATTR_EXTERNAL_SENSOR_STATUS: Final = 0x027E
ATTR_EXTERNAL_SENSOR_BINDING: Final = 0xFFF2
# Protocol-defined virtual identity from public Z2M code, not a user address.
W600_VIRTUAL_SENSOR: Final = bytes.fromhex("00158d00019d1b98")
W600_EXTERNAL_FRESHNESS: Final = 60.0  # Sample policy, not firmware timeout.
W600_EXTERNAL_CHANNELS: Final = {
    "temperature": (
        0x14,
        bytes.fromhex("00010055"),
        bytes.fromhex("150a0100000106e6b8a9e5baa6000000000001010765"),
    ),
    "availability": (
        0x17,
        bytes.fromhex("080007fd"),
        bytes.fromhex("150a0109e8aebee5a487e59ca8000000000001010365"),
    ),
}
PRESET_IDS: Final = (1, 2, 3, 5, 6)


def _decode_w600_preset_table(value: Any) -> dict[int, int]:
    """Accept complete tables only; preserve unknown records on later writes."""
    if not isinstance(value, bytes) or not value or len(value) != 1 + 5 * value[0]:
        return {}
    result = {}
    for offset in range(1, len(value), 5):
        preset = value[offset]
        if preset in PRESET_IDS:
            temperature = int.from_bytes(value[offset + 3 : offset + 5], "little")
            if preset in result or not 500 <= temperature <= 3000:
                return {}
            result[preset] = temperature
    return result if set(result) == set(PRESET_IDS) else {}


class W600Preset(t.enum8):
    """Native W600 profiles; Manual is entered through a setpoint write."""

    Home = 1
    Away = 2
    Sleep = 3
    Vacation = 5
    Wind_down = 6
    Manual = 255


def _temperature_source_name(value):
    return {0: "internal", 1: "external"}.get(value)


class W600TemperatureSource(t.enum8):
    """Select the temperature sensor used for regulation."""

    Internal = 0
    External = 1


class _ExternalTransactionFailed(Exception):
    """An external-source write failed or was superseded by a newer choice."""


def _external_request_channel(value):
    """Validate the W600 request envelope before responding."""
    if not isinstance(value, bytes) or len(value) != 21:
        return None
    if value[:4] != bytes.fromhex("aa710f84") or value[6:8] != b"\x06\x41":
        return None
    if value[8] not in (12, 15) or sum(value[:6]) & 0xFF:
        return None
    if value[9:17] != W600_VIRTUAL_SENSOR:
        return None
    return next(
        (
            name
            for name, (_, marker, _) in W600_EXTERNAL_CHANNELS.items()
            if value[17:] == marker
        ),
        None,
    )


def _external_sensor_problem(value):
    return {0: False, 1: False, 2: True}.get(value)


def _optional_flag(value):
    """Preserve unknown flags with a non-null local sentinel."""
    return {0: False, 1: True}.get(value)


def _decode_w600_heartbeat(value: Any) -> dict[int, Any]:
    """Decode W600 typed fields atomically; malformed packets publish nothing."""
    if not isinstance(value, (bytes, bytearray)):
        return {}
    remaining = bytes(value)
    fields = {}
    try:
        while remaining:
            key, remaining = t.uint8_t.deserialize(remaining)
            if not remaining or remaining[0] not in (
                0x10,
                0x20,
                0x21,
                0x23,
                0x28,
                0x29,
                0x30,
                0x31,
                0x41,
            ):
                return {}
            field, remaining = foundation.TypeValue.deserialize(remaining)
            fields[int(key)] = field.value
    except (ValueError, KeyError, TypeError):
        return {}
    return fields


class AqaraW600Status(LocalDataCluster):
    """Local derived values only: never send these attribute IDs over Zigbee."""

    cluster_id = 0xFC01
    ep_attribute = "w600_status"
    name = "W600 status"

    def __init__(self, *args, **kwargs):
        """Initialize per-device synchronization and protocol state."""
        super().__init__(*args, **kwargs)
        self._preset_lock = asyncio.Lock()

    class AttributeDefs(BaseAttributeDefs):
        """Define locally derived W600 status and control attributes."""

        battery_percentage: Final = ZCLAttributeDef(
            id=0x0000, type=t.uint8_t, access="r"
        )
        battery_millivolts: Final = ZCLAttributeDef(
            id=0x0001, type=t.uint16_t, access="r"
        )
        window_open: Final = ZCLAttributeDef(id=0x0002, type=t.uint8_t, access="r")
        valve_alarm: Final = ZCLAttributeDef(id=0x0003, type=t.uint8_t, access="r")
        external_temperature_problem: Final = ZCLAttributeDef(
            id=0x0004, type=t.uint8_t, access="r"
        )
        # W600 uses 255 as a real profile value. uint16 prevents ZHA's
        # numeric sensor from treating this local mirror as a uint8 non-value.
        device_state_raw: Final = ZCLAttributeDef(
            id=0x0005, type=t.uint16_t, access="r"
        )
        schedule_control: Final = ZCLAttributeDef(
            id=0x0006, type=t.uint8_t, access="rw"
        )
        external_temperature_input: Final = ZCLAttributeDef(
            id=0x0007, type=t.int16s, access="rw"
        )
        preset_home_temperature: Final = ZCLAttributeDef(
            id=0x0010, type=t.uint16_t, access="rw"
        )
        preset_away_temperature: Final = ZCLAttributeDef(
            id=0x0011, type=t.uint16_t, access="rw"
        )
        preset_sleep_temperature: Final = ZCLAttributeDef(
            id=0x0012, type=t.uint16_t, access="rw"
        )
        preset_vacation_temperature: Final = ZCLAttributeDef(
            id=0x0013, type=t.uint16_t, access="rw"
        )
        preset_wind_down_temperature: Final = ZCLAttributeDef(
            id=0x0014, type=t.uint16_t, access="rw"
        )

    _VALID_ATTRIBUTES = {
        0x0000,
        0x0001,
        0x0002,
        0x0003,
        0x0004,
        0x0005,
        0x0006,
        0x0007,
        *range(0x0010, 0x0015),
    }
    _DEFAULT_VALUES = {0x0002: 255, 0x0003: 255, 0x0004: 255}

    def _restore_status_cache(self):
        """Cache cloning bypasses report hooks; restore telemetry without radio IO."""
        if getattr(self, "_restoring_status", False):
            return
        fcc0 = getattr(self.endpoint, "aqara_w600_fcc0", None)
        if not isinstance(fcc0, AqaraW600FCC0):
            return
        self._restoring_status = True
        try:
            for attrid in (
                ATTR_HEARTBEAT,
                ATTR_DEVICE_STATE,
                ATTR_SCHEDULE_ENABLED,
                ATTR_EXTERNAL_SENSOR_STATUS,
                ATTR_PRESET_TEMPERATURE_TABLE,
            ):
                value = fcc0.get(attrid)
                if value is not None:
                    fcc0._sync_status_attribute(attrid, value)
        finally:
            self._restoring_status = False

    def get(self, key, default=None):
        """Restore missing derived values from the vendor attribute cache."""
        value = super().get(key, default)
        if value is None or value == 255:
            self._restore_status_cache()
            return super().get(key, default)
        return value

    async def _read_preset_table(self):
        fcc0 = self.endpoint.aqara_w600_fcc0
        value = fcc0.get(ATTR_PRESET_TEMPERATURE_TABLE)
        if not _decode_w600_preset_table(value):
            success, _ = await fcc0.read_attributes(
                [ATTR_PRESET_TEMPERATURE_TABLE],
                manufacturer=AQARA_MANUFACTURER_CODE,
                allow_cache=False,
            )
            value = success.get(ATTR_PRESET_TEMPERATURE_TABLE)
        return value

    async def read_attributes_raw(self, attributes, manufacturer=None, **kwargs):
        """Read local values and explicitly requested control state."""
        self._restore_status_cache()
        if 0x0006 in attributes:
            fcc0 = self.endpoint.aqara_w600_fcc0
            if fcc0.get(ATTR_SCHEDULE_ENABLED) is None:
                await fcc0.read_attributes(
                    [ATTR_SCHEDULE_ENABLED],
                    manufacturer=AQARA_MANUFACTURER_CODE,
                    allow_cache=False,
                )
            self.update_attribute(0x0006, fcc0.get(ATTR_SCHEDULE_ENABLED))
        if 0x0005 in attributes:
            fcc0 = self.endpoint.aqara_w600_fcc0
            try:
                await fcc0.read_attributes(
                    [ATTR_DEVICE_STATE],
                    manufacturer=AQARA_MANUFACTURER_CODE,
                    allow_cache=False,
                )
            except (TimeoutError, zigpy.exceptions.DeliveryError) as exc:
                _LOGGER.debug("W600 profile state read deferred: %s", exc)
            value = fcc0.get(ATTR_DEVICE_STATE)
            if value is not None:
                self.update_attribute(0x0005, value)
        if 0x0004 in attributes:
            fcc0 = self.endpoint.aqara_w600_fcc0
            try:
                await fcc0.read_attributes(
                    [ATTR_EXTERNAL_SENSOR_STATUS],
                    manufacturer=AQARA_MANUFACTURER_CODE,
                    allow_cache=False,
                )
            except (TimeoutError, zigpy.exceptions.DeliveryError) as exc:
                _LOGGER.debug("W600 external status read deferred: %s", exc)
        if any(attr in range(0x0010, 0x0015) for attr in attributes):
            async with self._preset_lock:
                try:
                    value = await self._read_preset_table()
                except (TimeoutError, zigpy.exceptions.DeliveryError) as exc:
                    _LOGGER.debug("W600 preset table read deferred: %s", exc)
                    value = None
                if _decode_w600_preset_table(value):
                    self.endpoint.aqara_w600_fcc0.update_attribute(
                        ATTR_PRESET_TEMPERATURE_TABLE, value
                    )
        return await super().read_attributes_raw(
            attributes, manufacturer=manufacturer, **kwargs
        )

    async def write_attributes(self, attributes, manufacturer=None, **kwargs):
        """Modify known profile entries without replacing the other table bytes."""
        if len(attributes) == 1:
            key, value = next(iter(attributes.items()))
            if self.find_attribute(key).id == 0x0006:
                result = await self.endpoint.aqara_w600_fcc0.set_schedule_enabled(value)
                return _map_write_result(result, [0x0006])
            if self.find_attribute(key).id == 0x0007:
                return await self.endpoint.aqara_w600_fcc0.set_external_temperature(
                    centidegrees=value
                )
        changes = {}
        for key, value in attributes.items():
            attr = self.find_attribute(key).id
            if attr not in range(0x0010, 0x0015):
                return [
                    [
                        foundation.WriteAttributesStatusRecord(
                            foundation.Status.READ_ONLY, attrid=attr
                        )
                    ]
                ]
            if (
                not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 500 <= value <= 3000
                or value % 50
            ):
                return [
                    [
                        foundation.WriteAttributesStatusRecord(
                            foundation.Status.INVALID_VALUE, attrid=attr
                        )
                    ]
                ]
            changes[PRESET_IDS[attr - 0x0010]] = int(value)
        async with self._preset_lock:
            raw = await self._read_preset_table()
            if not _decode_w600_preset_table(raw):
                return _map_write_result(
                    [], [0x0010 + PRESET_IDS.index(preset) for preset in changes]
                )
            table = bytearray(raw)
            for offset in range(1, len(table), 5):
                if table[offset] in changes:
                    table[offset + 3 : offset + 5] = changes[table[offset]].to_bytes(
                        2, "little"
                    )
            fcc0 = self.endpoint.aqara_w600_fcc0
            result = await fcc0.write_attributes(
                {ATTR_PRESET_TEMPERATURE_TABLE: t.LVBytes(table)},
                manufacturer=AQARA_MANUFACTURER_CODE,
                update_cache=False,
            )
            if _all_success(result):
                fcc0.update_attribute(ATTR_PRESET_TEMPERATURE_TABLE, t.LVBytes(table))
            return _map_write_result(
                result, [0x0010 + PRESET_IDS.index(preset) for preset in changes]
            )


# Confirmed mode matrix from the WT-A03E converter and real-device tests.
# The standard 0x0201/0x001C attribute is deliberately never sent.
W600_MODE_WRITES: Final = {
    SYS_OFF: {
        ATTR_THERMOSTAT_ENABLED: 0,
        ATTR_SCHEDULE_ENABLED: 0,
    },
    SYS_HEAT: {
        ATTR_THERMOSTAT_ENABLED: 1,
        ATTR_SCHEDULE_ENABLED: 0,
    },
    SYS_AUTO: {
        ATTR_THERMOSTAT_ENABLED: 1,
        ATTR_SCHEDULE_ENABLED: 1,
    },
}

# Keep the diagnostic entity's existing identity. Current Zigbee2MQTT uses
# SINGLE_PREC percent for 0x0360; confirm the wire type on deployed firmware.
# Zero means idle, positive means heating unless explicitly disabled.


def _iter_status_records(records: Any) -> Iterable[Any]:
    """Yield write-status records from Zigpy's nested response shape.

    Current Zigpy returns ``list[list[WriteAttributesStatusRecord]]`` because
    one call may be split into multiple wire requests.  Older releases and
    some test doubles return a flat list, so both shapes are accepted.
    """
    if isinstance(records, (list, tuple)):
        for item in records:
            yield from _iter_status_records(item)
    elif records is not None:
        yield records


def _all_success(records: Any) -> bool:
    """Return true only when every Zigpy write-status record is successful."""
    flattened = list(_iter_status_records(records))
    return bool(flattened) and all(
        getattr(record, "status", None) == foundation.Status.SUCCESS
        for record in flattened
    )


def _map_write_result(records, attribute_ids):
    """Map failed wire transactions back to the local attributes ZHA wrote."""
    if _all_success(records):
        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
    status = next(
        (
            record.status
            for record in _iter_status_records(records)
            if record.status != foundation.Status.SUCCESS
        ),
        foundation.Status.FAILURE,
    )
    return [
        [
            foundation.WriteAttributesStatusRecord(status, attrid=attrid)
            for attrid in attribute_ids
        ]
    ]


def _calibration_status_name(value: Any) -> str:
    """Return a stable human-readable name for the confirmed 0x027B enum."""
    return {
        0: "not_ready",
        1: "ready",
        2: "error",
        3: "in_progress",
    }.get(int(value), f"unknown_{value}")


def _key_matches_attrid(key: Any, attrid: int, name: str) -> bool:
    """Match a ``write_attributes`` dict key in every form Zigpy accepts.

    Zigpy's public ``write_attributes`` takes attribute names (str),
    numeric attribute ids (int) and ``ZCLAttributeDef`` objects as dict
    keys.  The quirk must recognise sensitive keys -- above all the
    standard ``system_mode``, which must never leak to the device -- in
    all accepted forms.
    """
    if isinstance(key, foundation.ZCLAttributeDef):
        return key.id == attrid or key.name == name
    if isinstance(key, str):
        return key == name
    try:
        return int(key) == attrid
    except (TypeError, ValueError):
        return False


class AqaraW600Thermostat(CustomCluster, Thermostat):
    """Thermostat cluster with W600's composite off/heat/auto mode path."""

    _CONSTANT_ATTRIBUTES = {
        ATTR_CTRL_SEQUENCE_OF_OPER: CTRL_SEQ_HEATING_ONLY,
    }

    def _fcc0(self):
        return getattr(self.endpoint, "aqara_w600_fcc0", None)

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Keep ZHA's stock Thermostat entity in a heating-only shape.

        ZHA 2.3 maps standard ZCL ``SystemMode.Auto`` to Home Assistant's
        ``heat_cool`` UI, which expects cooling setpoints the W600 does not
        implement and consequently leaves ``target_temperature`` empty.  The
        W600 schedule state remains cached in 0xFCC0/0x027D and is still used
        for writes; the generic ZHA entity is presented as heating-only until
        a dedicated entity implementation can expose a true ``auto`` mode.
        """
        if attrid == ATTR_CTRL_SEQUENCE_OF_OPER:
            value = CTRL_SEQ_HEATING_ONLY
        elif attrid == ATTR_SYSTEM_MODE and value == SYS_AUTO:
            value = SYS_HEAT
        super()._update_attribute(attrid, value)

    async def _write_fcc0(self, attributes: dict[int, int]):
        """Write confirmed W600 attributes with Aqara manufacturer code.

        ``update_cache=False`` keeps Zigpy from locally caching the
        attributes of a write before it is validated: the quirk updates
        the FCC0 cache itself only after the complete write set
        succeeded, so one partially failed write changes nothing
        locally (rule: no local state change presented as success).
        """
        fcc0 = self._fcc0()
        if fcc0 is None:
            raise RuntimeError("W600 Aqara cluster 0xFCC0 is unavailable")
        return await fcc0.write_attributes(
            attributes,
            manufacturer=AQARA_MANUFACTURER_CODE,
            update_cache=False,
        )

    def _sync_system_mode_from_w600(self) -> None:
        """Publish the persistent mode from enable and schedule telemetry."""
        fcc0 = self._fcc0()
        if fcc0 is None:
            return

        enabled = fcc0._attr_cache.get(ATTR_THERMOSTAT_ENABLED)
        schedule = fcc0._attr_cache.get(ATTR_SCHEDULE_ENABLED)
        if enabled is None:
            return

        if int(enabled) == 0:
            mode = SYS_OFF
        elif int(schedule or 0) != 0:
            mode = SYS_AUTO
        else:
            mode = SYS_HEAT
        self._update_attribute(ATTR_SYSTEM_MODE, mode)

    def _sync_running_state_from_valve(self, valve_position: Any) -> None:
        """Map valve telemetry to action only; never to persistent HVAC mode.

        Preserve fractional openings. An unknown enable state must not hide
        an observed opening, while explicit off retains the climate's idle
        convention. Missing or invalid valve samples do not invent a state.
        """
        fcc0 = self._fcc0()
        enabled = (
            fcc0._attr_cache.get(ATTR_THERMOSTAT_ENABLED) if fcc0 is not None else None
        )
        if enabled is not None and int(enabled) == 0:
            state = RUNSTATE_IDLE
        else:
            if (
                not isinstance(valve_position, (int, float))
                or not math.isfinite(valve_position)
                or valve_position < 0
            ):
                return
            state = RUNSTATE_HEAT_ON if valve_position > 0 else RUNSTATE_IDLE
        self._update_attribute(ATTR_RUNNING_STATE, state)

    async def _set_w600_mode(self, requested_mode: int) -> bool:
        """Apply the Z2M mode matrix without a standard system_mode write."""
        if requested_mode not in W600_MODE_WRITES:
            return False

        status = await self._write_fcc0(W600_MODE_WRITES[requested_mode])
        if not _all_success(status):
            return False

        # Z2M clears manual override for all explicit mode changes.
        hold_status = await super().write_attributes({ATTR_TEMP_SETPOINT_HOLD: 0})
        if not _all_success(hold_status):
            return False

        # Change the cache only after all device writes have succeeded.
        fcc0 = self._fcc0()
        for attrid, value in W600_MODE_WRITES[requested_mode].items():
            fcc0._update_attribute(attrid, value)
        self._update_attribute(ATTR_TEMP_SETPOINT_HOLD, 0)
        self._sync_system_mode_from_w600()
        if requested_mode == SYS_OFF:
            self._update_attribute(ATTR_RUNNING_STATE, RUNSTATE_IDLE)
        return True

    async def _prepare_setpoint_write(self) -> bool:
        """Wake an explicitly off thermostat into heat before the setpoint.

        Follows the Zigbee2MQTT reference order: ``0xFCC0/0x0271=1`` is sent
        before the standard ``0x0201/0x0012`` setpoint so the device is
        already in heat when the new target temperature arrives.

        The wake is attempted **only** when the FCC0 cache explicitly carries
        ``ATTR_THERMOSTAT_ENABLED == 0``.  An unknown cache (sleeping device,
        before the first attribute read) is treated as "do not wake" — the
        setpoint write must never be blocked on extra 0xFCC0 traffic, that
        was the regression that broke ``target_temperature`` in the climate
        card.  Returns ``True`` when a wake write was sent and succeeded,
        ``False`` otherwise; the caller must always proceed with the setpoint
        regardless of this return value.
        """
        fcc0 = self._fcc0()
        if fcc0 is None:
            return False

        # ``_attr_cache.get(...) is None`` distinguishes "unknown" from
        # an explicit zero.  Only an explicit zero triggers the wake.
        enabled_raw = fcc0._attr_cache.get(ATTR_THERMOSTAT_ENABLED)
        if enabled_raw is None or int(enabled_raw) != 0:
            return False

        try:
            status = await self._write_fcc0({ATTR_THERMOSTAT_ENABLED: 1})
        except (TimeoutError, zigpy.exceptions.DeliveryError) as exc:
            _LOGGER.warning(
                "W600 wake write (0xFCC0/0x0271=1) before setpoint failed: %s",
                exc,
            )
            return False

        if not _all_success(status):
            _LOGGER.warning(
                "W600 wake write (0xFCC0/0x0271=1) before setpoint returned a"
                " non-success status record; setpoint will be sent anyway"
            )
            return False

        fcc0._update_attribute(ATTR_THERMOSTAT_ENABLED, 1)
        self._sync_system_mode_from_w600()
        return True

    async def write_attributes(
        self, attributes: dict[str, Any], *args: Any, **kwargs: Any
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Route system_mode to 0xFCC0 and retain standard setpoint handling.

        Order for the setpoint path follows the Zigbee2MQTT reference:
        wake the device into heat first (when the cache explicitly says it
        is off), then write the standard setpoint, then arm the manual
        override when the schedule is on.
        """
        outgoing = dict(attributes)
        # Pop every accepted key form for system_mode; the last one wins
        # when a caller passes several.  This keeps the standard
        # 0x001C write strictly off the wire no matter how the caller
        # spells the key.
        requested_mode = None
        for key in list(outgoing):
            if _key_matches_attrid(key, ATTR_SYSTEM_MODE, "system_mode"):
                requested_mode = outgoing.pop(key)
        has_setpoint = any(
            _key_matches_attrid(
                key, ATTR_OCCUPIED_HEATING_SETPOINT, "occupied_heating_setpoint"
            )
            for key in outgoing
        )
        # Keep a flat internal list; Zigpy's public return shape is rebuilt
        # as one outer list at the end.  This matters on current Zigpy, where
        # ``Cluster.write_attributes`` returns list[list[StatusRecord]].
        result = []

        if requested_mode is not None:
            try:
                requested_mode = int(requested_mode)
            except (TypeError, ValueError):
                requested_mode = -1
            if requested_mode not in (SYS_OFF, SYS_HEAT, SYS_AUTO):
                result.append(
                    foundation.WriteAttributesStatusRecord(
                        status=foundation.Status.UNSUPPORTED_ATTRIBUTE,
                        attrid=ATTR_SYSTEM_MODE,
                    )
                )
            elif not await self._set_w600_mode(requested_mode):
                result.append(
                    foundation.WriteAttributesStatusRecord(
                        status=foundation.Status.FAILURE,
                        attrid=ATTR_SYSTEM_MODE,
                    )
                )
            else:
                result.append(
                    foundation.WriteAttributesStatusRecord(
                        status=foundation.Status.SUCCESS,
                        attrid=ATTR_SYSTEM_MODE,
                    )
                )

        # Per the Z2M reference, wake a sleeping/off device into heat before
        # the setpoint.  This is best-effort: a wake failure only logs and
        # never blocks the standard 0x0201/0x0012 write that follows.
        if has_setpoint:
            await self._prepare_setpoint_write()

        # The temperature write is the primary operation.  Do not gate it on
        # extra 0xFCC0 traffic: an unknown enabled-cache must not block the
        # write, and a sleeping battery device may defer the response.
        if outgoing:
            result.extend(
                _iter_status_records(
                    await super().write_attributes(outgoing, *args, **kwargs)
                )
            )

        if has_setpoint and outgoing:
            fcc0 = self._fcc0()
            if (
                fcc0 is not None
                and int(fcc0._attr_cache.get(ATTR_SCHEDULE_ENABLED) or 0) != 0
            ):
                hold_status = await super().write_attributes(
                    {ATTR_TEMP_SETPOINT_HOLD: 1}
                )
                if _all_success(hold_status):
                    self._update_attribute(ATTR_TEMP_SETPOINT_HOLD, 1)
                else:
                    _LOGGER.warning(
                        "W600 setpoint was written but manual override was not enabled"
                    )

        # Current Zigpy expects list[list[WriteAttributesStatusRecord]].
        # Returning the same shape also keeps ZHA's write helper compatible
        # when a mode and a setpoint are written in one service call.
        return [result]

    async def refresh_w600_mode_state(self) -> None:
        """Read the Z2M startup state needed to reconstruct the climate mode."""
        fcc0 = self._fcc0()
        if fcc0 is None:
            return
        await fcc0.read_attributes(
            [ATTR_THERMOSTAT_ENABLED, ATTR_SCHEDULE_ENABLED, ATTR_DEVICE_STATE],
            manufacturer=AQARA_MANUFACTURER_CODE,
        )
        await super().read_attributes(
            [ATTR_TEMP_SETPOINT_HOLD, ATTR_TEMP_SETPOINT_HOLD_DURATION]
        )
        self._sync_system_mode_from_w600()


class AqaraW600FCC0(CustomCluster):
    """Confirmed Aqara W600 attributes on manufacturer cluster 0xFCC0."""

    cluster_id = 0xFCC0
    name = "AqaraW600FCC0"
    ep_attribute = "aqara_w600_fcc0"

    def __init__(self, *args, **kwargs):
        """Initialize per-device synchronization and protocol state."""
        super().__init__(*args, **kwargs)
        # CatchingTaskMixin otherwise defaults to a class-shared task set.
        # Device removal must cancel only this cluster's request responses.
        self._tasks = set()
        self._external_lock = asyncio.Lock()
        self._external_generation = 0
        self._external_active = False
        self._external_availability = False
        self._external_sample = None
        self._external_requests = {}
        self._external_counter = 0x12
        self.endpoint.device.zdo.add_listener(self)
        self.endpoint.device._on_remove_callbacks.append(self._close_external)

    def _reset_external(self):
        self._external_generation += 1
        self._external_active = False
        self._external_availability = False
        self._external_sample = None
        self._external_requests.clear()
        status = getattr(self.endpoint, "w600_status", None)
        if status is not None:
            status.update_attribute(0x0007, None)

    def device_announce(self, device):
        """Never reuse cached samples after an observed device restart/rejoin."""
        self._reset_external()

    def _close_external(self):
        self._reset_external()
        self.endpoint.device.zdo.remove_listener(self)
        for task in tuple(self._tasks):
            task.cancel()

    async def _external_write(self, attrid, value, generation):
        if generation != self._external_generation:
            raise _ExternalTransactionFailed
        try:
            result = await super().write_attributes(
                {attrid: value},
                manufacturer=AQARA_MANUFACTURER_CODE,
                update_cache=False,
            )
        except (TimeoutError, zigpy.exceptions.DeliveryError):
            # Only protocol metadata: no sensor identities or raw payloads.
            action = value[6] if attrid == ATTR_EXTERNAL_SENSOR_BINDING else None
            slot = (
                value[13]
                if attrid == ATTR_EXTERNAL_SENSOR_BINDING and action in (2, 4)
                else None
            )
            _LOGGER.warning(
                "W600 external write failed: attribute=0x%04x, action=%s, slot=%s",
                attrid,
                action,
                slot,
            )
            raise
        if not _all_success(result) or generation != self._external_generation:
            raise _ExternalTransactionFailed

    async def _external_payload(self, action, body, generation):
        header = bytes((0xAA, 0x71, len(body) + 3, 0x44, self._external_counter))
        self._external_counter = (self._external_counter + 1) & 0xFF
        payload = (
            header + bytes(((-sum(header)) & 0xFF, action, 0x41, len(body))) + body
        )
        await self._external_write(
            ATTR_EXTERNAL_SENSOR_BINDING, t.LVBytes(payload), generation
        )

    async def _external_bind(self, unbind, generation):
        timestamp = struct.pack(">I", int(time.time()))
        # EUI64.serialize() is little-endian; the Aqara body uses network order.
        device = self.endpoint.device.ieee.serialize()[::-1]
        for slot, marker, descriptor in W600_EXTERNAL_CHANNELS.values():
            tail = bytes(12) if unbind else W600_VIRTUAL_SENSOR + marker + descriptor
            await self._external_payload(
                4 if unbind else 2,
                timestamp + bytes((slot,)) + device + tail,
                generation,
            )

    async def _external_send_sample(self, channel, value, generation):
        marker = W600_EXTERNAL_CHANNELS[channel][1]
        data = (
            struct.pack(">f", value)
            if channel == "temperature"
            else struct.pack(">I", 1)
        )
        await self._external_payload(5, W600_VIRTUAL_SENSOR + marker + data, generation)

    async def set_external_temperature(self, *, source=None, centidegrees=None):
        """Bind/source/sample transaction; no cached values are sent automatically."""
        attrid = ATTR_TEMPERATURE_SOURCE if source is not None else 0x0007
        failure = [
            [
                foundation.WriteAttributesStatusRecord(
                    foundation.Status.FAILURE, attrid=attrid
                )
            ]
        ]
        invalid = [
            [
                foundation.WriteAttributesStatusRecord(
                    foundation.Status.INVALID_VALUE, attrid=attrid
                )
            ]
        ]
        if source is not None and source not in (0, 1):
            return invalid
        if centidegrees is not None and (
            isinstance(centidegrees, bool)
            or not isinstance(centidegrees, (int, float))
            or not math.isfinite(centidegrees)
            or not -4000 <= centidegrees <= 12500
            or abs(centidegrees - round(centidegrees)) > 1e-6
        ):
            return invalid
        if source is None and centidegrees is None:
            return invalid
        if (
            centidegrees is not None
            and (self.get(ATTR_TEMPERATURE_SOURCE) if source is None else source) != 1
        ):
            _LOGGER.warning(
                "W600 external input rejected: select External successfully before sending a temperature"
            )
            return invalid
        received_at = time.monotonic()
        if source is not None:
            self._reset_external()
        generation = self._external_generation

        def require_fresh():
            if generation != self._external_generation or (
                centidegrees is not None
                and not 0 <= time.monotonic() - received_at <= W600_EXTERNAL_FRESHNESS
            ):
                raise _ExternalTransactionFailed

        async with self._external_lock:
            try:
                require_fresh()
                if source == 0:
                    await self._external_write(ATTR_TEMPERATURE_SOURCE, 0, generation)
                    # The device has confirmed internal mode even if a later
                    # unbind fails. Do not keep accepting inputs as external.
                    self.update_attribute(ATTR_TEMPERATURE_SOURCE, 0)
                    await self._external_bind(True, generation)
                else:
                    if not self._external_active:
                        self._external_active = True
                        await self._external_bind(False, generation)
                        await self._external_write(
                            ATTR_TEMPERATURE_SOURCE, 1, generation
                        )
                        self.update_attribute(ATTR_TEMPERATURE_SOURCE, 1)
                    if centidegrees is not None:
                        require_fresh()
                        value = round(centidegrees)
                        await self._external_send_sample(
                            "temperature", value, generation
                        )
                        require_fresh()
                        if not self._external_availability:
                            await self._external_send_sample(
                                "availability", value, generation
                            )
                            self._external_availability = True
                        require_fresh()
                        self._external_sample = (value, received_at)
                        status = getattr(self.endpoint, "w600_status", None)
                        if status is not None:
                            status.update_attribute(0x0007, value)
            except _ExternalTransactionFailed:
                if generation == self._external_generation:
                    self._reset_external()
                return failure
            except (
                TimeoutError,
                zigpy.exceptions.DeliveryError,
                asyncio.CancelledError,
            ):
                if generation == self._external_generation:
                    self._reset_external()
                raise
        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    async def _respond_external_request(self, tsn, payload, generation):
        channel = _external_request_channel(payload)
        if channel is None:
            return
        async with self._external_lock:
            now = time.monotonic()
            sample = self._external_sample
            if (
                generation != self._external_generation
                or not self._external_active
                or sample is None
                or not 0 <= now - sample[1] <= W600_EXTERNAL_FRESHNESS
            ):
                return
            self._external_requests = {
                key: stamp
                for key, stamp in self._external_requests.items()
                if 0 <= now - stamp <= W600_EXTERNAL_FRESHNESS
            }
            key = (tsn, payload)
            if key in self._external_requests:
                return
            try:
                await self._external_send_sample(channel, sample[0], generation)
            except _ExternalTransactionFailed:
                return
            if len(self._external_requests) >= 256:
                self._external_requests.pop(next(iter(self._external_requests)))
            self._external_requests[key] = now

    def handle_cluster_general_request(self, hdr, args, *, dst_addressing=None):
        """Process reports and validated external sensor requests."""
        super().handle_cluster_general_request(hdr, args, dst_addressing=dst_addressing)
        if (
            hdr.command_id == foundation.GeneralCommand.Report_Attributes
            and hdr.manufacturer == AQARA_MANUFACTURER_CODE
        ):
            for attr in args.attribute_reports:
                if (
                    attr.attrid == ATTR_EXTERNAL_SENSOR_BINDING
                    and _external_request_channel(attr.value.value) is not None
                ):
                    self.create_catching_task(
                        self._respond_external_request(
                            hdr.tsn, bytes(attr.value.value), self._external_generation
                        )
                    )

    async def set_schedule_enabled(self, value):
        """Toggle the existing schedule without enabling an off thermostat."""
        if value not in (0, 1):
            return [
                [
                    foundation.WriteAttributesStatusRecord(
                        foundation.Status.INVALID_VALUE, attrid=ATTR_SCHEDULE_ENABLED
                    )
                ]
            ]
        thermostat = self.endpoint.thermostat
        if value == 0:
            result = await thermostat.write_attributes(
                {ATTR_TEMP_SETPOINT_HOLD: 0},
                update_cache=False,
            )
            if not _all_success(result):
                return result
        result = await super().write_attributes(
            {ATTR_SCHEDULE_ENABLED: int(value)},
            manufacturer=AQARA_MANUFACTURER_CODE,
            update_cache=False,
        )
        if _all_success(result):
            self.update_attribute(ATTR_SCHEDULE_ENABLED, int(value))
            if value == 0:
                thermostat.update_attribute(ATTR_TEMP_SETPOINT_HOLD, 0)
        return result

    async def write_attributes(self, attributes, *args, **kwargs):
        """Select profiles with schedule-aware hold, never write profile 255."""
        source_keys = [
            key
            for key in attributes
            if _key_matches_attrid(key, ATTR_TEMPERATURE_SOURCE, "temperature_source")
        ]
        if source_keys:
            if len(attributes) != 1:
                return [
                    [
                        foundation.WriteAttributesStatusRecord(
                            foundation.Status.INVALID_VALUE,
                            attrid=ATTR_TEMPERATURE_SOURCE,
                        )
                    ]
                ]
            return await self.set_external_temperature(
                source=attributes[source_keys[0]]
            )
        outgoing = dict(attributes)
        preset = None
        for key in list(outgoing):
            if _key_matches_attrid(key, ATTR_DEVICE_STATE, "device_state"):
                preset = outgoing.pop(key)
        if preset is None:
            return await super().write_attributes(attributes, *args, **kwargs)
        # Separate profile transactions avoid partial unrelated changes.
        if outgoing or preset not in (1, 2, 3, 5, 6, 255):
            return [
                [
                    foundation.WriteAttributesStatusRecord(
                        foundation.Status.INVALID_VALUE, attrid=ATTR_DEVICE_STATE
                    )
                ]
            ]
        thermostat = self.endpoint.thermostat
        if preset == W600Preset.Manual:
            target = thermostat.get(ATTR_OCCUPIED_HEATING_SETPOINT)
            if target is None:
                return [
                    [
                        foundation.WriteAttributesStatusRecord(
                            foundation.Status.FAILURE, attrid=ATTR_DEVICE_STATE
                        )
                    ]
                ]
            result = await thermostat.write_attributes(
                {ATTR_OCCUPIED_HEATING_SETPOINT: target}
            )
        else:
            schedule = self.get(ATTR_SCHEDULE_ENABLED)
            if schedule is None:
                success, _ = await self.read_attributes(
                    [ATTR_SCHEDULE_ENABLED],
                    manufacturer=AQARA_MANUFACTURER_CODE,
                    allow_cache=False,
                )
                schedule = success.get(ATTR_SCHEDULE_ENABLED)
            if schedule not in (0, 1):
                return [
                    [
                        foundation.WriteAttributesStatusRecord(
                            foundation.Status.FAILURE, attrid=ATTR_DEVICE_STATE
                        )
                    ]
                ]
            result = await super().write_attributes(
                {ATTR_DEVICE_STATE: int(preset)},
                manufacturer=AQARA_MANUFACTURER_CODE,
                update_cache=False,
            )
            if _all_success(result) and schedule == 1:
                result = await thermostat.write_attributes({ATTR_TEMP_SETPOINT_HOLD: 1})
        if _all_success(result):
            self._update_attribute(ATTR_DEVICE_STATE, int(preset))
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
        return [
            [
                foundation.WriteAttributesStatusRecord(
                    foundation.Status.FAILURE, attrid=ATTR_DEVICE_STATE
                )
            ]
        ]

    class AttributeDefs(BaseAttributeDefs):
        """Define locally derived W600 status and control attributes."""

        """W600 attributes with their exact Aqara manufacturer code."""

        heartbeat: Final = ZCLAttributeDef(
            id=ATTR_HEARTBEAT,
            type=t.LVBytes,
            access="r",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        preset_temperature_table: Final = ZCLAttributeDef(
            id=ATTR_PRESET_TEMPERATURE_TABLE,
            type=t.LVBytes,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        temperature_source: Final = ZCLAttributeDef(
            id=ATTR_TEMPERATURE_SOURCE,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        external_sensor_binding: Final = ZCLAttributeDef(
            id=ATTR_EXTERNAL_SENSOR_BINDING,
            type=t.LVBytes,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        external_sensor_status: Final = ZCLAttributeDef(
            id=ATTR_EXTERNAL_SENSOR_STATUS,
            type=t.uint8_t,
            access="r",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        calibrate: Final = ZCLAttributeDef(
            id=ATTR_CALIBRATE, type=t.uint8_t, manufacturer_code=AQARA_MANUFACTURER_CODE
        )
        thermostat_enabled: Final = ZCLAttributeDef(
            id=ATTR_THERMOSTAT_ENABLED,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        window_detection: Final = ZCLAttributeDef(
            id=ATTR_WINDOW_DETECTION,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        temperature_control_abnormal_notification: Final = ZCLAttributeDef(
            id=ATTR_TEMPERATURE_CONTROL_ABNORMAL_NOTIFICATION,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        child_lock: Final = ZCLAttributeDef(
            id=ATTR_CHILD_LOCK,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        anti_freeze_temperature: Final = ZCLAttributeDef(
            id=ATTR_ANTI_FREEZE_TEMPERATURE,
            type=t.uint32_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        calibrated: Final = ZCLAttributeDef(
            id=ATTR_CALIBRATED,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        schedule_enabled: Final = ZCLAttributeDef(
            id=ATTR_SCHEDULE_ENABLED,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        device_state_aux: Final = ZCLAttributeDef(
            id=ATTR_DEVICE_STATE_AUX,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        device_state: Final = ZCLAttributeDef(
            id=ATTR_DEVICE_STATE,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        display_flip: Final = ZCLAttributeDef(
            id=ATTR_DISPLAY_FLIP,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        valve_position_raw: Final = ZCLAttributeDef(
            id=ATTR_VALVE_POSITION_RAW,
            type=t.Single,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)
        if attrid == ATTR_TEMPERATURE_SOURCE and value == 0 and self._external_active:
            self._reset_external()
        self._sync_status_attribute(attrid, value)
        thermostat = getattr(self.endpoint, "thermostat", None)
        if not isinstance(thermostat, AqaraW600Thermostat):
            return
        if attrid in (ATTR_THERMOSTAT_ENABLED, ATTR_SCHEDULE_ENABLED):
            thermostat._sync_system_mode_from_w600()
            if attrid == ATTR_THERMOSTAT_ENABLED:
                thermostat._sync_running_state_from_valve(
                    self._attr_cache.get(ATTR_VALVE_POSITION_RAW)
                )
        elif attrid == ATTR_VALVE_POSITION_RAW:
            thermostat._sync_running_state_from_valve(value)

    def _sync_status_attribute(self, attrid, value):
        """Derive local telemetry from a report or an existing vendor cache."""
        status = getattr(self.endpoint, "w600_status", None)
        if status is None:
            return
        updates = {}
        if attrid == ATTR_SCHEDULE_ENABLED:
            updates[0x0006] = value
        elif attrid == ATTR_DEVICE_STATE:
            updates[0x0005] = value
        elif attrid == ATTR_EXTERNAL_SENSOR_STATUS:
            problem = _external_sensor_problem(value)
            updates[0x0004] = 255 if problem is None else int(problem)
        elif attrid == ATTR_PRESET_TEMPERATURE_TABLE:
            table = _decode_w600_preset_table(value)
            updates.update(
                {
                    0x0010 + index: table[preset]
                    for index, preset in enumerate(PRESET_IDS)
                    if preset in table
                }
            )
        elif attrid == ATTR_HEARTBEAT:
            fields = _decode_w600_heartbeat(value)
            battery, voltage = fields.get(0x18), fields.get(0x17)
            if isinstance(battery, int) and 0 <= battery <= 100:
                updates[0x0000] = battery
            if isinstance(voltage, int) and 0 < voltage < 65535:
                updates[0x0001] = voltage
            block = fields.get(0x9C)
            if isinstance(block, bytes) and len(block) >= 8:
                code = block[4]
                window = {0x00: False, 0x0D: True, 0x0E: True}.get(code)
                alarm = {0x00: False, 0x0D: False, 0x0E: False, 0x10: True}.get(code)
                updates[0x0002] = 255 if window is None else int(window)
                updates[0x0003] = 255 if alarm is None else int(alarm)
        for local_id, local_value in updates.items():
            # Legacy cache entries are not visible to entity reads. Check the
            # typed cache without triggering recursive status restoration.
            if CustomCluster.get(status, local_id) != local_value:
                status.update_attribute(local_id, local_value)

    async def configure_reporting(self) -> None:
        """Refresh W600 state and request reports after a device wake-up."""
        await super().configure_reporting()
        try:
            await self.configure_reporting_multiple(
                {
                    self.find_attribute(
                        ATTR_THERMOSTAT_ENABLED,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_SCHEDULE_ENABLED,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_DEVICE_STATE,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_VALVE_POSITION_RAW,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_WINDOW_DETECTION,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_CHILD_LOCK,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_ANTI_FREEZE_TEMPERATURE,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_CALIBRATED,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_DISPLAY_FLIP,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                }
            )
        except (TimeoutError, zigpy.exceptions.DeliveryError) as exc:
            _LOGGER.warning("W600 FCC0 reporting configuration deferred: %s", exc)

        try:
            await self.read_attributes(
                [
                    ATTR_THERMOSTAT_ENABLED,
                    ATTR_SCHEDULE_ENABLED,
                    ATTR_DEVICE_STATE_AUX,
                    ATTR_DEVICE_STATE,
                    ATTR_VALVE_POSITION_RAW,
                    ATTR_WINDOW_DETECTION,
                    ATTR_CHILD_LOCK,
                    ATTR_ANTI_FREEZE_TEMPERATURE,
                    ATTR_CALIBRATED,
                    ATTR_DISPLAY_FLIP,
                ],
                manufacturer=AQARA_MANUFACTURER_CODE,
            )
        except (TimeoutError, zigpy.exceptions.DeliveryError) as exc:
            _LOGGER.warning("W600 FCC0 state read deferred: %s", exc)


# Single Quirk V2 registration.  The two replacement clusters retain the
# W600 transport and mode behavior while the same registration exposes the
# Aqara attributes as native Home Assistant entities. Vendor reads/writes
# retain manufacturer code 4447; derived values use the local status cluster.

_REPORTING = ReportingConfig(min_interval=5, max_interval=900, reportable_change=1)


(
    QuirkBuilder(AQARA, MODEL)
    .zigpy_device_class(CustomZigpyDevice)
    .replaces(AqaraW600Thermostat, endpoint_id=1)
    .replaces(AqaraW600FCC0, endpoint_id=1)
    .adds(AqaraW600Status, endpoint_id=1)
    .enum(
        attribute_name="temperature_source",
        enum_class=W600TemperatureSource,
        cluster_id=AqaraW600FCC0.cluster_id,
        initially_disabled=True,
        translation_key="temperature_source_control",
        fallback_name="Temperature source",
        unique_id_suffix="w600-temperature-source-control",
    )
    .number(
        attribute_name="external_temperature_input",
        cluster_id=AqaraW600Status.cluster_id,
        min_value=-40,
        max_value=125,
        step=0.01,
        multiplier=0.01,
        unit="°C",
        mode="box",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
        translation_key="external_temperature_input",
        fallback_name="External temperature input",
        unique_id_suffix="w600-external-temperature-input",
    )
    .switch(
        attribute_name="schedule_control",
        cluster_id=AqaraW600Status.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="schedule_control",
        fallback_name="Schedule",
        unique_id_suffix="w600-schedule-control",
    )
    .switch(
        attribute_name="temperature_control_abnormal_notification",
        cluster_id=AqaraW600FCC0.cluster_id,
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
        translation_key="temperature_control_abnormal_notification",
        fallback_name="Temperature control abnormal notification",
        unique_id_suffix="w600-abnormal-notification",
    )
    .sensor(
        attribute_name="temperature_source",
        cluster_id=AqaraW600FCC0.cluster_id,
        attribute_converter=_temperature_source_name,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="temperature_source",
        fallback_name="Temperature source",
        unique_id_suffix="w600-temperature-source",
    )
    .binary_sensor(
        attribute_name="external_temperature_problem",
        cluster_id=AqaraW600Status.cluster_id,
        attribute_converter=_optional_flag,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        initially_disabled=True,
        translation_key="external_temperature_problem",
        fallback_name="External temperature problem",
        unique_id_suffix="w600-external-temperature-problem",
    )
    .number(
        attribute_name="preset_home_temperature",
        cluster_id=AqaraW600Status.cluster_id,
        min_value=5,
        max_value=30,
        step=0.5,
        multiplier=0.01,
        unit="°C",
        mode="box",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
        translation_key="preset_home_temperature",
        fallback_name="Home temperature",
        unique_id_suffix="w600-preset-home-temperature",
    )
    .number(
        attribute_name="preset_away_temperature",
        cluster_id=AqaraW600Status.cluster_id,
        min_value=5,
        max_value=30,
        step=0.5,
        multiplier=0.01,
        unit="°C",
        mode="box",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
        translation_key="preset_away_temperature",
        fallback_name="Away temperature",
        unique_id_suffix="w600-preset-away-temperature",
    )
    .number(
        attribute_name="preset_sleep_temperature",
        cluster_id=AqaraW600Status.cluster_id,
        min_value=5,
        max_value=30,
        step=0.5,
        multiplier=0.01,
        unit="°C",
        mode="box",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
        translation_key="preset_sleep_temperature",
        fallback_name="Sleep temperature",
        unique_id_suffix="w600-preset-sleep-temperature",
    )
    .number(
        attribute_name="preset_vacation_temperature",
        cluster_id=AqaraW600Status.cluster_id,
        min_value=5,
        max_value=30,
        step=0.5,
        multiplier=0.01,
        unit="°C",
        mode="box",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
        translation_key="preset_vacation_temperature",
        fallback_name="Vacation temperature",
        unique_id_suffix="w600-preset-vacation-temperature",
    )
    .number(
        attribute_name="preset_wind_down_temperature",
        cluster_id=AqaraW600Status.cluster_id,
        min_value=5,
        max_value=30,
        step=0.5,
        multiplier=0.01,
        unit="°C",
        mode="box",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
        translation_key="preset_wind_down_temperature",
        fallback_name="Wind down temperature",
        unique_id_suffix="w600-preset-wind_down-temperature",
    )
    .enum(
        attribute_name="device_state",
        enum_class=W600Preset,
        cluster_id=AqaraW600FCC0.cluster_id,
        translation_key="preset",
        fallback_name="Preset",
        unique_id_suffix="w600-preset",
    )
    .binary_sensor(
        attribute_name="window_open",
        cluster_id=AqaraW600Status.cluster_id,
        attribute_converter=_optional_flag,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.WINDOW,
        translation_key="window_open",
        fallback_name="Window open",
        unique_id_suffix="w600-window-open",
    )
    .binary_sensor(
        attribute_name="valve_alarm",
        cluster_id=AqaraW600Status.cluster_id,
        attribute_converter=_optional_flag,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        translation_key="w600_temperature_control_problem",
        fallback_name="Temperature control problem",
        unique_id_suffix="w600-valve-alarm",
    )
    .sensor(
        attribute_name="battery_percentage",
        cluster_id=AqaraW600Status.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        unit="%",
        suggested_display_precision=0,
        translation_key="battery",
        fallback_name="Battery",
        unique_id_suffix="w600-battery",
    )
    .sensor(
        attribute_name="battery_millivolts",
        cluster_id=AqaraW600Status.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit="V",
        divisor=1000,
        suggested_display_precision=3,
        initially_disabled=True,
        translation_key="battery_voltage",
        fallback_name="Battery voltage",
        unique_id_suffix="w600-battery-voltage",
    )
    .prevent_default_entity_creation(
        endpoint_id=2,
        cluster_id=Thermostat.cluster_id,
    )
    .switch(
        attribute_name=AqaraW600FCC0.AttributeDefs.child_lock.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        reporting_config=_REPORTING,
        translation_key="child_lock",
        fallback_name="Child lock",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-child_lock",
    )
    .switch(
        attribute_name=AqaraW600FCC0.AttributeDefs.display_flip.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        reporting_config=_REPORTING,
        translation_key="display_flip",
        fallback_name="Display flip",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-display_flip",
    )
    .switch(
        attribute_name=AqaraW600FCC0.AttributeDefs.window_detection.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        reporting_config=_REPORTING,
        translation_key="window_detection",
        fallback_name="Open window detection",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-window_detection",
    )
    .number(
        attribute_name=AqaraW600FCC0.AttributeDefs.anti_freeze_temperature.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        min_value=5,
        max_value=15,
        step=0.5,
        unit="°C",
        mode="box",
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        reporting_config=_REPORTING,
        translation_key="anti_freeze_temperature",
        fallback_name="Anti-freeze temperature",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-anti_freeze_temperature",
    )
    .write_attr_button(
        attribute_name=AqaraW600FCC0.AttributeDefs.calibrate.name,
        attribute_value=1,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="calibrate",
        fallback_name="Start calibration",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-calibrate",
    )
    .sensor(
        attribute_name=AqaraW600FCC0.AttributeDefs.calibrated.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        attribute_converter=_calibration_status_name,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=_REPORTING,
        translation_key="calibration_status",
        fallback_name="Calibration status",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-calibration_status",
    )
    # Diagnostic controls for investigating schedule/override transitions.
    # Exposing these entities does not write a default or activate a hold.
    .number(
        attribute_name=Thermostat.AttributeDefs.temp_setpoint_hold_duration.name,
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        step=1,
        unit="min",
        mode="box",
        entity_type=EntityType.CONFIG,
        reporting_config=_REPORTING,
        initially_disabled=True,
        translation_key="temperature_setpoint_hold_duration",
        fallback_name="Temperature setpoint hold duration",
        unique_id_suffix=f"{Thermostat.cluster_id}-temp_setpoint_hold_duration",
    )
    .binary_sensor(
        attribute_name=AqaraW600FCC0.AttributeDefs.schedule_enabled.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=_REPORTING,
        initially_disabled=True,
        translation_key="schedule_enabled",
        fallback_name="Schedule enabled",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-schedule_enabled",
    )
    .binary_sensor(
        attribute_name=Thermostat.AttributeDefs.temp_setpoint_hold.name,
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=_REPORTING,
        translation_key="override_active",
        fallback_name="Override active",
        unique_id_suffix=f"{Thermostat.cluster_id}-override_active",
    )
    .sensor(
        attribute_name="local_temperature",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=2,
        divisor=100,
        suggested_display_precision=1,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit="°C",
        initially_disabled=True,
        translation_key="local_temperature_internal",
        fallback_name="Internal temperature (endpoint 2)",
        unique_id_suffix=f"{Thermostat.cluster_id}-ep2-local_temperature_internal",
    )
    .sensor(
        attribute_name=AqaraW600FCC0.AttributeDefs.valve_position_raw.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        suggested_display_precision=2,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=_REPORTING,
        translation_key="valve_position_raw",
        fallback_name="Valve position (raw)",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-valve_position_raw",
    )
    .sensor(
        attribute_name=AqaraW600FCC0.AttributeDefs.device_state_aux.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        suggested_display_precision=0,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=_REPORTING,
        initially_disabled=True,
        translation_key="device_state_aux",
        fallback_name="Device state auxiliary (raw)",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-device_state_aux",
    )
    .sensor(
        attribute_name="device_state_raw",
        cluster_id=AqaraW600Status.cluster_id,
        endpoint_id=1,
        suggested_display_precision=0,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="device_state",
        fallback_name="Device state (raw)",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-device_state",
    )
    .add_to_registry()
)

# Endpoint 2 is intentionally reduced to an optional, disabled temperature
# sensor.  The device currently reports 0 °C there; it must not create a
# second climate or HVAC-action entity, and the sensor can be enabled later
# if the firmware starts reporting a meaningful value.
