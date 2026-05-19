"""ZHA custom quirk for Zemismart ZPS-Z1 24 GHz mmWave Presence Sensor."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Final

import zigpy.types as t
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.zcl import foundation
from zigpy.zcl.foundation import ZCLAttributeDef
from zhaquirks.tuya import TUYA_CLUSTER_ID, TuyaData, TuyaDPType
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster
from zhaquirks.tuya import TuyaCommand, TuyaDatapointData

_LOGGER = logging.getLogger(__name__)

ZONE_COUNT: Final = 10

DP_PRESENCE_STATE = 1
DP_DETECTION_RANGE = 2
DP_ILLUMINANCE = 101
DP_ENERGY_VALUE = 102
DP_AI_SELF_LEARNING = 103
DP_HEARTBEAT_ENABLE = 104
DP_HEART = 105
DP_SENSITIVITY_PRESET = 112
DP_ZONE_MAP = 117
DP_NO_PERSON_TIME = 119
DP_INDICATOR = 123
DP_ENERGY_THRESHOLD = 124

DT_RAW = 0x00
DT_BOOL = 0x01
DT_VALUE = 0x02
DT_ENUM = 0x04


class PresenceState(t.enum8):
    absence = 0x00
    presence = 0x01
    sensor_close = 0x02


class AutoCalibrationCmd(t.enum8):
    standby = 0x00
    start = 0x01
    cancel = 0x05


class SensitivityPreset(t.enum8):
    high = 0x00
    medium = 0x01
    low = 0x02
    custom = 0x03


CALIB_STATUS_MAP: Final[dict[int, str]] = {
    0: "standby",
    1: "start",
    2: "learning",
    3: "success",
    4: "fail",
    5: "cancel",
}


def _to_app(raw: int) -> int:
    return round((raw / 255) * 100)


def _to_raw(app: int) -> int:
    return round((app / 100) * 255)


def _decode_energy(data: bytes) -> tuple[list[int], list[int]]:
    buf = bytes(data).ljust(20, b"\x00")
    motion = [buf[i] for i in range(ZONE_COUNT)]
    presence = [buf[ZONE_COUNT + i] for i in range(ZONE_COUNT)]
    return motion, presence


def _encode_energy(motion: list[int], presence: list[int]) -> bytes:
    buf = bytearray(20)
    for i in range(ZONE_COUNT):
        buf[i] = max(0, min(255, round(motion[i])))
        buf[ZONE_COUNT + i] = max(0, min(255, round(presence[i])))
    return bytes(buf)


def _tuya_raw(value: Any) -> bytes:
    """Return the raw Tuya datapoint bytes across zhaquirks API variants."""
    raw = getattr(value, "raw", value)
    if raw is None:
        return b""
    return bytes(raw)


def _enum_from_value(enum_cls: type[t.enum8], value: Any) -> t.enum8 | None:
    if isinstance(value, enum_cls):
        return value
    if hasattr(value, "value"):
        value = value.value
    elif isinstance(value, str):
        try:
            return enum_cls[value]
        except KeyError:
            return None
    try:
        return enum_cls(int(value))
    except (ValueError, TypeError):
        return None


class ZpsZ1ManufCluster(TuyaMCUCluster):
    """Tuya MCU cluster for the Zemismart ZPS-Z1."""

    _zone_active: list[bool]
    _motion_thr: list[int]
    _presence_thr: list[int]
    _thresholds_initialized: bool
    _energy_stream_on: bool
    _energy_stream_enabled_for_calibration: bool
    _keepalive_task: asyncio.Task | None
    _auto_calibration_status_raw: int | None
    _pending_zone_write: bool

    class AttributeDefs(TuyaMCUCluster.AttributeDefs):
        presence_state: Final = ZCLAttributeDef(
            id=0x0001,
            type=PresenceState,
            access="rp",
            is_manufacturer_specific=True,
        )
        detection_range: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint32_t,
            access="rwp",
            is_manufacturer_specific=True,
        )
        illuminance: Final = ZCLAttributeDef(
            id=0x0065,
            type=t.uint32_t,
            access="rp",
            is_manufacturer_specific=True,
        )
        auto_calibration_status: Final = ZCLAttributeDef(
            id=0x6560,
            type=t.CharacterString,
            access="rp",
            is_manufacturer_specific=True,
        )
        auto_calibration: Final = ZCLAttributeDef(
            id=0x0067,
            type=AutoCalibrationCmd,
            access="w",
            is_manufacturer_specific=True,
        )
        energy_streaming: Final = ZCLAttributeDef(
            id=0x006C,
            type=t.Bool,
            access="rwp",
            is_manufacturer_specific=True,
        )
        sensitivity_preset: Final = ZCLAttributeDef(
            id=0x0070,
            type=SensitivityPreset,
            access="rwp",
            is_manufacturer_specific=True,
        )
        presence_clear_cooldown: Final = ZCLAttributeDef(
            id=0x0077,
            type=t.uint32_t,
            access="rwp",
            is_manufacturer_specific=True,
        )
        led_indicator: Final = ZCLAttributeDef(
            id=0x007B,
            type=t.Bool,
            access="rwp",
            is_manufacturer_specific=True,
        )

        zone_1_active: Final = ZCLAttributeDef(id=0x6511, type=t.Bool, access="rwp", is_manufacturer_specific=True)
        zone_2_active: Final = ZCLAttributeDef(id=0x6512, type=t.Bool, access="rwp", is_manufacturer_specific=True)
        zone_3_active: Final = ZCLAttributeDef(id=0x6513, type=t.Bool, access="rwp", is_manufacturer_specific=True)
        zone_4_active: Final = ZCLAttributeDef(id=0x6514, type=t.Bool, access="rwp", is_manufacturer_specific=True)
        zone_5_active: Final = ZCLAttributeDef(id=0x6515, type=t.Bool, access="rwp", is_manufacturer_specific=True)
        zone_6_active: Final = ZCLAttributeDef(id=0x6516, type=t.Bool, access="rwp", is_manufacturer_specific=True)
        zone_7_active: Final = ZCLAttributeDef(id=0x6517, type=t.Bool, access="rwp", is_manufacturer_specific=True)
        zone_8_active: Final = ZCLAttributeDef(id=0x6518, type=t.Bool, access="rwp", is_manufacturer_specific=True)
        zone_9_active: Final = ZCLAttributeDef(id=0x6519, type=t.Bool, access="rwp", is_manufacturer_specific=True)
        zone_10_active: Final = ZCLAttributeDef(id=0x651A, type=t.Bool, access="rwp", is_manufacturer_specific=True)

        zone_1_motion_energy: Final = ZCLAttributeDef(id=0x6521, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_2_motion_energy: Final = ZCLAttributeDef(id=0x6522, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_3_motion_energy: Final = ZCLAttributeDef(id=0x6523, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_4_motion_energy: Final = ZCLAttributeDef(id=0x6524, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_5_motion_energy: Final = ZCLAttributeDef(id=0x6525, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_6_motion_energy: Final = ZCLAttributeDef(id=0x6526, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_7_motion_energy: Final = ZCLAttributeDef(id=0x6527, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_8_motion_energy: Final = ZCLAttributeDef(id=0x6528, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_9_motion_energy: Final = ZCLAttributeDef(id=0x6529, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_10_motion_energy: Final = ZCLAttributeDef(id=0x652A, type=t.uint8_t, access="rp", is_manufacturer_specific=True)

        zone_1_presence_energy: Final = ZCLAttributeDef(id=0x6531, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_2_presence_energy: Final = ZCLAttributeDef(id=0x6532, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_3_presence_energy: Final = ZCLAttributeDef(id=0x6533, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_4_presence_energy: Final = ZCLAttributeDef(id=0x6534, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_5_presence_energy: Final = ZCLAttributeDef(id=0x6535, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_6_presence_energy: Final = ZCLAttributeDef(id=0x6536, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_7_presence_energy: Final = ZCLAttributeDef(id=0x6537, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_8_presence_energy: Final = ZCLAttributeDef(id=0x6538, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_9_presence_energy: Final = ZCLAttributeDef(id=0x6539, type=t.uint8_t, access="rp", is_manufacturer_specific=True)
        zone_10_presence_energy: Final = ZCLAttributeDef(id=0x653A, type=t.uint8_t, access="rp", is_manufacturer_specific=True)

        zone_1_motion_threshold: Final = ZCLAttributeDef(id=0x6541, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_2_motion_threshold: Final = ZCLAttributeDef(id=0x6542, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_3_motion_threshold: Final = ZCLAttributeDef(id=0x6543, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_4_motion_threshold: Final = ZCLAttributeDef(id=0x6544, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_5_motion_threshold: Final = ZCLAttributeDef(id=0x6545, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_6_motion_threshold: Final = ZCLAttributeDef(id=0x6546, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_7_motion_threshold: Final = ZCLAttributeDef(id=0x6547, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_8_motion_threshold: Final = ZCLAttributeDef(id=0x6548, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_9_motion_threshold: Final = ZCLAttributeDef(id=0x6549, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_10_motion_threshold: Final = ZCLAttributeDef(id=0x654A, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)

        zone_1_presence_threshold: Final = ZCLAttributeDef(id=0x6551, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_2_presence_threshold: Final = ZCLAttributeDef(id=0x6552, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_3_presence_threshold: Final = ZCLAttributeDef(id=0x6553, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_4_presence_threshold: Final = ZCLAttributeDef(id=0x6554, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_5_presence_threshold: Final = ZCLAttributeDef(id=0x6555, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_6_presence_threshold: Final = ZCLAttributeDef(id=0x6556, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_7_presence_threshold: Final = ZCLAttributeDef(id=0x6557, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_8_presence_threshold: Final = ZCLAttributeDef(id=0x6558, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_9_presence_threshold: Final = ZCLAttributeDef(id=0x6559, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)
        zone_10_presence_threshold: Final = ZCLAttributeDef(id=0x655A, type=t.uint8_t, access="rwp", is_manufacturer_specific=True)

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        DP_PRESENCE_STATE: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "presence_state",
            converter=PresenceState,
        ),
        DP_DETECTION_RANGE: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "detection_range",
        ),
        DP_ILLUMINANCE: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "illuminance",
        ),
        DP_HEARTBEAT_ENABLE: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "energy_streaming",
            converter=bool,
        ),
        DP_NO_PERSON_TIME: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "presence_clear_cooldown",
        ),
        DP_INDICATOR: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "led_indicator",
            converter=bool,
        ),
    }

    data_point_handlers = {
        DP_PRESENCE_STATE: "_dp_2_attr_update",
        DP_DETECTION_RANGE: "_dp_2_attr_update",
        DP_ILLUMINANCE: "_dp_2_attr_update",
        DP_HEARTBEAT_ENABLE: "_dp_2_attr_update",
        DP_NO_PERSON_TIME: "_dp_2_attr_update",
        DP_INDICATOR: "_dp_2_attr_update",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._zone_active = [True] * ZONE_COUNT
        self._motion_thr = [128] * ZONE_COUNT
        self._presence_thr = [128] * ZONE_COUNT
        self._thresholds_initialized = False
        self._energy_stream_on = False
        self._energy_stream_enabled_for_calibration = False
        self._keepalive_task = None
        self._auto_calibration_status_raw = None
        self._pending_zone_write = False
        self._first_message_received = False

    def _update_attribute(self, attrid: int, value: Any) -> None:
        if attrid == self.AttributeDefs.auto_calibration_status.id and isinstance(value, int):
            value = CALIB_STATUS_MAP.get(value, f"unknown({value})")
        super()._update_attribute(attrid, value)

    def _process_tuya_datapoints(self, dp_values: list[Any]) -> bool:
        if not self._first_message_received:
            self._first_message_received = True
            self._update_attribute(
                self.attributes_by_name["auto_calibration_status"].id,
                "standby",
            )
            self._update_attribute(
                self.attributes_by_name["auto_calibration"].id,
                AutoCalibrationCmd.standby,
            )

        dp_error = False

        for dpv in dp_values:
            dp = dpv.dp
            data = _tuya_raw(dpv.data)
            _LOGGER.debug(
                "[ZPS-Z1] received Tuya DP%d: raw=%s",
                dp,
                data.hex(),
            )

            if dp == DP_ENERGY_VALUE:
                self._handle_energy_value(data)
            elif dp == DP_ZONE_MAP:
                self._handle_zone_map(data)
            elif dp == DP_ENERGY_THRESHOLD:
                self._handle_energy_threshold(data)
            elif dp == DP_HEART:
                continue
            elif dp == DP_AI_SELF_LEARNING:
                raw = data[0] if data else 0
                status = CALIB_STATUS_MAP.get(raw, f"unknown({raw})")
                _LOGGER.debug(
                    "[ZPS-Z1] received DP103 auto calibration status: raw=%s status=%s",
                    data.hex(),
                    status,
                )
                self._auto_calibration_status_raw = raw
                self._update_attribute(
                    self.attributes_by_name["auto_calibration_status"].id,
                    status,
                )
                if raw in (
                    int(AutoCalibrationCmd.standby),
                    int(AutoCalibrationCmd.start),
                    int(AutoCalibrationCmd.cancel),
                ):
                    self._update_attribute(
                        self.attributes_by_name["auto_calibration"].id,
                        AutoCalibrationCmd(raw),
                    )
                if raw in (3, 4, 5):
                    self._update_attribute(
                        self.attributes_by_name["auto_calibration"].id,
                        AutoCalibrationCmd.standby,
                    )
                    if self._energy_stream_enabled_for_calibration:
                        self.create_catching_task(
                            self._disable_calibration_energy_stream()
                        )
            elif dp == DP_SENSITIVITY_PRESET:
                try:
                    value = SensitivityPreset(data[0] if data else SensitivityPreset.custom)
                except ValueError:
                    value = SensitivityPreset.custom
                self._update_attribute(
                    self.attributes_by_name["sensitivity_preset"].id,
                    value,
                )
            else:
                try:
                    dp_handler = self.data_point_handlers[dp]
                    getattr(self, dp_handler)(dpv)
                except (AttributeError, KeyError):
                    _LOGGER.warning(
                        "[ZPS-Z1] unhandled Tuya DP%d: raw=%s",
                        dp,
                        data.hex(),
                    )
                    dp_error = True

        return dp_error

    def handle_get_data(self, command: TuyaCommand) -> foundation.Status:
        dp_error = self._process_tuya_datapoints(command.datapoints)
        return (
            foundation.Status.SUCCESS
            if not dp_error
            else foundation.Status.UNSUPPORTED_ATTRIBUTE
        )

    handle_set_data_response = handle_get_data
    handle_active_status_report = handle_get_data

    def handle_cluster_specific_commands(self, tsn: int, command_id: int, args: Any) -> None:
        dp_values = getattr(args, "dpValues", None) or []
        self._process_tuya_datapoints(dp_values)


    def _handle_energy_value(self, data: bytes) -> None:
        if len(data) < 20:
            _LOGGER.debug("[ZPS-Z1] ignoring short DP102 payload: %s", data.hex())
            return
        motion_raw, presence_raw = _decode_energy(data)
        for i in range(ZONE_COUNT):
            self._update_attribute(
                self.attributes_by_name[f"zone_{i + 1}_motion_energy"].id,
                _to_app(motion_raw[i]),
            )
            self._update_attribute(
                self.attributes_by_name[f"zone_{i + 1}_presence_energy"].id,
                _to_app(presence_raw[i]),
            )

    def _handle_zone_map(self, data: bytes) -> None:
        if len(data) < ZONE_COUNT:
            _LOGGER.debug("[ZPS-Z1] ignoring short DP117 payload: %s", data.hex())
            return

        zones = [bool(data[i]) for i in range(ZONE_COUNT)]
        _LOGGER.debug("[ZPS-Z1] received DP117 zone map: raw=%s active=%s", data.hex(), zones)
        if self._pending_zone_write:
            if zones != self._zone_active:
                _LOGGER.warning(
                    "[ZPS-Z1] DP117 mismatch, expected=%s received=%s; retrying",
                    self._zone_active,
                    zones,
                )
                self.create_catching_task(self._resend_zone_map())
                return
            self._pending_zone_write = False
        else:
            self._zone_active = zones

        for i, active in enumerate(zones):
            self._update_attribute(self.attributes_by_name[f"zone_{i + 1}_active"].id, active)

    def _handle_energy_threshold(self, data: bytes) -> None:
        if len(data) < 20:
            _LOGGER.debug("[ZPS-Z1] ignoring short DP124 payload: %s", data.hex())
            return

        motion_raw, presence_raw = _decode_energy(data)
        _LOGGER.debug(
            "[ZPS-Z1] received DP124 thresholds: raw=%s motion=%s presence=%s",
            data.hex(),
            motion_raw,
            presence_raw,
        )
        self._motion_thr = list(motion_raw)
        self._presence_thr = list(presence_raw)
        self._thresholds_initialized = True
        for i in range(ZONE_COUNT):
            self._update_attribute(
                self.attributes_by_name[f"zone_{i + 1}_motion_threshold"].id,
                _to_app(motion_raw[i]),
            )
            self._update_attribute(
                self.attributes_by_name[f"zone_{i + 1}_presence_threshold"].id,
                _to_app(presence_raw[i]),
            )

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        allow_cache: bool = False,
        **kwargs: Any,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_name = attr_def.name
            try:
                await self._set_attribute(attr_name, value)
            except Exception as exc:
                _LOGGER.warning(
                    "[ZPS-Z1] failed writing %s=%s: %s",
                    attr_name,
                    value,
                    exc,
                )
                return [[foundation.WriteAttributesStatusRecord(foundation.Status.FAILURE, attr_def.id)]]

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    async def _set_attribute(self, key: str, value: Any) -> None:
        if key == "detection_range":
            v = max(0, min(500, round(int(value) / 50) * 50))
            await self._send_dp(DP_DETECTION_RANGE, DT_VALUE, list(v.to_bytes(4, "big")))

        elif key == "sensitivity_preset":
            v = _enum_from_value(SensitivityPreset, value)
            if v is not None:
                await self._send_dp(DP_SENSITIVITY_PRESET, DT_ENUM, [int(v)])
                self._update_attribute(self.attributes_by_name["sensitivity_preset"].id, v)

        elif key == "presence_clear_cooldown":
            v = max(2, min(60, round(int(value))))
            await self._send_dp(DP_NO_PERSON_TIME, DT_VALUE, list(v.to_bytes(4, "big")))

        elif key == "led_indicator":
            await self._send_dp(DP_INDICATOR, DT_BOOL, [1 if bool(value) else 0])
            self._update_attribute(self.attributes_by_name["led_indicator"].id, bool(value))

        elif key == "energy_streaming":
            on = bool(value)
            await self._send_dp(DP_HEARTBEAT_ENABLE, DT_BOOL, [1 if on else 0])
            self._energy_stream_on = on
            if not on:
                self._energy_stream_enabled_for_calibration = False
            self._update_attribute(self.attributes_by_name["energy_streaming"].id, on)
            if on:
                self._start_keepalive()
            else:
                self._stop_keepalive()

        elif key == "auto_calibration":
            v = _enum_from_value(AutoCalibrationCmd, value)
            if v is None:
                raise ValueError(f"unsupported auto_calibration value: {value!r}")

            if v is AutoCalibrationCmd.standby:
                self._update_attribute(
                    self.attributes_by_name["auto_calibration"].id,
                    v,
                )
                return

            if v is AutoCalibrationCmd.start and not self._energy_stream_on:
                _LOGGER.debug(
                    "[ZPS-Z1] enabling energy streaming before auto calibration"
                )
                await self._send_dp(DP_HEARTBEAT_ENABLE, DT_BOOL, [1])
                self._energy_stream_on = True
                self._energy_stream_enabled_for_calibration = True
                self._update_attribute(
                    self.attributes_by_name["energy_streaming"].id,
                    True,
                )
                self._start_keepalive()
                await asyncio.sleep(0.5)

            _LOGGER.debug(
                "[ZPS-Z1] sending auto_calibration command: %s (%d)",
                v.name,
                int(v),
            )
            _LOGGER.debug(
                "[ZPS-Z1] sending DP103 auto calibration command: status=%s raw=%02x",
                v.name,
                int(v),
            )
            await self._send_dp(DP_AI_SELF_LEARNING, DT_ENUM, [int(v)])
            self._update_attribute(
                self.attributes_by_name["auto_calibration"].id,
                v,
            )

        elif key.startswith("zone_") and key.endswith("_active"):
            idx = int(key.split("_")[1]) - 1
            zones = list(self._zone_active)
            zones[idx] = bool(value)
            self._zone_active = zones
            self._pending_zone_write = True
            await self._send_dp(DP_ZONE_MAP, DT_RAW, [1 if active else 0 for active in zones])
            self._update_attribute(self.attributes_by_name[f"zone_{idx + 1}_active"].id, zones[idx])

        elif key.startswith("zone_") and key.endswith("_motion_threshold"):
            await self._ensure_thresholds_initialized()
            idx = int(key.split("_")[1]) - 1
            motion = list(self._motion_thr)
            app_value = max(0, min(100, round(int(value))))
            motion[idx] = _to_raw(app_value)
            self._motion_thr = motion
            await self._send_dp(DP_ENERGY_THRESHOLD, DT_RAW, list(_encode_energy(motion, self._presence_thr)))
            await asyncio.sleep(0.15)
            await self._send_dp(DP_SENSITIVITY_PRESET, DT_ENUM, [int(SensitivityPreset.custom)])
            self._update_attribute(self.attributes_by_name[key].id, app_value)
            self._update_attribute(self.attributes_by_name["sensitivity_preset"].id, SensitivityPreset.custom)

        elif key.startswith("zone_") and key.endswith("_presence_threshold"):
            await self._ensure_thresholds_initialized()
            idx = int(key.split("_")[1]) - 1
            presence = list(self._presence_thr)
            app_value = max(0, min(100, round(int(value))))
            presence[idx] = _to_raw(app_value)
            self._presence_thr = presence
            await self._send_dp(DP_ENERGY_THRESHOLD, DT_RAW, list(_encode_energy(self._motion_thr, presence)))
            await asyncio.sleep(0.15)
            await self._send_dp(DP_SENSITIVITY_PRESET, DT_ENUM, [int(SensitivityPreset.custom)])
            self._update_attribute(self.attributes_by_name[key].id, app_value)
            self._update_attribute(self.attributes_by_name["sensitivity_preset"].id, SensitivityPreset.custom)

        else:
            _LOGGER.debug("[ZPS-Z1] unhandled writable attribute: %s", key)

    async def _resend_zone_map(self) -> None:
        await asyncio.sleep(0.5)
        self._pending_zone_write = True
        await self._send_dp(DP_ZONE_MAP, DT_RAW, [1 if active else 0 for active in self._zone_active])

    async def _ensure_thresholds_initialized(self) -> None:
        if self._thresholds_initialized:
            return

        if self._load_thresholds_from_cache():
            return

        await self._query_data()
        await asyncio.sleep(0.5)

        if self._thresholds_initialized or self._load_thresholds_from_cache():
            return

        raise ValueError("energy thresholds are not initialized yet")

    def _load_thresholds_from_cache(self) -> bool:
        attr_cache = getattr(self, "_attr_cache", {})
        motion: list[int] = []
        presence: list[int] = []

        for i in range(ZONE_COUNT):
            motion_attr = self.attributes_by_name[f"zone_{i + 1}_motion_threshold"].id
            presence_attr = self.attributes_by_name[f"zone_{i + 1}_presence_threshold"].id

            if motion_attr not in attr_cache or presence_attr not in attr_cache:
                return False

            motion.append(_to_raw(int(attr_cache[motion_attr])))
            presence.append(_to_raw(int(attr_cache[presence_attr])))

        self._motion_thr = motion
        self._presence_thr = presence
        self._thresholds_initialized = True
        return True

    def _start_keepalive(self) -> None:
        self._stop_keepalive()
        self._keepalive_task = asyncio.get_running_loop().create_task(
            self._keepalive_loop()
        )

    def _stop_keepalive(self) -> None:
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
        self._keepalive_task = None

    async def _keepalive_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(5)
                await self._send_dp(DP_HEARTBEAT_ENABLE, DT_BOOL, [1])
        except asyncio.CancelledError:
            pass

    async def _disable_calibration_energy_stream(self) -> None:
        try:
            await self._send_dp(DP_HEARTBEAT_ENABLE, DT_BOOL, [0])
            self._energy_stream_on = False
            self._energy_stream_enabled_for_calibration = False
            self._stop_keepalive()
            self._update_attribute(
                self.attributes_by_name["energy_streaming"].id,
                False,
            )
        except Exception as exc:
            _LOGGER.debug("[ZPS-Z1] disabling calibration energy stream failed: %s", exc)

    async def _send_dp(self, dp: int, datatype: int, data: list[int]) -> None:
        if datatype == DT_BOOL:
            tuya_data = TuyaData(bool(data[0] if data else 0))
        elif datatype == DT_VALUE:
            tuya_data = TuyaData(int.from_bytes(bytes(data).rjust(4, b"\x00")[-4:], "big"))
        elif datatype == DT_ENUM:
            tuya_data = TuyaData(t.enum8(data[0] if data else 0))
        else:
            tuya_data = TuyaData()
            tuya_data.dp_type = TuyaDPType.RAW
            tuya_data.raw = bytes(data)
        tsn = self.endpoint.device.application.get_sequence()
        cmd = TuyaCommand(
            status=0,
            tsn=tsn,
            datapoints=[TuyaDatapointData(dp, tuya_data)],
        )
        await self.command(
            self.mcu_write_command,
            cmd,
            expect_reply=False,
            tsn=tsn,
        )

    async def _query_data(self) -> None:
        """Ask the Tuya MCU to report its current datapoint state."""
        try:
            await self.command(
                self.ServerCommandDefs.query_data.id,
                expect_reply=False,
            )
        except Exception as exc:
            _LOGGER.debug("[ZPS-Z1] Tuya data query failed: %s", exc)

builder = QuirkBuilder("_TZE284_ft7qqpx3", "TS0601")
builder.adds(ZpsZ1ManufCluster).skip_configuration()

builder.binary_sensor(
    attribute_name="presence_state",
    cluster_id=TUYA_CLUSTER_ID,
    endpoint_id=1,
    device_class=BinarySensorDeviceClass.OCCUPANCY,
    entity_type=EntityType.STANDARD,
    fallback_name="Occupancy",
    translation_key="occupancy",
    attribute_initialized_from_cache=False,
)
builder.enum(
    attribute_name="presence_state",
    enum_class=PresenceState,
    cluster_id=TUYA_CLUSTER_ID,
    endpoint_id=1,
    entity_platform=EntityPlatform.SENSOR,
    entity_type=EntityType.STANDARD,
    fallback_name="Presence state",
    translation_key="presence_state",
)
builder.sensor(
    attribute_name="illuminance",
    cluster_id=TUYA_CLUSTER_ID,
    endpoint_id=1,
    fallback_name="Illuminance",
    translation_key="illuminance",
)
builder.number(
    attribute_name="detection_range",
    cluster_id=TUYA_CLUSTER_ID,
    endpoint_id=1,
    min_value=0,
    max_value=500,
    step=50,
    fallback_name="Detection range",
    translation_key="detection_range",
    entity_type=EntityType.CONFIG,
)
builder.number(
    attribute_name="presence_clear_cooldown",
    cluster_id=TUYA_CLUSTER_ID,
    endpoint_id=1,
    min_value=2,
    max_value=60,
    step=1,
    fallback_name="Presence clear cooldown",
    translation_key="presence_clear_cooldown",
    entity_type=EntityType.CONFIG,
)
builder.enum(
    attribute_name="sensitivity_preset",
    enum_class=SensitivityPreset,
    cluster_id=TUYA_CLUSTER_ID,
    endpoint_id=1,
    entity_platform=EntityPlatform.SELECT,
    entity_type=EntityType.CONFIG,
    fallback_name="Sensitivity preset",
    translation_key="sensitivity_preset",
)
builder.enum(
    attribute_name="auto_calibration",
    enum_class=AutoCalibrationCmd,
    cluster_id=TUYA_CLUSTER_ID,
    endpoint_id=1,
    entity_platform=EntityPlatform.SELECT,
    entity_type=EntityType.CONFIG,
    fallback_name="Auto calibration",
    translation_key="auto_calibration",
    attribute_initialized_from_cache=False,
)
builder.sensor(
    attribute_name="auto_calibration_status",
    cluster_id=TUYA_CLUSTER_ID,
    endpoint_id=1,
    entity_type=EntityType.DIAGNOSTIC,
    fallback_name="Auto calibration status",
    translation_key="auto_calibration_status",
    attribute_initialized_from_cache=False,
)
builder.switch(
    attribute_name="led_indicator",
    cluster_id=TUYA_CLUSTER_ID,
    endpoint_id=1,
    fallback_name="LED indicator",
    translation_key="led_indicator",
    entity_type=EntityType.CONFIG,
)
builder.switch(
    attribute_name="energy_streaming",
    cluster_id=TUYA_CLUSTER_ID,
    endpoint_id=1,
    fallback_name="Energy streaming",
    translation_key="energy_streaming",
    entity_type=EntityType.CONFIG,
)

for zone in range(1, ZONE_COUNT + 1):
    start = (zone - 1) * 50
    end = zone * 50
    builder.switch(
        attribute_name=f"zone_{zone}_active",
        cluster_id=TUYA_CLUSTER_ID,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        fallback_name=f"Zone {zone} active ({start}-{end} cm)",
        translation_key=f"zone_{zone}_active",
    )

for metric in ("motion", "presence"):
    for zone in range(1, ZONE_COUNT + 1):
        builder.sensor(
            attribute_name=f"zone_{zone}_{metric}_energy",
            cluster_id=TUYA_CLUSTER_ID,
            endpoint_id=1,
            entity_type=EntityType.DIAGNOSTIC,
            fallback_name=f"Zone {zone} {metric} energy",
            translation_key=f"zone_{zone}_{metric}_energy",
        )

for metric in ("motion", "presence"):
    for zone in range(1, ZONE_COUNT + 1):
        builder.number(
            attribute_name=f"zone_{zone}_{metric}_threshold",
            cluster_id=TUYA_CLUSTER_ID,
            endpoint_id=1,
            min_value=0,
            max_value=100,
            step=1,
            entity_type=EntityType.CONFIG,
            fallback_name=f"Zone {zone} {metric} threshold",
            translation_key=f"zone_{zone}_{metric}_threshold",
        )

builder.add_to_registry()
