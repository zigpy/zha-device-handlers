"""Sonoff SWV - Zigbee smart water valve."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    NumberDeviceClass,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,  # 传感器设备类
    SensorStateClass,  # 传感器状态类（用于折线图）
)

# 导入单位常量（时长/体积）
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t
from zigpy.zcl import (
    AttributeReadEvent,
    AttributeReportedEvent,
    AttributeUpdatedEvent,
    AttributeWrittenEvent,
    foundation,
)
from zigpy.zcl.foundation import BaseAttributeDefs, Status, ZCLAttributeDef

from zhaquirks import LocalDataCluster

SINGLE_IRRIGATION_ARRAY_ITEM_TYPE = foundation.DataTypeId.uint8
SINGLE_IRRIGATION_PAYLOAD_LEN = 12
SINGLE_IRRIGATION_DURATION_MIN_MIN = 0
SINGLE_IRRIGATION_DURATION_MAX_MIN = 65535
SINGLE_IRRIGATION_STEP_MIN = 1
SINGLE_IRRIGATION_AMOUNT_MIN = 0
SINGLE_IRRIGATION_AMOUNT_MAX = 10000
SINGLE_IRRIGATION_FAIL_SAFE_MIN = 0
SINGLE_IRRIGATION_FAIL_SAFE_MAX = 65535
SINGLE_IRRIGATION_DEFAULT_TOTAL_DURATION_MIN = 10
SINGLE_IRRIGATION_DEFAULT_AMOUNT = 30
SINGLE_IRRIGATION_DEFAULT_FAIL_SAFE_DURATION_MIN = 10
SINGLE_IRRIGATION_ZB_AMOUNT_UNIT_LITER = 0x01
MANUAL_IRRIGATION_DURATION_MIN = 1
MANUAL_IRRIGATION_DURATION_MAX = 719
MANUAL_IRRIGATION_AMOUNT_MIN = 1
MANUAL_IRRIGATION_AMOUNT_MAX = 10000
SCHEDULE_IRRIGATION_TOTAL_DURATION_MIN = 1
SCHEDULE_IRRIGATION_TOTAL_DURATION_MAX = 719
SCHEDULE_IRRIGATION_DURATION_MIN = 1
SCHEDULE_IRRIGATION_DURATION_MAX = 60
SCHEDULE_IRRIGATION_INTERVAL_DURATION_MIN = 1
SCHEDULE_IRRIGATION_INTERVAL_DURATION_MAX = 60
SCHEDULE_IRRIGATION_FAIL_SAFE_MIN = 1
SCHEDULE_IRRIGATION_FAIL_SAFE_MAX = 719
QUARTERLY_ADJUSTMENT_PAYLOAD_LEN = 12
QUARTERLY_ADJUSTMENT_DEFAULT_VALUE = 10
IRRIGATION_PLAN_PAYLOAD_LEN = 28
IRRIGATION_PLAN_MAX_COUNT = 6
IRRIGATION_PLAN_SET_COMMAND_ID = 0x06
IRRIGATION_PLAN_REMOVE_COMMAND_ID = 0x07
USER_DELAY_PAYLOAD_LEN = 4
USER_DELAY_SET_COMMAND_ID = 0x08
USER_DELAY_MAX_HOURS = 7 * 24
ZIGBEE_EPOCH_OFFSET = 946684800


def _u16_be(data: bytes) -> int:
    """Decode an unsigned big-endian 16-bit integer."""

    return int.from_bytes(data[:2], "big")


def _put_u16_be(value: int) -> list[int]:
    """Encode an unsigned big-endian 16-bit integer."""

    return list(int(value).to_bytes(2, "big"))


def _put_u32_be(value: int) -> list[int]:
    """Encode an unsigned big-endian 32-bit integer."""

    return list(int(value).to_bytes(4, "big"))


class IrrigationPlanPayload(t.FixedList):
    """Raw 28-byte irrigation plan payload."""

    _item_type = t.uint8_t
    _length = IRRIGATION_PLAN_PAYLOAD_LEN


class QuarterlyAdjustmentPayload(t.FixedList):
    """Raw 12-byte quarterly adjustment payload."""

    _item_type = t.uint8_t
    _length = QUARTERLY_ADJUSTMENT_PAYLOAD_LEN


class UserDelayPayload(t.FixedList):
    """Raw 4-byte user rain delay timestamp payload."""

    _item_type = t.uint8_t
    _length = USER_DELAY_PAYLOAD_LEN


class QuarterlyAdjustmentState:
    """State container for seasonal watering adjustment."""

    def __init__(self, values: list[int] | None = None):
        """Initialize monthly seasonal adjustment values."""

        self.values = list(
            values
            or [QUARTERLY_ADJUSTMENT_DEFAULT_VALUE] * QUARTERLY_ADJUSTMENT_PAYLOAD_LEN
        )
        if len(self.values) != QUARTERLY_ADJUSTMENT_PAYLOAD_LEN:
            raise ValueError("Quarterly adjustment state must contain 12 values")

    def to_payload(self) -> bytes:
        """Return the 12-byte firmware payload."""

        return bytes(int(value) for value in self.values)


class SingleIrrigationMode(t.enum8):
    """Single irrigation mode."""

    Duration = 0x00
    Volume = 0x01


class IrrigationPlanMode(t.enum8):
    """Auto irrigation plan mode."""

    Duration = 0x00
    Volume = 0x01
    Duration_With_Interval = 0x02


class DurationOnlyIrrigationPlanMode(t.enum8):
    """Auto irrigation plan mode for devices without a flow meter."""

    Duration = 0x00
    Duration_With_Interval = 0x02


class IrrigationAmountUnit(t.enum8):
    """Single irrigation amount unit."""

    Liter = 0x00
    US_Gallon = 0x01
    Imperial_Gallon = 0x02


@dataclass
class SingleIrrigationState:
    """Decoded Sonoff single irrigation setting."""

    irrigation_mode: int = SingleIrrigationMode.Duration
    total_duration_min: int = SINGLE_IRRIGATION_DEFAULT_TOTAL_DURATION_MIN
    zb_amount_unit: int = SINGLE_IRRIGATION_ZB_AMOUNT_UNIT_LITER
    amount: int = SINGLE_IRRIGATION_DEFAULT_AMOUNT
    fail_safe_duration_min: int = SINGLE_IRRIGATION_DEFAULT_FAIL_SAFE_DURATION_MIN


class IrrigationLoopType(t.enum8):
    """Irrigation schedule loop type."""

    Odd_Day = 0x00
    Even_Day = 0x01
    Days = 0x02
    Week = 0x03
    Only = 0x04


class IrrigationPlanRepeat(t.enum8):
    """Simplified irrigation schedule repeat mode."""

    Odd_Day = 0x00
    Even_Day = 0x01
    Interval = 0x02
    Custom = 0x03


@dataclass
class IrrigationPlan:
    """Sonoff auto irrigation plan in the Zigbee command payload format."""

    index: int = 0
    enabled: int = 1
    enable_datetime: int = 0
    irrigation_mode: int = SingleIrrigationMode.Duration
    start_datetime: int = 0
    total_duration_min: int = SINGLE_IRRIGATION_DEFAULT_TOTAL_DURATION_MIN
    duration_min: int = 0
    interval_duration_min: int = 0
    amount_unit: int = SINGLE_IRRIGATION_ZB_AMOUNT_UNIT_LITER
    amount: int = SINGLE_IRRIGATION_DEFAULT_AMOUNT
    fail_safe_duration_min: int = SINGLE_IRRIGATION_DEFAULT_FAIL_SAFE_DURATION_MIN
    create_datetime: int = 0
    repeat_mode: int = IrrigationPlanRepeat.Custom
    repeat_value: int = 0


def _validate_irrigation_plan_index(index: int) -> None:
    """Validate that a schedule index is supported by the firmware."""

    if not 0 <= int(index) < IRRIGATION_PLAN_MAX_COUNT:
        raise ValueError("Irrigation plan index must be between 0 and 5")


def _repeat_to_loop_info(repeat_mode: int, repeat_value: int) -> tuple[int, int]:
    """Convert simplified repeat settings to firmware loop fields."""

    repeat_mode = int(repeat_mode)
    repeat_value = int(repeat_value)
    if repeat_mode == IrrigationPlanRepeat.Odd_Day:
        return IrrigationLoopType.Odd_Day, 0
    if repeat_mode == IrrigationPlanRepeat.Even_Day:
        return IrrigationLoopType.Even_Day, 0
    if repeat_mode == IrrigationPlanRepeat.Interval:
        if not 1 <= repeat_value <= 30:
            raise ValueError("Irrigation plan interval must be between 1 and 30 days")
        return IrrigationLoopType.Days, repeat_value
    if repeat_mode == IrrigationPlanRepeat.Custom:
        if not 0 <= repeat_value <= 0x7F:
            raise ValueError("Irrigation plan custom weekday mask must be 0..127")
        return IrrigationLoopType.Week, repeat_value
    raise ValueError("Unsupported irrigation plan repeat mode")


def _seconds_from_midnight(hour: int, minute: int) -> int:
    """Return elapsed seconds from midnight for the current day."""

    return int(hour) * 3600 + int(minute) * 60


def _zigbee_date_timestamp(year: int, month: int, day: int) -> int:
    """Return the Zigbee epoch timestamp for a date at midnight UTC."""

    return int(
        datetime(int(year), int(month), int(day), tzinfo=UTC).timestamp()
        - ZIGBEE_EPOCH_OFFSET
    )


def _zigbee_now_timestamp() -> int:
    """Return the current UTC timestamp using the Zigbee epoch."""

    return int(datetime.now(tz=UTC).timestamp() - ZIGBEE_EPOCH_OFFSET)


def _local_timezone_offset_seconds() -> int:
    """Return the local runtime timezone offset in seconds."""

    offset = datetime.now().astimezone().utcoffset()
    if offset is None:
        return 0
    return int(offset.total_seconds())


def _zigbee_timestamp_to_ymd(value: int) -> tuple[int, int, int]:
    """Convert a Zigbee epoch timestamp to year/month/day."""

    dt = datetime.fromtimestamp(int(value) + ZIGBEE_EPOCH_OFFSET, tz=UTC)
    return dt.year, dt.month, dt.day


def encode_irrigation_plan_payload(plan: IrrigationPlan) -> bytes:
    """Encode a Zigbee auto irrigation plan command payload."""

    _validate_irrigation_plan_index(plan.index)
    loop_type, loop_option = _repeat_to_loop_info(plan.repeat_mode, plan.repeat_value)

    payload: list[int] = [
        int(plan.index),
        int(plan.enabled),
        int(loop_type),
        int(loop_option),
        *_put_u32_be(plan.enable_datetime),
        int(plan.irrigation_mode),
        *_put_u32_be(plan.start_datetime),
        *_put_u16_be(plan.total_duration_min),
        *_put_u16_be(plan.duration_min),
        *_put_u16_be(plan.interval_duration_min),
        int(plan.amount_unit),
        *_put_u16_be(plan.amount),
        *_put_u16_be(plan.fail_safe_duration_min),
        *_put_u32_be(plan.create_datetime),
    ]
    if len(payload) != IRRIGATION_PLAN_PAYLOAD_LEN:
        raise ValueError("Irrigation plan payload must be 28 bytes")
    return bytes(payload)


def quarterly_adjustment_payload_from_value(value: Any) -> bytes:
    """Normalize quarterly adjustment input to 12 raw bytes."""

    if isinstance(value, foundation.Array):
        value = value.value
    if isinstance(value, (bytes, bytearray)) or isinstance(value, t.LVList):
        data = bytes(value)
    elif isinstance(value, list):
        data = bytes(int(item) for item in value)
    else:
        raise TypeError("Unsupported quarterly adjustment payload value")
    if len(data) != QUARTERLY_ADJUSTMENT_PAYLOAD_LEN:
        raise ValueError("Quarterly adjustment payload must be 12 bytes")
    return data


def quarterly_adjustment_array_from_payload(
    payload: bytes | list[int] | foundation.Array,
) -> foundation.Array:
    """Wrap a quarterly adjustment payload in a ZCL array value."""

    data = quarterly_adjustment_payload_from_value(payload)
    return foundation.Array(
        type=SINGLE_IRRIGATION_ARRAY_ITEM_TYPE,
        value=t.LVList[t.uint8_t, t.uint16_t](data),
    )


def single_irrigation_array_from_payload(
    payload: bytes | list[int],
) -> foundation.Array:
    """Wrap a single irrigation payload in a ZCL array value."""

    return foundation.Array(
        type=SINGLE_IRRIGATION_ARRAY_ITEM_TYPE,
        value=t.LVList[t.uint8_t, t.uint16_t](payload),
    )


def single_irrigation_payload_from_array(value: Any) -> bytes:
    """Extract the single irrigation payload bytes from a decoded ZCL array."""

    if isinstance(value, foundation.Array):
        if value.value is None:
            raise ValueError("Single irrigation payload is empty")
        return bytes(value.value)
    if isinstance(value, (bytes, bytearray)):
        if len(value) >= 3 and value[0] == SINGLE_IRRIGATION_ARRAY_ITEM_TYPE:
            length = int.from_bytes(value[1:3], "little")
            return bytes(value[3 : 3 + length])
        return bytes(value)
    if isinstance(value, list):
        return bytes(value)
    if isinstance(value, t.LVList):
        return bytes(value)
    raise ValueError("Unsupported single irrigation payload value")


async def write_sonoff_array_attribute(
    cluster: CustomCluster,
    attr_def: ZCLAttributeDef,
    value: foundation.Array,
) -> list:
    """Write a Sonoff private array attribute with an explicit ZCL array type."""

    attr = foundation.Attribute(attr_def.id, foundation.TypeValue())
    data_type_id = getattr(foundation, "DataTypeId", None)
    attr.value.type = getattr(data_type_id, "array", 0x48)
    attr.value.value = value
    return await cluster.write_attributes_raw([attr])


def decode_single_irrigation_payload(
    payload: bytes | list[int] | foundation.Array,
) -> SingleIrrigationState:
    """Decode a Sonoff single irrigation setting payload."""

    data = single_irrigation_payload_from_array(payload)
    if len(data) < SINGLE_IRRIGATION_PAYLOAD_LEN:
        raise ValueError("Single irrigation payload is too short")

    return SingleIrrigationState(
        irrigation_mode=data[0],
        total_duration_min=_u16_be(data[1:3]),
        zb_amount_unit=data[7],
        amount=_u16_be(data[8:10]),
        fail_safe_duration_min=_u16_be(data[10:12]),
    )


def encode_single_irrigation_payload(state: SingleIrrigationState) -> bytes:
    """Encode a Sonoff single irrigation setting payload."""

    irrigation_mode = int(state.irrigation_mode)
    total_duration_min = state.total_duration_min
    amount = state.amount
    fail_safe_duration_min = state.fail_safe_duration_min

    if irrigation_mode == SingleIrrigationMode.Duration:
        amount = 0
        fail_safe_duration_min = 0
    elif irrigation_mode == SingleIrrigationMode.Volume:
        total_duration_min = 0
    else:
        irrigation_mode = SingleIrrigationMode.Duration
        amount = 0
        fail_safe_duration_min = 0

    payload: list[int] = [
        irrigation_mode,
        *_put_u16_be(total_duration_min),
        *_put_u16_be(0),
        *_put_u16_be(0),
        int(state.zb_amount_unit),
        *_put_u16_be(amount),
        *_put_u16_be(fail_safe_duration_min),
    ]
    return bytes(payload)


class ValveState(t.enum8):
    """Water valve state (8位变量，按位定义)."""

    # 基础状态（单一位）
    Normal = 0  # 000 (无任何异常)
    Water_Shortage = 1 << 0  # 001 (bit0: 缺水)
    Water_Leakage = 1 << 1  # 010 (bit1: 漏水)
    Anti_Frost_Alarm = 1 << 2  # 100 (bit2: 防霜冻报警)
    Water_Shortage_Channel_2 = 1 << 4  # bit4: 二通道缺水
    # 组合状态（多位同时触发）
    Water_Shortage_And_Leakage = Water_Shortage | Water_Leakage  # 011
    Water_Shortage_And_Frost = Water_Shortage | Anti_Frost_Alarm  # 101
    Water_Leakage_And_Frost = Water_Leakage | Anti_Frost_Alarm  # 110
    All_Alarms = Water_Shortage | Water_Leakage | Anti_Frost_Alarm  # 111


class CustomSonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11
    ep_attribute = "sonoff_cluster"

    class ServerCommandDefs(foundation.BaseCommandDefs):
        """Server command definitions."""

        irrigation_plan_set = foundation.ZCLCommandDef(
            id=IRRIGATION_PLAN_SET_COMMAND_ID,
            schema={"payload": IrrigationPlanPayload},
            is_manufacturer_specific=False,
        )
        irrigation_plan_remove = foundation.ZCLCommandDef(
            id=IRRIGATION_PLAN_REMOVE_COMMAND_ID,
            schema={"index": t.uint8_t},
            is_manufacturer_specific=False,
        )
        user_delay_set = foundation.ZCLCommandDef(
            id=USER_DELAY_SET_COMMAND_ID,
            schema={"payload": UserDelayPayload},
            is_manufacturer_specific=False,
        )

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # 童锁
        child_lock = ZCLAttributeDef(
            id=0x0000,
            type=t.Bool,
            manufacturer_code=None,
        )
        water_valve_state = ZCLAttributeDef(
            id=0x500C,
            type=ValveState,
            manufacturer_code=None,
        )
        # 用水时长
        water_usage_duration = ZCLAttributeDef(
            id=0x501C,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        # 用水量
        water_usage_volume = ZCLAttributeDef(
            id=0x501B,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        # 单次开阀浇水设置
        single_irrigation_set = ZCLAttributeDef(
            id=0x501D,
            type=foundation.Array,
            manufacturer_code=None,
        )
        # 水流单位
        unit_of_water_flow = ZCLAttributeDef(
            id=0x5021,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        # 季节调整浇水
        quarterly_adjustment = ZCLAttributeDef(
            id=0x501E,
            type=foundation.Array,
            manufacturer_code=None,
        )
        # 手动雨水延迟结束时间
        user_delay_end_datetime = ZCLAttributeDef(
            id=0x5014,
            type=t.uint32_t,
            manufacturer_code=None,
        )

    def __init__(self, *args, **kwargs):
        """Init and listen for single irrigation attribute changes."""
        super().__init__(*args, **kwargs)
        self._single_irrigation_state = SingleIrrigationState()
        self._quarterly_adjustment = QuarterlyAdjustmentState()
        self.on_event(
            AttributeReadEvent.event_type, self._handle_single_irrigation_change
        )
        self.on_event(
            AttributeReportedEvent.event_type, self._handle_single_irrigation_change
        )
        self.on_event(
            AttributeUpdatedEvent.event_type, self._handle_single_irrigation_change
        )
        self.on_event(
            AttributeWrittenEvent.event_type, self._handle_single_irrigation_change
        )
        self.on_event(
            AttributeReadEvent.event_type, self._handle_quarterly_adjustment_change
        )
        self.on_event(
            AttributeReportedEvent.event_type, self._handle_quarterly_adjustment_change
        )
        self.on_event(
            AttributeUpdatedEvent.event_type, self._handle_quarterly_adjustment_change
        )
        self.on_event(
            AttributeWrittenEvent.event_type, self._handle_quarterly_adjustment_change
        )

    def _handle_single_irrigation_change(
        self,
        event: AttributeReadEvent
        | AttributeReportedEvent
        | AttributeUpdatedEvent
        | AttributeWrittenEvent,
    ) -> None:
        """Sync single irrigation state to the local config cluster."""
        if isinstance(event, AttributeWrittenEvent) and event.status != Status.SUCCESS:
            return
        if event.attribute_id == self.AttributeDefs.unit_of_water_flow.id:
            if hasattr(self.endpoint, "sonoff_single_irrigation_config"):
                self.endpoint.sonoff_single_irrigation_config.update_amount_unit(
                    int(event.value)
                )
            return
        if event.attribute_id != self.AttributeDefs.single_irrigation_set.id:
            return

        values = [event.value]
        if isinstance(event, AttributeReadEvent) and event.raw_value is not event.value:
            values.append(event.raw_value)

        for value in values:
            try:
                self._single_irrigation_state = decode_single_irrigation_payload(value)
                break
            except (TypeError, ValueError):
                continue
        else:
            return

        if hasattr(self.endpoint, "sonoff_single_irrigation_config"):
            self.endpoint.sonoff_single_irrigation_config._has_device_single_irrigation_state = True
            self.endpoint.sonoff_single_irrigation_config.update_single_irrigation_state(
                self._single_irrigation_state
            )

    def _handle_quarterly_adjustment_change(
        self,
        event: AttributeReadEvent
        | AttributeReportedEvent
        | AttributeUpdatedEvent
        | AttributeWrittenEvent,
    ) -> None:
        """Sync quarterly adjustment to the local config cluster."""
        if isinstance(event, AttributeWrittenEvent) and event.status != Status.SUCCESS:
            return
        if event.attribute_id != self.AttributeDefs.quarterly_adjustment.id:
            return

        values = [event.value]
        if isinstance(event, AttributeReadEvent) and event.raw_value is not event.value:
            values.append(event.raw_value)

        for value in values:
            try:
                payload = quarterly_adjustment_payload_from_value(value)
                self._quarterly_adjustment = QuarterlyAdjustmentState(list(payload))
                break
            except (TypeError, ValueError):
                continue
        else:
            return

        if hasattr(self.endpoint, "sonoff_irrigation_plan_config"):
            self.endpoint.sonoff_irrigation_plan_config.update_quarterly_adjustment(
                self._quarterly_adjustment.values
            )

    async def apply_custom_configuration(self, *args, **kwargs):
        """Avoid blocking ZHA pairing on optional private attribute reads."""
        return None


class SonoffSingleIrrigationConfigCluster(LocalDataCluster):
    """Local cluster for individual single irrigation configuration entities."""

    cluster_id = 0xFBFE
    ep_attribute = "sonoff_single_irrigation_config"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        irrigation_mode: Final = ZCLAttributeDef(id=0x0010, type=SingleIrrigationMode)
        total_duration_min: Final = ZCLAttributeDef(id=0x0011, type=t.uint16_t)
        amount_unit: Final = ZCLAttributeDef(id=0x0012, type=t.uint8_t)
        amount: Final = ZCLAttributeDef(id=0x0013, type=t.uint16_t)
        fail_safe_duration_min: Final = ZCLAttributeDef(id=0x0014, type=t.uint16_t)

    def __init__(self, *args, **kwargs):
        """Init with conservative default single irrigation state."""
        super().__init__(*args, **kwargs)
        self._single_irrigation_state = SingleIrrigationState()
        self._amount_unit = IrrigationAmountUnit.Liter
        self._has_device_single_irrigation_state = False
        self._update_attribute(
            self.AttributeDefs.irrigation_mode.id,
            self._single_irrigation_state.irrigation_mode,
        )
        self._update_attribute(
            self.AttributeDefs.total_duration_min.id,
            self._single_irrigation_state.total_duration_min,
        )
        self._update_attribute(
            self.AttributeDefs.amount_unit.id,
            self._amount_unit,
        )
        self._update_attribute(
            self.AttributeDefs.amount.id,
            self._single_irrigation_state.amount,
        )
        self._update_attribute(
            self.AttributeDefs.fail_safe_duration_min.id,
            self._single_irrigation_state.fail_safe_duration_min,
        )

    def update_single_irrigation_state(self, state: SingleIrrigationState) -> None:
        """Update local attributes from decoded single irrigation state."""
        self._single_irrigation_state = SingleIrrigationState(
            irrigation_mode=state.irrigation_mode,
            total_duration_min=state.total_duration_min,
            zb_amount_unit=state.zb_amount_unit,
            amount=self._single_irrigation_state.amount,
            fail_safe_duration_min=self._single_irrigation_state.fail_safe_duration_min,
        )
        if state.irrigation_mode == SingleIrrigationMode.Volume:
            if state.amount != 0:
                self._single_irrigation_state.amount = state.amount
            if state.fail_safe_duration_min != 0:
                self._single_irrigation_state.fail_safe_duration_min = (
                    state.fail_safe_duration_min
                )

        updates = {
            self.AttributeDefs.irrigation_mode.id: self._single_irrigation_state.irrigation_mode,
            self.AttributeDefs.total_duration_min.id: self._single_irrigation_state.total_duration_min,
            self.AttributeDefs.amount_unit.id: self._amount_unit,
            self.AttributeDefs.amount.id: self._single_irrigation_state.amount,
            self.AttributeDefs.fail_safe_duration_min.id: self._single_irrigation_state.fail_safe_duration_min,
        }
        for attr_id, value in updates.items():
            self._update_attribute(attr_id, value)

    def update_amount_unit(self, unit: int) -> None:
        """Update local amount unit from the real 0x5021 attribute."""
        self._amount_unit = int(unit)
        self._update_attribute(self.AttributeDefs.amount_unit.id, self._amount_unit)

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list:
        """Merge local writes into the real single irrigation aggregate attribute."""
        state = SingleIrrigationState(
            irrigation_mode=self._single_irrigation_state.irrigation_mode,
            total_duration_min=self._single_irrigation_state.total_duration_min,
            zb_amount_unit=self._single_irrigation_state.zb_amount_unit,
            amount=self._single_irrigation_state.amount,
            fail_safe_duration_min=self._single_irrigation_state.fail_safe_duration_min,
        )
        pending_mode = state.irrigation_mode
        pending_amount_unit = self._amount_unit

        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if attr_id == self.AttributeDefs.irrigation_mode.id:
                pending_mode = int(value)
            elif attr_id == self.AttributeDefs.amount_unit.id:
                pending_amount_unit = int(value)

        for attr in attributes:
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if pending_mode == SingleIrrigationMode.Duration and attr_id in (
                self.AttributeDefs.amount.id,
                self.AttributeDefs.fail_safe_duration_min.id,
            ):
                raise ValueError(
                    "Single irrigation amount and fail safe duration are only "
                    "configurable in volume mode"
                )
            if (
                pending_mode == SingleIrrigationMode.Volume
                and attr_id == self.AttributeDefs.total_duration_min.id
            ):
                raise ValueError(
                    "Single irrigation total duration is only configurable in "
                    "duration mode"
                )

        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if attr_id == self.AttributeDefs.irrigation_mode.id:
                state.irrigation_mode = int(value)
            elif attr_id == self.AttributeDefs.total_duration_min.id:
                state.total_duration_min = max(
                    MANUAL_IRRIGATION_DURATION_MIN,
                    min(int(value), MANUAL_IRRIGATION_DURATION_MAX),
                )
            elif attr_id == self.AttributeDefs.amount_unit.id:
                self._amount_unit = int(value)
            elif attr_id == self.AttributeDefs.amount.id:
                state.amount = max(
                    MANUAL_IRRIGATION_AMOUNT_MIN,
                    min(int(value), MANUAL_IRRIGATION_AMOUNT_MAX),
                )
            elif attr_id == self.AttributeDefs.fail_safe_duration_min.id:
                state.fail_safe_duration_min = max(
                    MANUAL_IRRIGATION_DURATION_MIN,
                    min(int(value), MANUAL_IRRIGATION_DURATION_MAX),
                )

        attr_ids = {self.find_attribute(attr).id for attr in attributes}
        unit_result = None
        config_result = None
        if self.AttributeDefs.amount_unit.id in attr_ids:
            unit_result = await self.endpoint.sonoff_cluster.write_attributes(
                {
                    CustomSonoffCluster.AttributeDefs.unit_of_water_flow.id: t.uint8_t(
                        pending_amount_unit
                    )
                }
            )

        if attr_ids.intersection(
            {
                self.AttributeDefs.irrigation_mode.id,
                self.AttributeDefs.total_duration_min.id,
                self.AttributeDefs.amount.id,
                self.AttributeDefs.fail_safe_duration_min.id,
            }
        ):
            payload = encode_single_irrigation_payload(state)
            zcl_array = single_irrigation_array_from_payload(payload)
            config_result = await self.endpoint.sonoff_cluster.write_attributes(
                {CustomSonoffCluster.AttributeDefs.single_irrigation_set.id: zcl_array}
            )

        result = config_result if config_result is not None else unit_result
        if unit_result is not None and self._write_succeeded(unit_result):
            self.update_amount_unit(pending_amount_unit)
        if config_result is not None and self._write_succeeded(config_result):
            self._has_device_single_irrigation_state = False
            self._single_irrigation_state = state
            self._update_attribute(
                self.AttributeDefs.irrigation_mode.id,
                self._single_irrigation_state.irrigation_mode,
            )
            self._update_attribute(
                self.AttributeDefs.total_duration_min.id,
                self._single_irrigation_state.total_duration_min,
            )
            self._update_attribute(
                self.AttributeDefs.amount.id,
                self._single_irrigation_state.amount,
            )
            self._update_attribute(
                self.AttributeDefs.fail_safe_duration_min.id,
                self._single_irrigation_state.fail_safe_duration_min,
            )
        return result

    @staticmethod
    def _write_succeeded(result: list) -> bool:
        """Return whether a Zigpy write_attributes response succeeded."""
        try:
            records = result[0]
        except (IndexError, TypeError):
            return False
        return all(record.status == Status.SUCCESS for record in records)


class SonoffDurationOnlySingleIrrigationConfigCluster(LocalDataCluster):
    """Local single irrigation configuration for devices without a flow meter."""

    cluster_id = 0xFBFE
    ep_attribute = "sonoff_single_irrigation_config"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        total_duration_min: Final = ZCLAttributeDef(id=0x0011, type=t.uint16_t)

    def __init__(self, *args, **kwargs):
        """Init with duration-only defaults."""
        super().__init__(*args, **kwargs)
        self._single_irrigation_state = SingleIrrigationState(
            irrigation_mode=SingleIrrigationMode.Duration,
            total_duration_min=SINGLE_IRRIGATION_DEFAULT_TOTAL_DURATION_MIN,
            zb_amount_unit=SINGLE_IRRIGATION_ZB_AMOUNT_UNIT_LITER,
            amount=0,
            fail_safe_duration_min=0,
        )
        self._update_attribute(
            self.AttributeDefs.total_duration_min.id,
            self._single_irrigation_state.total_duration_min,
        )

    def update_single_irrigation_state(self, state: SingleIrrigationState) -> None:
        """Update duration-only local state from decoded device data."""
        self._single_irrigation_state = SingleIrrigationState(
            irrigation_mode=SingleIrrigationMode.Duration,
            total_duration_min=state.total_duration_min,
            zb_amount_unit=SINGLE_IRRIGATION_ZB_AMOUNT_UNIT_LITER,
            amount=0,
            fail_safe_duration_min=0,
        )
        self._update_attribute(
            self.AttributeDefs.total_duration_min.id,
            self._single_irrigation_state.total_duration_min,
        )

    def update_amount_unit(self, unit: int) -> None:
        """Ignore water-flow unit updates on duration-only devices."""

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list:
        """Write only the duration portion of the real single irrigation setting."""
        result = []
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            if attr_def.id == self.AttributeDefs.total_duration_min.id:
                state = SingleIrrigationState(
                    irrigation_mode=SingleIrrigationMode.Duration,
                    total_duration_min=max(
                        MANUAL_IRRIGATION_DURATION_MIN,
                        min(int(value), MANUAL_IRRIGATION_DURATION_MAX),
                    ),
                    zb_amount_unit=SINGLE_IRRIGATION_ZB_AMOUNT_UNIT_LITER,
                    amount=0,
                    fail_safe_duration_min=0,
                )
                payload = encode_single_irrigation_payload(state)
                zcl_array = single_irrigation_array_from_payload(payload)
                result = await write_sonoff_array_attribute(
                    self.endpoint.sonoff_cluster,
                    CustomSonoffCluster.AttributeDefs.single_irrigation_set,
                    zcl_array,
                )
                if SonoffSingleIrrigationConfigCluster._write_succeeded(result):
                    self._single_irrigation_state = state

        self._update_attribute(
            self.AttributeDefs.total_duration_min.id,
            self._single_irrigation_state.total_duration_min,
        )
        if result:
            return result
        return [[foundation.WriteAttributesStatusRecord(status=Status.SUCCESS)]]


class SonoffManualRainDelayConfigCluster(LocalDataCluster):
    """Local cluster for manual rain delay command entities."""

    cluster_id = 0xFBFC
    ep_attribute = "sonoff_manual_rain_delay_config"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        delay_hours: Final = ZCLAttributeDef(id=0x0010, type=t.uint16_t)
        apply_delay: Final = ZCLAttributeDef(id=0x0011, type=t.uint8_t)
        clear_delay: Final = ZCLAttributeDef(id=0x0012, type=t.uint8_t)
        timezone_offset_hours: Final = ZCLAttributeDef(id=0x0013, type=t.int8s)

    def __init__(self, *args, **kwargs):
        """Initialize local manual rain delay state."""
        super().__init__(*args, **kwargs)
        self._delay_hours = 24
        self._timezone_offset_hours = int(_local_timezone_offset_seconds() / 3600)
        self._update_attribute(self.AttributeDefs.delay_hours.id, self._delay_hours)
        self._update_attribute(
            self.AttributeDefs.timezone_offset_hours.id,
            self._timezone_offset_hours,
        )

    async def _send_user_delay_timestamp(self, end_timestamp: int) -> Any:
        """Send the firmware user delay command payload."""

        payload = UserDelayPayload(_put_u32_be(end_timestamp))
        return await self.endpoint.sonoff_cluster.command(
            USER_DELAY_SET_COMMAND_ID,
            payload=payload,
            manufacturer=None,
            expect_reply=False,
        )

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list:
        """Update delay duration or trigger the manual rain delay command."""
        result = []
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if attr_id == self.AttributeDefs.delay_hours.id:
                self._delay_hours = max(0, min(int(value), USER_DELAY_MAX_HOURS))
            elif attr_id == self.AttributeDefs.timezone_offset_hours.id:
                self._timezone_offset_hours = max(-12, min(int(value), 14))
            elif attr_id == self.AttributeDefs.apply_delay.id:
                delay_hours = max(0, min(self._delay_hours, USER_DELAY_MAX_HOURS))
                end_timestamp = (
                    _zigbee_now_timestamp()
                    + self._timezone_offset_hours * 3600
                    + delay_hours * 3600
                )
                result = await self._send_user_delay_timestamp(end_timestamp)
            elif attr_id == self.AttributeDefs.clear_delay.id:
                result = await self._send_user_delay_timestamp(0)

        self._update_attribute(self.AttributeDefs.delay_hours.id, self._delay_hours)
        self._update_attribute(
            self.AttributeDefs.timezone_offset_hours.id,
            self._timezone_offset_hours,
        )
        if result:
            return result
        return [[foundation.WriteAttributesStatusRecord(status=Status.SUCCESS)]]


class SonoffIrrigationPlanConfigCluster(LocalDataCluster):
    """Local cluster for auto irrigation plan configuration entities."""

    cluster_id = 0xFBFD
    ep_attribute = "sonoff_irrigation_plan_config"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        plan_index: Final = ZCLAttributeDef(id=0x0020, type=t.uint8_t)
        effective_year: Final = ZCLAttributeDef(id=0x0021, type=t.uint16_t)
        effective_month: Final = ZCLAttributeDef(id=0x0022, type=t.uint8_t)
        effective_day: Final = ZCLAttributeDef(id=0x0023, type=t.uint8_t)
        repeat_mode: Final = ZCLAttributeDef(id=0x0024, type=IrrigationPlanRepeat)
        repeat_value: Final = ZCLAttributeDef(id=0x0025, type=t.uint8_t)
        weekday_monday: Final = ZCLAttributeDef(id=0x0027, type=t.uint8_t)
        weekday_tuesday: Final = ZCLAttributeDef(id=0x0028, type=t.uint8_t)
        weekday_wednesday: Final = ZCLAttributeDef(id=0x0029, type=t.uint8_t)
        weekday_thursday: Final = ZCLAttributeDef(id=0x002A, type=t.uint8_t)
        weekday_friday: Final = ZCLAttributeDef(id=0x002B, type=t.uint8_t)
        weekday_saturday: Final = ZCLAttributeDef(id=0x002C, type=t.uint8_t)
        weekday_sunday: Final = ZCLAttributeDef(id=0x002D, type=t.uint8_t)
        start_hour: Final = ZCLAttributeDef(id=0x002E, type=t.uint8_t)
        start_minute: Final = ZCLAttributeDef(id=0x002F, type=t.uint8_t)
        apply_plan: Final = ZCLAttributeDef(id=0x0030, type=t.uint8_t)
        remove_plan: Final = ZCLAttributeDef(id=0x0031, type=t.uint8_t)
        plan_irrigation_mode: Final = ZCLAttributeDef(
            id=0x0032, type=IrrigationPlanMode
        )
        duration_min: Final = ZCLAttributeDef(id=0x0033, type=t.uint16_t)
        interval_duration_min: Final = ZCLAttributeDef(id=0x0034, type=t.uint16_t)
        plan_amount: Final = ZCLAttributeDef(id=0x0035, type=t.uint16_t)
        plan_fail_safe_duration_min: Final = ZCLAttributeDef(id=0x0036, type=t.uint16_t)
        plan_total_duration_min: Final = ZCLAttributeDef(id=0x0037, type=t.uint16_t)
        seasonal_adjustment_january: Final = ZCLAttributeDef(id=0x0040, type=t.uint8_t)
        seasonal_adjustment_february: Final = ZCLAttributeDef(id=0x0041, type=t.uint8_t)
        seasonal_adjustment_march: Final = ZCLAttributeDef(id=0x0042, type=t.uint8_t)
        seasonal_adjustment_april: Final = ZCLAttributeDef(id=0x0043, type=t.uint8_t)
        seasonal_adjustment_may: Final = ZCLAttributeDef(id=0x0044, type=t.uint8_t)
        seasonal_adjustment_june: Final = ZCLAttributeDef(id=0x0045, type=t.uint8_t)
        seasonal_adjustment_july: Final = ZCLAttributeDef(id=0x0046, type=t.uint8_t)
        seasonal_adjustment_august: Final = ZCLAttributeDef(id=0x0047, type=t.uint8_t)
        seasonal_adjustment_september: Final = ZCLAttributeDef(
            id=0x0048, type=t.uint8_t
        )
        seasonal_adjustment_october: Final = ZCLAttributeDef(id=0x0049, type=t.uint8_t)
        seasonal_adjustment_november: Final = ZCLAttributeDef(id=0x004A, type=t.uint8_t)
        seasonal_adjustment_december: Final = ZCLAttributeDef(id=0x004B, type=t.uint8_t)

    def __init__(self, *args, **kwargs):
        """Initialize local schedule state."""
        super().__init__(*args, **kwargs)
        now = datetime.now()
        self._plan_index = 0
        self._effective_year = now.year
        self._effective_month = now.month
        self._effective_day = now.day
        self._repeat_mode = IrrigationPlanRepeat.Custom
        self._repeat_value = 0
        self._irrigation_mode = IrrigationPlanMode.Duration
        self._total_duration_min = SINGLE_IRRIGATION_DEFAULT_TOTAL_DURATION_MIN
        self._duration_min = 5
        self._interval_duration_min = 5
        self._amount = SINGLE_IRRIGATION_DEFAULT_AMOUNT
        self._fail_safe_duration_min = SINGLE_IRRIGATION_DEFAULT_FAIL_SAFE_DURATION_MIN
        self._weekday_mask = 0
        self._start_hour = 8
        self._start_minute = 0
        self._quarterly_adjustment = QuarterlyAdjustmentState()
        self._update_all_attributes()
        self._ui_date_year, self._ui_date_month, self._ui_date_day = (
            now.year,
            now.month,
            now.day,
        )

    def _quarterly_adjustment_attr_defs(self) -> tuple[ZCLAttributeDef, ...]:
        """Return monthly seasonal adjustment attributes in month order."""

        return (
            self.AttributeDefs.seasonal_adjustment_january,
            self.AttributeDefs.seasonal_adjustment_february,
            self.AttributeDefs.seasonal_adjustment_march,
            self.AttributeDefs.seasonal_adjustment_april,
            self.AttributeDefs.seasonal_adjustment_may,
            self.AttributeDefs.seasonal_adjustment_june,
            self.AttributeDefs.seasonal_adjustment_july,
            self.AttributeDefs.seasonal_adjustment_august,
            self.AttributeDefs.seasonal_adjustment_september,
            self.AttributeDefs.seasonal_adjustment_october,
            self.AttributeDefs.seasonal_adjustment_november,
            self.AttributeDefs.seasonal_adjustment_december,
        )

    def _update_all_attributes(self) -> None:
        """Mirror the local plan into entity attributes."""
        updates = {
            self.AttributeDefs.plan_index.id: self._plan_index,
            self.AttributeDefs.effective_year.id: self._effective_year,
            self.AttributeDefs.effective_month.id: self._effective_month,
            self.AttributeDefs.effective_day.id: self._effective_day,
            self.AttributeDefs.repeat_mode.id: self._repeat_mode,
            self.AttributeDefs.repeat_value.id: self._repeat_value,
            self.AttributeDefs.plan_irrigation_mode.id: self._irrigation_mode,
            self.AttributeDefs.plan_total_duration_min.id: self._total_duration_min,
            self.AttributeDefs.duration_min.id: self._duration_min,
            self.AttributeDefs.interval_duration_min.id: self._interval_duration_min,
            self.AttributeDefs.plan_amount.id: self._amount,
            self.AttributeDefs.plan_fail_safe_duration_min.id: self._fail_safe_duration_min,
            self.AttributeDefs.weekday_sunday.id: int(bool(self._weekday_mask & 0x01)),
            self.AttributeDefs.weekday_monday.id: int(bool(self._weekday_mask & 0x02)),
            self.AttributeDefs.weekday_tuesday.id: int(bool(self._weekday_mask & 0x04)),
            self.AttributeDefs.weekday_wednesday.id: int(
                bool(self._weekday_mask & 0x08)
            ),
            self.AttributeDefs.weekday_thursday.id: int(
                bool(self._weekday_mask & 0x10)
            ),
            self.AttributeDefs.weekday_friday.id: int(bool(self._weekday_mask & 0x20)),
            self.AttributeDefs.weekday_saturday.id: int(
                bool(self._weekday_mask & 0x40)
            ),
            self.AttributeDefs.start_hour.id: self._start_hour,
            self.AttributeDefs.start_minute.id: self._start_minute,
        }
        for attr_def, value in zip(
            self._quarterly_adjustment_attr_defs(),
            self._quarterly_adjustment.values,
            strict=False,
        ):
            updates[attr_def.id] = value
        for attr_id, value in updates.items():
            self._update_attribute(attr_id, value)

    def update_quarterly_adjustment(self, values: list[int]) -> None:
        """Update local monthly seasonal adjustment state."""
        self._quarterly_adjustment = QuarterlyAdjustmentState(values)
        self._update_all_attributes()

    def _current_water_flow_unit(self) -> int:
        """Return the single global water flow unit used by the device."""

        unit = getattr(self.endpoint.sonoff_cluster, "_attr_cache", {}).get(
            CustomSonoffCluster.AttributeDefs.unit_of_water_flow.id
        )
        if unit is None and hasattr(self.endpoint, "sonoff_single_irrigation_config"):
            unit = self.endpoint.sonoff_single_irrigation_config._amount_unit
        if unit is None:
            unit = IrrigationAmountUnit.Liter

        unit = int(unit)
        if unit > 2:
            return int(IrrigationAmountUnit.Liter)
        return unit

    def _plan_from_current_config(self) -> IrrigationPlan:
        """Build a firmware plan from simple schedule fields and irrigation config."""
        _validate_irrigation_plan_index(self._plan_index)
        enable_datetime = _zigbee_date_timestamp(
            self._effective_year, self._effective_month, self._effective_day
        )
        start_datetime = _seconds_from_midnight(self._start_hour, self._start_minute)

        repeat_value = self._repeat_value
        if self._repeat_mode == IrrigationPlanRepeat.Custom:
            repeat_value = self._weekday_mask

        irrigation_mode = int(self._irrigation_mode)
        amount = 0
        fail_safe_duration_min = 0
        duration_min = 0
        interval_duration_min = 0
        if irrigation_mode == IrrigationPlanMode.Volume:
            amount = self._amount
            fail_safe_duration_min = self._fail_safe_duration_min
        elif irrigation_mode == IrrigationPlanMode.Duration_With_Interval:
            duration_min = max(1, self._duration_min)
            interval_duration_min = max(1, self._interval_duration_min)
        else:
            irrigation_mode = IrrigationPlanMode.Duration

        return IrrigationPlan(
            index=self._plan_index,
            enabled=1,
            enable_datetime=enable_datetime,
            irrigation_mode=irrigation_mode,
            start_datetime=start_datetime,
            total_duration_min=self._total_duration_min,
            duration_min=duration_min,
            interval_duration_min=interval_duration_min,
            amount_unit=self._current_water_flow_unit(),
            amount=amount,
            fail_safe_duration_min=fail_safe_duration_min,
            create_datetime=_zigbee_now_timestamp(),
            repeat_mode=self._repeat_mode,
            repeat_value=repeat_value,
        )

    def _validate_plan_before_send(self) -> None:
        """Validate cross-field schedule constraints before sending to firmware."""

        if int(self._irrigation_mode) != int(IrrigationPlanMode.Duration_With_Interval):
            return

        calculated_duration = self._duration_min + self._interval_duration_min
        if calculated_duration > self._total_duration_min:
            raise ValueError(
                "Scheduled irrigation duration plus interval duration must be "
                "less than or equal to scheduled total duration"
            )

    def _write_local_plan_attribute(self, attr_id: int, value: Any) -> bool:
        """Update a local schedule field and return whether it was handled."""

        if attr_id == self.AttributeDefs.plan_index.id:
            _validate_irrigation_plan_index(value)
            self._plan_index = int(value)
        elif attr_id == self.AttributeDefs.effective_year.id:
            self._effective_year = int(value)
        elif attr_id == self.AttributeDefs.effective_month.id:
            self._effective_month = int(value)
        elif attr_id == self.AttributeDefs.effective_day.id:
            self._effective_day = int(value)
        elif attr_id == self.AttributeDefs.repeat_mode.id:
            self._repeat_mode = int(value)
        elif attr_id == self.AttributeDefs.repeat_value.id:
            self._repeat_value = int(value)
        elif attr_id == self.AttributeDefs.plan_irrigation_mode.id:
            self._irrigation_mode = max(0, min(int(value), 2))
        elif attr_id == self.AttributeDefs.plan_total_duration_min.id:
            self._total_duration_min = max(
                SCHEDULE_IRRIGATION_TOTAL_DURATION_MIN,
                min(int(value), SCHEDULE_IRRIGATION_TOTAL_DURATION_MAX),
            )
        elif attr_id == self.AttributeDefs.duration_min.id:
            self._duration_min = max(
                SCHEDULE_IRRIGATION_DURATION_MIN,
                min(int(value), SCHEDULE_IRRIGATION_DURATION_MAX),
            )
        elif attr_id == self.AttributeDefs.interval_duration_min.id:
            self._interval_duration_min = max(
                SCHEDULE_IRRIGATION_INTERVAL_DURATION_MIN,
                min(int(value), SCHEDULE_IRRIGATION_INTERVAL_DURATION_MAX),
            )
        elif attr_id == self.AttributeDefs.plan_amount.id:
            self._amount = max(
                SINGLE_IRRIGATION_AMOUNT_MIN,
                min(int(value), SINGLE_IRRIGATION_AMOUNT_MAX),
            )
        elif attr_id == self.AttributeDefs.plan_fail_safe_duration_min.id:
            self._fail_safe_duration_min = max(
                SCHEDULE_IRRIGATION_FAIL_SAFE_MIN,
                min(int(value), SCHEDULE_IRRIGATION_FAIL_SAFE_MAX),
            )
        elif attr_id == self.AttributeDefs.weekday_sunday.id:
            self._weekday_mask = (self._weekday_mask & ~0x01) | int(bool(value))
        elif attr_id == self.AttributeDefs.weekday_monday.id:
            self._weekday_mask = (self._weekday_mask & ~0x02) | (int(bool(value)) << 1)
        elif attr_id == self.AttributeDefs.weekday_tuesday.id:
            self._weekday_mask = (self._weekday_mask & ~0x04) | (int(bool(value)) << 2)
        elif attr_id == self.AttributeDefs.weekday_wednesday.id:
            self._weekday_mask = (self._weekday_mask & ~0x08) | (int(bool(value)) << 3)
        elif attr_id == self.AttributeDefs.weekday_thursday.id:
            self._weekday_mask = (self._weekday_mask & ~0x10) | (int(bool(value)) << 4)
        elif attr_id == self.AttributeDefs.weekday_friday.id:
            self._weekday_mask = (self._weekday_mask & ~0x20) | (int(bool(value)) << 5)
        elif attr_id == self.AttributeDefs.weekday_saturday.id:
            self._weekday_mask = (self._weekday_mask & ~0x40) | (int(bool(value)) << 6)
        elif attr_id == self.AttributeDefs.start_hour.id:
            self._start_hour = int(value)
        elif attr_id == self.AttributeDefs.start_minute.id:
            self._start_minute = int(value)
        else:
            return False
        return True

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list:
        """Update local plan fields or trigger set/remove actions."""
        result = []
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if self._write_local_plan_attribute(attr_id, value):
                continue
            if attr_id in {
                attr_def.id for attr_def in self._quarterly_adjustment_attr_defs()
            }:
                values = list(self._quarterly_adjustment.values)
                for index, attr_def in enumerate(
                    self._quarterly_adjustment_attr_defs()
                ):
                    if attr_id == attr_def.id:
                        values[index] = int(value)
                        break
                self._quarterly_adjustment = QuarterlyAdjustmentState(values)
                result = await self.endpoint.sonoff_cluster.write_attributes(
                    {
                        CustomSonoffCluster.AttributeDefs.quarterly_adjustment.id: quarterly_adjustment_array_from_payload(
                            self._quarterly_adjustment.to_payload()
                        )
                    }
                )
            elif attr_id == self.AttributeDefs.apply_plan.id:
                self._validate_plan_before_send()
                payload = encode_irrigation_plan_payload(
                    self._plan_from_current_config()
                )
                result = await self.endpoint.sonoff_cluster.command(
                    IRRIGATION_PLAN_SET_COMMAND_ID,
                    payload=IrrigationPlanPayload(payload),
                    manufacturer=None,
                    expect_reply=False,
                )
            elif attr_id == self.AttributeDefs.remove_plan.id:
                _validate_irrigation_plan_index(self._plan_index)
                result = await self.endpoint.sonoff_cluster.command(
                    IRRIGATION_PLAN_REMOVE_COMMAND_ID,
                    index=t.uint8_t(self._plan_index),
                    manufacturer=None,
                    expect_reply=False,
                )

        self._update_all_attributes()
        if result:
            return result
        return [[foundation.WriteAttributesStatusRecord(status=Status.SUCCESS)]]


class SonoffDurationOnlyIrrigationPlanConfigCluster(SonoffIrrigationPlanConfigCluster):
    """Local auto irrigation plan configuration for devices without a flow meter."""

    ep_attribute = "sonoff_irrigation_plan_config"

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list:
        """Update local plan fields while rejecting volume mode."""
        normalized_attributes = dict(attributes)
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            if (
                attr_def.id == self.AttributeDefs.plan_irrigation_mode.id
                and int(value) == 1
            ):
                normalized_attributes[attr] = int(IrrigationPlanMode.Duration)
        return await super().write_attributes(normalized_attributes, **kwargs)

    def _current_water_flow_unit(self) -> int:
        """Use a fixed placeholder unit because duration-only devices have no unit UI."""

        return SINGLE_IRRIGATION_ZB_AMOUNT_UNIT_LITER

    def _plan_from_current_config(self) -> IrrigationPlan:
        """Build a duration-only firmware plan."""
        _validate_irrigation_plan_index(self._plan_index)
        enable_datetime = _zigbee_date_timestamp(
            self._effective_year, self._effective_month, self._effective_day
        )
        start_datetime = _seconds_from_midnight(self._start_hour, self._start_minute)

        repeat_value = self._repeat_value
        if self._repeat_mode == IrrigationPlanRepeat.Custom:
            repeat_value = self._weekday_mask

        irrigation_mode = int(self._irrigation_mode)
        duration_min = 0
        interval_duration_min = 0
        if irrigation_mode == IrrigationPlanMode.Duration_With_Interval:
            duration_min = max(1, self._duration_min)
            interval_duration_min = max(1, self._interval_duration_min)
        else:
            irrigation_mode = IrrigationPlanMode.Duration

        return IrrigationPlan(
            index=self._plan_index,
            enabled=1,
            enable_datetime=enable_datetime,
            irrigation_mode=irrigation_mode,
            start_datetime=start_datetime,
            total_duration_min=self._total_duration_min,
            duration_min=duration_min,
            interval_duration_min=interval_duration_min,
            amount_unit=self._current_water_flow_unit(),
            amount=0,
            fail_safe_duration_min=0,
            create_datetime=_zigbee_now_timestamp(),
            repeat_mode=self._repeat_mode,
            repeat_value=repeat_value,
        )


(
    # QuirkBuilder("SONOFF", "SWV")
    QuirkBuilder("SONOFF", "SWV-ZFU")
    # .also_applies_to("SONOFF", "SWV-ZFU")
    .also_applies_to("SONOFF", "SWV-ZFE")
    .replaces(CustomSonoffCluster)
    .adds(SonoffSingleIrrigationConfigCluster)
    .adds(SonoffManualRainDelayConfigCluster)
    .switch(
        CustomSonoffCluster.AttributeDefs.child_lock.name,
        CustomSonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="swv_child_lock",
        fallback_name="1.1 Child lock",
    )
    .enum(
        CustomSonoffCluster.AttributeDefs.unit_of_water_flow.name,
        IrrigationAmountUnit,
        CustomSonoffCluster.cluster_id,
        translation_key="manual_irrigation_amount_unit",
        fallback_name="2.1 Capacity Units",
    )
    .enum(
        SonoffSingleIrrigationConfigCluster.AttributeDefs.irrigation_mode.name,
        SingleIrrigationMode,
        SonoffSingleIrrigationConfigCluster.cluster_id,
        translation_key="manual_single_irrigation_mode",
        fallback_name="3.1 Manual Irrigation Mode",
    )
    .number(
        SonoffSingleIrrigationConfigCluster.AttributeDefs.total_duration_min.name,
        SonoffSingleIrrigationConfigCluster.cluster_id,
        min_value=MANUAL_IRRIGATION_DURATION_MIN,
        max_value=MANUAL_IRRIGATION_DURATION_MAX,
        step=SINGLE_IRRIGATION_STEP_MIN,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        mode="box",
        translation_key="manual_single_irrigation_total_duration",
        fallback_name="3.2 Manual irrigation duration",
    )
    .number(
        SonoffSingleIrrigationConfigCluster.AttributeDefs.amount.name,
        SonoffSingleIrrigationConfigCluster.cluster_id,
        min_value=MANUAL_IRRIGATION_AMOUNT_MIN,
        max_value=MANUAL_IRRIGATION_AMOUNT_MAX,
        step=1,
        mode="box",
        translation_key="manual_single_irrigation_amount",
        fallback_name="3.3 Manual irrigation capacity",
    )
    .number(
        SonoffSingleIrrigationConfigCluster.AttributeDefs.fail_safe_duration_min.name,
        SonoffSingleIrrigationConfigCluster.cluster_id,
        min_value=MANUAL_IRRIGATION_DURATION_MIN,
        max_value=MANUAL_IRRIGATION_DURATION_MAX,
        step=SINGLE_IRRIGATION_STEP_MIN,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        mode="box",
        translation_key="manual_single_irrigation_fail_safe_duration",
        fallback_name="3.4 Manual irrigation capacity-failsafe time",
    )
    .number(
        SonoffManualRainDelayConfigCluster.AttributeDefs.delay_hours.name,
        SonoffManualRainDelayConfigCluster.cluster_id,
        min_value=0,
        max_value=USER_DELAY_MAX_HOURS,
        step=1,
        mode="box",
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.HOURS,
        translation_key="manual_rain_delay_hours",
        fallback_name="4.1 Rain delay hours",
    )
    .number(
        SonoffManualRainDelayConfigCluster.AttributeDefs.timezone_offset_hours.name,
        SonoffManualRainDelayConfigCluster.cluster_id,
        min_value=-12,
        max_value=14,
        step=1,
        mode="box",
        translation_key="manual_rain_delay_timezone_offset",
        fallback_name="4.2 Rain delay timezone offset",
    )
    .write_attr_button(
        SonoffManualRainDelayConfigCluster.AttributeDefs.apply_delay.name,
        SonoffManualRainDelayConfigCluster.AttributeDefs.apply_delay.id,
        cluster_id=SonoffManualRainDelayConfigCluster.cluster_id,
        translation_key="manual_rain_delay_set",
        fallback_name="4.3 Rain delay set",
    )
    .write_attr_button(
        SonoffManualRainDelayConfigCluster.AttributeDefs.clear_delay.name,
        SonoffManualRainDelayConfigCluster.AttributeDefs.clear_delay.id,
        cluster_id=SonoffManualRainDelayConfigCluster.cluster_id,
        translation_key="manual_rain_delay_clear",
        fallback_name="4.4 Rain delay clear",
    )
    .adds(SonoffIrrigationPlanConfigCluster)
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.plan_index.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=0,
        max_value=5,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_plan_index",
        fallback_name="5.1 Schedule irrigation plan index",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.effective_year.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=2026,
        max_value=2099,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_plan_effective_year",
        fallback_name="5.2 Effective Year",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.effective_month.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=12,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_plan_effective_month",
        fallback_name="5.3 Effective Month",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.effective_day.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=31,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_plan_effective_day",
        fallback_name="5.4 Effective Day",
    )
    .enum(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.plan_irrigation_mode.name,
        IrrigationPlanMode,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        translation_key="schedule_irrigation_mode",
        fallback_name="5.7 Scheduled Irrigation Mode",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.plan_total_duration_min.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=SCHEDULE_IRRIGATION_TOTAL_DURATION_MIN,
        max_value=SCHEDULE_IRRIGATION_TOTAL_DURATION_MAX,
        step=SINGLE_IRRIGATION_STEP_MIN,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        mode="box",
        translation_key="schedule_irrigation_total_duration",
        fallback_name="5.8 Scheduled Irrigation Total Duration",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.plan_amount.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=SINGLE_IRRIGATION_AMOUNT_MIN,
        max_value=SINGLE_IRRIGATION_AMOUNT_MAX,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_amount",
        fallback_name="5.11 Scheduled Irrigation Capacity",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.plan_fail_safe_duration_min.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=SCHEDULE_IRRIGATION_FAIL_SAFE_MIN,
        max_value=SCHEDULE_IRRIGATION_FAIL_SAFE_MAX,
        step=SINGLE_IRRIGATION_STEP_MIN,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        mode="box",
        translation_key="schedule_irrigation_fail_safe_duration",
        fallback_name="5.12 Scheduled irrigation capacity-failsafe time",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.duration_min.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=SCHEDULE_IRRIGATION_DURATION_MIN,
        max_value=SCHEDULE_IRRIGATION_DURATION_MAX,
        step=SINGLE_IRRIGATION_STEP_MIN,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        mode="box",
        translation_key="schedule_irrigation_duration",
        fallback_name="5.9 Scheduled Irrigation Duration",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.interval_duration_min.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=SCHEDULE_IRRIGATION_INTERVAL_DURATION_MIN,
        max_value=SCHEDULE_IRRIGATION_INTERVAL_DURATION_MAX,
        step=SINGLE_IRRIGATION_STEP_MIN,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        mode="box",
        translation_key="schedule_irrigation_interval_duration",
        fallback_name="5.10 Scheduled Irrigation Interval Duration",
    )
    .enum(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.repeat_mode.name,
        IrrigationPlanRepeat,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        translation_key="schedule_irrigation_plan_repeat_mode",
        fallback_name="5.13 Scheduled Irrigation Repeat Mode",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.repeat_value.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=0,
        max_value=30,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_plan_repeat_value",
        fallback_name="5.14 Scheduled Irrigation Repeat Value",
    )
    .switch(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.weekday_monday.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="schedule_irrigation_plan_monday",
        fallback_name="5.15 Schedule-Monday",
    )
    .switch(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.weekday_tuesday.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="schedule_irrigation_plan_tuesday",
        fallback_name="5.16 Schedule-Tuesday",
    )
    .switch(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.weekday_wednesday.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="schedule_irrigation_plan_wednesday",
        fallback_name="5.17 Schedule-Wednesday",
    )
    .switch(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.weekday_thursday.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="schedule_irrigation_plan_thursday",
        fallback_name="5.18 Schedule-Thursday",
    )
    .switch(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.weekday_friday.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="schedule_irrigation_plan_friday",
        fallback_name="5.19 Schedule-Friday",
    )
    .switch(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.weekday_saturday.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="schedule_irrigation_plan_saturday",
        fallback_name="5.20 Schedule-Saturday",
    )
    .switch(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.weekday_sunday.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="schedule_irrigation_plan_sunday",
        fallback_name="5.21 Schedule-Sunday",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.start_hour.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=0,
        max_value=23,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_plan_start_hour",
        fallback_name="5.5 Effective Hour",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.start_minute.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=0,
        max_value=59,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_plan_start_minute",
        fallback_name="5.6 Effective Minute",
    )
    .write_attr_button(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.apply_plan.name,
        SonoffIrrigationPlanConfigCluster.AttributeDefs.apply_plan.id,
        cluster_id=SonoffIrrigationPlanConfigCluster.cluster_id,
        translation_key="schedule_irrigation_plan_set",
        fallback_name="5.22 Schedule Set",
    )
    .write_attr_button(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.remove_plan.name,
        SonoffIrrigationPlanConfigCluster.AttributeDefs.remove_plan.id,
        cluster_id=SonoffIrrigationPlanConfigCluster.cluster_id,
        translation_key="schedule_irrigation_plan_remove",
        fallback_name="5.23 Schedule Remove",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_january.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_january",
        fallback_name="6.1 schedule seasonal adjustment january(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_january",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_february.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_february",
        fallback_name="6.2 schedule seasonal adjustment february(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_february",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_march.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_march",
        fallback_name="6.3 schedule seasonal adjustment march(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_march",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_april.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_april",
        fallback_name="6.4 schedule seasonal adjustment april(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_april",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_may.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_may",
        fallback_name="6.5 schedule seasonal adjustment may(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_may",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_june.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_june",
        fallback_name="6.6 schedule seasonal adjustment june(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_june",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_july.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_july",
        fallback_name="6.7 schedule seasonal adjustment july(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_july",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_august.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_august",
        fallback_name="6.8 schedule seasonal adjustment august(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_august",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_september.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_september",
        fallback_name="6.9 schedule seasonal adjustment september(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_september",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_october.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_october",
        fallback_name="6.10 schedule seasonal adjustment october(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_october",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_november.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_november",
        fallback_name="6.11 schedule seasonal adjustment november(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_november",
    )
    .number(
        SonoffIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_december.name,
        SonoffIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_december",
        fallback_name="6.12 schedule seasonal adjustment december(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_december",
    )
    # 1. 漏水传感器（bit1）
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        device_class=BinarySensorDeviceClass.MOISTURE,
        attribute_converter=lambda x: x & ValveState.Water_Leakage,
        unique_id_suffix="water_leak_status",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="water_leak",
        fallback_name="Water leak",
    )
    # 2. 缺水传感器（bit0）
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        # bit0 或 bit4 任一置位都显示缺水报警，不区分通道
        attribute_converter=lambda x: (
            x & (ValveState.Water_Shortage | ValveState.Water_Shortage_Channel_2)
        ),
        unique_id_suffix="water_depletion_status",
        translation_key="Water depletion",
        fallback_name="Water depletion",
    )
    # 3. 用水时长传感器（通道1，端点1）
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.water_usage_duration.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.MINUTES,
        unique_id_suffix="water_usage_duration",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="water_usage_duration",
        fallback_name="Water usage duration",
    )
    # 4. 用水量传感器
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.water_usage_volume.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        device_class=SensorDeviceClass.VOLUME,
        state_class=SensorStateClass.TOTAL_INCREASING,  # VOLUME 类必须用 total_increasing
        unique_id_suffix="water_usage_volume",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="water_usage_volume",
        fallback_name="Water usage volume",
    )
    .add_to_registry()
)

(
    # QuirkBuilder("SONOFF", "SWV")
    QuirkBuilder("SONOFF", "SWV-ZNU")
    # .also_applies_to("SONOFF", "SWV-ZNU")
    .also_applies_to("SONOFF", "SWV-ZNE")
    .replaces(CustomSonoffCluster)
    .adds(SonoffDurationOnlySingleIrrigationConfigCluster)
    .adds(SonoffManualRainDelayConfigCluster)
    .switch(
        CustomSonoffCluster.AttributeDefs.child_lock.name,
        CustomSonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="swv_child_lock",
        fallback_name="1.1 Child lock",
    )
    .number(
        SonoffDurationOnlySingleIrrigationConfigCluster.AttributeDefs.total_duration_min.name,
        SonoffDurationOnlySingleIrrigationConfigCluster.cluster_id,
        min_value=MANUAL_IRRIGATION_DURATION_MIN,
        max_value=MANUAL_IRRIGATION_DURATION_MAX,
        step=SINGLE_IRRIGATION_STEP_MIN,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        mode="box",
        translation_key="manual_single_irrigation_total_duration",
        fallback_name="2.1 Manual irrigation duration",
    )
    .number(
        SonoffManualRainDelayConfigCluster.AttributeDefs.delay_hours.name,
        SonoffManualRainDelayConfigCluster.cluster_id,
        min_value=0,
        max_value=USER_DELAY_MAX_HOURS,
        step=1,
        mode="box",
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.HOURS,
        translation_key="manual_rain_delay_hours",
        fallback_name="3.1 Rain delay hours",
    )
    .number(
        SonoffManualRainDelayConfigCluster.AttributeDefs.timezone_offset_hours.name,
        SonoffManualRainDelayConfigCluster.cluster_id,
        min_value=-12,
        max_value=14,
        step=1,
        mode="box",
        translation_key="manual_rain_delay_timezone_offset",
        fallback_name="3.2 Rain delay timezone offset",
    )
    .write_attr_button(
        SonoffManualRainDelayConfigCluster.AttributeDefs.apply_delay.name,
        SonoffManualRainDelayConfigCluster.AttributeDefs.apply_delay.id,
        cluster_id=SonoffManualRainDelayConfigCluster.cluster_id,
        translation_key="manual_rain_delay_set",
        fallback_name="3.3 Rain delay set",
    )
    .write_attr_button(
        SonoffManualRainDelayConfigCluster.AttributeDefs.clear_delay.name,
        SonoffManualRainDelayConfigCluster.AttributeDefs.clear_delay.id,
        cluster_id=SonoffManualRainDelayConfigCluster.cluster_id,
        translation_key="manual_rain_delay_clear",
        fallback_name="3.4 Rain delay clear",
    )
    .adds(SonoffDurationOnlyIrrigationPlanConfigCluster)
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.plan_index.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=0,
        max_value=5,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_plan_index",
        fallback_name="4.1 Schedule irrigation plan index",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.effective_year.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=2000,
        max_value=2099,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_plan_effective_year",
        fallback_name="4.2 Effective Year",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.effective_month.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=12,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_plan_effective_month",
        fallback_name="4.3 Effective Month",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.effective_day.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=31,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_plan_effective_day",
        fallback_name="4.4 Effective Day",
    )
    .enum(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.plan_irrigation_mode.name,
        DurationOnlyIrrigationPlanMode,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        translation_key="schedule_irrigation_mode",
        fallback_name="4.7 Schedule Irrigation Mode",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.plan_total_duration_min.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=SCHEDULE_IRRIGATION_TOTAL_DURATION_MIN,
        max_value=SCHEDULE_IRRIGATION_TOTAL_DURATION_MAX,
        step=SINGLE_IRRIGATION_STEP_MIN,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        mode="box",
        translation_key="schedule_irrigation_total_duration",
        fallback_name="4.8 Scheduled Irrigation Total Duration",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.duration_min.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=SCHEDULE_IRRIGATION_DURATION_MIN,
        max_value=SCHEDULE_IRRIGATION_DURATION_MAX,
        step=SINGLE_IRRIGATION_STEP_MIN,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        mode="box",
        translation_key="schedule_irrigation_duration",
        fallback_name="4.9 Scheduled Irrigation Duration",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.interval_duration_min.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=SCHEDULE_IRRIGATION_INTERVAL_DURATION_MIN,
        max_value=SCHEDULE_IRRIGATION_INTERVAL_DURATION_MAX,
        step=SINGLE_IRRIGATION_STEP_MIN,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        mode="box",
        translation_key="schedule_irrigation_interval_duration",
        fallback_name="4.10 Scheduled Irrigation Interval Duration",
    )
    .enum(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.repeat_mode.name,
        IrrigationPlanRepeat,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        translation_key="schedule_irrigation_plan_repeat_mode",
        fallback_name="4.11 Schedule Repeat Mode",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.repeat_value.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=0,
        max_value=30,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_plan_repeat_value",
        fallback_name="4.12 Scheduled Irrigation Repeat Value",
    )
    .switch(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.weekday_monday.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="schedule_irrigation_plan_monday",
        fallback_name="4.13 Schedule Monday",
    )
    .switch(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.weekday_tuesday.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="schedule_irrigation_plan_tuesday",
        fallback_name="4.14 Schedule Tuesday",
    )
    .switch(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.weekday_wednesday.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="schedule_irrigation_plan_wednesday",
        fallback_name="4.15 Schedule Wednesday",
    )
    .switch(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.weekday_thursday.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="schedule_irrigation_plan_thursday",
        fallback_name="4.16 Schedule Thursday",
    )
    .switch(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.weekday_friday.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="schedule_irrigation_plan_friday",
        fallback_name="4.17 Schedule Friday",
    )
    .switch(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.weekday_saturday.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="schedule_irrigation_plan_saturday",
        fallback_name="4.18 Schedule Saturday",
    )
    .switch(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.weekday_sunday.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="schedule_irrigation_plan_sunday",
        fallback_name="4.19 Schedule Sunday",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.start_hour.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=0,
        max_value=23,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_plan_start_hour",
        fallback_name="4.5 Schedule Start Hour",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.start_minute.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=0,
        max_value=59,
        step=1,
        mode="box",
        translation_key="schedule_irrigation_plan_start_minute",
        fallback_name="4.6 Schedule Start Minute",
    )
    .write_attr_button(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.apply_plan.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.apply_plan.id,
        cluster_id=SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        translation_key="schedule_irrigation_plan_set",
        fallback_name="4.20 Schedule Set",
    )
    .write_attr_button(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.remove_plan.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.remove_plan.id,
        cluster_id=SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        translation_key="schedule_irrigation_plan_remove",
        fallback_name="4.21 Schedule Remove",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_january.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_january",
        fallback_name="5.1 Schedule Seasonal Adjustment January(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_january",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_february.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_february",
        fallback_name="5.2 Schedule Seasonal Adjustment February(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_february",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_march.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_march",
        fallback_name="5.3 Schedule Seasonal Adjustment March(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_march",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_april.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_april",
        fallback_name="5.4 Schedule Seasonal Adjustment April(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_april",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_may.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_may",
        fallback_name="5.5 Schedule Seasonal Adjustment May(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_may",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_june.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_june",
        fallback_name="5.6 Schedule Seasonal Adjustment June(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_june",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_july.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_july",
        fallback_name="5.7 Schedule Seasonal Adjustment July(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_july",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_august.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_august",
        fallback_name="5.8 Schedule Seasonal Adjustment August(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_august",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_september.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_september",
        fallback_name="5.9 Schedule Seasonal Adjustment September(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_september",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_october.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_october",
        fallback_name="5.10 Schedule Seasonal Adjustment October(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_october",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_november.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_november",
        fallback_name="5.11 Schedule Seasonal Adjustment November(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_november",
    )
    .number(
        SonoffDurationOnlyIrrigationPlanConfigCluster.AttributeDefs.seasonal_adjustment_december.name,
        SonoffDurationOnlyIrrigationPlanConfigCluster.cluster_id,
        min_value=1,
        max_value=20,
        step=1,
        mode="box",
        translation_key="schedule_seasonal_adjustment_december",
        fallback_name="5.12 Schedule Seasonal Adjustment December(value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
        unique_id_suffix="schedule_seasonal_adjustment_december",
    )
    # 1. 新增：用水时长传感器
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.water_usage_duration.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        device_class=SensorDeviceClass.DURATION,  # 时长类传感器
        state_class=SensorStateClass.MEASUREMENT,  # 关键：测量值，支持折线图
        unit=UnitOfTime.MINUTES,  # 单位：分钟
        unique_id_suffix="water_usage_duration",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="water_usage_duration",
        fallback_name="Water usage duration",
    )
    .add_to_registry()
)
