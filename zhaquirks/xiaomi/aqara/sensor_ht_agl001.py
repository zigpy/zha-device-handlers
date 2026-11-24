"""Quirk for the Aqara Climate Sensor W100 (lumi.sensor_ht.agl001).

Exposes the three buttons (plus/center/minus = endpoints 1/2/3) as zha_event and
device-automation triggers via the shared Aqara ``MultistateInputCluster``, and battery
from the 0xFCC0 heartbeat struct. The W100 reports battery percent only in heartbeat
tag 102 — there is no tag-1 voltage, and the standard PowerConfiguration attribute
always reports 0 — so ``XiaomiCluster._parse_aqara_attributes`` maps tag 102 for this
model (matching zigbee2mqtt's TH-S04D converter,
https://github.com/Koenkk/zigbee-herdsman-converters/pull/10787).

It also turns the W100 into a setpoint authority for Home Assistant, the same feature
Zigbee2MQTT has (Koenkk/zigbee-herdsman-converters#13876, worked out with the Aqara
firmware developer):

- a *virtual* Thermostat cluster on endpoint 1 gives ZHA a real climate entity;
- `W100AqaraCluster` bridges it to the device:
  - firmware < 1643 ("PMTSD" protocol): state travels as ASCII `P_p_M_m_T_t_S_s_D_d`
    inside framed writes to 0xFCC0/0xFFF2. Every W100-initiated frame (type 0x84)
    must be acknowledged with a type 0x24 frame, a PMTSD request (frame ending with
    the `08 00 08 44` marker) is answered with the current state, and device-side
    changes arrive as *partial* strings that must be merged and echoed back, or the
    W100 blocks (E01/E02). Whole degrees only.
  - firmware >= 1643 ("HA" protocol): 0xFCC0/0x0174 TLV (tag 0x01 mode, 0x02 setpoint
    x100, 0x03 fan — values aligned with ZCL) and 0xFCC0/0x0175 setpoint step.
    Writing 0x0174 with valid tags subscribes the device; invalid-only data
    unsubscribes it. The protocol is detected by reading 0x0175.
- `thermostat_mode` (local attribute 0xFFE3, above PR #5508's 0xFFE0-0xFFE2) is
  exposed as an enum entity; the device state comes from 0xFCC0/0x0172 bit 0.

Scope of this first version: heating (Off/Heat) only. Cool/Auto, fan and the Z2M
`system_modes`/`fan_modes`/`setpoint_step` options are follow-ups; a mode the panel
selects that is not supported is reverted on the panel.
"""

from __future__ import annotations

import asyncio
import random
import struct
from typing import Any, Final

from zigpy import types as t
from zigpy.exceptions import DeliveryError, ZigbeeException
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.builder import EntityFilter, EntityPlatform, QuirkBuilder
from zhaquirks.const import COMMAND, DOUBLE_PRESS, LONG_PRESS, LONG_RELEASE, SHORT_PRESS
from zhaquirks.xiaomi import (
    AQARA,
    RelativeHumidityCluster,
    TemperatureMeasurementCluster,
    XiaomiAqaraE1Cluster,
    XiaomiPowerConfiguration,
)
from zhaquirks.xiaomi.aqara.opple_remote import (
    COMMAND_1_DOUBLE,
    COMMAND_1_HOLD,
    COMMAND_1_RELEASE,
    COMMAND_1_SINGLE,
    COMMAND_2_DOUBLE,
    COMMAND_2_HOLD,
    COMMAND_2_RELEASE,
    COMMAND_2_SINGLE,
    COMMAND_3_DOUBLE,
    COMMAND_3_HOLD,
    COMMAND_3_RELEASE,
    COMMAND_3_SINGLE,
    MultistateInputCluster,
)

PLUS_BUTTON = "plus"
CENTER_BUTTON = "center"
MINUS_BUTTON = "minus"

AQARA_MANUFACTURER_CODE = 0x115F

# 0xFFF2 "sensor_link" frame types and actions
FRAME_TYPE_TO_DEVICE = 0x44
FRAME_TYPE_FROM_DEVICE = 0x84
FRAME_TYPE_ACK = 0x24
FRAME_ACTION_LINK = 0x02
FRAME_ACTION_UNLINK = 0x04
FRAME_ACTION_VALUE = 0x05

# IEEE of the virtual "hub" the W100 links its thermostat to
HUB_IEEE = bytes.fromhex("54ef4480711a")
PMTSD_MARKER = bytes.fromhex("08000844")
# Tail of the legacy subscribe frame (labelled "air conditioner function" in Chinese)
SUBSCRIBE_TAIL = bytes.fromhex("08000844150a0109e7a9bae8b083e58a9f000000000001012a40")
UNSUBSCRIBE_PAD = bytes(12)

# "HA" protocol: 0xFCC0 attributes and TLV layout
HA_THERMOSTAT_STATE = 0x0174
HA_SETPOINT_STEP = 0x0175
HA_TAG_MODE = 0x01
HA_TAG_SETPOINT = 0x02
HA_TAG_FAN = 0x03
HA_TAG_MIN_HEAT = 0x04
HA_TAG_MAX_HEAT = 0x05
HA_TAG_MIN_COOL = 0x06
HA_TAG_MAX_COOL = 0x07
HA_TYPE_ENUM8 = 0x30
HA_TYPE_INT16 = 0x29
HA_TYPE_SIZES = {
    0x10: 1,  # boolean
    0x18: 1,  # bitmap8
    0x20: 1,  # uint8
    0x28: 1,  # int8
    0x30: 1,  # enum8
    0x21: 2,  # uint16
    0x29: 2,  # int16
}
# Writing this to 0x0174 (no valid tag) unsubscribes the W100
HA_UNSUBSCRIBE = bytes.fromhex("001000")
HA_FAN_AUTO = 5
HA_DEFAULT_STEP = 50  # 0.5 °C, in °C x 100

SystemMode = Thermostat.SystemMode
ZCL_SYSTEM_MODE = Thermostat.AttributeDefs.system_mode.id
ZCL_OCCUPIED_SETPOINT = Thermostat.AttributeDefs.occupied_heating_setpoint.id
ZCL_LOCAL_TEMPERATURE = Thermostat.AttributeDefs.local_temperature.id
ZCL_MIN_HEAT = Thermostat.AttributeDefs.min_heat_setpoint_limit.id
ZCL_MAX_HEAT = Thermostat.AttributeDefs.max_heat_setpoint_limit.id
ZCL_CTRL_SEQUENCE = Thermostat.AttributeDefs.ctrl_sequence_of_oper.id

# PMTSD mode field (M): 0 = cool, 1 = heat, 2 = auto. Only heat is supported for now.
PMTSD_HEAT = 1
SUPPORTED_MODES = (SystemMode.Off, SystemMode.Heat)

DEFAULT_SYSTEM_MODE = SystemMode.Heat
DEFAULT_SETPOINT = 2000  # 20.0 °C, in 0.01 °C
MIN_SETPOINT = 500  # 5 °C
MAX_SETPOINT = 3000  # 30 °C


class ThermostatMode(t.enum8):
    """Thermostat mode of the W100 panel."""

    Off = 0x00
    On = 0x01


def build_frame(
    counter: int,
    action: int,
    payload: bytes,
    frame_type: int = FRAME_TYPE_TO_DEVICE,
) -> bytes:
    """Wrap a payload in the Aqara 0xFFF2 frame header.

    ``AA 71 <len+3> <type> <counter> <checksum> <action> 41 <len> <payload>``: the
    checksum makes the first six bytes sum to 0 (mod 256), and the W100 rejects frames
    with wrong lengths (setpoints below 10 °C never applied with hardcoded lengths).
    """
    header = bytes([0xAA, 0x71, len(payload) + 3, frame_type, counter & 0xFF])
    checksum = (256 - sum(header)) & 0xFF
    return header + bytes([checksum, action, 0x41, len(payload)]) + payload


class W100ThermostatCluster(LocalDataCluster, Thermostat):
    """Virtual Thermostat cluster bridged to the W100 thermostat protocol.

    The W100 has no Thermostat cluster: ``LocalDataCluster`` keeps bind, reporting
    configuration and reads off the air, and mode/setpoint writes are bridged to
    ``W100AqaraCluster``. The cache only changes after a successful device write, so a
    rejected write never leaves the entity showing the requested value (the E1 TRV
    lesson, zha-device-handlers#5536).
    """

    _CONSTANT_ATTRIBUTES = {
        ZCL_MIN_HEAT: MIN_SETPOINT,
        ZCL_MAX_HEAT: MAX_SETPOINT,
        ZCL_CTRL_SEQUENCE: Thermostat.ControlSequenceOfOperation.Heating_Only,
    }
    _DEFAULT_VALUES = {
        ZCL_SYSTEM_MODE: DEFAULT_SYSTEM_MODE,
        ZCL_OCCUPIED_SETPOINT: DEFAULT_SETPOINT,
    }
    # Fed by the W100's own temperature measurement
    _VALID_ATTRIBUTES = {ZCL_LOCAL_TEMPERATURE}

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Bridge system_mode and occupied_heating_setpoint to the device."""
        system_mode = None
        setpoint = None
        remaining: dict[Any, Any] = {}
        for attr, value in attributes.items():
            try:
                attr_id = self.find_attribute(attr).id
            except KeyError:
                remaining[attr] = value
                continue
            if attr_id == ZCL_SYSTEM_MODE:
                system_mode = value
            elif attr_id == ZCL_OCCUPIED_SETPOINT:
                setpoint = value
            else:
                remaining[attr] = value

        if system_mode is not None or setpoint is not None:
            # Raises when the device does not take it: nothing is cached then.
            await self.endpoint.opple_cluster.write_thermostat_state(
                system_mode=system_mode, setpoint=setpoint
            )
        if remaining:
            await super().write_attributes(remaining, **kwargs)
        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


class W100AqaraCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer cluster with the W100 thermostat protocol."""

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        sensor_mode: Final = ZCLAttributeDef(
            id=0x0172,
            type=t.uint8_t,
            access="r",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        ha_thermostat_state: Final = ZCLAttributeDef(
            id=HA_THERMOSTAT_STATE,
            type=t.LVBytes,
            access="rw",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        ha_setpoint_step: Final = ZCLAttributeDef(
            id=HA_SETPOINT_STEP,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        sensor_link: Final = ZCLAttributeDef(
            id=0xFFF2,
            type=t.LVBytes,
            access="w",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        thermostat_mode: Final = ZCLAttributeDef(
            id=0xFFE3, type=ThermostatMode, access="rw"
        )

    def __init__(self, *args, **kwargs):
        """Initialize the frame counter and the background task registry."""
        super().__init__(*args, **kwargs)
        self._frame_counter = random.randint(0, 255)
        self._background_tasks: set[asyncio.Task] = set()

    # -- helpers -----------------------------------------------------------

    @property
    def _uses_ha_protocol(self) -> bool:
        """Return whether the firmware speaks the "HA" attributes protocol.

        Derived from the (persisted) attribute cache: 0x0175 answered a probe, or
        0x0174 was reported.
        """
        return (
            self.get(self.AttributeDefs.ha_setpoint_step.id) is not None
            or self.get(self.AttributeDefs.ha_thermostat_state.id) is not None
        )

    def _next_counter(self) -> int:
        """Return the next frame counter: the W100 expects it to increment."""
        self._frame_counter = (self._frame_counter + 1) & 0xFF
        return self._frame_counter

    def _current_state(self) -> tuple[int, int]:
        """Return the (system_mode, setpoint x100) held by the virtual cluster."""
        thermostat = self.endpoint.thermostat
        return (
            thermostat.get(ZCL_SYSTEM_MODE, DEFAULT_SYSTEM_MODE),
            thermostat.get(ZCL_OCCUPIED_SETPOINT, DEFAULT_SETPOINT),
        )

    def get(self, key: int | str, default: Any | None = None) -> Any:
        """Return a cached attribute; thermostat_mode falls back on sensor_mode.

        thermostat_mode is bit 0 of the device's sensor_mode (0x0172). The device
        reports and ZHA restores sensor_mode across restarts, but not the derived
        local attribute, which would leave the select entity unknown.
        """
        value = super().get(key, default)
        if value is not default:
            return value
        try:
            attr_id = self.find_attribute(key).id
        except KeyError:
            return value
        sensor_mode = super().get(self.AttributeDefs.sensor_mode.id)
        if attr_id == self.AttributeDefs.thermostat_mode.id and sensor_mode is not None:
            return ThermostatMode.On if sensor_mode & 1 else ThermostatMode.Off
        return value

    async def _write_device(self, attributes: dict[int, Any]) -> None:
        """Write attributes to the device, raising when it rejects them.

        zigpy reports a rejected write as a status record rather than an exception,
        and the thermostat cache must only follow writes the device accepted.
        """
        for records in await super().write_attributes(attributes):
            for record in records:
                if record.status != foundation.Status.SUCCESS:
                    raise DeliveryError(
                        f"The W100 rejected the write: {record.status!r}",
                        status=record.status,
                    )

    async def _write_frame(self, frame: bytes) -> None:
        await self._write_device({self.AttributeDefs.sensor_link.id: frame})

    # -- bridged thermostat writes ------------------------------------------

    async def write_thermostat_state(
        self, system_mode: Any = None, setpoint: Any = None
    ) -> None:
        """Write a mode and/or setpoint change, then cache it on success."""
        if system_mode is not None:
            system_mode = SystemMode(system_mode)
            if system_mode not in SUPPORTED_MODES:
                raise ValueError(
                    f"The W100 thermostat supports {[m.name for m in SUPPORTED_MODES]}"
                    f" only, not {system_mode.name}"
                )
        if setpoint is not None:
            setpoint = int(setpoint)
            if not MIN_SETPOINT <= setpoint <= MAX_SETPOINT:
                raise ValueError(
                    f"occupied_heating_setpoint must be between {MIN_SETPOINT / 100}"
                    f" and {MAX_SETPOINT / 100} °C"
                )

        if self._uses_ha_protocol:
            await self._write_ha_state(system_mode, setpoint)
        else:
            await self._send_pmtsd(system_mode, setpoint)

        thermostat = self.endpoint.thermostat
        if system_mode is not None:
            thermostat.update_attribute(ZCL_SYSTEM_MODE, system_mode)
        if setpoint is not None:
            thermostat.update_attribute(ZCL_OCCUPIED_SETPOINT, setpoint)

    async def _write_ha_state(
        self, system_mode: int | None, setpoint: int | None
    ) -> None:
        """Write only the changed field: the W100 keeps one setpoint per mode."""
        value = self._encode_ha_state(mode=system_mode, setpoint=setpoint)
        await self._write_device({self.AttributeDefs.ha_thermostat_state.id: value})

    async def _send_pmtsd(
        self, system_mode: int | None = None, setpoint: int | None = None
    ) -> None:
        """Send the full thermostat state as a PMTSD frame (whole degrees)."""
        mode, current_setpoint = self._current_state()
        if system_mode is not None:
            mode = system_mode
        if setpoint is not None:
            current_setpoint = setpoint

        p = 1 if mode == SystemMode.Off else 0
        # Whole degrees, rounding half up like Zigbee2MQTT (not Python's banker's round)
        degrees = (current_setpoint + 50) // 100
        ascii_payload = f"P{p}_M{PMTSD_HEAT}_T{degrees}_S0_D0"
        payload = (
            b"\x00\x00"
            + HUB_IEEE
            + PMTSD_MARKER
            + bytes([len(ascii_payload)])
            + ascii_payload.encode()
        )
        await self._write_frame(
            build_frame(self._next_counter(), FRAME_ACTION_VALUE, payload)
        )

    # -- thermostat mode (subscribe / unsubscribe) ---------------------------

    async def _set_thermostat_mode(self, mode: ThermostatMode) -> None:
        """Subscribe or unsubscribe the W100 to the virtual thermostat."""
        if self._uses_ha_protocol:
            if mode == ThermostatMode.On:
                await self._write_device(
                    {self.AttributeDefs.ha_setpoint_step.id: HA_DEFAULT_STEP}
                )
                state_mode, setpoint = self._current_state()
                value = self._encode_ha_state(
                    mode=state_mode,
                    setpoint=setpoint,
                    fan=HA_FAN_AUTO,
                    with_limits=True,
                )
            else:
                value = HA_UNSUBSCRIBE
            await self._write_device({self.AttributeDefs.ha_thermostat_state.id: value})
        else:
            device_ieee = self.endpoint.device.ieee.serialize()[::-1]  # big-endian
            prefix = b"\x68\x91" + random.randbytes(2) + b"\x18" + device_ieee
            if mode == ThermostatMode.On:
                payload = prefix + b"\x00\x00" + HUB_IEEE + SUBSCRIBE_TAIL
                action = FRAME_ACTION_LINK
            else:
                payload = prefix + UNSUBSCRIBE_PAD
                action = FRAME_ACTION_UNLINK
            await self._write_frame(build_frame(self._next_counter(), action, payload))
        super()._update_attribute(self.AttributeDefs.thermostat_mode.id, mode)

    @staticmethod
    def _encode_ha_state(
        mode: int | None = None,
        setpoint: int | None = None,
        fan: int | None = None,
        with_limits: bool = False,
    ) -> bytes:
        """Encode a 0x0174 TLV value."""
        tlv = b""
        if mode is not None:
            tlv += bytes([HA_TAG_MODE, HA_TYPE_ENUM8, int(mode) & 0xFF])
        if setpoint is not None:
            tlv += bytes([HA_TAG_SETPOINT, HA_TYPE_INT16]) + struct.pack(
                "<h", int(setpoint)
            )
        if fan is not None:
            tlv += bytes([HA_TAG_FAN, HA_TYPE_ENUM8, int(fan)])
        if with_limits:
            for tag, value in (
                (HA_TAG_MIN_HEAT, MIN_SETPOINT),
                (HA_TAG_MAX_HEAT, MAX_SETPOINT),
                (HA_TAG_MIN_COOL, MIN_SETPOINT),
                (HA_TAG_MAX_COOL, MAX_SETPOINT),
            ):
                tlv += bytes([tag, HA_TYPE_INT16]) + struct.pack("<h", value)
        return tlv

    @staticmethod
    def _decode_ha_state(value: bytes) -> dict[str, int]:
        """Decode a 0x0174 TLV report: mode, setpoint (x100) and fan."""
        result: dict[str, int] = {}
        index = 0
        while index + 2 <= len(value):
            tag, data_type = value[index], value[index + 1]
            size = HA_TYPE_SIZES.get(data_type)
            if size is None or index + 2 + size > len(value):
                break  # unknown or truncated TLV, keep what was decoded
            raw = value[index + 2 : index + 2 + size]
            decoded = int.from_bytes(raw, "little", signed=data_type in (0x28, 0x29))
            if tag == HA_TAG_MODE:
                result["mode"] = decoded
            elif tag == HA_TAG_SETPOINT:
                result["setpoint"] = decoded
            elif tag == HA_TAG_FAN:
                result["fan"] = decoded
            index += 2 + size
        return result

    # -- reports from the device ---------------------------------------------

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Route device reports: 0x0172 mode, 0x0174 state, 0xFFF2 frames."""
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.sensor_mode.id and isinstance(value, int):
            mode = ThermostatMode.On if value & 1 else ThermostatMode.Off
            super()._update_attribute(self.AttributeDefs.thermostat_mode.id, mode)
        elif attrid == self.AttributeDefs.ha_thermostat_state.id and isinstance(
            value, bytes | bytearray
        ):
            self._apply_ha_state(self._decode_ha_state(bytes(value)))
        elif attrid == self.AttributeDefs.sensor_link.id and isinstance(
            value, bytes | bytearray
        ):
            frame = bytes(value)
            # The second header byte is 0x71 in coordinator frames, but the panel also
            # sends 0x72 frames: acknowledge by type, like zigbee2mqtt, not by header.
            if len(frame) > 4 and frame[0] == 0xAA:
                # Report handling is synchronous, the frame exchange is not.
                task = asyncio.get_running_loop().create_task(
                    self._handle_w100_frame(frame)
                )
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

    def _apply_ha_state(self, decoded: dict[str, int]) -> None:
        """Mirror a 0x0174 report into the virtual thermostat."""
        thermostat = self.endpoint.thermostat
        mode = decoded.get("mode")
        if mode is not None and mode in SUPPORTED_MODES:
            thermostat.update_attribute(ZCL_SYSTEM_MODE, SystemMode(mode))
        if "setpoint" in decoded:
            thermostat.update_attribute(ZCL_OCCUPIED_SETPOINT, decoded["setpoint"])

    async def _handle_w100_frame(self, frame: bytes) -> None:
        """Handle a frame sent by the W100: acknowledge it, then act on it."""
        if len(frame) > 4 and frame[3] == FRAME_TYPE_FROM_DEVICE:
            # Without the acknowledgement the W100 blocks (E01/E02).
            ack = build_frame(
                frame[4],
                FRAME_ACTION_VALUE,
                b"\x00\x00\x00" + HUB_IEEE + b"\x00",
                frame_type=FRAME_TYPE_ACK,
            )
            try:
                await self._write_frame(ack)
            except (ZigbeeException, TimeoutError):
                self.warning("W100: failed to acknowledge a device frame")

        self.debug("W100: frame from device: %s", frame.hex())
        if frame.endswith(PMTSD_MARKER):
            # PMTSD request: the panel asks for its state, which it only does when
            # someone uses it. A panel that is off ignores an unsolicited power-on but
            # honors one sent as the answer to its request (seen on firmware 1641), so
            # this is where it is turned on.
            self.endpoint.thermostat.update_attribute(ZCL_SYSTEM_MODE, SystemMode.Heat)
            await self._echo_state()
            return

        index = frame.find(PMTSD_MARKER)
        if index == -1 or index + 4 >= len(frame):
            return
        payload_len = frame[index + 4]
        start, end = index + 5, index + 5 + payload_len
        if payload_len == 0 or end > len(frame):
            return
        try:
            ascii_payload = frame[start:end].rstrip(b"\x00").decode("ascii")
        except UnicodeDecodeError:
            return

        changes: dict[str, str] = {}
        for pair in ascii_payload.split("_"):
            if len(pair) >= 2:
                changes[pair[0].lower()] = pair[1:]
        if changes:
            await self._apply_pmtsd_changes(changes)

    async def _apply_pmtsd_changes(self, changes: dict[str, str]) -> None:
        """Merge a partial PMTSD update from the W100 and echo the state back."""
        thermostat = self.endpoint.thermostat
        mode, setpoint = self._current_state()
        try:
            if "p" in changes:
                mode = SystemMode.Off if int(changes["p"]) else SystemMode.Heat
            if "m" in changes and int(changes["m"]) != PMTSD_HEAT:
                # Not supported yet: keep the cached mode, the echo reverts the panel.
                self.debug("W100: ignoring unsupported PMTSD mode %s", changes["m"])
            if "t" in changes:
                setpoint = round(float(changes["t"]) * 100)
        except ValueError:
            # Still answer: an unanswered change is what makes the W100 block.
            self.debug("W100: ignoring malformed PMTSD update %s", changes)
            await self._echo_state()
            return

        thermostat.update_attribute(ZCL_SYSTEM_MODE, mode)
        thermostat.update_attribute(
            ZCL_OCCUPIED_SETPOINT, min(max(setpoint, MIN_SETPOINT), MAX_SETPOINT)
        )
        # Echo the merged state back, otherwise the W100 blocks the next local
        # change (E02).
        await self._echo_state()

    async def _echo_state(self) -> None:
        """Send the current state to the W100 (PMTSD firmware only)."""
        if self._uses_ha_protocol:
            return
        try:
            await self._send_pmtsd()
        except (ZigbeeException, TimeoutError):
            self.warning("W100: failed to send the thermostat state to the device")

    # -- writes and reads of this cluster's attributes ------------------------

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Translate the local thermostat_mode attribute into frames."""
        remaining: dict[Any, Any] = {}
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            if attr_def.id == self.AttributeDefs.thermostat_mode.id:
                await self._set_thermostat_mode(ThermostatMode(value))
            else:
                remaining[attr] = value
        if remaining:
            return await super().write_attributes(remaining, **kwargs)
        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    async def read_attributes(
        self,
        attributes: list[int | str | foundation.ZCLAttributeDef],
        allow_cache: bool = False,
        only_cache: bool = False,
        **kwargs,
    ) -> Any:
        """Answer thermostat_mode from the cache, refreshed from 0x0172 first."""
        attr_defs = [self.find_attribute(attr) for attr in attributes]
        mode_def = self.AttributeDefs.thermostat_mode
        if mode_def in attr_defs and not only_cache:
            # 0x0172 bit 0 is the thermostat mode. The W100 sleeps: use the cache
            # when it does not answer.
            try:
                await super().read_attributes(
                    [self.AttributeDefs.sensor_mode.id], **kwargs
                )
            except (ZigbeeException, TimeoutError):
                self.debug("W100: no answer to a thermostat mode refresh")

        success: dict[Any, Any] = {}
        failure: dict[Any, foundation.Status] = {}
        remaining = []
        for attr, attr_def in zip(attributes, attr_defs, strict=True):
            if attr_def.id != mode_def.id:
                remaining.append(attr)
            elif (value := self.get(attr_def.id)) is None:
                failure[attr] = foundation.Status.UNSUPPORTED_ATTRIBUTE
            else:
                success[attr] = value
        if remaining:
            remote_success, remote_failure = await super().read_attributes(
                remaining, allow_cache, only_cache, **kwargs
            )
            success.update(remote_success)
            failure.update(remote_failure)
        return success, failure

    async def apply_custom_configuration(self, *args, **kwargs) -> None:
        """Probe the firmware protocol and sync the thermostat mode at pairing.

        Newer firmware answers a read of 0x0175 (setpoint step); PMTSD-only firmware
        reports UNSUPPORTED_ATTRIBUTE. A sleeping device is retried at the next
        reconfigure, the legacy protocol is assumed until then.
        """
        step_id = self.AttributeDefs.ha_setpoint_step.id
        try:
            await super().read_attributes([step_id])
            await super().read_attributes([self.AttributeDefs.sensor_mode.id])
        except (ZigbeeException, TimeoutError):
            self.debug("W100: no answer to the thermostat protocol probe")
        self.debug(
            "W100: thermostat protocol: %s",
            "ha" if self._uses_ha_protocol else "legacy (PMTSD)",
        )


class W100TemperatureMeasurement(TemperatureMeasurementCluster):
    """TemperatureMeasurement that feeds the virtual thermostat's local temperature."""

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Copy measured_value (0.01 °C, same unit as local_temperature) over."""
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.measured_value.id:
            self.endpoint.thermostat.update_attribute(ZCL_LOCAL_TEMPERATURE, value)


class W100PowerConfiguration(XiaomiPowerConfiguration):
    """PowerConfiguration that drops the device's own ZCL battery reports.

    The W100's battery_percentage_remaining attribute always reports 0, and a
    reporting config from a pre-quirk join persists in the device — a 0 every
    max-interval that overwrites the heartbeat-derived value. Battery comes solely
    from the 0xFCC0 heartbeat via ``battery_percent_reported``.
    """

    def handle_cluster_general_request(self, hdr, args, *, dst_addressing=None):
        """Drop attribute reports; pass everything else through."""
        if hdr.command_id == foundation.GeneralCommand.Report_Attributes:
            return
        super().handle_cluster_general_request(hdr, args, dst_addressing=dst_addressing)


(
    QuirkBuilder(AQARA, "lumi.sensor_ht.agl001")
    .friendly_name(manufacturer="Aqara", model="Climate Sensor W100")
    .replaces(W100TemperatureMeasurement)
    .replaces(RelativeHumidityCluster)
    .replaces(W100PowerConfiguration)
    .replaces(W100AqaraCluster)
    .adds(W100ThermostatCluster)
    .replaces(MultistateInputCluster)
    .replaces(MultistateInputCluster, endpoint_id=2)
    .replaces(MultistateInputCluster, endpoint_id=3)
    # Keep the climate entity only: the other Thermostat entities (HVAC action, PI
    # heating demand, setpoint change source, setpoint limits) mean nothing for a
    # virtual thermostat.
    .removes_entity(
        EntityFilter(
            endpoint_id=1,
            cluster_id=Thermostat.cluster_id,
            platform=EntityPlatform.SENSOR,
        ),
        EntityFilter(
            endpoint_id=1,
            cluster_id=Thermostat.cluster_id,
            platform=EntityPlatform.NUMBER,
        ),
    )
    .enum(
        attribute_name=W100AqaraCluster.AttributeDefs.thermostat_mode.name,
        enum_class=ThermostatMode,
        cluster_id=W100AqaraCluster.cluster_id,
        translation_key="thermostat_mode",
        fallback_name="Thermostat mode",
    )
    .device_automation_triggers(
        {
            (SHORT_PRESS, PLUS_BUTTON): {COMMAND: COMMAND_1_SINGLE},
            (DOUBLE_PRESS, PLUS_BUTTON): {COMMAND: COMMAND_1_DOUBLE},
            (LONG_PRESS, PLUS_BUTTON): {COMMAND: COMMAND_1_HOLD},
            (LONG_RELEASE, PLUS_BUTTON): {COMMAND: COMMAND_1_RELEASE},
            (SHORT_PRESS, CENTER_BUTTON): {COMMAND: COMMAND_2_SINGLE},
            (DOUBLE_PRESS, CENTER_BUTTON): {COMMAND: COMMAND_2_DOUBLE},
            (LONG_PRESS, CENTER_BUTTON): {COMMAND: COMMAND_2_HOLD},
            (LONG_RELEASE, CENTER_BUTTON): {COMMAND: COMMAND_2_RELEASE},
            (SHORT_PRESS, MINUS_BUTTON): {COMMAND: COMMAND_3_SINGLE},
            (DOUBLE_PRESS, MINUS_BUTTON): {COMMAND: COMMAND_3_DOUBLE},
            (LONG_PRESS, MINUS_BUTTON): {COMMAND: COMMAND_3_HOLD},
            (LONG_RELEASE, MINUS_BUTTON): {COMMAND: COMMAND_3_RELEASE},
        }
    )
    .add_to_registry()
)
