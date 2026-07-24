"""SONOFF TP-WGZBA thermostat custom ZHA quirk."""

from __future__ import annotations

from enum import IntEnum
from typing import Any, Final

try:
    from zha.application.platforms.number import NumberMode
except ImportError:
    # Keep custom quirks compatible with older ZHA releases.
    from zha.application.platforms.number.device_class import NumberMode
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    DataTypeId,
    ZCLAttributeDef,
    ZCLCommandDef,
)

try:
    from zhaquirks.builder import (
        EntityPlatform,
        EntityType,
        NumberDeviceClass,
        QuirkBuilder,
        UnitOfTemperature,
        UnitOfTime,
    )
    from zhaquirks.clusters import CustomCluster
except ModuleNotFoundError:
    # Keep custom quirks compatible with the builder layout in older HA releases.
    from homeassistant.const import UnitOfTemperature, UnitOfTime

    from zhaquirks import CustomCluster
    from zhaquirks.tuya.builder import (
        EntityPlatform,
        EntityType,
        NumberDeviceClass,
        QuirkBuilder,
    )

SONOFF_PRIVATE_CLUSTER_ID = 0xFC11
DEVICE_WORK_MODE_SOURCE_ATTR_ID = 0x0018
DEVICE_WORK_MODE_TEMPORARY_MANUAL = 0x05

CMD_TEMPORARY_MODE = 0x11
CMD_TEMPORARY_MODE_UI_APPLY = 0x80
CMD_WEEKLY_SCHEDULE_UI_APPLY = 0x81
CMD_WEEKLY_SCHEDULE_UI_READ = 0x82

TEMPORARY_MODE_EXIT = 0x00
TEMPORARY_MODE_BOOST = 0x01
TEMPORARY_MODE_TIMER = 0x02

ZCL_STRUCT_ITEM_COUNT = b"\x02\x00"
ZCL_DATA_TYPE_INT16 = 0x29
ZCL_DATA_TYPE_UINT16 = 0x21

TEMPERATURE_CONTROL_THRESHOLD_LOW_DEFAULT = -200
TEMPERATURE_CONTROL_THRESHOLD_HIGH_DEFAULT = 200
HVAC_MESSAGE_TLV_OPEN_WINDOW = 0x00
HVAC_MESSAGE_TLV_OPEN_WINDOW_LEN = 0x01
NTC_CURRENT_TEMPERATURE_CODE_INVALID = -32768
NTC_CURRENT_TEMPERATURE_CODE_OPEN_CIRCUIT = -32512
NTC_CURRENT_TEMPERATURE_CODE_SHORT_CIRCUIT = -32256
NTC_CURRENT_TEMPERATURE_CODE_ADC_INVALID = -32000
NTC_CURRENT_TEMPERATURE_MIN_VALID = -27315
RELAY_OUTPUT_TYPE_VALID_MASK = 0x03

THERMOSTAT_LOCAL_TEMPERATURE_ATTR_ID = 0x0000
CURRENT_NTC_TEMPERATURE_RAW_ATTR_ID = 0x6031

TEMPERATURE_CONTROL_THRESHOLD_LOW_ATTR_ID = 0x7000
TEMPERATURE_CONTROL_THRESHOLD_HIGH_ATTR_ID = 0x7001
RADAR_DND_START_MINUTE_ATTR_ID = 0x7002
RADAR_DND_END_MINUTE_ATTR_ID = 0x7003
SCREEN_NIGHT_START_MINUTE_ATTR_ID = 0x7004
SCREEN_NIGHT_END_MINUTE_ATTR_ID = 0x7005
RELAY_OUTPUT_TYPE_RELAY1_ATTR_ID = 0x7006
RELAY_OUTPUT_TYPE_RELAY2_ATTR_ID = 0x7007
TEMPERATURE_SENSOR_SELECT_ATTR_ID = 0x7008
EXTERNAL_TEMPERATURE_INPUT_ATTR_ID = 0x7009
EXTERNAL_TEMPERATURE_SENSOR_ATTR_ID = 0x700A
HVAC_MESSAGE_OPEN_WINDOW_STATE_ATTR_ID = 0x7F0B
NTC_CURRENT_TEMPERATURE_ATTR_ID = 0x7F0C
NTC_CURRENT_TEMPERATURE_STATE_ATTR_ID = 0x7F0D
TEMPORARY_TEMPERATURE_MODE_STATE_ATTR_ID = 0x7F0E
NTC_CURRENT_TEMPERATURE_DISPLAY_ATTR_ID = 0x7F0F

TEMPORARY_MODE_UI_MODE_ATTR_ID = 0x7100
TEMPORARY_MODE_UI_DURATION_MINUTES_ATTR_ID = 0x7101
TEMPORARY_MODE_UI_TARGET_TEMP_ATTR_ID = 0x7102
TPWGZBA_UI_SYSTEM_MODE_ATTR_ID = 0x7103
DEVICE_WORK_MODE_ATTR_ID = 0x7104

WEEKLY_SCHEDULE_UI_DAY_ATTR_ID = 0x7200
WEEKLY_SCHEDULE_UI_TEMP_ATTR_IDS = tuple(0x7200 + index for index in range(1, 13))
WEEKLY_SCHEDULE_UI_TIME_ATTR_IDS = tuple(0x720C + index for index in range(1, 13))
WEEKLY_SCHEDULE_UI_TRANSITION_COUNT_ATTR_ID = 0x7219

TEMPORARY_MODE_UI_DURATION_MINUTES_DEFAULT = 30
TEMPORARY_MODE_UI_DURATION_MINUTES_MAX = 1439
TEMPORARY_MODE_BOOST_TARGET_TEMP_X100 = 3000
TEMPORARY_MODE_UI_TARGET_TEMP_MIN_X100 = 500
TEMPORARY_MODE_UI_TARGET_TEMP_MAX_X100 = 3000
EXTERNAL_TEMPERATURE_INPUT_MIN_X100 = 0
EXTERNAL_TEMPERATURE_INPUT_MAX_X100 = 9990

WEEKLY_SCHEDULE_UI_TEMP_MIN_X100 = 500
WEEKLY_SCHEDULE_UI_TEMP_MAX_X100 = 3000
WEEKLY_SCHEDULE_DAY_MASK_ALL = 0x7F
WEEKLY_SCHEDULE_TRANSITION_MAX = 14
WEEKLY_SCHEDULE_TIME_MAX = 1439
WEEKLY_SCHEDULE_UI_TIME_STEP_MINUTES = 30
WEEKLY_SCHEDULE_UI_TIME_NULL = 0xFFFF
WEEKLY_SCHEDULE_UI_SLOT_MAX = 12
WEEKLY_SCHEDULE_UI_TIMES = (
    0,
    120,
    240,
    360,
    480,
    600,
    720,
    840,
    960,
    1080,
    1200,
    1320,
)
WEEKLY_SCHEDULE_UI_TIME_SELECT_MAX = (
    WEEKLY_SCHEDULE_TIME_MAX // WEEKLY_SCHEDULE_UI_TIME_STEP_MINUTES
) * WEEKLY_SCHEDULE_UI_TIME_STEP_MINUTES


def _write_succeeded(
    result: list[list[foundation.WriteAttributesStatusRecord]],
) -> bool:
    """Return whether a write response contains only successful statuses."""

    return bool(result) and all(
        record.status == foundation.Status.SUCCESS
        for records in result
        for record in records
    )


WeeklyScheduleUiTime = IntEnum(
    "WeeklyScheduleUiTime",
    {
        "NULL": WEEKLY_SCHEDULE_UI_TIME_NULL,
        **{
            f"{minute // 60:02d}:{minute % 60:02d}": minute
            for minute in range(
                0,
                WEEKLY_SCHEDULE_UI_TIME_SELECT_MAX + 1,
                WEEKLY_SCHEDULE_UI_TIME_STEP_MINUTES,
            )
        },
    },
)
WeeklyScheduleUiTimeFirst = IntEnum("WeeklyScheduleUiTimeFirst", {"00:00": 0})
TimeOfDay30Min = IntEnum(
    "TimeOfDay30Min",
    {
        f"{minute // 60:02d}:{minute % 60:02d}": minute
        for minute in range(
            0,
            WEEKLY_SCHEDULE_UI_TIME_SELECT_MAX + 1,
            WEEKLY_SCHEDULE_UI_TIME_STEP_MINUTES,
        )
    },
)


class RawBytes(bytes):
    """Raw private attribute payload without a length prefix."""

    def __new__(cls, value: Any = b"") -> RawBytes:
        """Create raw bytes from bytes-like values or decoded ZCL structures."""

        if value is None:
            raw_value = b""
        elif isinstance(value, cls) or isinstance(
            value, (bytes, bytearray, memoryview)
        ):
            raw_value = bytes(value)
        elif isinstance(value, foundation.TypeValue):
            if isinstance(value.value, foundation.ZCLStructure):
                raw_value = value.value.serialize()
            else:
                raw_value = value.serialize()
        elif isinstance(value, foundation.ZCLStructure):
            raw_value = value.serialize()
        elif isinstance(value, (list, tuple)) and all(
            isinstance(item, foundation.TypeValue) for item in value
        ):
            raw_value = foundation.ZCLStructure(value).serialize()
        else:
            raw_value = bytes(value)

        return super().__new__(cls, raw_value)

    @classmethod
    def deserialize(cls, data: bytes) -> tuple[RawBytes, bytes]:
        """Deserialize all remaining bytes."""

        return cls(data), b""

    def serialize(self) -> bytes:
        """Serialize as-is."""

        return bytes(self)


class Uint8ArrayPayload(bytes):
    """ZCL array payload backed by uint8 elements."""

    def __new__(cls, value: Any = b"") -> Uint8ArrayPayload:
        """Create an array payload from bytes-like values or decoded zigpy arrays."""

        if value is None:
            raw_value = b""
        elif isinstance(value, cls):
            raw_value = bytes(value)
        elif isinstance(value, foundation.Array):
            if int(value.type) != int(DataTypeId.uint8):
                raise ValueError(
                    f"Expected uint8 array, got element type {value.type!r}"
                )
            raw_value = bytes(int(item) for item in value.value)
        elif isinstance(value, (bytes, bytearray, memoryview)):
            raw_value = bytes(value)
        else:
            raw_value = bytes(value)

        return super().__new__(cls, raw_value)

    @classmethod
    def deserialize(cls, data: bytes) -> tuple[Uint8ArrayPayload, bytes]:
        """Deserialize a uint8 array payload from element-type/count-prefixed bytes."""

        if len(data) < 3:
            raise ValueError("Data is too short to contain a uint8 array payload")

        element_type = data[0]
        if element_type != int(DataTypeId.uint8):
            raise ValueError(
                f"Expected uint8 array element type, got 0x{element_type:02X}"
            )

        payload_len = int.from_bytes(data[1:3], "little")
        end = 3 + payload_len
        if len(data) < end:
            raise ValueError("Data is too short for declared uint8 array payload")

        return cls(data[3:end]), data[end:]

    def serialize(self) -> bytes:
        """Serialize as element-type/count-prefixed uint8 array content."""

        payload = bytes(self)
        return (
            bytes((int(DataTypeId.uint8),))
            + len(payload).to_bytes(2, "little")
            + payload
        )


class RadarSensitivity(t.enum8):
    """Radar sensitivity level."""

    Low = 0x00
    Medium = 0x01
    High = 0x02


class RelayOutputType(t.enum8):
    """Relay output type."""

    Normally_Open = 0x00
    Normally_Closed = 0x01


class BtPairingBroadcastReq(t.enum8):
    """Bluetooth pairing broadcast request state."""

    Disable = 0x00
    Enable = 0x01


class HvacMessageOpenWindowState(t.enum8):
    """HVAC message window opening state."""

    closed = 0x00
    open = 0x01


class NtcCurrentTemperatureState(t.enum8):
    """NTC current temperature diagnostic state."""

    normal = 0x00
    idle = 0x01


class WeeklyScheduleActiveGroup(t.enum8):
    """Weekly schedule active group."""

    Schedule_1 = 0x00
    Schedule_2 = 0x01
    Schedule_3 = 0x02


class TPWGZBASystemMode(t.enum8):
    """TP-WGZBA thermostat system mode."""

    Off = 0x00
    Schedule = 0x01
    Manual = 0x04


class TPWGZBADeviceWorkMode(t.enum8):
    """Device work mode exposed as a read-only display value."""

    Off = 0x00
    Schedule = 0x01
    Manual = 0x04
    Temporary_Manual = 0x05


class TemporaryTemperatureModeSettings(t.enum8):
    """Private temporary temperature mode settings."""

    Boost = 0x00
    Timer = 0x01
    Idle = 0xFF


class TemporaryTemperatureModeState(t.enum8):
    """Displayed temporary temperature mode state."""

    Boost = 0x00
    Timer = 0x01
    Idle = 0x02


class TemporaryModeUiAction(t.enum8):
    """Temporary mode action exposed through the ZHA UI."""

    Exit = TEMPORARY_MODE_EXIT
    Boost = TEMPORARY_MODE_BOOST
    Timer = TEMPORARY_MODE_TIMER


class TemporaryModeUiSelectableAction(t.enum8):
    """Temporary mode actions selectable from the ZHA dropdown."""

    Boost = TEMPORARY_MODE_BOOST
    Timer = TEMPORARY_MODE_TIMER


class WeeklyScheduleUiDay(t.enum8):
    """Weekly schedule UI day selector."""

    Sunday = 0x00
    Monday = 0x01
    Tuesday = 0x02
    Wednesday = 0x03
    Thursday = 0x04
    Friday = 0x05
    Saturday = 0x06


class TemperatureSensorSelect(t.enum8):
    """Temperature source used for the thermostat local temperature."""

    internal = 0x00
    external = 0x01
    external_2 = 0x02
    external_3 = 0x03


class SonoffTPWGZBAThermostatCluster(CustomCluster, Thermostat):
    """Thermostat cluster helpers for the standard weekly schedule commands."""

    def __init__(self, *args, **kwargs):
        """Hide unsupported standard heat setpoint limit attributes."""

        super().__init__(*args, **kwargs)
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.min_heat_setpoint_limit.id
        )
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.max_heat_setpoint_limit.id
        )

    @staticmethod
    def _system_mode_to_ha(value: Any) -> Any:
        """Expose schedule and manual as Heat so HA keeps the heating setpoint UI."""

        device_mode = TPWGZBASystemMode(int(value))
        if device_mode in (
            TPWGZBASystemMode.Schedule,
            TPWGZBASystemMode.Manual,
        ):
            return Thermostat.SystemMode.Heat
        return Thermostat.SystemMode(int(device_mode))

    @staticmethod
    def _system_mode_to_device(value: Any) -> Any:
        """Convert HA Heat writes to manual mode and keep other modes aligned."""

        ha_mode = Thermostat.SystemMode(int(value))
        if ha_mode == Thermostat.SystemMode.Heat:
            return TPWGZBASystemMode.Manual
        return TPWGZBASystemMode(int(ha_mode))

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Mirror the real mode in the private cluster and keep the HA cache standard."""

        if attrid == Thermostat.AttributeDefs.system_mode.id:
            private_cluster = getattr(self.endpoint, "sonoff_private", None)
            if private_cluster is not None:
                private_cluster._update_attribute(
                    SonoffTPWGZBAPrivateCluster.AttributeDefs.tp_wgzba_ui_system_mode.id,
                    TPWGZBASystemMode(int(value)),
                )
                private_cluster._update_device_work_mode_from_system(value)
            value = self._system_mode_to_ha(value)
        super()._update_attribute(attrid, value)

    async def read_attributes_raw(
        self, attributes: list[int], manufacturer: int | None = None, **kwargs
    ) -> tuple[list[foundation.ReadAttributeRecord], ...]:
        """Normalize system_mode reads to the standard thermostat enum."""

        result = await super().read_attributes_raw(
            attributes, manufacturer=manufacturer, **kwargs
        )
        for records in result:
            for record in records:
                if (
                    record.status == foundation.Status.SUCCESS
                    and record.attrid == Thermostat.AttributeDefs.system_mode.id
                ):
                    record.value.value = self._system_mode_to_ha(record.value.value)
        return result

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Normalize HA standard modes before writing them to the thermostat cluster."""

        mapped_attributes = attributes.copy()
        for key in list(mapped_attributes):
            if key in (
                Thermostat.AttributeDefs.system_mode,
                Thermostat.AttributeDefs.system_mode.id,
                Thermostat.AttributeDefs.system_mode.name,
            ):
                mapped_attributes[key] = self._system_mode_to_device(
                    mapped_attributes[key]
                )
        return await super().write_attributes(mapped_attributes, **kwargs)

    async def configure_reporting_multiple(
        self, config: dict[foundation.ZCLAttributeDef, foundation.ReportingConfig]
    ) -> dict[foundation.ZCLAttributeDef, foundation.Status]:
        """Skip reporting configuration for local_temperature."""

        skipped: dict[foundation.ZCLAttributeDef, foundation.Status] = {}
        remaining: dict[foundation.ZCLAttributeDef, foundation.ReportingConfig] = {}

        for attr_def, reporting_config in config.items():
            if attr_def.id == THERMOSTAT_LOCAL_TEMPERATURE_ATTR_ID:
                skipped[attr_def] = foundation.Status.SUCCESS
            else:
                remaining[attr_def] = reporting_config

        if not remaining:
            return skipped

        result = await super().configure_reporting_multiple(remaining)
        result.update(skipped)
        return result

    async def write_real_system_mode(
        self,
        mode: TPWGZBASystemMode | int,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Write the real TP-WGZBA mode without the HA Heat remap."""

        real_mode = TPWGZBASystemMode(int(mode))
        result = await super().write_attributes(
            {Thermostat.AttributeDefs.system_mode.id: real_mode},
            **kwargs,
        )
        if _write_succeeded(result):
            self._update_attribute(Thermostat.AttributeDefs.system_mode.id, real_mode)
        return result

    async def set_weekly_schedule_heat_for_group(
        self,
        group_id: int,
        day_of_week_mask: int,
        transitions: list[tuple[int, int | float]],
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
    ):
        """Switch the active schedule group and send the standard heating schedule."""

        private_cluster = getattr(self.endpoint, "sonoff_private", None)
        if private_cluster is None:
            raise ValueError("sonoff_private cluster is not available on this endpoint")

        await private_cluster.set_active_schedule_group(group_id)
        return await self.set_weekly_schedule_heat(
            day_of_week_mask,
            transitions,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
        )

    async def set_weekly_schedule_heat(
        self,
        day_of_week_mask: int,
        transitions: list[tuple[int, int | float]],
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
    ):
        """Send standard Set Weekly Schedule in heating mode."""

        day_mask = int(day_of_week_mask)
        if day_mask <= 0 or (day_mask & ~WEEKLY_SCHEDULE_DAY_MASK_ALL) != 0:
            raise ValueError("day_of_week_mask must be 0x01..0x7F")

        transition_count = len(transitions)
        if transition_count <= 0 or transition_count > WEEKLY_SCHEDULE_TRANSITION_MAX:
            raise ValueError("transitions must contain 1..14 entries")

        values: list[int] = []
        previous_minute = -1
        for index, (minute_of_day, target_temperature) in enumerate(transitions):
            minute = int(minute_of_day)
            if minute < 0 or minute > WEEKLY_SCHEDULE_TIME_MAX:
                raise ValueError("transition time must be 0..1439 minutes")
            if index == 0 and minute != 0:
                raise ValueError("the first transition must start at 00:00")
            if minute <= previous_minute:
                raise ValueError("transition times must be strictly increasing")

            target_temperature_value = float(target_temperature)
            if (
                abs(target_temperature_value)
                > float(WEEKLY_SCHEDULE_UI_TEMP_MAX_X100) / 100.0
            ):
                target_temperature_value /= 100.0
            target_x100 = int(round(target_temperature_value * 100))
            if not (
                WEEKLY_SCHEDULE_UI_TEMP_MIN_X100
                <= target_x100
                <= WEEKLY_SCHEDULE_UI_TEMP_MAX_X100
            ):
                raise ValueError("target temperature must be 5.0..30.0 Celsius")

            values.extend((minute, target_x100))
            previous_minute = minute

        return await self.command(
            self.ServerCommandDefs.set_weekly_schedule.id,
            transition_count,
            self.SeqDayOfWeek(day_mask),
            self.SeqMode.Heat,
            values,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
        )

    async def get_weekly_schedule_heat(
        self,
        day_of_week_mask: int,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
    ):
        """Send standard Get Weekly Schedule in heating mode."""

        day_mask = int(day_of_week_mask)
        if day_mask <= 0 or (day_mask & ~WEEKLY_SCHEDULE_DAY_MASK_ALL) != 0:
            raise ValueError("day_of_week_mask must be 0x01..0x7F")
        if day_mask & (day_mask - 1):
            raise ValueError("get_weekly_schedule_heat currently supports one day only")

        return await self.command(
            self.ServerCommandDefs.get_weekly_schedule.id,
            self.SeqDayOfWeek(day_mask),
            self.SeqMode.Heat,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
        )

    async def get_weekly_schedule_heat_for_group(
        self,
        group_id: int,
        day_of_week_mask: int,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
    ):
        """Switch the active schedule group and query one day of schedule data."""

        private_cluster = getattr(self.endpoint, "sonoff_private", None)
        if private_cluster is None:
            raise ValueError("sonoff_private cluster is not available on this endpoint")

        await private_cluster.set_active_schedule_group(group_id)
        return await self.get_weekly_schedule_heat(
            day_of_week_mask,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
        )

    async def clear_weekly_schedule_current_group(
        self,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
    ):
        """Send standard Clear Weekly Schedule for the active group."""

        return await self.command(
            self.ServerCommandDefs.clear_weekly_schedule.id,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
        )


class SonoffTPWGZBAPrivateCluster(CustomCluster):
    """SONOFF private cluster 0xFC11 used by TP-WGZBA."""

    cluster_id = SONOFF_PRIVATE_CLUSTER_ID
    name = "SONOFF TP-WGZBA private cluster"
    ep_attribute = "sonoff_private"

    class AttributeDefs(BaseAttributeDefs):
        """0xFC11 attribute definitions from the firmware project."""

        child_lock: Final = ZCLAttributeDef(
            id=0x0000, type=t.Bool, access="rw", manufacturer_code=None
        )
        bt_pairing_broadcast_req: Final = ZCLAttributeDef(
            id=0x0029, type=t.uint8_t, access="rw", manufacturer_code=None
        )
        window_opening_detection: Final = ZCLAttributeDef(
            id=0x6000, type=t.Bool, access="rw", manufacturer_code=None
        )
        device_work_mode_source: Final = ZCLAttributeDef(
            id=DEVICE_WORK_MODE_SOURCE_ATTR_ID,
            type=t.uint8_t,
            access="rp",
            manufacturer_code=None,
        )
        frost_proof_temperature: Final = ZCLAttributeDef(
            id=0x6002, type=t.int16s, access="rw", manufacturer_code=None
        )
        temporary_temperature_mode_settings: Final = ZCLAttributeDef(
            id=0x6014, type=t.uint8_t, access="rp", manufacturer_code=None
        )
        weekly_schedule_active_num: Final = ZCLAttributeDef(
            id=0x601D, type=t.uint8_t, access="rw", manufacturer_code=None
        )
        remote_attribute_linkage: Final = ZCLAttributeDef(
            id=0x601E,
            type=Uint8ArrayPayload,
            zcl_type=DataTypeId.array,
            access="rw",
            manufacturer_code=None,
        )
        temperature_control_threshold: Final = ZCLAttributeDef(
            id=0x601F,
            type=RawBytes,
            zcl_type=DataTypeId.struct,
            access="rw",
            manufacturer_code=None,
        )
        radar_sensitivity_level: Final = ZCLAttributeDef(
            id=0x6020, type=t.uint8_t, access="rw", manufacturer_code=None
        )
        radar_do_not_disturb_enable: Final = ZCLAttributeDef(
            id=0x6021, type=t.Bool, access="rw", manufacturer_code=None
        )
        radar_do_not_disturb_period: Final = ZCLAttributeDef(
            id=0x6022,
            type=RawBytes,
            zcl_type=DataTypeId.struct,
            access="rw",
            manufacturer_code=None,
        )
        screen_working_brightness: Final = ZCLAttributeDef(
            id=0x6023, type=t.uint8_t, access="rw", manufacturer_code=None
        )
        screen_standby_brightness: Final = ZCLAttributeDef(
            id=0x6024, type=t.uint8_t, access="rw", manufacturer_code=None
        )
        screen_night_standby_brightness: Final = ZCLAttributeDef(
            id=0x6025, type=t.uint8_t, access="rw", manufacturer_code=None
        )
        screen_night_mode_enable: Final = ZCLAttributeDef(
            id=0x6026, type=t.Bool, access="rw", manufacturer_code=None
        )
        screen_night_mode_period: Final = ZCLAttributeDef(
            id=0x6027,
            type=RawBytes,
            zcl_type=DataTypeId.struct,
            access="rw",
            manufacturer_code=None,
        )
        relay_output_type_bitmap: Final = ZCLAttributeDef(
            id=0x6028, type=t.uint8_t, access="rw", manufacturer_code=None
        )
        hvac_message_notification: Final = ZCLAttributeDef(
            id=0x6030, type=RawBytes, access="rp", manufacturer_code=None
        )
        current_ntc_temperature_raw: Final = ZCLAttributeDef(
            id=0x6031, type=t.int16s, access="rp", manufacturer_code=None
        )
        overheat_protection_temperature: Final = ZCLAttributeDef(
            id=0x6032, type=t.int16s, access="rw", manufacturer_code=None
        )
        overheat_protection_enable: Final = ZCLAttributeDef(
            id=0x6034, type=t.Bool, access="rw", manufacturer_code=None
        )
        radar_enable: Final = ZCLAttributeDef(
            id=0x6035, type=t.Bool, access="rw", manufacturer_code=None
        )

        temperature_control_threshold_low: Final = ZCLAttributeDef(
            id=TEMPERATURE_CONTROL_THRESHOLD_LOW_ATTR_ID, type=t.int16s, access="rw"
        )
        temperature_control_threshold_high: Final = ZCLAttributeDef(
            id=TEMPERATURE_CONTROL_THRESHOLD_HIGH_ATTR_ID, type=t.int16s, access="rw"
        )
        radar_do_not_disturb_start_minute: Final = ZCLAttributeDef(
            id=RADAR_DND_START_MINUTE_ATTR_ID, type=t.uint16_t, access="rw"
        )
        radar_do_not_disturb_end_minute: Final = ZCLAttributeDef(
            id=RADAR_DND_END_MINUTE_ATTR_ID, type=t.uint16_t, access="rw"
        )
        screen_night_mode_start_minute: Final = ZCLAttributeDef(
            id=SCREEN_NIGHT_START_MINUTE_ATTR_ID, type=t.uint16_t, access="rw"
        )
        screen_night_mode_end_minute: Final = ZCLAttributeDef(
            id=SCREEN_NIGHT_END_MINUTE_ATTR_ID, type=t.uint16_t, access="rw"
        )
        relay_output_type_relay1: Final = ZCLAttributeDef(
            id=RELAY_OUTPUT_TYPE_RELAY1_ATTR_ID, type=RelayOutputType, access="rw"
        )
        relay_output_type_relay2: Final = ZCLAttributeDef(
            id=RELAY_OUTPUT_TYPE_RELAY2_ATTR_ID, type=RelayOutputType, access="rw"
        )
        temperature_sensor_select: Final = ZCLAttributeDef(
            id=TEMPERATURE_SENSOR_SELECT_ATTR_ID,
            type=TemperatureSensorSelect,
            access="rw",
        )
        external_temperature_input: Final = ZCLAttributeDef(
            id=EXTERNAL_TEMPERATURE_INPUT_ATTR_ID, type=t.int16s, access="rw"
        )
        external_temperature_sensor: Final = ZCLAttributeDef(
            id=EXTERNAL_TEMPERATURE_SENSOR_ATTR_ID, type=t.Bool, access="rw"
        )
        hvac_message_open_window_state: Final = ZCLAttributeDef(
            id=HVAC_MESSAGE_OPEN_WINDOW_STATE_ATTR_ID,
            type=HvacMessageOpenWindowState,
            access="rp",
        )
        current_ntc_temperature: Final = ZCLAttributeDef(
            id=NTC_CURRENT_TEMPERATURE_ATTR_ID, type=t.int16s, access="rp"
        )
        current_ntc_temperature_state: Final = ZCLAttributeDef(
            id=NTC_CURRENT_TEMPERATURE_STATE_ATTR_ID,
            type=NtcCurrentTemperatureState,
            access="rp",
        )
        temporary_temperature_mode_state: Final = ZCLAttributeDef(
            id=TEMPORARY_TEMPERATURE_MODE_STATE_ATTR_ID,
            type=TemporaryTemperatureModeState,
            access="rp",
        )
        current_ntc_temperature_display: Final = ZCLAttributeDef(
            id=NTC_CURRENT_TEMPERATURE_DISPLAY_ATTR_ID,
            type=t.CharacterString,
            access="rp",
        )

        tp_wgzba_ui_system_mode: Final = ZCLAttributeDef(
            id=TPWGZBA_UI_SYSTEM_MODE_ATTR_ID, type=TPWGZBASystemMode, access="rw"
        )
        device_work_mode: Final = ZCLAttributeDef(
            id=DEVICE_WORK_MODE_ATTR_ID, type=TPWGZBADeviceWorkMode, access="rp"
        )
        temporary_mode_ui_action: Final = ZCLAttributeDef(
            id=TEMPORARY_MODE_UI_MODE_ATTR_ID, type=TemporaryModeUiAction, access="rw"
        )
        temporary_mode_ui_duration_minutes: Final = ZCLAttributeDef(
            id=TEMPORARY_MODE_UI_DURATION_MINUTES_ATTR_ID,
            type=t.uint16_t,
            access="rw",
        )
        temporary_mode_ui_target_temperature: Final = ZCLAttributeDef(
            id=TEMPORARY_MODE_UI_TARGET_TEMP_ATTR_ID, type=t.int16s, access="rw"
        )
        weekly_schedule_ui_day: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_DAY_ATTR_ID, type=WeeklyScheduleUiDay, access="rw"
        )
        weekly_schedule_ui_transition_count: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TRANSITION_COUNT_ATTR_ID, type=t.uint8_t, access="rw"
        )
        weekly_schedule_ui_time1: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TIME_ATTR_IDS[0], type=t.uint16_t, access="rw"
        )
        weekly_schedule_ui_time2: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TIME_ATTR_IDS[1], type=t.uint16_t, access="rw"
        )
        weekly_schedule_ui_time3: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TIME_ATTR_IDS[2], type=t.uint16_t, access="rw"
        )
        weekly_schedule_ui_time4: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TIME_ATTR_IDS[3], type=t.uint16_t, access="rw"
        )
        weekly_schedule_ui_time5: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TIME_ATTR_IDS[4], type=t.uint16_t, access="rw"
        )
        weekly_schedule_ui_time6: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TIME_ATTR_IDS[5], type=t.uint16_t, access="rw"
        )
        weekly_schedule_ui_time7: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TIME_ATTR_IDS[6], type=t.uint16_t, access="rw"
        )
        weekly_schedule_ui_time8: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TIME_ATTR_IDS[7], type=t.uint16_t, access="rw"
        )
        weekly_schedule_ui_time9: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TIME_ATTR_IDS[8], type=t.uint16_t, access="rw"
        )
        weekly_schedule_ui_time10: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TIME_ATTR_IDS[9], type=t.uint16_t, access="rw"
        )
        weekly_schedule_ui_time11: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TIME_ATTR_IDS[10], type=t.uint16_t, access="rw"
        )
        weekly_schedule_ui_time12: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TIME_ATTR_IDS[11], type=t.uint16_t, access="rw"
        )
        weekly_schedule_ui_temp1: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TEMP_ATTR_IDS[0], type=t.int16s, access="rw"
        )
        weekly_schedule_ui_temp2: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TEMP_ATTR_IDS[1], type=t.int16s, access="rw"
        )
        weekly_schedule_ui_temp3: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TEMP_ATTR_IDS[2], type=t.int16s, access="rw"
        )
        weekly_schedule_ui_temp4: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TEMP_ATTR_IDS[3], type=t.int16s, access="rw"
        )
        weekly_schedule_ui_temp5: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TEMP_ATTR_IDS[4], type=t.int16s, access="rw"
        )
        weekly_schedule_ui_temp6: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TEMP_ATTR_IDS[5], type=t.int16s, access="rw"
        )
        weekly_schedule_ui_temp7: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TEMP_ATTR_IDS[6], type=t.int16s, access="rw"
        )
        weekly_schedule_ui_temp8: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TEMP_ATTR_IDS[7], type=t.int16s, access="rw"
        )
        weekly_schedule_ui_temp9: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TEMP_ATTR_IDS[8], type=t.int16s, access="rw"
        )
        weekly_schedule_ui_temp10: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TEMP_ATTR_IDS[9], type=t.int16s, access="rw"
        )
        weekly_schedule_ui_temp11: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TEMP_ATTR_IDS[10], type=t.int16s, access="rw"
        )
        weekly_schedule_ui_temp12: Final = ZCLAttributeDef(
            id=WEEKLY_SCHEDULE_UI_TEMP_ATTR_IDS[11], type=t.int16s, access="rw"
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Commands sent from ZHA to the TP-WGZBA private cluster."""

        temporary_mode: Final = ZCLCommandDef(
            id=CMD_TEMPORARY_MODE,
            schema={"payload": RawBytes},
        )
        temporary_mode_ui_apply: Final = ZCLCommandDef(
            id=CMD_TEMPORARY_MODE_UI_APPLY,
            schema={},
        )
        weekly_schedule_ui_apply: Final = ZCLCommandDef(
            id=CMD_WEEKLY_SCHEDULE_UI_APPLY,
            schema={},
        )
        weekly_schedule_ui_read: Final = ZCLCommandDef(
            id=CMD_WEEKLY_SCHEDULE_UI_READ,
            schema={},
        )

    class ClientCommandDefs(BaseCommandDefs):
        """Responses sent from TP-WGZBA back to ZHA."""

        temporary_mode_response: Final = ZCLCommandDef(
            id=CMD_TEMPORARY_MODE,
            schema={"payload": RawBytes},
        )

    _WEEKLY_TIME_ATTRS = (
        AttributeDefs.weekly_schedule_ui_time1,
        AttributeDefs.weekly_schedule_ui_time2,
        AttributeDefs.weekly_schedule_ui_time3,
        AttributeDefs.weekly_schedule_ui_time4,
        AttributeDefs.weekly_schedule_ui_time5,
        AttributeDefs.weekly_schedule_ui_time6,
        AttributeDefs.weekly_schedule_ui_time7,
        AttributeDefs.weekly_schedule_ui_time8,
        AttributeDefs.weekly_schedule_ui_time9,
        AttributeDefs.weekly_schedule_ui_time10,
        AttributeDefs.weekly_schedule_ui_time11,
        AttributeDefs.weekly_schedule_ui_time12,
    )
    _WEEKLY_TEMP_ATTRS = (
        AttributeDefs.weekly_schedule_ui_temp1,
        AttributeDefs.weekly_schedule_ui_temp2,
        AttributeDefs.weekly_schedule_ui_temp3,
        AttributeDefs.weekly_schedule_ui_temp4,
        AttributeDefs.weekly_schedule_ui_temp5,
        AttributeDefs.weekly_schedule_ui_temp6,
        AttributeDefs.weekly_schedule_ui_temp7,
        AttributeDefs.weekly_schedule_ui_temp8,
        AttributeDefs.weekly_schedule_ui_temp9,
        AttributeDefs.weekly_schedule_ui_temp10,
        AttributeDefs.weekly_schedule_ui_temp11,
        AttributeDefs.weekly_schedule_ui_temp12,
    )
    _WEEKLY_UI_ATTRS = (
        AttributeDefs.weekly_schedule_ui_day,
        AttributeDefs.weekly_schedule_ui_transition_count,
        *_WEEKLY_TIME_ATTRS,
        *_WEEKLY_TEMP_ATTRS,
    )

    def __init__(self, *args, **kwargs):
        """Seed stable defaults for virtual attrs so HA does not show Unknown."""

        super().__init__(*args, **kwargs)
        self._update_attribute(
            self.AttributeDefs.temporary_temperature_mode_settings.id,
            t.uint8_t(int(TemporaryTemperatureModeSettings.Idle)),
        )
        self._update_attribute(
            self.AttributeDefs.device_work_mode.id,
            TPWGZBADeviceWorkMode.Schedule,
        )
        self._update_attribute(
            self.AttributeDefs.current_ntc_temperature_state.id,
            NtcCurrentTemperatureState.idle,
        )
        self._update_attribute(
            self.AttributeDefs.current_ntc_temperature_display.id,
            "Not Connected",
        )
        self._update_attribute(
            self.AttributeDefs.radar_do_not_disturb_start_minute.id,
            0,
        )
        self._update_attribute(
            self.AttributeDefs.radar_do_not_disturb_end_minute.id,
            0,
        )
        self._update_attribute(
            self.AttributeDefs.screen_night_mode_start_minute.id,
            0,
        )
        self._update_attribute(
            self.AttributeDefs.screen_night_mode_end_minute.id,
            0,
        )
        self._update_attribute(
            self.AttributeDefs.temperature_sensor_select.id,
            TemperatureSensorSelect.internal,
        )
        self._update_attribute(
            self.AttributeDefs.external_temperature_input.id,
            EXTERNAL_TEMPERATURE_INPUT_MIN_X100,
        )
        self._update_attribute(
            self.AttributeDefs.external_temperature_sensor.id,
            False,
        )
        self._update_attribute(
            self.AttributeDefs.temporary_mode_ui_action.id,
            TemporaryModeUiAction.Boost,
        )
        self._update_attribute(
            self.AttributeDefs.temporary_mode_ui_duration_minutes.id,
            TEMPORARY_MODE_UI_DURATION_MINUTES_DEFAULT,
        )
        self._update_attribute(
            self.AttributeDefs.temporary_mode_ui_target_temperature.id,
            TEMPORARY_MODE_BOOST_TARGET_TEMP_X100,
        )
        self._update_attribute(
            self.AttributeDefs.weekly_schedule_ui_day.id,
            WeeklyScheduleUiDay.Sunday,
        )
        self._update_attribute(
            self.AttributeDefs.weekly_schedule_ui_transition_count.id,
            1,
        )
        self._update_attribute(
            self.AttributeDefs.weekly_schedule_ui_time1.id,
            0,
        )
        self._update_attribute(
            self.AttributeDefs.weekly_schedule_ui_temp1.id,
            WEEKLY_SCHEDULE_UI_TEMP_MIN_X100,
        )
        for attr_def in self._WEEKLY_TIME_ATTRS[1:]:
            self._update_attribute(attr_def.id, WEEKLY_SCHEDULE_UI_TIME_NULL)
        for attr_def in self._WEEKLY_TEMP_ATTRS[1:]:
            self._update_attribute(attr_def.id, WEEKLY_SCHEDULE_UI_TEMP_MIN_X100)

    async def configure_reporting_multiple(
        self, config: dict[foundation.ZCLAttributeDef, foundation.ReportingConfig]
    ) -> dict[foundation.ZCLAttributeDef, foundation.Status]:
        """Map virtual reporting to real attrs and skip unsupported raw NTC reporting."""

        skipped: dict[foundation.ZCLAttributeDef, foundation.Status] = {}
        remaining: dict[foundation.ZCLAttributeDef, foundation.ReportingConfig] = {}
        hvac_message_attr = self.AttributeDefs.hvac_message_notification
        ntc_temperature_attr = self.AttributeDefs.current_ntc_temperature_raw
        device_work_mode_source_attr = self.AttributeDefs.device_work_mode_source

        for attr_def, reporting_config in config.items():
            if attr_def.id == CURRENT_NTC_TEMPERATURE_RAW_ATTR_ID:
                skipped[attr_def] = foundation.Status.SUCCESS
            elif attr_def.id == DEVICE_WORK_MODE_ATTR_ID:
                remaining[device_work_mode_source_attr] = reporting_config
            elif attr_def.id in (
                NTC_CURRENT_TEMPERATURE_ATTR_ID,
                NTC_CURRENT_TEMPERATURE_STATE_ATTR_ID,
            ):
                remaining[ntc_temperature_attr] = reporting_config
            elif attr_def.id == HVAC_MESSAGE_OPEN_WINDOW_STATE_ATTR_ID:
                remaining[hvac_message_attr] = reporting_config
            else:
                remaining[attr_def] = reporting_config

        if not remaining:
            return skipped

        result = await super().configure_reporting_multiple(remaining)
        if hvac_message_attr in result:
            result[self.AttributeDefs.hvac_message_open_window_state] = result[
                hvac_message_attr
            ]
        if ntc_temperature_attr in result:
            result[self.AttributeDefs.current_ntc_temperature] = result[
                ntc_temperature_attr
            ]
            result[self.AttributeDefs.current_ntc_temperature_state] = result[
                ntc_temperature_attr
            ]
        if device_work_mode_source_attr in result:
            result[self.AttributeDefs.device_work_mode] = result[
                device_work_mode_source_attr
            ]
        result.update(skipped)
        return result

    async def set_active_schedule_group(
        self, group_id: int, manufacturer: int | t.uint16_t | None = None
    ):
        """Set the active weekly schedule group."""

        return await self.write_attributes(
            {self.AttributeDefs.weekly_schedule_active_num.id: self._group(group_id)},
            manufacturer=manufacturer,
        )

    def _normalize_weekly_schedule_ui_minute(self, value: Any) -> int:
        """Snap UI time values to the nearest 30-minute option."""

        if self._coerce_int(value) == WEEKLY_SCHEDULE_UI_TIME_NULL:
            return WEEKLY_SCHEDULE_UI_TIME_NULL

        minute = self._clamp(self._coerce_int(value), 0, WEEKLY_SCHEDULE_TIME_MAX)
        return min(
            (
                (minute + (WEEKLY_SCHEDULE_UI_TIME_STEP_MINUTES // 2))
                // WEEKLY_SCHEDULE_UI_TIME_STEP_MINUTES
            )
            * WEEKLY_SCHEDULE_UI_TIME_STEP_MINUTES,
            WEEKLY_SCHEDULE_UI_TIME_SELECT_MAX,
        )

    def _validate_weekly_schedule_ui_updates(self, updates: dict[int, Any]) -> int:
        """Validate staged weekly schedule UI writes and return the effective count."""

        transition_count_value = updates.get(
            self.AttributeDefs.weekly_schedule_ui_transition_count.id,
            self.get(self.AttributeDefs.weekly_schedule_ui_transition_count.name),
        )
        transition_count = (
            WEEKLY_SCHEDULE_UI_SLOT_MAX
            if transition_count_value is None
            else self._clamp(
                self._coerce_int(transition_count_value),
                1,
                WEEKLY_SCHEDULE_UI_SLOT_MAX,
            )
        )

        previous_minute = 0
        null_seen = False
        effective_transition_count = 1
        for index, (attr_def, default_minute) in enumerate(
            zip(self._WEEKLY_TIME_ATTRS, WEEKLY_SCHEDULE_UI_TIMES, strict=True)
        ):
            minute_value = updates.get(attr_def.id, self.get(attr_def.name))
            minute = (
                0
                if index == 0
                else default_minute
                if minute_value is None
                else self._normalize_weekly_schedule_ui_minute(minute_value)
            )
            if index == 0:
                continue

            if minute == WEEKLY_SCHEDULE_UI_TIME_NULL:
                null_seen = True
                continue

            if null_seen:
                raise ValueError(
                    "weekly schedule time slots after NULL must also be NULL"
                )

            minimum_minute = previous_minute + WEEKLY_SCHEDULE_UI_TIME_STEP_MINUTES
            if minute < minimum_minute:
                raise ValueError(
                    "weekly schedule time slot "
                    f"{index + 1} must be at least "
                    f"{minimum_minute // 60:02d}:{minimum_minute % 60:02d} or NULL"
                )

            previous_minute = minute
            effective_transition_count = index + 1

        if null_seen:
            return effective_transition_count
        return max(transition_count, effective_transition_count)

    def _weekly_schedule_ui_values(self) -> tuple[int, list[tuple[int, int]]]:
        """Return cached weekly schedule UI values with safe defaults."""

        day = self.get(self.AttributeDefs.weekly_schedule_ui_day.name)
        day_value = (
            int(WeeklyScheduleUiDay.Sunday)
            if day is None
            else int(WeeklyScheduleUiDay(int(day)))
        )

        transition_count_value = self.get(
            self.AttributeDefs.weekly_schedule_ui_transition_count.name
        )
        transition_count = (
            WEEKLY_SCHEDULE_UI_SLOT_MAX
            if transition_count_value is None
            else self._clamp(
                self._coerce_int(transition_count_value),
                1,
                WEEKLY_SCHEDULE_UI_SLOT_MAX,
            )
        )

        raw_minute_values = [
            self.get(attr_def.name) for attr_def in self._WEEKLY_TIME_ATTRS
        ]

        inferred_transition_count = 1
        for index in range(WEEKLY_SCHEDULE_UI_SLOT_MAX - 1, 0, -1):
            raw_minute_value = raw_minute_values[index]
            if raw_minute_value is None:
                continue
            if (
                self._normalize_weekly_schedule_ui_minute(raw_minute_value)
                != WEEKLY_SCHEDULE_UI_TIME_NULL
            ):
                inferred_transition_count = index + 1
                break

        transition_count = max(transition_count, inferred_transition_count)

        transitions: list[tuple[int, int]] = []
        for index, _default_minute in enumerate(WEEKLY_SCHEDULE_UI_TIMES):
            minute_value = raw_minute_values[index]
            minute = (
                0
                if index == 0
                else WEEKLY_SCHEDULE_UI_TIME_NULL
                if minute_value is None
                else self._normalize_weekly_schedule_ui_minute(minute_value)
            )
            temp_value = self.get(self._WEEKLY_TEMP_ATTRS[index].name)
            temp = (
                WEEKLY_SCHEDULE_UI_TEMP_MIN_X100
                if temp_value is None
                else self._clamp(
                    self._coerce_int(temp_value),
                    WEEKLY_SCHEDULE_UI_TEMP_MIN_X100,
                    WEEKLY_SCHEDULE_UI_TEMP_MAX_X100,
                )
            )
            if index > 0 and minute == WEEKLY_SCHEDULE_UI_TIME_NULL:
                break
            transitions.append((minute, temp))

        return day_value, transitions[:transition_count]

    def _update_weekly_schedule_ui_from_rsp(self, rsp: Any) -> None:
        """Update cached weekly schedule UI values from a standard get response."""

        if rsp is None:
            return

        day_mask = getattr(rsp, "day_of_week_for_sequence", None)
        values = getattr(rsp, "values", None)
        transition_count = getattr(rsp, "num_transitions_for_sequence", None)
        if (
            day_mask is None
            or transition_count is None
            or not isinstance(values, (list, tuple))
        ):
            return

        self._update_attribute(
            self.AttributeDefs.weekly_schedule_ui_day.id,
            self._weekly_schedule_standard_mask_to_ui_day(day_mask),
        )
        self._update_attribute(
            self.AttributeDefs.weekly_schedule_ui_transition_count.id,
            self._clamp(
                self._coerce_int(transition_count),
                1,
                WEEKLY_SCHEDULE_UI_SLOT_MAX,
            ),
        )

        slot_minutes = [WEEKLY_SCHEDULE_UI_TIME_NULL] * WEEKLY_SCHEDULE_UI_SLOT_MAX
        slot_temps = [WEEKLY_SCHEDULE_UI_TEMP_MIN_X100] * WEEKLY_SCHEDULE_UI_SLOT_MAX
        actual_transition_count = self._clamp(
            self._coerce_int(transition_count), 1, WEEKLY_SCHEDULE_UI_SLOT_MAX
        )

        for transition_index in range(actual_transition_count):
            minute: int | None = None
            temp: int | None = None
            transition_value = (
                values[transition_index] if transition_index < len(values) else None
            )

            if transition_value is not None:
                minute_value = getattr(transition_value, "transition_time", None)
                if minute_value is None:
                    minute_value = getattr(transition_value, "trans_time", None)
                if minute_value is None:
                    minute_value = getattr(transition_value, "transTime", None)

                temp_value = getattr(transition_value, "heat_setpoint", None)
                if temp_value is None:
                    temp_value = getattr(transition_value, "heatSetpoint", None)

                if minute_value is not None and temp_value is not None:
                    minute = self._normalize_weekly_schedule_ui_minute(minute_value)
                    temp = self._clamp(
                        self._coerce_int(temp_value),
                        WEEKLY_SCHEDULE_UI_TEMP_MIN_X100,
                        WEEKLY_SCHEDULE_UI_TEMP_MAX_X100,
                    )

            if minute is None or temp is None:
                time_index = transition_index * 2
                value_index = time_index + 1
                if value_index >= len(values):
                    break
                minute = self._normalize_weekly_schedule_ui_minute(values[time_index])
                temp = self._clamp(
                    self._coerce_int(values[value_index]),
                    WEEKLY_SCHEDULE_UI_TEMP_MIN_X100,
                    WEEKLY_SCHEDULE_UI_TEMP_MAX_X100,
                )

            slot_minutes[transition_index] = minute
            slot_temps[transition_index] = temp

        slot_minutes[0] = 0

        for attr_def, minute in zip(self._WEEKLY_TIME_ATTRS, slot_minutes, strict=True):
            self._update_attribute(attr_def.id, minute)
        for attr_def, temp in zip(self._WEEKLY_TEMP_ATTRS, slot_temps, strict=True):
            self._update_attribute(attr_def.id, temp)

    async def exit_temporary_mode(self):
        """Send 0x11 exit temporary mode command."""

        return await self.command(CMD_TEMPORARY_MODE, bytes([TEMPORARY_MODE_EXIT]))

    async def set_boost(self, duration_seconds: int, target_temperature: float | int):
        """Send 0x11 Boost command."""

        return await self._set_temporary_mode(
            TEMPORARY_MODE_BOOST, duration_seconds, target_temperature
        )

    async def set_timer(self, duration_seconds: int, target_temperature: float | int):
        """Send 0x11 Timer command."""

        return await self._set_temporary_mode(
            TEMPORARY_MODE_TIMER, duration_seconds, target_temperature
        )

    async def _set_temporary_mode(
        self, mode: int, duration_seconds: int, target_temperature: float | int
    ):
        """Encode and send the 0x11 temporary mode payload."""

        duration = int(duration_seconds)
        if duration <= 0 or duration > 86399:
            raise ValueError("duration_seconds must be 1..86399")

        target_x100 = int(round(float(target_temperature) * 100))
        payload = (
            bytes([mode])
            + duration.to_bytes(4, "little", signed=False)
            + target_x100.to_bytes(2, "little", signed=True)
        )
        return await self.command(CMD_TEMPORARY_MODE, payload)

    @staticmethod
    def _group(group_id: int) -> int:
        """Normalize schedule group id."""

        group = int(group_id)
        if group < 0 or group > 2:
            raise ValueError("group_id must be 0..2")
        return group

    @staticmethod
    def _weekly_schedule_ui_day_to_standard_mask(day: int) -> int:
        """Convert the UI day enum to the thermostat day mask."""

        return 1 << int(day)

    @staticmethod
    def _weekly_schedule_standard_mask_to_ui_day(day_mask: int) -> int:
        """Convert a one-bit thermostat day mask to the UI day enum."""

        mask = int(day_mask)
        for bit in range(7):
            if mask & (1 << bit):
                return bit
        return int(WeeklyScheduleUiDay.Sunday)

    def _temporary_mode_ui_values(self) -> tuple[TemporaryModeUiAction, int, int]:
        """Return cached temporary mode UI values with safe defaults."""

        mode = self.get(self.AttributeDefs.temporary_mode_ui_action.name)
        duration_minutes = self.get(
            self.AttributeDefs.temporary_mode_ui_duration_minutes.name
        )
        target_temperature = self.get(
            self.AttributeDefs.temporary_mode_ui_target_temperature.name
        )

        mode_value = (
            TemporaryModeUiAction.Boost
            if mode is None
            else TemporaryModeUiAction(int(mode))
        )
        duration_value = (
            TEMPORARY_MODE_UI_DURATION_MINUTES_DEFAULT
            if duration_minutes is None
            else self._clamp(
                self._coerce_int(duration_minutes),
                1,
                TEMPORARY_MODE_UI_DURATION_MINUTES_MAX,
            )
        )

        if target_temperature is None:
            thermostat_cluster = getattr(self.endpoint, "thermostat", None)
            if thermostat_cluster is not None:
                target_temperature = thermostat_cluster.get(
                    Thermostat.AttributeDefs.occupied_heating_setpoint.name
                )
            if target_temperature is None:
                target_temperature = TEMPORARY_MODE_BOOST_TARGET_TEMP_X100

        if mode_value == TemporaryModeUiAction.Boost:
            target_value = TEMPORARY_MODE_BOOST_TARGET_TEMP_X100
        else:
            target_value = self._clamp(
                self._coerce_int(target_temperature),
                TEMPORARY_MODE_UI_TARGET_TEMP_MIN_X100,
                TEMPORARY_MODE_UI_TARGET_TEMP_MAX_X100,
            )
        return mode_value, duration_value, target_value

    @staticmethod
    def _clamp(value: int, minimum: int, maximum: int) -> int:
        """Clamp a numeric value."""

        return max(minimum, min(maximum, value))

    @staticmethod
    def _coerce_int(value: Any) -> int:
        """Coerce values that may arrive as enum/float/string to int."""

        return int(round(float(value)))

    @staticmethod
    def _as_bytes(value: Any) -> bytes | None:
        """Best-effort bytes conversion for raw vendor payloads."""

        if value is None:
            return None
        if isinstance(value, (bytes, bytearray, RawBytes)):
            return bytes(value)
        if hasattr(value, "serialize"):
            return value.serialize()
        try:
            return bytes(value)
        except TypeError:
            return None

    @staticmethod
    def _read_record(
        attr_id: int,
        value: Any,
        status: foundation.Status = foundation.Status.SUCCESS,
    ) -> foundation.ReadAttributeRecord:
        """Build a synthetic read response record for virtual attributes."""

        record = foundation.ReadAttributeRecord(
            attrid=attr_id,
            status=status,
            value=foundation.TypeValue(),
        )
        record.value.value = value
        return record

    @staticmethod
    def _pop_attribute_value(
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        attr_def: foundation.ZCLAttributeDef,
    ) -> tuple[bool, Any]:
        """Pop one attribute using def/id/name compatibility."""

        for key in list(attributes):
            if key in (attr_def, attr_def.id, attr_def.name):
                return True, attributes.pop(key)
        return False, None

    @staticmethod
    def _split_read_results(
        results: tuple[list[foundation.ReadAttributeRecord], ...],
    ) -> tuple[
        list[foundation.ReadAttributeRecord], list[foundation.ReadAttributeRecord]
    ]:
        """Split raw read results into success and failure lists."""

        success = list(results[0]) if results else []
        failed = list(results[1]) if len(results) > 1 else []
        return success, failed

    @staticmethod
    def _first_status(
        records: list[foundation.ReadAttributeRecord],
    ) -> foundation.Status:
        """Return the first failure status or UNSUPPORTED_ATTRIBUTE."""

        return records[0].status if records else foundation.Status.UNSUPPORTED_ATTRIBUTE

    @classmethod
    def _decode_threshold_pair(cls, value: Any) -> tuple[int, int]:
        """Decode the packed threshold struct."""

        raw = cls._as_bytes(value)
        if raw is None or len(raw) != 8:
            return (
                TEMPERATURE_CONTROL_THRESHOLD_LOW_DEFAULT,
                TEMPERATURE_CONTROL_THRESHOLD_HIGH_DEFAULT,
            )
        return (
            int.from_bytes(raw[3:5], "little", signed=True),
            int.from_bytes(raw[6:8], "little", signed=True),
        )

    @classmethod
    def _encode_threshold_pair(cls, low: int, high: int) -> bytes:
        """Encode low/high thresholds into the vendor struct payload."""

        return (
            ZCL_STRUCT_ITEM_COUNT
            + bytes([ZCL_DATA_TYPE_INT16])
            + int(low).to_bytes(2, "little", signed=True)
            + bytes([ZCL_DATA_TYPE_INT16])
            + int(high).to_bytes(2, "little", signed=True)
        )

    @classmethod
    def _decode_time_period(cls, value: Any) -> tuple[int, int]:
        """Decode a packed start/end minute struct."""

        raw = cls._as_bytes(value)
        if raw is None or len(raw) != 8:
            return 0, 0
        return (
            int.from_bytes(raw[3:5], "little", signed=False),
            int.from_bytes(raw[6:8], "little", signed=False),
        )

    @classmethod
    def _encode_time_period(cls, start: int, end: int) -> bytes:
        """Encode a packed start/end minute struct."""

        return (
            ZCL_STRUCT_ITEM_COUNT
            + bytes([ZCL_DATA_TYPE_UINT16])
            + int(start).to_bytes(2, "little", signed=False)
            + bytes([ZCL_DATA_TYPE_UINT16])
            + int(end).to_bytes(2, "little", signed=False)
        )

    @classmethod
    def _decode_relay_output_type(cls, value: Any) -> tuple[int, int]:
        """Decode the relay output bitmap into per-relay values."""

        relay_bitmap = int(value) if value is not None else 0
        relay_bitmap &= RELAY_OUTPUT_TYPE_VALID_MASK
        return relay_bitmap & 0x01, (relay_bitmap >> 1) & 0x01

    @classmethod
    def _encode_relay_output_type(cls, relay1: int, relay2: int) -> int:
        """Encode per-relay values back to the bitmap."""

        return (int(relay1) & 0x01) | ((int(relay2) & 0x01) << 1)

    def _decode_remote_attribute_linkage(
        self, value: Any
    ) -> tuple[TemperatureSensorSelect, int]:
        """Decode 0x601E into a source selector and external temperature."""

        cached_sensor_select = self.get(
            self.AttributeDefs.temperature_sensor_select.name
        )
        sensor_select = (
            TemperatureSensorSelect(int(cached_sensor_select))
            if cached_sensor_select is not None
            else TemperatureSensorSelect.internal
        )
        cached_external_temperature = self.get(
            self.AttributeDefs.external_temperature_input.name
        )
        external_temperature = (
            self._clamp(
                self._coerce_int(cached_external_temperature),
                EXTERNAL_TEMPERATURE_INPUT_MIN_X100,
                EXTERNAL_TEMPERATURE_INPUT_MAX_X100,
            )
            if cached_external_temperature is not None
            else EXTERNAL_TEMPERATURE_INPUT_MIN_X100
        )

        raw = self._as_bytes(value)
        if raw is None:
            return sensor_select, external_temperature

        if not raw or all(byte == 0 for byte in raw):
            return TemperatureSensorSelect.internal, external_temperature

        if len(raw) >= 3 and raw[0] == 0 and all(byte == 0 for byte in raw[3:]):
            return TemperatureSensorSelect.internal, external_temperature

        remote_cfg_num = raw[0]
        offset = 3
        parsed = 0
        while offset + 1 < len(raw) and parsed < remote_cfg_num:
            tlv_type = raw[offset]
            tlv_length = raw[offset + 1]
            offset += 2
            data = raw[offset : offset + tlv_length]
            offset += tlv_length
            parsed += 1

            if tlv_type != 0x01 or tlv_length != 0x03 or len(data) != 0x03:
                continue

            try:
                sensor_select = TemperatureSensorSelect(int(data[0]))
            except ValueError:
                continue

            external_temperature = self._clamp(
                int.from_bytes(data[1:3], "little", signed=True),
                EXTERNAL_TEMPERATURE_INPUT_MIN_X100,
                EXTERNAL_TEMPERATURE_INPUT_MAX_X100,
            )
            break

        return sensor_select, external_temperature

    @classmethod
    def _encode_remote_attribute_linkage(
        cls,
        sensor_select: TemperatureSensorSelect | int,
        external_temperature: int,
    ) -> bytes:
        """Encode the selected source and external temperature back to 0x601E."""

        external_temperature = cls._clamp(
            int(external_temperature),
            EXTERNAL_TEMPERATURE_INPUT_MIN_X100,
            EXTERNAL_TEMPERATURE_INPUT_MAX_X100,
        )
        return bytes(
            (0x01, 0x01, 0x00, 0x01, 0x03, int(sensor_select))
        ) + external_temperature.to_bytes(2, "little", signed=True)

    @classmethod
    def _decode_hvac_message_open_window_state(
        cls, value: Any
    ) -> HvacMessageOpenWindowState:
        """Decode the open-window TLV state from the vendor payload."""

        raw = cls._as_bytes(value)
        if (
            raw is not None
            and len(raw) >= 3
            and raw[0] == 0x20
            and int.from_bytes(raw[1:3], "little", signed=False) == (len(raw) - 3)
        ):
            raw = raw[3:]
        if (
            raw is None
            or len(raw) < 3
            or raw[0] != HVAC_MESSAGE_TLV_OPEN_WINDOW
            or raw[1] != HVAC_MESSAGE_TLV_OPEN_WINDOW_LEN
        ):
            return HvacMessageOpenWindowState.closed
        return (
            HvacMessageOpenWindowState.open
            if raw[2] != 0
            else HvacMessageOpenWindowState.closed
        )

    @classmethod
    def _decode_ntc_current_temperature(
        cls, value: Any
    ) -> tuple[int | None, NtcCurrentTemperatureState]:
        """Decode the current NTC temperature and its validity state."""

        raw_value = (
            int(value) if value is not None else NTC_CURRENT_TEMPERATURE_CODE_INVALID
        )
        if raw_value in (
            NTC_CURRENT_TEMPERATURE_CODE_INVALID,
            NTC_CURRENT_TEMPERATURE_CODE_OPEN_CIRCUIT,
            NTC_CURRENT_TEMPERATURE_CODE_SHORT_CIRCUIT,
            NTC_CURRENT_TEMPERATURE_CODE_ADC_INVALID,
        ):
            return None, NtcCurrentTemperatureState.idle
        if raw_value < NTC_CURRENT_TEMPERATURE_MIN_VALID:
            return None, NtcCurrentTemperatureState.idle
        return raw_value, NtcCurrentTemperatureState.normal

    @classmethod
    def _decode_temporary_temperature_mode_state(
        cls, value: Any
    ) -> TemporaryTemperatureModeState:
        """Map the raw temporary mode setting to a display-safe enum."""

        if int(value) == int(TemporaryTemperatureModeSettings.Boost):
            return TemporaryTemperatureModeState.Boost
        if int(value) == int(TemporaryTemperatureModeSettings.Timer):
            return TemporaryTemperatureModeState.Timer
        return TemporaryTemperatureModeState.Idle

    @staticmethod
    def _device_work_mode_from_system(system_mode: Any) -> TPWGZBADeviceWorkMode:
        """Map the raw thermostat system mode to the display work mode."""

        mode = TPWGZBASystemMode(int(system_mode))
        return TPWGZBADeviceWorkMode(int(mode))

    def _refresh_device_work_mode(self) -> None:
        """Refresh the display work mode from the cached standard system mode."""

        current_mode = self.get(self.AttributeDefs.tp_wgzba_ui_system_mode.name)
        if current_mode is None:
            thermostat_cluster = getattr(self.endpoint, "thermostat", None)
            if thermostat_cluster is None:
                return
            current_mode = thermostat_cluster.get(
                Thermostat.AttributeDefs.system_mode.name
            )
        if current_mode is None:
            return

        self._update_device_work_mode_from_system(current_mode)

    def _update_device_work_mode_from_system(self, system_mode: Any) -> None:
        """Update the display work mode from a raw thermostat system mode."""

        super()._update_attribute(
            self.AttributeDefs.device_work_mode.id,
            self._device_work_mode_from_system(system_mode),
        )

    @classmethod
    def _format_ntc_current_temperature_display(
        cls, current_temp: int | None, current_state: NtcCurrentTemperatureState
    ) -> str:
        """Format the displayed NTC temperature content for ZHA."""

        if (
            current_state == NtcCurrentTemperatureState.normal
            and current_temp is not None
        ):
            return f"{current_temp / 100:.2f} C"
        return "Not Connected"

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Update the raw attribute cache and keep virtual mirrors synchronized."""

        super()._update_attribute(attrid, value)

        if attrid == self.AttributeDefs.temperature_control_threshold.id:
            low, high = self._decode_threshold_pair(value)
            super()._update_attribute(
                self.AttributeDefs.temperature_control_threshold_low.id, low
            )
            super()._update_attribute(
                self.AttributeDefs.temperature_control_threshold_high.id, high
            )
        elif attrid == self.AttributeDefs.radar_do_not_disturb_period.id:
            start, end = self._decode_time_period(value)
            super()._update_attribute(
                self.AttributeDefs.radar_do_not_disturb_start_minute.id,
                self._normalize_weekly_schedule_ui_minute(start),
            )
            super()._update_attribute(
                self.AttributeDefs.radar_do_not_disturb_end_minute.id,
                self._normalize_weekly_schedule_ui_minute(end),
            )
        elif attrid == self.AttributeDefs.screen_night_mode_period.id:
            start, end = self._decode_time_period(value)
            super()._update_attribute(
                self.AttributeDefs.screen_night_mode_start_minute.id,
                self._normalize_weekly_schedule_ui_minute(start),
            )
            super()._update_attribute(
                self.AttributeDefs.screen_night_mode_end_minute.id,
                self._normalize_weekly_schedule_ui_minute(end),
            )
        elif attrid == self.AttributeDefs.relay_output_type_bitmap.id:
            relay1, relay2 = self._decode_relay_output_type(value)
            super()._update_attribute(
                self.AttributeDefs.relay_output_type_relay1.id, relay1
            )
            super()._update_attribute(
                self.AttributeDefs.relay_output_type_relay2.id, relay2
            )
        elif attrid == self.AttributeDefs.remote_attribute_linkage.id:
            sensor_select, external_temperature = self._decode_remote_attribute_linkage(
                value
            )
            super()._update_attribute(
                self.AttributeDefs.temperature_sensor_select.id, sensor_select
            )
            super()._update_attribute(
                self.AttributeDefs.external_temperature_input.id, external_temperature
            )
            super()._update_attribute(
                self.AttributeDefs.external_temperature_sensor.id,
                sensor_select != TemperatureSensorSelect.internal,
            )
        elif attrid == self.AttributeDefs.hvac_message_notification.id:
            super()._update_attribute(
                self.AttributeDefs.hvac_message_open_window_state.id,
                self._decode_hvac_message_open_window_state(value),
            )
        elif attrid == self.AttributeDefs.current_ntc_temperature_raw.id:
            current_temp, current_state = self._decode_ntc_current_temperature(value)
            super()._update_attribute(
                self.AttributeDefs.current_ntc_temperature.id, current_temp
            )
            super()._update_attribute(
                self.AttributeDefs.current_ntc_temperature_state.id, current_state
            )
            super()._update_attribute(
                self.AttributeDefs.current_ntc_temperature_display.id,
                self._format_ntc_current_temperature_display(
                    current_temp, current_state
                ),
            )
        elif attrid == self.AttributeDefs.temporary_temperature_mode_settings.id:
            super()._update_attribute(
                self.AttributeDefs.temporary_temperature_mode_state.id,
                self._decode_temporary_temperature_mode_state(value),
            )
        elif attrid == self.AttributeDefs.device_work_mode_source.id:
            if int(value) == DEVICE_WORK_MODE_TEMPORARY_MANUAL:
                super()._update_attribute(
                    self.AttributeDefs.device_work_mode.id,
                    TPWGZBADeviceWorkMode.Temporary_Manual,
                )
            else:
                self._refresh_device_work_mode()

    async def _read_real_system_mode(
        self, manufacturer: int | None = None
    ) -> TPWGZBASystemMode:
        """Read or infer the real TP-WGZBA work mode for the extra mode entity."""

        thermostat_cluster = getattr(self.endpoint, "thermostat", None)
        if thermostat_cluster is not None:
            raw_success, _ = self._split_read_results(
                await thermostat_cluster._read_attributes(
                    [Thermostat.AttributeDefs.system_mode.id],
                    manufacturer=manufacturer,
                )
            )
            if raw_success and raw_success[0].status == foundation.Status.SUCCESS:
                cached_mode = raw_success[0].value.value
                thermostat_cluster._update_attribute(
                    Thermostat.AttributeDefs.system_mode.id, cached_mode
                )
                mode = (
                    TPWGZBASystemMode.Manual
                    if int(cached_mode) == int(Thermostat.SystemMode.Heat)
                    else TPWGZBASystemMode(int(cached_mode))
                )
                self._update_attribute(
                    self.AttributeDefs.tp_wgzba_ui_system_mode.id, mode
                )
                return mode

        cached = self.get(self.AttributeDefs.tp_wgzba_ui_system_mode.name)
        if cached is not None:
            return TPWGZBASystemMode(int(cached))

        return TPWGZBASystemMode.Schedule

    async def _read_device_work_mode(
        self, manufacturer: int | None = None
    ) -> TPWGZBADeviceWorkMode:
        """Read the display work mode from standard mode and temporary reports."""

        mode = await self._read_real_system_mode(manufacturer=manufacturer)

        mode_source = self.get(self.AttributeDefs.device_work_mode_source.name)
        raw_success, _ = self._split_read_results(
            await super().read_attributes_raw(
                [self.AttributeDefs.device_work_mode_source.id],
                manufacturer=manufacturer,
            )
        )
        if raw_success and raw_success[0].status == foundation.Status.SUCCESS:
            mode_source = t.uint8_t(int(raw_success[0].value.value))
            self._update_attribute(
                self.AttributeDefs.device_work_mode_source.id,
                mode_source,
            )

        display_mode = self._device_work_mode_from_system(mode)
        if (
            mode_source is not None
            and int(mode_source) == DEVICE_WORK_MODE_TEMPORARY_MANUAL
        ):
            display_mode = TPWGZBADeviceWorkMode.Temporary_Manual
        super()._update_attribute(self.AttributeDefs.device_work_mode.id, display_mode)
        return display_mode

    async def read_attributes_raw(
        self, attributes: list[int], manufacturer: int | None = None, **kwargs
    ) -> tuple[list[foundation.ReadAttributeRecord], ...]:
        """Serve virtual attributes locally and proxy real vendor attributes."""

        success: list[foundation.ReadAttributeRecord] = []
        failed: list[foundation.ReadAttributeRecord] = []
        remaining = list(attributes)

        if self.AttributeDefs.temporary_temperature_mode_settings.id in remaining:
            remaining.remove(self.AttributeDefs.temporary_temperature_mode_settings.id)
            cached_mode = self.get(
                self.AttributeDefs.temporary_temperature_mode_settings.name
            )
            if cached_mode is None:
                raw_success, raw_failed = self._split_read_results(
                    await super().read_attributes_raw(
                        [self.AttributeDefs.temporary_temperature_mode_settings.id],
                        manufacturer=manufacturer,
                        **kwargs,
                    )
                )
                if raw_success and raw_success[0].status == foundation.Status.SUCCESS:
                    cached_mode = t.uint8_t(int(raw_success[0].value.value))
                else:
                    cached_mode = t.uint8_t(int(TemporaryTemperatureModeSettings.Idle))
            else:
                cached_mode = t.uint8_t(int(cached_mode))

            self._update_attribute(
                self.AttributeDefs.temporary_temperature_mode_settings.id,
                cached_mode,
            )
            success.append(
                self._read_record(
                    self.AttributeDefs.temporary_temperature_mode_settings.id,
                    cached_mode,
                )
            )

        if self.AttributeDefs.temporary_temperature_mode_state.id in remaining:
            remaining.remove(self.AttributeDefs.temporary_temperature_mode_state.id)
            raw_mode = self.get(
                self.AttributeDefs.temporary_temperature_mode_settings.name
            )
            if raw_mode is None:
                raw_mode = t.uint8_t(int(TemporaryTemperatureModeSettings.Idle))
            display_mode = self._decode_temporary_temperature_mode_state(raw_mode)
            self._update_attribute(
                self.AttributeDefs.temporary_temperature_mode_state.id,
                display_mode,
            )
            success.append(
                self._read_record(
                    self.AttributeDefs.temporary_temperature_mode_state.id,
                    display_mode,
                )
            )

        if self.AttributeDefs.tp_wgzba_ui_system_mode.id in remaining:
            remaining.remove(self.AttributeDefs.tp_wgzba_ui_system_mode.id)
            mode = await self._read_real_system_mode(manufacturer=manufacturer)
            success.append(
                self._read_record(self.AttributeDefs.tp_wgzba_ui_system_mode.id, mode)
            )

        if self.AttributeDefs.device_work_mode.id in remaining:
            remaining.remove(self.AttributeDefs.device_work_mode.id)
            mode = await self._read_device_work_mode(manufacturer=manufacturer)
            success.append(
                self._read_record(self.AttributeDefs.device_work_mode.id, mode)
            )

        temporary_mode_ui_ids = {
            self.AttributeDefs.temporary_mode_ui_action.id,
            self.AttributeDefs.temporary_mode_ui_duration_minutes.id,
            self.AttributeDefs.temporary_mode_ui_target_temperature.id,
        }
        requested = [attr for attr in remaining if attr in temporary_mode_ui_ids]
        if requested:
            remaining = [
                attr for attr in remaining if attr not in temporary_mode_ui_ids
            ]
            mode, duration_minutes, target_temperature = (
                self._temporary_mode_ui_values()
            )
            ui_values = {
                self.AttributeDefs.temporary_mode_ui_action.id: mode,
                self.AttributeDefs.temporary_mode_ui_duration_minutes.id: duration_minutes,
                self.AttributeDefs.temporary_mode_ui_target_temperature.id: target_temperature,
            }
            for attr_id, value in ui_values.items():
                self._update_attribute(attr_id, value)
            success.extend(
                self._read_record(attr_id, ui_values[attr_id]) for attr_id in requested
            )

        weekly_ui_ids = {attr_def.id for attr_def in self._WEEKLY_UI_ATTRS}
        requested = [attr for attr in remaining if attr in weekly_ui_ids]
        if requested:
            remaining = [attr for attr in remaining if attr not in weekly_ui_ids]
            day, transitions = self._weekly_schedule_ui_values()
            ui_values = {
                self.AttributeDefs.weekly_schedule_ui_day.id: day,
                self.AttributeDefs.weekly_schedule_ui_transition_count.id: len(
                    transitions
                ),
            }
            for index, attr_def in enumerate(self._WEEKLY_TIME_ATTRS):
                ui_values[attr_def.id] = (
                    0
                    if index == 0
                    else transitions[index][0]
                    if index < len(transitions)
                    else WEEKLY_SCHEDULE_UI_TIME_NULL
                )
            for index, attr_def in enumerate(self._WEEKLY_TEMP_ATTRS):
                ui_values[attr_def.id] = (
                    transitions[index][1]
                    if index < len(transitions)
                    else WEEKLY_SCHEDULE_UI_TEMP_MIN_X100
                )
            success.extend(
                self._read_record(attr_id, ui_values[attr_id]) for attr_id in requested
            )

        virtual_reads = (
            (
                {
                    self.AttributeDefs.temperature_control_threshold_low.id,
                    self.AttributeDefs.temperature_control_threshold_high.id,
                },
                self.AttributeDefs.temperature_control_threshold.id,
                lambda raw: {
                    self.AttributeDefs.temperature_control_threshold_low.id: self._decode_threshold_pair(
                        raw
                    )[0],
                    self.AttributeDefs.temperature_control_threshold_high.id: self._decode_threshold_pair(
                        raw
                    )[1],
                },
            ),
            (
                {
                    self.AttributeDefs.radar_do_not_disturb_start_minute.id,
                    self.AttributeDefs.radar_do_not_disturb_end_minute.id,
                },
                self.AttributeDefs.radar_do_not_disturb_period.id,
                lambda raw: {
                    self.AttributeDefs.radar_do_not_disturb_start_minute.id: self._normalize_weekly_schedule_ui_minute(
                        self._decode_time_period(raw)[0]
                    ),
                    self.AttributeDefs.radar_do_not_disturb_end_minute.id: self._normalize_weekly_schedule_ui_minute(
                        self._decode_time_period(raw)[1]
                    ),
                },
            ),
            (
                {
                    self.AttributeDefs.screen_night_mode_start_minute.id,
                    self.AttributeDefs.screen_night_mode_end_minute.id,
                },
                self.AttributeDefs.screen_night_mode_period.id,
                lambda raw: {
                    self.AttributeDefs.screen_night_mode_start_minute.id: self._normalize_weekly_schedule_ui_minute(
                        self._decode_time_period(raw)[0]
                    ),
                    self.AttributeDefs.screen_night_mode_end_minute.id: self._normalize_weekly_schedule_ui_minute(
                        self._decode_time_period(raw)[1]
                    ),
                },
            ),
            (
                {
                    self.AttributeDefs.relay_output_type_relay1.id,
                    self.AttributeDefs.relay_output_type_relay2.id,
                },
                self.AttributeDefs.relay_output_type_bitmap.id,
                lambda raw: {
                    self.AttributeDefs.relay_output_type_relay1.id: self._decode_relay_output_type(
                        raw
                    )[0],
                    self.AttributeDefs.relay_output_type_relay2.id: self._decode_relay_output_type(
                        raw
                    )[1],
                },
            ),
            (
                {
                    self.AttributeDefs.temperature_sensor_select.id,
                    self.AttributeDefs.external_temperature_input.id,
                    self.AttributeDefs.external_temperature_sensor.id,
                },
                self.AttributeDefs.remote_attribute_linkage.id,
                lambda raw: {
                    self.AttributeDefs.temperature_sensor_select.id: self._decode_remote_attribute_linkage(
                        raw
                    )[0],
                    self.AttributeDefs.external_temperature_input.id: self._decode_remote_attribute_linkage(
                        raw
                    )[1],
                    self.AttributeDefs.external_temperature_sensor.id: self._decode_remote_attribute_linkage(
                        raw
                    )[0]
                    != TemperatureSensorSelect.internal,
                },
            ),
            (
                {self.AttributeDefs.hvac_message_open_window_state.id},
                self.AttributeDefs.hvac_message_notification.id,
                lambda raw: {
                    self.AttributeDefs.hvac_message_open_window_state.id: self._decode_hvac_message_open_window_state(
                        raw
                    )
                },
            ),
            (
                {
                    self.AttributeDefs.current_ntc_temperature.id,
                    self.AttributeDefs.current_ntc_temperature_state.id,
                    self.AttributeDefs.current_ntc_temperature_display.id,
                },
                self.AttributeDefs.current_ntc_temperature_raw.id,
                lambda raw: {
                    self.AttributeDefs.current_ntc_temperature.id: self._decode_ntc_current_temperature(
                        raw
                    )[0],
                    self.AttributeDefs.current_ntc_temperature_state.id: self._decode_ntc_current_temperature(
                        raw
                    )[1],
                    self.AttributeDefs.current_ntc_temperature_display.id: self._format_ntc_current_temperature_display(
                        self._decode_ntc_current_temperature(raw)[0],
                        self._decode_ntc_current_temperature(raw)[1],
                    ),
                },
            ),
        )

        for requested_ids, raw_attr_id, decode in virtual_reads:
            requested = [attr for attr in remaining if attr in requested_ids]
            if not requested:
                continue

            remaining = [attr for attr in remaining if attr not in requested_ids]
            raw_success, raw_failed = self._split_read_results(
                await super().read_attributes_raw(
                    [raw_attr_id],
                    manufacturer=manufacturer,
                    **kwargs,
                )
            )
            if raw_success and raw_success[0].status == foundation.Status.SUCCESS:
                self._update_attribute(raw_attr_id, raw_success[0].value.value)
                values = decode(raw_success[0].value.value)
                success.extend(
                    self._read_record(attr_id, values[attr_id]) for attr_id in requested
                )
            elif raw_attr_id in (
                self.AttributeDefs.remote_attribute_linkage.id,
                self.AttributeDefs.radar_do_not_disturb_period.id,
                self.AttributeDefs.screen_night_mode_period.id,
            ):
                values = decode(None)
                success.extend(
                    self._read_record(attr_id, values[attr_id]) for attr_id in requested
                )
            else:
                status = self._first_status(raw_failed)
                failed.extend(
                    self._read_record(attr_id, None, status) for attr_id in requested
                )

        if remaining:
            raw_success, raw_failed = self._split_read_results(
                await super().read_attributes_raw(
                    remaining, manufacturer=manufacturer, **kwargs
                )
            )
            success.extend(raw_success)
            failed.extend(raw_failed)

        return (success, failed) if failed else (success,)

    async def _write_ui_system_mode(
        self,
        mode: TPWGZBASystemMode,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Write the virtual UI mode and update its cache only on success."""

        thermostat_cluster = getattr(self.endpoint, "thermostat", None)
        if thermostat_cluster is None:
            return [
                [
                    foundation.WriteAttributesStatusRecord(
                        foundation.Status.UNSUPPORTED_ATTRIBUTE,
                        self.AttributeDefs.tp_wgzba_ui_system_mode.id,
                    )
                ]
            ]

        write_real_system_mode = getattr(
            thermostat_cluster, "write_real_system_mode", None
        )
        if write_real_system_mode is not None:
            result = await write_real_system_mode(mode, **kwargs)
        else:
            result = await thermostat_cluster.write_attributes(
                {Thermostat.AttributeDefs.system_mode.id: mode},
                **kwargs,
            )

        if _write_succeeded(result):
            self._update_attribute(self.AttributeDefs.tp_wgzba_ui_system_mode.id, mode)
            self._update_device_work_mode_from_system(mode)
        return result

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Handle virtual attribute writes and proxy real vendor writes."""

        result: list[list[foundation.WriteAttributesStatusRecord]] = []
        remaining_attributes = attributes.copy()

        has_ui_system_mode, ui_system_mode_value = self._pop_attribute_value(
            remaining_attributes, self.AttributeDefs.tp_wgzba_ui_system_mode
        )
        if has_ui_system_mode:
            result.extend(
                await self._write_ui_system_mode(
                    TPWGZBASystemMode(int(ui_system_mode_value)), **kwargs
                )
            )

        temporary_mode_ui_updates: dict[int, Any] = {}
        has_ui_action, ui_action_value = self._pop_attribute_value(
            remaining_attributes, self.AttributeDefs.temporary_mode_ui_action
        )
        if has_ui_action:
            temporary_mode_ui_updates[
                self.AttributeDefs.temporary_mode_ui_action.id
            ] = TemporaryModeUiAction(int(ui_action_value))

        has_ui_duration, ui_duration_value = self._pop_attribute_value(
            remaining_attributes, self.AttributeDefs.temporary_mode_ui_duration_minutes
        )
        if has_ui_duration:
            temporary_mode_ui_updates[
                self.AttributeDefs.temporary_mode_ui_duration_minutes.id
            ] = self._clamp(
                self._coerce_int(ui_duration_value),
                1,
                TEMPORARY_MODE_UI_DURATION_MINUTES_MAX,
            )

        effective_ui_action = temporary_mode_ui_updates.get(
            self.AttributeDefs.temporary_mode_ui_action.id,
            self.get(self.AttributeDefs.temporary_mode_ui_action.name),
        )
        effective_ui_action = (
            TemporaryModeUiAction.Boost
            if effective_ui_action is None
            else TemporaryModeUiAction(int(effective_ui_action))
        )

        has_ui_target, ui_target_value = self._pop_attribute_value(
            remaining_attributes,
            self.AttributeDefs.temporary_mode_ui_target_temperature,
        )
        if has_ui_target:
            if effective_ui_action == TemporaryModeUiAction.Boost:
                temporary_mode_ui_updates[
                    self.AttributeDefs.temporary_mode_ui_target_temperature.id
                ] = TEMPORARY_MODE_BOOST_TARGET_TEMP_X100
            else:
                temporary_mode_ui_updates[
                    self.AttributeDefs.temporary_mode_ui_target_temperature.id
                ] = self._clamp(
                    self._coerce_int(ui_target_value),
                    TEMPORARY_MODE_UI_TARGET_TEMP_MIN_X100,
                    TEMPORARY_MODE_UI_TARGET_TEMP_MAX_X100,
                )

        if (
            (has_ui_action or has_ui_duration or has_ui_target)
            and effective_ui_action == TemporaryModeUiAction.Boost
            and self.AttributeDefs.temporary_mode_ui_target_temperature.id
            not in temporary_mode_ui_updates
        ):
            temporary_mode_ui_updates[
                self.AttributeDefs.temporary_mode_ui_target_temperature.id
            ] = TEMPORARY_MODE_BOOST_TARGET_TEMP_X100

        if temporary_mode_ui_updates:
            for attr_id, value in temporary_mode_ui_updates.items():
                self._update_attribute(attr_id, value)
            result.append(
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            )

        weekly_schedule_ui_updates: dict[int, Any] = {}
        for attr_def in self._WEEKLY_UI_ATTRS:
            has_value, attr_value = self._pop_attribute_value(
                remaining_attributes, attr_def
            )
            if not has_value:
                continue

            if attr_def.id == self.AttributeDefs.weekly_schedule_ui_day.id:
                weekly_schedule_ui_updates[attr_def.id] = WeeklyScheduleUiDay(
                    self._clamp(self._coerce_int(attr_value), 0, 6)
                )
            elif (
                attr_def.id == self.AttributeDefs.weekly_schedule_ui_transition_count.id
            ):
                weekly_schedule_ui_updates[attr_def.id] = self._clamp(
                    self._coerce_int(attr_value),
                    1,
                    WEEKLY_SCHEDULE_UI_SLOT_MAX,
                )
            elif attr_def.id == self.AttributeDefs.weekly_schedule_ui_time1.id:
                weekly_schedule_ui_updates[attr_def.id] = 0
            elif attr_def in self._WEEKLY_TIME_ATTRS:
                weekly_schedule_ui_updates[attr_def.id] = (
                    self._normalize_weekly_schedule_ui_minute(attr_value)
                )
            else:
                weekly_schedule_ui_updates[attr_def.id] = self._clamp(
                    self._coerce_int(attr_value),
                    WEEKLY_SCHEDULE_UI_TEMP_MIN_X100,
                    WEEKLY_SCHEDULE_UI_TEMP_MAX_X100,
                )

        if weekly_schedule_ui_updates:
            weekly_schedule_ui_updates[
                self.AttributeDefs.weekly_schedule_ui_transition_count.id
            ] = self._validate_weekly_schedule_ui_updates(weekly_schedule_ui_updates)
            for attr_id, value in weekly_schedule_ui_updates.items():
                self._update_attribute(attr_id, value)
            result.append(
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            )

        has_external_temperature_sensor, external_temperature_sensor_value = (
            self._pop_attribute_value(
                remaining_attributes, self.AttributeDefs.external_temperature_sensor
            )
        )
        has_sensor_select, sensor_select_value = self._pop_attribute_value(
            remaining_attributes, self.AttributeDefs.temperature_sensor_select
        )
        has_external_temperature, external_temperature_value = (
            self._pop_attribute_value(
                remaining_attributes, self.AttributeDefs.external_temperature_input
            )
        )
        if (
            has_external_temperature_sensor
            or has_sensor_select
            or has_external_temperature
        ):
            current_sensor_select, current_external_temperature = (
                self._decode_remote_attribute_linkage(
                    self.get(self.AttributeDefs.remote_attribute_linkage.name)
                )
            )
            new_sensor_select = (
                TemperatureSensorSelect.external
                if bool(external_temperature_sensor_value)
                else TemperatureSensorSelect.internal
                if has_external_temperature_sensor
                else TemperatureSensorSelect(int(sensor_select_value))
                if has_sensor_select
                else current_sensor_select
            )
            new_external_temperature = (
                self._clamp(
                    self._coerce_int(external_temperature_value),
                    EXTERNAL_TEMPERATURE_INPUT_MIN_X100,
                    EXTERNAL_TEMPERATURE_INPUT_MAX_X100,
                )
                if has_external_temperature
                else current_external_temperature
            )
            if (
                (has_external_temperature_sensor or has_sensor_select)
                and new_sensor_select != TemperatureSensorSelect.internal
                and not has_external_temperature
                and self.get(self.AttributeDefs.remote_attribute_linkage.name) is None
            ):
                raise ValueError(
                    "external_temperature_input must be set before switching to an external temperature source"
                )

            raw_value = self._encode_remote_attribute_linkage(
                new_sensor_select, new_external_temperature
            )
            result += await super().write_attributes(
                {self.AttributeDefs.remote_attribute_linkage.id: raw_value},
                **kwargs,
            )
            self._update_attribute(
                self.AttributeDefs.remote_attribute_linkage.id, raw_value
            )

        packed_writes = (
            (
                self.AttributeDefs.temperature_control_threshold_low,
                self.AttributeDefs.temperature_control_threshold_high,
                self.AttributeDefs.temperature_control_threshold,
                self._decode_threshold_pair,
                self._encode_threshold_pair,
                lambda value: self._clamp(self._coerce_int(value), -250, 250),
            ),
            (
                self.AttributeDefs.radar_do_not_disturb_start_minute,
                self.AttributeDefs.radar_do_not_disturb_end_minute,
                self.AttributeDefs.radar_do_not_disturb_period,
                self._decode_time_period,
                self._encode_time_period,
                self._normalize_weekly_schedule_ui_minute,
            ),
            (
                self.AttributeDefs.screen_night_mode_start_minute,
                self.AttributeDefs.screen_night_mode_end_minute,
                self.AttributeDefs.screen_night_mode_period,
                self._decode_time_period,
                self._encode_time_period,
                self._normalize_weekly_schedule_ui_minute,
            ),
            (
                self.AttributeDefs.relay_output_type_relay1,
                self.AttributeDefs.relay_output_type_relay2,
                self.AttributeDefs.relay_output_type_bitmap,
                self._decode_relay_output_type,
                self._encode_relay_output_type,
                lambda value: self._clamp(self._coerce_int(value), 0, 1),
            ),
        )

        for (
            first_attr,
            second_attr,
            raw_attr,
            decode,
            encode,
            normalize,
        ) in packed_writes:
            has_first, first_value = self._pop_attribute_value(
                remaining_attributes, first_attr
            )
            has_second, second_value = self._pop_attribute_value(
                remaining_attributes, second_attr
            )
            if not (has_first or has_second):
                continue

            current_first, current_second = decode(self.get(raw_attr.name))
            new_first = normalize(first_value) if has_first else current_first
            new_second = normalize(second_value) if has_second else current_second
            raw_value = encode(new_first, new_second)
            result += await super().write_attributes({raw_attr.id: raw_value}, **kwargs)
            self._update_attribute(raw_attr.id, raw_value)

        for raw_attr, start_attr, end_attr in (
            (
                self.AttributeDefs.radar_do_not_disturb_period,
                self.AttributeDefs.radar_do_not_disturb_start_minute,
                self.AttributeDefs.radar_do_not_disturb_end_minute,
            ),
            (
                self.AttributeDefs.screen_night_mode_period,
                self.AttributeDefs.screen_night_mode_start_minute,
                self.AttributeDefs.screen_night_mode_end_minute,
            ),
        ):
            has_raw, raw_value = self._pop_attribute_value(
                remaining_attributes, raw_attr
            )
            if not has_raw:
                continue

            raw_bytes = self._as_bytes(raw_value)
            if raw_bytes is None or len(raw_bytes) != 8:
                cached_start = self.get(start_attr.name)
                cached_end = self.get(end_attr.name)
                raw_bytes = self._encode_time_period(
                    self._normalize_weekly_schedule_ui_minute(
                        0 if cached_start is None else cached_start
                    ),
                    self._normalize_weekly_schedule_ui_minute(
                        0 if cached_end is None else cached_end
                    ),
                )
            result += await super().write_attributes({raw_attr.id: raw_bytes}, **kwargs)
            self._update_attribute(raw_attr.id, raw_bytes)

        if remaining_attributes:
            result += await super().write_attributes(remaining_attributes, **kwargs)

        return result

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ):
        """Handle virtual UI commands before forwarding real cluster commands."""

        if command_id == self.ServerCommandDefs.temporary_mode_ui_apply.id:
            mode, duration_minutes, target_temperature = (
                self._temporary_mode_ui_values()
            )
            if mode == TemporaryModeUiAction.Exit:
                return await self.exit_temporary_mode()

            duration_seconds = duration_minutes * 60
            target_temperature_celsius = target_temperature / 100.0
            if mode == TemporaryModeUiAction.Boost:
                return await self.set_boost(
                    duration_seconds, target_temperature_celsius
                )
            if mode == TemporaryModeUiAction.Timer:
                return await self.set_timer(
                    duration_seconds, target_temperature_celsius
                )
            raise ValueError(f"unsupported temporary mode UI action: {mode!r}")

        if command_id == self.ServerCommandDefs.weekly_schedule_ui_apply.id:
            thermostat_cluster = getattr(self.endpoint, "thermostat", None)
            if thermostat_cluster is None:
                raise ValueError("thermostat cluster is not available on this endpoint")

            day, transitions = self._weekly_schedule_ui_values()
            if len(transitions) <= 1:
                raise ValueError(
                    "weekly schedule must contain at least one non-NULL time slot after 00:00"
                )
            return await thermostat_cluster.set_weekly_schedule_heat_for_group(
                int(self.get(self.AttributeDefs.weekly_schedule_active_num.name) or 0),
                self._weekly_schedule_ui_day_to_standard_mask(day),
                transitions,
                manufacturer=manufacturer,
                expect_reply=expect_reply,
                tsn=tsn,
            )

        if command_id == self.ServerCommandDefs.weekly_schedule_ui_read.id:
            thermostat_cluster = getattr(self.endpoint, "thermostat", None)
            if thermostat_cluster is None:
                raise ValueError("thermostat cluster is not available on this endpoint")

            day, _ = self._weekly_schedule_ui_values()
            rsp = await thermostat_cluster.get_weekly_schedule_heat_for_group(
                int(self.get(self.AttributeDefs.weekly_schedule_active_num.name) or 0),
                self._weekly_schedule_ui_day_to_standard_mask(day),
                manufacturer=manufacturer,
                expect_reply=expect_reply,
                tsn=tsn,
            )
            self._update_weekly_schedule_ui_from_rsp(rsp)
            return rsp

        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )


_BUILDER = (
    QuirkBuilder("SONOFF", "TP-WGZBA")
    .replaces(SonoffTPWGZBAThermostatCluster)
    .replaces(SonoffTPWGZBAPrivateCluster)
    .prevent_default_entity_creation(
        cluster_id=Thermostat.cluster_id,
        unique_id_suffix="local_temperature_calibration",
    )
    .enum(
        SonoffTPWGZBAPrivateCluster.AttributeDefs.tp_wgzba_ui_system_mode.name,
        TPWGZBASystemMode,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        translation_key="device_work_mode",
        fallback_name="Device work mode",
    )
    .enum(
        SonoffTPWGZBAPrivateCluster.AttributeDefs.device_work_mode.name,
        TPWGZBADeviceWorkMode,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="device_work_mode_state",
        fallback_name="Device work mode state",
    )
)

for attr_name, translation_key, fallback_name in (
    ("child_lock", "child_lock", "Child lock"),
    (
        "bt_pairing_broadcast_req",
        "bluetooth_pairing_request",
        "Bluetooth pairing request",
    ),
    (
        "window_opening_detection",
        "window_opening_detection",
        "Window opening detection",
    ),
):
    _BUILDER = _BUILDER.switch(
        getattr(SonoffTPWGZBAPrivateCluster.AttributeDefs, attr_name).name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        translation_key=translation_key,
        fallback_name=fallback_name,
    )

_BUILDER = (
    _BUILDER.number(
        Thermostat.AttributeDefs.local_temperature_calibration.name,
        Thermostat.cluster_id,
        min_value=-10.0,
        max_value=10.0,
        step=0.1,
        unit=UnitOfTemperature.CELSIUS,
        mode=NumberMode.SLIDER,
        unique_id_suffix="local_temperature_calibration_slider",
        multiplier=0.1,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    .number(
        SonoffTPWGZBAPrivateCluster.AttributeDefs.frost_proof_temperature.name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        min_value=5.0,
        max_value=15.0,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="frost_proof_temperature",
        fallback_name="Frost proof temperature",
    )
    .switch(
        SonoffTPWGZBAPrivateCluster.AttributeDefs.external_temperature_sensor.name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        translation_key="external_temperature_sensor",
        fallback_name="External temperature sensor",
    )
    .number(
        SonoffTPWGZBAPrivateCluster.AttributeDefs.external_temperature_input.name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        min_value=0.0,
        max_value=99.9,
        step=0.1,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="external_temperature_input",
        fallback_name="External temperature",
    )
    .command_button(
        SonoffTPWGZBAPrivateCluster.ServerCommandDefs.weekly_schedule_ui_apply.name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        translation_key="schedule_apply",
        fallback_name="Schedule apply",
    )
    .command_button(
        SonoffTPWGZBAPrivateCluster.ServerCommandDefs.weekly_schedule_ui_read.name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        translation_key="schedule_fetch",
        fallback_name="Schedule fetch",
    )
    .enum(
        SonoffTPWGZBAPrivateCluster.AttributeDefs.weekly_schedule_active_num.name,
        WeeklyScheduleActiveGroup,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        translation_key="schedule_group",
        fallback_name="Schedule group",
    )
    .enum(
        SonoffTPWGZBAPrivateCluster.AttributeDefs.weekly_schedule_ui_day.name,
        WeeklyScheduleUiDay,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        translation_key="schedule_operating_day",
        fallback_name="Schedule operating day",
    )
)

for slot in range(WEEKLY_SCHEDULE_UI_SLOT_MAX):
    time_attr = SonoffTPWGZBAPrivateCluster._WEEKLY_TIME_ATTRS[slot]
    temp_attr = SonoffTPWGZBAPrivateCluster._WEEKLY_TEMP_ATTRS[slot]
    _BUILDER = _BUILDER.enum(
        time_attr.name,
        WeeklyScheduleUiTimeFirst if slot == 0 else WeeklyScheduleUiTime,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        translation_key=f"schedule_period_{slot + 1}_time",
        fallback_name=f"Schedule period {slot + 1} time",
    ).number(
        temp_attr.name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        min_value=5.0,
        max_value=30.0,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key=f"schedule_period_{slot + 1}_temp",
        fallback_name=f"Schedule period {slot + 1} temp",
    )

for attr_name, min_value, max_value, step, translation_key, fallback_name in (
    (
        "temperature_control_threshold_low",
        -2.6,
        -0.2,
        0.2,
        "heating_low_threshold",
        "Heating low threshold",
    ),
    (
        "temperature_control_threshold_high",
        0,
        2.6,
        0.2,
        "heating_high_threshold",
        "Heating high threshold",
    ),
):
    _BUILDER = _BUILDER.number(
        getattr(SonoffTPWGZBAPrivateCluster.AttributeDefs, attr_name).name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        min_value=min_value,
        max_value=max_value,
        step=step,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key=translation_key,
        fallback_name=fallback_name,
    )

for attr_name, translation_key, fallback_name in (
    ("radar_enable", "radar_enable", "Radar enable"),
    ("radar_do_not_disturb_enable", "radar_do_not_disturb", "Radar do not disturb"),
    ("screen_night_mode_enable", "display_night_mode", "Display night mode"),
    (
        "overheat_protection_enable",
        "ntc_overheat_protection_enable",
        "NTC overheat protection enable",
    ),
):
    _BUILDER = _BUILDER.switch(
        getattr(SonoffTPWGZBAPrivateCluster.AttributeDefs, attr_name).name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        translation_key=translation_key,
        fallback_name=fallback_name,
    )

for attr_name, enum_type, translation_key, fallback_name in (
    (
        "radar_sensitivity_level",
        RadarSensitivity,
        "radar_sensitivity_level",
        "Radar sensitivity level",
    ),
    (
        "radar_do_not_disturb_start_minute",
        TimeOfDay30Min,
        "radar_do_not_disturb_start_time",
        "Radar do not disturb start time",
    ),
    (
        "radar_do_not_disturb_end_minute",
        TimeOfDay30Min,
        "radar_do_not_disturb_end_time",
        "Radar do not disturb end time",
    ),
    (
        "screen_night_mode_start_minute",
        TimeOfDay30Min,
        "display_night_mode_start_time",
        "Display night mode start time",
    ),
    (
        "screen_night_mode_end_minute",
        TimeOfDay30Min,
        "display_night_mode_end_time",
        "Display night mode end time",
    ),
    (
        "relay_output_type_relay1",
        RelayOutputType,
        "relay_heating_contact_type",
        "Relay heating contact type",
    ),
    (
        "relay_output_type_relay2",
        RelayOutputType,
        "relay_boiler_contact_type",
        "Relay boiler contact type",
    ),
):
    _BUILDER = _BUILDER.enum(
        getattr(SonoffTPWGZBAPrivateCluster.AttributeDefs, attr_name).name,
        enum_type,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        translation_key=translation_key,
        fallback_name=fallback_name,
    )

for attr_name, max_value, translation_key, fallback_name in (
    (
        "screen_working_brightness",
        8,
        "display_active_brightness",
        "Display active brightness",
    ),
    (
        "screen_standby_brightness",
        8,
        "display_standby_brightness",
        "Display standby brightness",
    ),
    (
        "screen_night_standby_brightness",
        8,
        "display_night_standby_brightness",
        "Display night standby brightness",
    ),
):
    _BUILDER = _BUILDER.number(
        getattr(SonoffTPWGZBAPrivateCluster.AttributeDefs, attr_name).name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        min_value=0,
        max_value=max_value,
        step=1,
        translation_key=translation_key,
        fallback_name=fallback_name,
    )

_BUILDER = (
    _BUILDER.command_button(
        SonoffTPWGZBAPrivateCluster.ServerCommandDefs.temporary_mode_ui_apply.name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        translation_key="override_apply",
        fallback_name="Override apply",
    )
    .command_button(
        SonoffTPWGZBAPrivateCluster.ServerCommandDefs.temporary_mode.name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        command_args=(bytes([TEMPORARY_MODE_EXIT]),),
        translation_key="override_exit",
        fallback_name="Override exit",
    )
    .enum(
        SonoffTPWGZBAPrivateCluster.AttributeDefs.temporary_mode_ui_action.name,
        TemporaryModeUiSelectableAction,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        translation_key="override_mode",
        fallback_name="Override mode",
    )
    .number(
        SonoffTPWGZBAPrivateCluster.AttributeDefs.temporary_mode_ui_target_temperature.name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        min_value=5.0,
        max_value=30.0,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="override_target_temperature",
        fallback_name="Override target temperature",
    )
    .number(
        SonoffTPWGZBAPrivateCluster.AttributeDefs.temporary_mode_ui_duration_minutes.name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        min_value=1,
        max_value=TEMPORARY_MODE_UI_DURATION_MINUTES_MAX,
        step=1,
        unit=UnitOfTime.MINUTES,
        translation_key="override_period",
        fallback_name="Override period",
    )
    .enum(
        SonoffTPWGZBAPrivateCluster.AttributeDefs.temporary_temperature_mode_state.name,
        TemporaryTemperatureModeState,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="override_mode_state",
        fallback_name="Override mode",
    )
    .enum(
        SonoffTPWGZBAPrivateCluster.AttributeDefs.hvac_message_open_window_state.name,
        HvacMessageOpenWindowState,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="open_window_state",
        fallback_name="Open window state",
    )
    .sensor(
        SonoffTPWGZBAPrivateCluster.AttributeDefs.current_ntc_temperature_display.name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        translation_key="ntc_temperature",
        fallback_name="NTC temperature",
    )
    .number(
        SonoffTPWGZBAPrivateCluster.AttributeDefs.overheat_protection_temperature.name,
        SonoffTPWGZBAPrivateCluster.cluster_id,
        min_value=20.0,
        max_value=50.0,
        step=0.01,
        unit=UnitOfTemperature.CELSIUS,
        mode=NumberMode.SLIDER,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="ntc_overheat_protection_temperature",
        fallback_name="NTC overheat protection temperature",
    )
)

_BUILDER.add_to_registry()
