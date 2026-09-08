"""SONOFF SWV dual-channel Zigbee water valve quirk."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import UnitOfTime, UnitOfVolume
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

# Constants
SINGLE_IRRIGATION_ARRAY_ITEM_TYPE = foundation.DataTypeId.uint8
SINGLE_IRRIGATION_PAYLOAD_LEN = 12
SINGLE_IRRIGATION_DURATION_MIN_MIN = 1
SINGLE_IRRIGATION_DURATION_MAX_MIN = 719
SINGLE_IRRIGATION_STEP_MIN = 1
SINGLE_IRRIGATION_AMOUNT_MIN = 1
SINGLE_IRRIGATION_AMOUNT_MAX = 10000
SINGLE_IRRIGATION_FAIL_SAFE_MIN = 1
SINGLE_IRRIGATION_FAIL_SAFE_MAX = 719
SINGLE_IRRIGATION_DEFAULT_TOTAL_DURATION_MIN = 10
SINGLE_IRRIGATION_DEFAULT_AMOUNT = 30
SINGLE_IRRIGATION_DEFAULT_FAIL_SAFE_DURATION_MIN = 10
SINGLE_IRRIGATION_ZB_AMOUNT_UNIT_LITER = 0x00
IRRIGATION_PLAN_PAYLOAD_LEN = 28
IRRIGATION_PLAN_MAX_COUNT = 6
IRRIGATION_PLAN_SET_COMMAND_ID = 0x06
IRRIGATION_PLAN_REMOVE_COMMAND_ID = 0x07
MANUAL_RAIN_DELAY_CONTROL = 0x08
USER_DELAY_MAX_HOURS = 7 * 24
QUARTERLY_ADJUSTMENT_PAYLOAD_LEN = 12
QUARTERLY_ADJUSTMENT_DEFAULT_VALUE = 10
ZIGBEE_EPOCH_OFFSET = 946684800

# Feature switches for optional sensor entities (default OFF)
ENABLE_REALTIME_IRRIGATION_DURATION = False
ENABLE_HOUR_IRRIGATION_DURATION = False
ENABLE_HOUR_IRRIGATION_VOLUME = False
ENABLE_USER_DELAY_END_DATETIME = False


def _u16_be(data: bytes) -> int:
    """Decode an unsigned big-endian 16-bit integer."""

    return int.from_bytes(data[:2], "big")


def _put_u16_be(value: int) -> list[int]:
    """Encode an unsigned big-endian 16-bit integer."""

    return list(int(value).to_bytes(2, "big"))


def _put_u32_be(value: int) -> list[int]:
    """Encode an unsigned big-endian 32-bit integer."""

    return list(int(value).to_bytes(4, "big"))


class DelayTimestampPayload(t.FixedList):
    """Raw 4-byte big-endian delay-end Zigbee epoch timestamp."""

    _item_type = t.uint8_t
    _length = 4


# Irrigation plan payload
class IrrigationPlanPayload(t.FixedList):
    """Raw 28-byte irrigation plan payload."""

    _item_type = t.uint8_t
    _length = IRRIGATION_PLAN_PAYLOAD_LEN


class QuarterlyAdjustmentPayload(t.FixedList):
    """Raw 12-byte quarterly adjustment payload."""

    _item_type = t.uint8_t
    _length = QUARTERLY_ADJUSTMENT_PAYLOAD_LEN


class QuarterlyAdjustmentState:
    """State container for seasonal watering adjustment."""

    def __init__(self, values: list[int] | None = None):
        """Initialize with default or provided seasonal adjustment values."""
        self.values = list(
            values
            or [QUARTERLY_ADJUSTMENT_DEFAULT_VALUE] * QUARTERLY_ADJUSTMENT_PAYLOAD_LEN
        )
        if len(self.values) != QUARTERLY_ADJUSTMENT_PAYLOAD_LEN:
            raise ValueError("Quarterly adjustment state must contain 12 values")

    def to_payload(self) -> bytes:
        """Return the quarterly adjustment values as raw bytes."""
        return bytes(int(value) for value in self.values)


class SingleIrrigationPayload(t.LVList, item_type=t.uint8_t, length_type=t.uint16_t):
    """SONOFF single irrigation uint8 array payload."""

    @staticmethod
    def _coerce_value(value: Any) -> bytes | list[int] | tuple[int, ...]:
        while hasattr(value, "value") and not isinstance(
            value, (bytes, bytearray, list, tuple)
        ):
            inner_value = getattr(value, "value", None)
            if inner_value is None or inner_value is value:
                break
            value = inner_value

        if isinstance(value, (bytes, bytearray)):
            if len(value) >= 3 and value[0] == SINGLE_IRRIGATION_ARRAY_ITEM_TYPE:
                length = int.from_bytes(value[1:3], "little")
                return bytes(value[3 : 3 + length])
            return bytes(value)

        if isinstance(value, t.LVList):
            return list(value)

        if isinstance(value, (list, tuple)):
            return [int(item) for item in value]

        return value

    def __new__(cls, value=()):
        """Create a new instance, coercing the value to the expected format."""
        return super().__new__(cls, cls._coerce_value(value))

    def __init__(self, value=()):
        """Initialize with coerced value."""
        super().__init__(self._coerce_value(value))


# Single irrigation mode enum (duration, volume, duration with interval)
class SingleIrrigationMode(t.enum8):
    """Single irrigation mode."""

    Duration = 0x00
    Volume = 0x01
    Duration_With_Interval = 0x02


# Manual irrigation mode enum (duration, volume only — no interval support)
class ManualIrrigationMode(t.enum8):
    """Manual irrigation mode (duration / volume only)."""

    Duration = 0x00
    Volume = 0x01


# Amount unit enum (gallon, liter)
class IrrigationAmountUnit(t.enum8):
    """Single irrigation amount unit."""

    Liter = 0x00
    US_Gallon = 0x01
    Imperial_Gallon = 0x02


# Data class (corresponds to single irrigation array)
@dataclass
class SingleIrrigationState:
    """Decoded SONOFF single irrigation setting."""

    irrigation_mode: int = SingleIrrigationMode.Duration
    total_duration_min: int = SINGLE_IRRIGATION_DEFAULT_TOTAL_DURATION_MIN
    duration_min: int = SINGLE_IRRIGATION_DURATION_MIN_MIN
    # interval_duration_min: int = 0
    amount_unit: int = SINGLE_IRRIGATION_ZB_AMOUNT_UNIT_LITER
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


# Data class (corresponds to plan)
@dataclass
class IrrigationPlan:
    """Sonoff auto irrigation plan in the Zigbee command payload format."""

    index: int = 0  # Index
    enabled: int = 1
    enable_datetime: int = 0
    irrigation_mode: int = SingleIrrigationMode.Duration
    start_datetime: int = 0  # Start time
    total_duration_min: int = (
        SINGLE_IRRIGATION_DEFAULT_TOTAL_DURATION_MIN  # Total duration
    )
    duration_min: int = 0
    interval_duration_min: int = 0  # Interval duration
    amount_unit: int = SINGLE_IRRIGATION_ZB_AMOUNT_UNIT_LITER  # Amount unit
    amount: int = SINGLE_IRRIGATION_DEFAULT_AMOUNT  # Amount
    fail_safe_duration_min: int = SINGLE_IRRIGATION_DEFAULT_FAIL_SAFE_DURATION_MIN
    create_datetime: int = 0
    repeat_mode: int = IrrigationPlanRepeat.Custom  # Repeat mode
    repeat_value: int = 0


# Validate irrigation plan index
def _validate_irrigation_plan_index(index: int) -> None:
    """Validate that a schedule index is supported by the firmware."""

    if not 0 <= int(index) < IRRIGATION_PLAN_MAX_COUNT:
        raise ValueError("Irrigation plan index must be between 0 and 5")


# Validate schedule repeat mode
def _repeat_to_loop_info(repeat_mode: int, repeat_value: int) -> tuple[int, int]:
    """Convert simplified repeat settings to firmware loop fields."""

    repeat_mode = int(repeat_mode)
    repeat_value = int(repeat_value)
    if repeat_mode == IrrigationPlanRepeat.Odd_Day:  # Odd day cycle
        return IrrigationLoopType.Odd_Day, 0
    if repeat_mode == IrrigationPlanRepeat.Even_Day:  # Even day cycle
        return IrrigationLoopType.Even_Day, 0
    if (
        repeat_mode == IrrigationPlanRepeat.Interval
    ):  # Interval cycle, repeat_value is interval days (1..30)
        if not 1 <= repeat_value <= 30:
            raise ValueError("Irrigation plan interval must be between 1 and 30 days")
        return IrrigationLoopType.Days, repeat_value
    if (
        repeat_mode == IrrigationPlanRepeat.Custom
    ):  # Custom cycle, repeat_value is weekday mask (0..127, bit0=Sun, bit1=Mon..bit6=Sat)
        if not 0 <= repeat_value <= 0x7F:
            raise ValueError("Irrigation plan custom weekday mask must be 0..127")
        return IrrigationLoopType.Week, repeat_value
    raise ValueError("Unsupported irrigation plan repeat mode")


# Seconds elapsed since midnight
def _seconds_from_midnight(hour: int, minute: int) -> int:
    """Return elapsed seconds from midnight for the current day."""

    return int(hour) * 3600 + int(minute) * 60


# Convert YMD to Zigbee epoch timestamp (seconds)
def _zigbee_date_timestamp(year: int, month: int, day: int) -> int:
    """Return the Zigbee epoch timestamp for a date at midnight UTC."""

    return int(
        datetime(int(year), int(month), int(day), tzinfo=UTC).timestamp()
        - ZIGBEE_EPOCH_OFFSET
    )


# Return current UTC time as Zigbee epoch timestamp (seconds)
def _zigbee_now_timestamp() -> int:
    """Return the current UTC timestamp using the Zigbee epoch."""

    return int(datetime.now(tz=UTC).timestamp() - ZIGBEE_EPOCH_OFFSET)


def _local_timezone_offset_seconds() -> int:
    """Return the local runtime timezone offset in seconds."""

    offset = datetime.now().astimezone().utcoffset()
    if offset is None:
        return 0
    return int(offset.total_seconds())


# Convert Zigbee epoch timestamp to year/month/day tuple
def _zigbee_timestamp_to_ymd(value: int) -> tuple[int, int, int]:
    """Convert a Zigbee epoch timestamp to year/month/day."""

    dt = datetime.fromtimestamp(int(value) + ZIGBEE_EPOCH_OFFSET, tz=UTC)
    return dt.year, dt.month, dt.day


# Encode irrigation plan payload to Zigbee protocol byte format
def encode_irrigation_plan_payload(plan: IrrigationPlan) -> bytes:
    """Encode a Zigbee auto irrigation plan command payload."""

    _validate_irrigation_plan_index(plan.index)  # Validate plan index
    loop_type, loop_option = _repeat_to_loop_info(
        plan.repeat_mode, plan.repeat_value
    )  # Validate schedule repeat mode

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


def single_irrigation_array_from_payload(
    payload: bytes | list[int],
) -> SingleIrrigationPayload:
    """Wrap a single irrigation payload in a ZCL array value."""

    return SingleIrrigationPayload(payload)


def single_irrigation_array_from_payload_test(
    payload: bytes | list[int],
) -> foundation.Array:
    """Wrap a single irrigation payload in a ZCL array value."""

    return foundation.Array(
        type=SINGLE_IRRIGATION_ARRAY_ITEM_TYPE,
        value=t.LVList[t.uint8_t, t.uint16_t](payload),
    )


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


# Unpack ZCL array to single irrigation payload
def single_irrigation_payload_from_array(value: Any) -> bytes:
    """Extract the single irrigation payload bytes from a decoded ZCL array."""

    if isinstance(value, foundation.Array):
        if value.value is None:
            raise ValueError("Single irrigation payload is empty")
        if isinstance(value.value, (bytes, bytearray)):
            return single_irrigation_payload_from_array(value.value)
        return bytes(int(item) for item in value.value)
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


# Decode Sonoff irrigation data
def decode_single_irrigation_payload(
    payload: bytes | list[int] | foundation.Array,
) -> SingleIrrigationState:
    """Decode the SONOFF single irrigation aggregate payload."""

    data = single_irrigation_payload_from_array(payload)
    if len(data) < SINGLE_IRRIGATION_PAYLOAD_LEN:
        raise ValueError("Single irrigation payload is too short")

    return SingleIrrigationState(
        irrigation_mode=data[0],
        total_duration_min=_u16_be(data[1:3]),
        # duration_min=_u16_be(data[3:5]),
        # interval_duration_min=_u16_be(data[5:7]),
        amount_unit=data[7],
        amount=_u16_be(data[8:10]),
        fail_safe_duration_min=_u16_be(data[10:12]),
    )


# Encode irrigation state object to byte payload
def encode_single_irrigation_payload(state: SingleIrrigationState) -> bytes:
    """Encode the SONOFF single irrigation aggregate payload."""

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
        int(state.amount_unit),
        *_put_u16_be(amount),
        *_put_u16_be(fail_safe_duration_min),
    ]
    return bytes(payload)


# Valve abnormal state bitmap
class ValveState(t.enum8):
    """Water valve abnormal state bitmap."""

    # Basic states (single bit)
    Normal = 0  # 000 (no abnormal state)
    Water_Shortage = 1 << 0  # 001 (bit0: water shortage)
    Water_Leakage = 1 << 1  # 010 (bit1: water leakage)
    Anti_Frost_Alarm = 1 << 2  # 100 (bit2: anti-frost alarm)
    Water_Shortage_Channel_2 = 1 << 4  # bit4: channel 2 water shortage
    # Combined states (multi-bit)
    Water_Shortage_And_Leakage = Water_Shortage | Water_Leakage
    Water_Shortage_And_Frost = Water_Shortage | Anti_Frost_Alarm
    Water_Leakage_And_Frost = Water_Leakage | Anti_Frost_Alarm
    All_Alarms = Water_Shortage | Water_Leakage | Anti_Frost_Alarm


class SonoffWaterValveCluster(CustomCluster):
    """SONOFF private cluster for SWV water valves."""

    cluster_id = 0xFC11
    ep_attribute = "sonoff_cluster"

    class ServerCommandDefs(foundation.BaseCommandDefs):
        """SONOFF private server command definitions."""

        # Irrigation plan set command
        irrigation_plan_set = foundation.ZCLCommandDef(
            id=IRRIGATION_PLAN_SET_COMMAND_ID,
            schema={"payload": IrrigationPlanPayload},
            is_manufacturer_specific=False,
        )
        # Irrigation plan remove command
        irrigation_plan_remove = foundation.ZCLCommandDef(
            id=IRRIGATION_PLAN_REMOVE_COMMAND_ID,
            schema={"index": t.uint8_t},
            is_manufacturer_specific=False,
        )
        # User delay set command (rain delay) — 4-byte big-endian Zigbee epoch
        user_delay_set = foundation.ZCLCommandDef(
            id=MANUAL_RAIN_DELAY_CONTROL,
            schema={"delay_end_timestamp": DelayTimestampPayload},
            is_manufacturer_specific=False,
        )

    class AttributeDefs(BaseAttributeDefs):
        """SONOFF private attribute definitions."""

        # Child lock state attribute definition
        child_lock = ZCLAttributeDef(
            id=0x0000,
            type=t.Bool,
            manufacturer_code=None,
        )
        # Realtime irrigation duration attribute definition
        realtime_irrigation_duration = ZCLAttributeDef(
            id=0x5006,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        # Realtime irrigation volume attribute definition
        realtime_irrigation_volume = ZCLAttributeDef(
            id=0x5007,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        # Valve abnormal state attribute definition
        valve_abnormal_state = ZCLAttributeDef(
            id=0x500C,
            type=ValveState,
            manufacturer_code=None,
        )
        # Daily irrigation volume attribute definition
        daily_irrigation_volume = ZCLAttributeDef(
            id=0x500F,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        # User delay end datetime attribute definition
        user_delay_end_datetime = ZCLAttributeDef(
            id=0x5014,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        # Weather delay duration attribute definition
        weather_delay_duration = ZCLAttributeDef(
            id=0x5019,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        # Daily irrigation duration attribute definition
        daily_irrigation_duration = ZCLAttributeDef(
            id=0x501A,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        # Hourly irrigation volume attribute definition
        hour_irrigation_volume = ZCLAttributeDef(
            id=0x501B,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        # Hourly irrigation duration attribute definition
        hour_irrigation_duration = ZCLAttributeDef(
            id=0x501C,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        # Single irrigation setting attribute definition
        single_irrigation_set = ZCLAttributeDef(
            id=0x501D,
            type=SingleIrrigationPayload,
            manufacturer_code=None,
        )
        # Seasonal adjustment attribute definition
        quarterly_adjustment = ZCLAttributeDef(
            id=0x501E,
            type=foundation.Array,
            manufacturer_code=None,
        )
        # Water flow unit attribute definition
        unit_of_water_flow = ZCLAttributeDef(
            id=0x5021,
            type=t.uint8_t,
            manufacturer_code=None,
        )

    def __init__(self, *args, **kwargs):
        """Initialize and listen for single irrigation aggregate changes."""

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
        self.on_event(AttributeReadEvent.event_type, self._handle_user_delay_change)
        self.on_event(AttributeReportedEvent.event_type, self._handle_user_delay_change)
        self.on_event(AttributeUpdatedEvent.event_type, self._handle_user_delay_change)
        self.on_event(AttributeWrittenEvent.event_type, self._handle_user_delay_change)

    # Handle single irrigation attribute changes
    def _handle_single_irrigation_change(
        self,
        event: AttributeReadEvent
        | AttributeReportedEvent
        | AttributeUpdatedEvent
        | AttributeWrittenEvent,
    ) -> None:
        """Sync decoded single irrigation state to the local config cluster."""

        if isinstance(event, AttributeWrittenEvent) and event.status != Status.SUCCESS:
            return

        if event.attribute_id == self.AttributeDefs.unit_of_water_flow.id:
            # Sync amount unit to the standalone global cluster (endpoint 1)
            target = self.endpoint
            if not hasattr(target, "sonoff_amount_unit_config"):
                target = self.endpoint.device.endpoints.get(1)
            if target is not None and hasattr(target, "sonoff_amount_unit_config"):
                target.sonoff_amount_unit_config.update_amount_unit(int(event.value))
            return

        if event.attribute_id != self.AttributeDefs.single_irrigation_set.id:
            return

        values = [event.value]
        if isinstance(event, AttributeReadEvent) and event.raw_value is not event.value:
            values.append(event.raw_value)

        for value in values:
            try:
                self._single_irrigation_state = decode_single_irrigation_payload(
                    value
                )  # Parse single irrigation setting attribute value
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

        if hasattr(self.endpoint, "sonoff_seasonal_adjustment_config"):
            self.endpoint.sonoff_seasonal_adjustment_config.update_quarterly_adjustment(
                self._quarterly_adjustment.values
            )

    def _handle_user_delay_change(
        self,
        event: AttributeReadEvent
        | AttributeReportedEvent
        | AttributeUpdatedEvent
        | AttributeWrittenEvent,
    ) -> None:
        """Sync user delay end datetime (0x5014) to the local delay config cluster."""

        if isinstance(event, AttributeWrittenEvent) and event.status != Status.SUCCESS:
            return
        if event.attribute_id != self.AttributeDefs.user_delay_end_datetime.id:
            return

        values = [event.value]
        if isinstance(event, AttributeReadEvent) and event.raw_value is not event.value:
            values.append(event.raw_value)

        for value in values:
            try:
                timestamp = int(value)
                if hasattr(self.endpoint, "sonoff_user_delay_config"):
                    self.endpoint.sonoff_user_delay_config.update_delay_end_timestamp(
                        timestamp
                    )
                break
            except (TypeError, ValueError):
                continue

    async def apply_custom_configuration(self, *args, **kwargs):
        """Read single irrigation configuration during pairing."""

        await self.read_attributes(
            [
                self.AttributeDefs.unit_of_water_flow.id,
                self.AttributeDefs.user_delay_end_datetime.id,
            ]
        )


# ****************************** Amount unit (global) start *****************************************************


class SonoffAmountUnitConfigCluster(LocalDataCluster):
    """Global cluster for irrigation amount unit, shared by manual irrigation and schedules."""

    cluster_id = 0xFBF9
    ep_attribute = "sonoff_amount_unit_config"

    class AttributeDefs(BaseAttributeDefs):
        """Amount unit attribute."""

        amount_unit: Final = ZCLAttributeDef(id=0x0070, type=IrrigationAmountUnit)

    def __init__(self, *args, **kwargs):
        """Initialize with default unit and sync from device."""
        super().__init__(*args, **kwargs)
        self._amount_unit = IrrigationAmountUnit.Liter
        self._update_attribute(self.AttributeDefs.amount_unit.id, self._amount_unit)

    def update_amount_unit(self, unit: int) -> None:
        """Update local amount unit from the real 0x5021 attribute."""
        self._amount_unit = int(unit)
        self._update_attribute(self.AttributeDefs.amount_unit.id, self._amount_unit)

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list:
        """When user changes the amount unit, write 0x5021 to the device."""
        result = None
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if attr_id == self.AttributeDefs.amount_unit.id:
                self._amount_unit = int(value)
                self._update_attribute(attr_id, self._amount_unit)
                # Write 0x5021 to the real SONOFF private cluster on endpoint 1
                result = await self.endpoint.sonoff_cluster.write_attributes_raw(
                    [
                        foundation.Attribute(
                            attrid=SonoffWaterValveCluster.AttributeDefs.unit_of_water_flow.id,
                            value=foundation.TypeValue(
                                type=foundation.DataTypeId.uint8,
                                value=t.uint8_t(self._amount_unit),
                            ),
                        )
                    ]
                )

        if result is not None:
            return result
        return [[foundation.WriteAttributesStatusRecord(status=Status.SUCCESS)]]


# ****************************** Manual irrigation entities start *****************************************************


class SonoffSingleIrrigationConfigCluster(LocalDataCluster):
    """Local cluster exposing pieces of the aggregate single irrigation setting."""

    cluster_id = 0xFBFE
    ep_attribute = "sonoff_single_irrigation_config"

    class AttributeDefs(BaseAttributeDefs):
        """Local single irrigation configuration attributes."""

        irrigation_mode: Final = ZCLAttributeDef(id=0x0010, type=SingleIrrigationMode)
        total_duration_min: Final = ZCLAttributeDef(id=0x0011, type=t.uint16_t)
        amount: Final = ZCLAttributeDef(id=0x0013, type=t.uint16_t)
        fail_safe_duration_min: Final = ZCLAttributeDef(id=0x0014, type=t.uint16_t)

    def __init__(self, *args, **kwargs):
        """Initialize with conservative single irrigation defaults."""

        super().__init__(*args, **kwargs)
        self._single_irrigation_state = SingleIrrigationState()
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
            self.AttributeDefs.amount.id,
            self._single_irrigation_state.amount,
        )
        self._update_attribute(
            self.AttributeDefs.fail_safe_duration_min.id,
            self._single_irrigation_state.fail_safe_duration_min,
        )

    # Called by parser when device reports, updates entities for HA
    def update_single_irrigation_state(self, state: SingleIrrigationState) -> None:
        """Update local attributes from decoded single irrigation state."""

        self._single_irrigation_state = SingleIrrigationState(
            irrigation_mode=state.irrigation_mode,
            total_duration_min=state.total_duration_min,
            amount_unit=state.amount_unit,
            amount=self._single_irrigation_state.amount,
            fail_safe_duration_min=self._single_irrigation_state.fail_safe_duration_min,
        )
        # Sync amount unit to the standalone global cluster
        if hasattr(self.endpoint, "sonoff_amount_unit_config"):
            self.endpoint.sonoff_amount_unit_config.update_amount_unit(
                int(state.amount_unit)
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
            self.AttributeDefs.amount.id: self._single_irrigation_state.amount,
            self.AttributeDefs.fail_safe_duration_min.id: self._single_irrigation_state.fail_safe_duration_min,
        }
        for attr_id, value in updates.items():
            self._update_attribute(attr_id, value)

    # Update amount unit (delegate to global amount unit cluster)
    def update_amount_unit(self, unit: int) -> None:
        """Delegate to the global amount unit cluster."""
        if hasattr(self.endpoint, "sonoff_amount_unit_config"):
            self.endpoint.sonoff_amount_unit_config.update_amount_unit(unit)

    # Write manual irrigation attributes to zigbee
    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list:
        """Merge local config writes into the real aggregate attribute."""

        # Read amount_unit from the shared global cluster
        global_unit = IrrigationAmountUnit.Liter
        if hasattr(self.endpoint, "sonoff_amount_unit_config"):
            global_unit = int(self.endpoint.sonoff_amount_unit_config._amount_unit)

        state = SingleIrrigationState(
            irrigation_mode=self._single_irrigation_state.irrigation_mode,
            total_duration_min=self._single_irrigation_state.total_duration_min,
            amount_unit=global_unit,
            amount=self._single_irrigation_state.amount,
            fail_safe_duration_min=self._single_irrigation_state.fail_safe_duration_min,
        )

        # Determine the final mode after this write (mode change may be in the same batch)
        final_mode = state.irrigation_mode
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            if attr_def.id == self.AttributeDefs.irrigation_mode.id:
                final_mode = int(value)

        for attr in attributes:
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if final_mode == SingleIrrigationMode.Duration and attr_id in (
                self.AttributeDefs.amount.id,
                self.AttributeDefs.fail_safe_duration_min.id,
            ):
                raise ValueError(
                    "Single irrigation amount and fail safe duration are only "
                    "configurable in volume mode"
                )
            if (
                final_mode == SingleIrrigationMode.Volume
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
                state.total_duration_min = int(value)
            elif attr_id == self.AttributeDefs.amount.id:
                state.amount = int(value)
            elif attr_id == self.AttributeDefs.fail_safe_duration_min.id:
                state.fail_safe_duration_min = int(value)

        attr_ids = {self.find_attribute(attr).id for attr in attributes}
        config_result = None

        if attr_ids.intersection(
            {
                self.AttributeDefs.irrigation_mode.id,
                self.AttributeDefs.total_duration_min.id,
                self.AttributeDefs.amount.id,
                self.AttributeDefs.fail_safe_duration_min.id,
            }
        ):
            payload = encode_single_irrigation_payload(state)
            zcl_array = single_irrigation_array_from_payload_test(payload)
            raw_result = await self.endpoint.sonoff_cluster.write_attributes_raw(
                [
                    foundation.Attribute(
                        attrid=SonoffWaterValveCluster.AttributeDefs.single_irrigation_set.id,
                        value=foundation.TypeValue(
                            type=foundation.DataTypeId.array,
                            value=zcl_array,
                        ),
                    )
                ]
            )
            config_result = raw_result

        # Only update local state on successful write, otherwise keep original to stay consistent with device
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
            return [[foundation.WriteAttributesStatusRecord(status=Status.SUCCESS)]]
        else:
            # Write failed — return failure for all attempted attrs
            return [
                [
                    foundation.WriteAttributesStatusRecord(
                        status=Status.FAILURE,
                        attrid=self.find_attribute(attr).id,
                    )
                    for attr, value in attributes.items()
                ]
            ]

    @staticmethod
    def _write_succeeded(result: list) -> bool:
        """Return whether a Zigpy write_attributes response succeeded."""

        try:
            records = result[0]
        except (IndexError, TypeError):
            return False

        # zigpy may return either:
        # 1) WriteAttributesResponse (iterable of status records)
        # 2) list[WriteAttributesStatusRecord]
        # 3) list[list[WriteAttributesStatusRecord]]
        # Normalize to an iterable of status records.
        if hasattr(records, "status"):
            records = result
        elif hasattr(records, "status_records"):
            records = records.status_records

        try:
            return all(
                getattr(record, "status", None) == Status.SUCCESS for record in records
            )
        except TypeError:
            return False


# ****************************** Schedule plan start *****************************************************
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
        irrigation_mode: Final = ZCLAttributeDef(id=0x0032, type=SingleIrrigationMode)
        total_duration_min: Final = ZCLAttributeDef(id=0x0033, type=t.uint16_t)
        amount: Final = ZCLAttributeDef(id=0x0034, type=t.uint16_t)
        fail_safe_duration_min: Final = ZCLAttributeDef(id=0x0035, type=t.uint16_t)
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
        duration_min: Final = ZCLAttributeDef(id=0x0036, type=t.uint16_t)
        interval_duration_min: Final = ZCLAttributeDef(id=0x0037, type=t.uint16_t)

    # Initialize attribute values
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
        self._weekday_mask = 0
        self._start_hour = 8
        self._start_minute = 0
        self._irrigation_mode = SingleIrrigationMode.Duration
        self._total_duration_min = SINGLE_IRRIGATION_DEFAULT_TOTAL_DURATION_MIN
        self._duration_min = 0
        self._interval_duration_min = 0
        self._amount = SINGLE_IRRIGATION_DEFAULT_AMOUNT
        self._fail_safe_duration_min = SINGLE_IRRIGATION_DEFAULT_FAIL_SAFE_DURATION_MIN
        self._update_all_attributes()
        self._ui_date_year, self._ui_date_month, self._ui_date_day = (
            now.year,
            now.month,
            now.day,
        )

    # Sync local irrigation plan data to entity attributes
    def _update_all_attributes(self) -> None:
        """Mirror the local plan into entity attributes."""
        updates = {
            self.AttributeDefs.plan_index.id: self._plan_index,
            self.AttributeDefs.effective_year.id: self._effective_year,
            self.AttributeDefs.effective_month.id: self._effective_month,
            self.AttributeDefs.effective_day.id: self._effective_day,
            self.AttributeDefs.repeat_mode.id: self._repeat_mode,
            self.AttributeDefs.repeat_value.id: self._repeat_value,
            self.AttributeDefs.irrigation_mode.id: self._irrigation_mode,
            self.AttributeDefs.total_duration_min.id: self._total_duration_min,
            self.AttributeDefs.duration_min.id: self._duration_min,
            self.AttributeDefs.interval_duration_min.id: self._interval_duration_min,
            self.AttributeDefs.amount.id: self._amount,
            self.AttributeDefs.fail_safe_duration_min.id: self._fail_safe_duration_min,
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
            self.AttributeDefs.weekday_sunday.id: int(bool(self._weekday_mask & 0x01)),
            self.AttributeDefs.start_hour.id: self._start_hour,
            self.AttributeDefs.start_minute.id: self._start_minute,
        }
        for attr_id, value in updates.items():
            self._update_attribute(attr_id, value)

    # Build irrigation plan (used when creating schedule, not needed for removal)
    def _plan_from_current_config(self) -> IrrigationPlan:
        """Build a firmware plan from simple schedule fields and irrigation config."""
        _validate_irrigation_plan_index(self._plan_index)
        # Enable date
        enable_datetime = _zigbee_date_timestamp(
            self._effective_year, self._effective_month, self._effective_day
        )
        # Start time
        start_datetime = _seconds_from_midnight(self._start_hour, self._start_minute)

        # Repeat strategy
        repeat_value = self._repeat_value
        if self._repeat_mode == IrrigationPlanRepeat.Custom:
            repeat_value = self._weekday_mask

        # Get unit from global amount unit cluster
        amount_unit = IrrigationAmountUnit.Liter
        if hasattr(self.endpoint, "sonoff_amount_unit_config"):
            amount_unit = int(self.endpoint.sonoff_amount_unit_config._amount_unit)

        # Zero-out fields not applicable in the current irrigation mode
        plan_total_duration = self._total_duration_min
        plan_duration = self._duration_min
        plan_interval_duration = self._interval_duration_min
        plan_amount = self._amount
        plan_fail_safe = self._fail_safe_duration_min
        if self._irrigation_mode == SingleIrrigationMode.Volume:
            plan_total_duration = 0
            plan_duration = 0
            plan_interval_duration = 0
        elif self._irrigation_mode in (
            SingleIrrigationMode.Duration,
            SingleIrrigationMode.Duration_With_Interval,
        ):
            plan_amount = 0
            plan_fail_safe = 0
            if self._irrigation_mode == SingleIrrigationMode.Duration:
                plan_duration = 0
                plan_interval_duration = 0

        return IrrigationPlan(
            index=self._plan_index,
            enabled=1,
            enable_datetime=enable_datetime,
            irrigation_mode=self._irrigation_mode,
            start_datetime=start_datetime,
            total_duration_min=plan_total_duration,
            duration_min=plan_duration,
            interval_duration_min=plan_interval_duration,
            amount_unit=amount_unit,
            amount=plan_amount,
            fail_safe_duration_min=plan_fail_safe,
            create_datetime=_zigbee_now_timestamp(),
            repeat_mode=self._repeat_mode,
            repeat_value=repeat_value,
        )

    # HA entity modifications are cached locally; only sent to Zigbee device when apply/remove button is clicked
    async def write_attributes(  # noqa: C901
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list:
        """Update local plan fields or trigger set/remove actions."""
        # Determine the final mode after this write (mode change may be in the same batch)
        pending_mode = self._irrigation_mode
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            if attr_def.id == self.AttributeDefs.irrigation_mode.id:
                pending_mode = int(value)

        for attr in attributes:
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if pending_mode in (
                SingleIrrigationMode.Duration,
                SingleIrrigationMode.Duration_With_Interval,
            ) and attr_id in (
                self.AttributeDefs.amount.id,
                self.AttributeDefs.fail_safe_duration_min.id,
            ):
                raise ValueError(
                    "Irrigation amount and fail safe duration are only "
                    "configurable in volume mode"
                )
            if (
                pending_mode == SingleIrrigationMode.Volume
                and attr_id == self.AttributeDefs.total_duration_min.id
            ):
                raise ValueError(
                    "Irrigation total duration is only configurable in duration mode"
                )
            if (
                pending_mode != SingleIrrigationMode.Duration_With_Interval
                and attr_id
                in (
                    self.AttributeDefs.duration_min.id,
                    self.AttributeDefs.interval_duration_min.id,
                )
            ):
                raise ValueError(
                    "Duration and interval duration are only configurable "
                    "in duration-with-interval mode"
                )

        result = []
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
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
            elif attr_id == self.AttributeDefs.irrigation_mode.id:
                self._irrigation_mode = int(value)
            elif attr_id == self.AttributeDefs.total_duration_min.id:
                self._total_duration_min = int(value)
            elif attr_id == self.AttributeDefs.duration_min.id:
                self._duration_min = int(value)
            elif attr_id == self.AttributeDefs.interval_duration_min.id:
                self._interval_duration_min = int(value)
            elif attr_id == self.AttributeDefs.amount.id:
                self._amount = int(value)
            elif attr_id == self.AttributeDefs.fail_safe_duration_min.id:
                self._fail_safe_duration_min = int(value)
            elif attr_id == self.AttributeDefs.weekday_monday.id:
                self._weekday_mask = (self._weekday_mask & ~0x02) | (
                    int(bool(value)) << 1
                )
            elif attr_id == self.AttributeDefs.weekday_tuesday.id:
                self._weekday_mask = (self._weekday_mask & ~0x04) | (
                    int(bool(value)) << 2
                )
            elif attr_id == self.AttributeDefs.weekday_wednesday.id:
                self._weekday_mask = (self._weekday_mask & ~0x08) | (
                    int(bool(value)) << 3
                )
            elif attr_id == self.AttributeDefs.weekday_thursday.id:
                self._weekday_mask = (self._weekday_mask & ~0x10) | (
                    int(bool(value)) << 4
                )
            elif attr_id == self.AttributeDefs.weekday_friday.id:
                self._weekday_mask = (self._weekday_mask & ~0x20) | (
                    int(bool(value)) << 5
                )
            elif attr_id == self.AttributeDefs.weekday_saturday.id:
                self._weekday_mask = (self._weekday_mask & ~0x40) | (
                    int(bool(value)) << 6
                )
            elif attr_id == self.AttributeDefs.weekday_sunday.id:
                self._weekday_mask = (self._weekday_mask & ~0x01) | int(bool(value))
            elif attr_id == self.AttributeDefs.start_hour.id:
                self._start_hour = int(value)
            elif attr_id == self.AttributeDefs.start_minute.id:
                self._start_minute = int(value)
            elif attr_id == self.AttributeDefs.apply_plan.id:  # Set plan
                plan = self._plan_from_current_config()
                payload = encode_irrigation_plan_payload(plan)
                # Wrap payload in ZCL command and send to Zigbee device
                result = await self.endpoint.sonoff_cluster.command(
                    IRRIGATION_PLAN_SET_COMMAND_ID,
                    payload=IrrigationPlanPayload(payload),
                    manufacturer=None,
                    expect_reply=False,
                )
            elif attr_id == self.AttributeDefs.remove_plan.id:  # Remove plan
                _validate_irrigation_plan_index(self._plan_index)
                # Wrap payload in ZCL command and send to Zigbee device
                result = await self.endpoint.sonoff_cluster.command(
                    IRRIGATION_PLAN_REMOVE_COMMAND_ID,
                    index=t.uint8_t(self._plan_index),
                    manufacturer=None,
                    expect_reply=False,
                )

        # Validate duration/interval constraints in Duration_With_Interval mode
        if pending_mode == SingleIrrigationMode.Duration_With_Interval:
            final_total = self._total_duration_min
            final_duration = self._duration_min
            final_interval = self._interval_duration_min
            for attr, value in attributes.items():
                attr_def = self.find_attribute(attr)
                if attr_def.id == self.AttributeDefs.total_duration_min.id:
                    final_total = int(value)
                elif attr_def.id == self.AttributeDefs.duration_min.id:
                    final_duration = int(value)
                elif attr_def.id == self.AttributeDefs.interval_duration_min.id:
                    final_interval = int(value)
            if final_duration > final_total:
                raise ValueError(
                    f"Duration ({final_duration} min) must not exceed "
                    f"total duration ({final_total} min)"
                )
            if final_interval > final_total:
                raise ValueError(
                    f"Interval duration ({final_interval} min) must not exceed "
                    f"total duration ({final_total} min)"
                )
            if final_duration + final_interval > final_total:
                raise ValueError(
                    f"Duration ({final_duration} min) + interval duration "
                    f"({final_interval} min) must not exceed "
                    f"total duration ({final_total} min)"
                )

        self._update_all_attributes()
        if result:
            return result
        return [[foundation.WriteAttributesStatusRecord(status=Status.SUCCESS)]]


# ****************************** Channel 2 schedule plan start *****************************************************
class SonoffIrrigationPlanConfigClusterCh2(LocalDataCluster):
    """Local cluster for channel 2 auto irrigation plan configuration entities.

    Fully independent from the channel 1 cluster.  Registered on endpoint 2
    via ``adds(..., endpoint_id=2)`` so that zigpy automatically binds it to
    the correct endpoint, and ``self.endpoint.sonoff_cluster.command(...)``
    naturally reaches the firmware channel-2 handler.
    """

    cluster_id = 0xFBFB
    ep_attribute = "sonoff_irrigation_plan_config_ch2"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions (shifted IDs vs channel 1)."""

        plan_index: Final = ZCLAttributeDef(id=0x0040, type=t.uint8_t)
        effective_year: Final = ZCLAttributeDef(id=0x0041, type=t.uint16_t)
        effective_month: Final = ZCLAttributeDef(id=0x0042, type=t.uint8_t)
        effective_day: Final = ZCLAttributeDef(id=0x0043, type=t.uint8_t)
        repeat_mode: Final = ZCLAttributeDef(id=0x0044, type=IrrigationPlanRepeat)
        repeat_value: Final = ZCLAttributeDef(id=0x0045, type=t.uint8_t)
        irrigation_mode: Final = ZCLAttributeDef(id=0x0052, type=SingleIrrigationMode)
        total_duration_min: Final = ZCLAttributeDef(id=0x0053, type=t.uint16_t)
        amount: Final = ZCLAttributeDef(id=0x0054, type=t.uint16_t)
        fail_safe_duration_min: Final = ZCLAttributeDef(id=0x0055, type=t.uint16_t)
        weekday_monday: Final = ZCLAttributeDef(id=0x0047, type=t.uint8_t)
        weekday_tuesday: Final = ZCLAttributeDef(id=0x0048, type=t.uint8_t)
        weekday_wednesday: Final = ZCLAttributeDef(id=0x0049, type=t.uint8_t)
        weekday_thursday: Final = ZCLAttributeDef(id=0x004A, type=t.uint8_t)
        weekday_friday: Final = ZCLAttributeDef(id=0x004B, type=t.uint8_t)
        weekday_saturday: Final = ZCLAttributeDef(id=0x004C, type=t.uint8_t)
        weekday_sunday: Final = ZCLAttributeDef(id=0x004D, type=t.uint8_t)
        start_hour: Final = ZCLAttributeDef(id=0x004E, type=t.uint8_t)
        start_minute: Final = ZCLAttributeDef(id=0x004F, type=t.uint8_t)
        apply_plan: Final = ZCLAttributeDef(id=0x0050, type=t.uint8_t)
        remove_plan: Final = ZCLAttributeDef(id=0x0051, type=t.uint8_t)
        duration_min: Final = ZCLAttributeDef(id=0x0056, type=t.uint16_t)
        interval_duration_min: Final = ZCLAttributeDef(id=0x0057, type=t.uint16_t)

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
        self._weekday_mask = 0
        self._start_hour = 8
        self._start_minute = 0
        self._irrigation_mode = SingleIrrigationMode.Duration
        self._total_duration_min = SINGLE_IRRIGATION_DEFAULT_TOTAL_DURATION_MIN
        self._duration_min = 0
        self._interval_duration_min = 0
        self._amount = SINGLE_IRRIGATION_DEFAULT_AMOUNT
        self._fail_safe_duration_min = SINGLE_IRRIGATION_DEFAULT_FAIL_SAFE_DURATION_MIN
        self._update_all_attributes()

    def _update_all_attributes(self) -> None:
        """Mirror the local plan into entity attributes."""
        updates = {
            self.AttributeDefs.plan_index.id: self._plan_index,
            self.AttributeDefs.effective_year.id: self._effective_year,
            self.AttributeDefs.effective_month.id: self._effective_month,
            self.AttributeDefs.effective_day.id: self._effective_day,
            self.AttributeDefs.repeat_mode.id: self._repeat_mode,
            self.AttributeDefs.repeat_value.id: self._repeat_value,
            self.AttributeDefs.irrigation_mode.id: self._irrigation_mode,
            self.AttributeDefs.total_duration_min.id: self._total_duration_min,
            self.AttributeDefs.duration_min.id: self._duration_min,
            self.AttributeDefs.interval_duration_min.id: self._interval_duration_min,
            self.AttributeDefs.amount.id: self._amount,
            self.AttributeDefs.fail_safe_duration_min.id: self._fail_safe_duration_min,
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
            self.AttributeDefs.weekday_sunday.id: int(bool(self._weekday_mask & 0x01)),
            self.AttributeDefs.start_hour.id: self._start_hour,
            self.AttributeDefs.start_minute.id: self._start_minute,
        }
        for attr_id, value in updates.items():
            self._update_attribute(attr_id, value)

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

        # Get unit from global amount unit cluster (endpoint 1)
        amount_unit = IrrigationAmountUnit.Liter
        endpoint_1 = self.endpoint.device.endpoints.get(1)
        if endpoint_1 is not None and hasattr(endpoint_1, "sonoff_amount_unit_config"):
            amount_unit = int(endpoint_1.sonoff_amount_unit_config._amount_unit)

        # Zero-out fields not applicable in the current irrigation mode
        plan_total_duration = self._total_duration_min
        plan_duration = self._duration_min
        plan_interval_duration = self._interval_duration_min
        plan_amount = self._amount
        plan_fail_safe = self._fail_safe_duration_min
        if self._irrigation_mode == SingleIrrigationMode.Volume:
            plan_total_duration = 0
            plan_duration = 0
            plan_interval_duration = 0
        elif self._irrigation_mode in (
            SingleIrrigationMode.Duration,
            SingleIrrigationMode.Duration_With_Interval,
        ):
            plan_amount = 0
            plan_fail_safe = 0
            if self._irrigation_mode == SingleIrrigationMode.Duration:
                plan_duration = 0
                plan_interval_duration = 0

        return IrrigationPlan(
            index=self._plan_index,
            enabled=1,
            enable_datetime=enable_datetime,
            irrigation_mode=self._irrigation_mode,
            start_datetime=start_datetime,
            total_duration_min=plan_total_duration,
            duration_min=plan_duration,
            interval_duration_min=plan_interval_duration,
            amount_unit=amount_unit,
            amount=plan_amount,
            fail_safe_duration_min=plan_fail_safe,
            create_datetime=_zigbee_now_timestamp(),
            repeat_mode=self._repeat_mode,
            repeat_value=repeat_value,
        )

    async def write_attributes(  # noqa: C901
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list:
        """Update local plan fields or trigger set/remove actions (channel 2)."""
        # Determine the final mode after this write (mode change may be in the same batch)
        pending_mode = self._irrigation_mode
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            if attr_def.id == self.AttributeDefs.irrigation_mode.id:
                pending_mode = int(value)

        for attr in attributes:
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if pending_mode in (
                SingleIrrigationMode.Duration,
                SingleIrrigationMode.Duration_With_Interval,
            ) and attr_id in (
                self.AttributeDefs.amount.id,
                self.AttributeDefs.fail_safe_duration_min.id,
            ):
                raise ValueError(
                    "Irrigation amount and fail safe duration are only "
                    "configurable in volume mode"
                )
            if (
                pending_mode == SingleIrrigationMode.Volume
                and attr_id == self.AttributeDefs.total_duration_min.id
            ):
                raise ValueError(
                    "Irrigation total duration is only configurable in duration mode"
                )
            if (
                pending_mode != SingleIrrigationMode.Duration_With_Interval
                and attr_id
                in (
                    self.AttributeDefs.duration_min.id,
                    self.AttributeDefs.interval_duration_min.id,
                )
            ):
                raise ValueError(
                    "Duration and interval duration are only configurable "
                    "in duration-with-interval mode"
                )

        result = []
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
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
            elif attr_id == self.AttributeDefs.irrigation_mode.id:
                self._irrigation_mode = int(value)
            elif attr_id == self.AttributeDefs.total_duration_min.id:
                self._total_duration_min = int(value)
            elif attr_id == self.AttributeDefs.duration_min.id:
                self._duration_min = int(value)
            elif attr_id == self.AttributeDefs.interval_duration_min.id:
                self._interval_duration_min = int(value)
            elif attr_id == self.AttributeDefs.amount.id:
                self._amount = int(value)
            elif attr_id == self.AttributeDefs.fail_safe_duration_min.id:
                self._fail_safe_duration_min = int(value)
            elif attr_id == self.AttributeDefs.weekday_monday.id:
                self._weekday_mask = (self._weekday_mask & ~0x02) | (
                    int(bool(value)) << 1
                )
            elif attr_id == self.AttributeDefs.weekday_tuesday.id:
                self._weekday_mask = (self._weekday_mask & ~0x04) | (
                    int(bool(value)) << 2
                )
            elif attr_id == self.AttributeDefs.weekday_wednesday.id:
                self._weekday_mask = (self._weekday_mask & ~0x08) | (
                    int(bool(value)) << 3
                )
            elif attr_id == self.AttributeDefs.weekday_thursday.id:
                self._weekday_mask = (self._weekday_mask & ~0x10) | (
                    int(bool(value)) << 4
                )
            elif attr_id == self.AttributeDefs.weekday_friday.id:
                self._weekday_mask = (self._weekday_mask & ~0x20) | (
                    int(bool(value)) << 5
                )
            elif attr_id == self.AttributeDefs.weekday_saturday.id:
                self._weekday_mask = (self._weekday_mask & ~0x40) | (
                    int(bool(value)) << 6
                )
            elif attr_id == self.AttributeDefs.weekday_sunday.id:
                self._weekday_mask = (self._weekday_mask & ~0x01) | int(bool(value))
            elif attr_id == self.AttributeDefs.start_hour.id:
                self._start_hour = int(value)
            elif attr_id == self.AttributeDefs.start_minute.id:
                self._start_minute = int(value)
            elif attr_id == self.AttributeDefs.apply_plan.id:
                plan = self._plan_from_current_config()
                payload = encode_irrigation_plan_payload(plan)
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

        # Validate duration/interval constraints in Duration_With_Interval mode
        if pending_mode == SingleIrrigationMode.Duration_With_Interval:
            final_total = self._total_duration_min
            final_duration = self._duration_min
            final_interval = self._interval_duration_min
            for attr, value in attributes.items():
                attr_def = self.find_attribute(attr)
                if attr_def.id == self.AttributeDefs.total_duration_min.id:
                    final_total = int(value)
                elif attr_def.id == self.AttributeDefs.duration_min.id:
                    final_duration = int(value)
                elif attr_def.id == self.AttributeDefs.interval_duration_min.id:
                    final_interval = int(value)
            if final_duration > final_total:
                raise ValueError(
                    f"Duration ({final_duration} min) must not exceed "
                    f"total duration ({final_total} min)"
                )
            if final_interval > final_total:
                raise ValueError(
                    f"Interval duration ({final_interval} min) must not exceed "
                    f"total duration ({final_total} min)"
                )
            if final_duration + final_interval > final_total:
                raise ValueError(
                    f"Duration ({final_duration} min) + interval duration "
                    f"({final_interval} min) must not exceed "
                    f"total duration ({final_total} min)"
                )

        self._update_all_attributes()
        if result:
            return result
        return [[foundation.WriteAttributesStatusRecord(status=Status.SUCCESS)]]


# ****************************** User delay (rain delay) start *****************************************************


class SonoffUserDelayConfigCluster(LocalDataCluster):
    """Local cluster for manual rain / user delay configuration.

    Sends command 0x08 on the SONOFF private cluster (0xFC11) which triggers
    ``rtcScheduleIrrigationTaskSkip()`` in the firmware — marking all irrigation
    tasks whose start_time falls between now and the delay end timestamp as
    skipped.  A value of 0 clears the delay.
    """

    cluster_id = 0xFBFC
    ep_attribute = "sonoff_user_delay_config"

    class AttributeDefs(BaseAttributeDefs):
        """Local user-delay configuration attributes."""

        delay_hours: Final = ZCLAttributeDef(id=0x0060, type=t.uint8_t)
        timezone_offset_hours: Final = ZCLAttributeDef(id=0x0063, type=t.int8s)
        apply_delay: Final = ZCLAttributeDef(id=0x0061, type=t.uint8_t)
        clear_delay: Final = ZCLAttributeDef(id=0x0062, type=t.uint8_t)
        delay_end_timestamp: Final = ZCLAttributeDef(id=0x0064, type=t.uint32_t)

    def __init__(self, *args, **kwargs):
        """Initialise with sensible defaults and listen for firmware reports."""
        super().__init__(*args, **kwargs)
        self._delay_hours: int = 24
        self._timezone_offset_hours: int = int(_local_timezone_offset_seconds() / 3600)
        self._delay_end_timestamp: int = 0  # Zigbee epoch, 0 = no active delay
        self._update_attribute(self.AttributeDefs.delay_hours.id, self._delay_hours)
        self._update_attribute(
            self.AttributeDefs.timezone_offset_hours.id,
            self._timezone_offset_hours,
        )
        self._update_attribute(
            self.AttributeDefs.delay_end_timestamp.id,
            self._delay_end_timestamp,
        )

    def update_delay_end_timestamp(self, timestamp: int) -> None:
        """Update local delay end timestamp from device 0x5014 attribute report."""
        self._delay_end_timestamp = int(timestamp)
        self._update_attribute(
            self.AttributeDefs.delay_end_timestamp.id, self._delay_end_timestamp
        )

    async def _send_user_delay_timestamp(self, end_timestamp: int) -> Any:
        """Send the firmware user delay command payload."""

        return await self.endpoint.sonoff_cluster.command(
            MANUAL_RAIN_DELAY_CONTROL,
            delay_end_timestamp=DelayTimestampPayload(_put_u32_be(end_timestamp)),
            manufacturer=None,
            expect_reply=False,
        )

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **_kwargs: Any,
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
                # Send 0 to clear the delay — firmware treats this as
                # "no tasks in range" which clears all is_delay flags.
                result = await self._send_user_delay_timestamp(0)

        self._update_attribute(self.AttributeDefs.delay_hours.id, self._delay_hours)
        self._update_attribute(
            self.AttributeDefs.timezone_offset_hours.id,
            self._timezone_offset_hours,
        )
        if result:
            return result
        return [[foundation.WriteAttributesStatusRecord(status=Status.SUCCESS)]]


# ****************************** Seasonal adjustment (global) start *****************************************************


class SonoffSeasonalAdjustmentConfigCluster(LocalDataCluster):
    """Local cluster for seasonal (monthly) watering adjustment — global, shared by all channels."""

    cluster_id = 0xFAFE
    ep_attribute = "sonoff_seasonal_adjustment_config"

    class AttributeDefs(BaseAttributeDefs):
        """Monthly seasonal adjustment attributes."""

        seasonal_adjustment_january: Final = ZCLAttributeDef(id=0x0080, type=t.uint8_t)
        seasonal_adjustment_february: Final = ZCLAttributeDef(id=0x0081, type=t.uint8_t)
        seasonal_adjustment_march: Final = ZCLAttributeDef(id=0x0082, type=t.uint8_t)
        seasonal_adjustment_april: Final = ZCLAttributeDef(id=0x0083, type=t.uint8_t)
        seasonal_adjustment_may: Final = ZCLAttributeDef(id=0x0084, type=t.uint8_t)
        seasonal_adjustment_june: Final = ZCLAttributeDef(id=0x0085, type=t.uint8_t)
        seasonal_adjustment_july: Final = ZCLAttributeDef(id=0x0086, type=t.uint8_t)
        seasonal_adjustment_august: Final = ZCLAttributeDef(id=0x0087, type=t.uint8_t)
        seasonal_adjustment_september: Final = ZCLAttributeDef(
            id=0x0088, type=t.uint8_t
        )
        seasonal_adjustment_october: Final = ZCLAttributeDef(id=0x0089, type=t.uint8_t)
        seasonal_adjustment_november: Final = ZCLAttributeDef(id=0x008A, type=t.uint8_t)
        seasonal_adjustment_december: Final = ZCLAttributeDef(id=0x008B, type=t.uint8_t)

    def __init__(self, *args, **kwargs):
        """Initialize with default quarterly adjustment values."""
        super().__init__(*args, **kwargs)
        self._quarterly_adjustment = QuarterlyAdjustmentState()
        self._update_all_attributes()

    def _monthly_attr_defs(self) -> tuple[ZCLAttributeDef, ...]:
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
        """Mirror the local quarterly adjustment state into entity attributes."""
        for attr_def, value in zip(
            self._monthly_attr_defs(),
            self._quarterly_adjustment.values,
            strict=False,
        ):
            self._update_attribute(attr_def.id, value)

    def update_quarterly_adjustment(self, values: list[int]) -> None:
        """Update local monthly seasonal adjustment state from device report."""
        self._quarterly_adjustment = QuarterlyAdjustmentState(values)
        self._update_all_attributes()

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list:
        """Write a single month's adjustment value, merging into the full 12-byte array."""
        values = list(self._quarterly_adjustment.values)
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            for index, month_def in enumerate(self._monthly_attr_defs()):
                if attr_def.id == month_def.id:
                    values[index] = int(value)
                    break
        self._quarterly_adjustment = QuarterlyAdjustmentState(values)
        result = await self.endpoint.sonoff_cluster.write_attributes(
            {
                SonoffWaterValveCluster.AttributeDefs.quarterly_adjustment.id: quarterly_adjustment_array_from_payload(
                    self._quarterly_adjustment.to_payload()
                )
            }
        )
        self._update_all_attributes()
        if result:
            return result
        return [[foundation.WriteAttributesStatusRecord(status=Status.SUCCESS)]]


# ****************************** Amount unit entity (global) start *****************************************************


def add_amount_unit_config_entity(builder: QuirkBuilder) -> QuirkBuilder:
    """Add the global amount unit config entity, shared by manual and schedules."""

    return builder.adds(SonoffAmountUnitConfigCluster).enum(
        SonoffAmountUnitConfigCluster.AttributeDefs.amount_unit.name,
        IrrigationAmountUnit,
        SonoffAmountUnitConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="irrigation_amount_unit",
        fallback_name="2.1 Capacity Units",
    )


# ****************************** Seasonal adjustment entities start *****************************************************


def add_seasonal_adjustment_entities(builder: QuirkBuilder) -> QuirkBuilder:
    """Add seasonal (monthly) watering adjustment config entities — global, shared by all channels."""

    return (
        builder.adds(SonoffSeasonalAdjustmentConfigCluster)
        .number(
            SonoffSeasonalAdjustmentConfigCluster.AttributeDefs.seasonal_adjustment_january.name,
            SonoffSeasonalAdjustmentConfigCluster.cluster_id,
            min_value=1,
            max_value=20,
            step=1,
            mode="box",
            translation_key="schedule_seasonal_adjustment_january",
            fallback_name="7.1 Schedule seasonal adjustment january (value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
            unique_id_suffix="schedule_seasonal_adjustment_january",
        )
        .number(
            SonoffSeasonalAdjustmentConfigCluster.AttributeDefs.seasonal_adjustment_february.name,
            SonoffSeasonalAdjustmentConfigCluster.cluster_id,
            min_value=1,
            max_value=20,
            step=1,
            mode="box",
            translation_key="schedule_seasonal_adjustment_february",
            fallback_name="7.2 Schedule seasonal adjustment february (value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
            unique_id_suffix="schedule_seasonal_adjustment_february",
        )
        .number(
            SonoffSeasonalAdjustmentConfigCluster.AttributeDefs.seasonal_adjustment_march.name,
            SonoffSeasonalAdjustmentConfigCluster.cluster_id,
            min_value=1,
            max_value=20,
            step=1,
            mode="box",
            translation_key="schedule_seasonal_adjustment_march",
            fallback_name="7.3 Schedule seasonal adjustment march (value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
            unique_id_suffix="schedule_seasonal_adjustment_march",
        )
        .number(
            SonoffSeasonalAdjustmentConfigCluster.AttributeDefs.seasonal_adjustment_april.name,
            SonoffSeasonalAdjustmentConfigCluster.cluster_id,
            min_value=1,
            max_value=20,
            step=1,
            mode="box",
            translation_key="schedule_seasonal_adjustment_april",
            fallback_name="7.4 Schedule seasonal adjustment april (value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
            unique_id_suffix="schedule_seasonal_adjustment_april",
        )
        .number(
            SonoffSeasonalAdjustmentConfigCluster.AttributeDefs.seasonal_adjustment_may.name,
            SonoffSeasonalAdjustmentConfigCluster.cluster_id,
            min_value=1,
            max_value=20,
            step=1,
            mode="box",
            translation_key="schedule_seasonal_adjustment_may",
            fallback_name="7.5 Schedule seasonal adjustment may (value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
            unique_id_suffix="schedule_seasonal_adjustment_may",
        )
        .number(
            SonoffSeasonalAdjustmentConfigCluster.AttributeDefs.seasonal_adjustment_june.name,
            SonoffSeasonalAdjustmentConfigCluster.cluster_id,
            min_value=1,
            max_value=20,
            step=1,
            mode="box",
            translation_key="schedule_seasonal_adjustment_june",
            fallback_name="7.6 Schedule seasonal adjustment june (value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
            unique_id_suffix="schedule_seasonal_adjustment_june",
        )
        .number(
            SonoffSeasonalAdjustmentConfigCluster.AttributeDefs.seasonal_adjustment_july.name,
            SonoffSeasonalAdjustmentConfigCluster.cluster_id,
            min_value=1,
            max_value=20,
            step=1,
            mode="box",
            translation_key="schedule_seasonal_adjustment_july",
            fallback_name="7.7 Schedule seasonal adjustment july (value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
            unique_id_suffix="schedule_seasonal_adjustment_july",
        )
        .number(
            SonoffSeasonalAdjustmentConfigCluster.AttributeDefs.seasonal_adjustment_august.name,
            SonoffSeasonalAdjustmentConfigCluster.cluster_id,
            min_value=1,
            max_value=20,
            step=1,
            mode="box",
            translation_key="schedule_seasonal_adjustment_august",
            fallback_name="7.8 Schedule seasonal adjustment august (value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
            unique_id_suffix="schedule_seasonal_adjustment_august",
        )
        .number(
            SonoffSeasonalAdjustmentConfigCluster.AttributeDefs.seasonal_adjustment_september.name,
            SonoffSeasonalAdjustmentConfigCluster.cluster_id,
            min_value=1,
            max_value=20,
            step=1,
            mode="box",
            translation_key="schedule_seasonal_adjustment_september",
            fallback_name="7.9 Schedule seasonal adjustment september (value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
            unique_id_suffix="schedule_seasonal_adjustment_september",
        )
        .number(
            SonoffSeasonalAdjustmentConfigCluster.AttributeDefs.seasonal_adjustment_october.name,
            SonoffSeasonalAdjustmentConfigCluster.cluster_id,
            min_value=1,
            max_value=20,
            step=1,
            mode="box",
            translation_key="schedule_seasonal_adjustment_october",
            fallback_name="7.10 Schedule seasonal adjustment october (value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
            unique_id_suffix="schedule_seasonal_adjustment_october",
        )
        .number(
            SonoffSeasonalAdjustmentConfigCluster.AttributeDefs.seasonal_adjustment_november.name,
            SonoffSeasonalAdjustmentConfigCluster.cluster_id,
            min_value=1,
            max_value=20,
            step=1,
            mode="box",
            translation_key="schedule_seasonal_adjustment_november",
            fallback_name="7.11 Schedule seasonal adjustment november (value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
            unique_id_suffix="schedule_seasonal_adjustment_november",
        )
        .number(
            SonoffSeasonalAdjustmentConfigCluster.AttributeDefs.seasonal_adjustment_december.name,
            SonoffSeasonalAdjustmentConfigCluster.cluster_id,
            min_value=1,
            max_value=20,
            step=1,
            mode="box",
            translation_key="schedule_seasonal_adjustment_december",
            fallback_name="7.12 Schedule seasonal adjustment december (value is 10x actual watering multiplier: 1 means 0.1x, 13 means 1.3x)",
            unique_id_suffix="schedule_seasonal_adjustment_december",
        )
    )


# ****************************** Manual irrigation entities start *****************************************************
# Split aggregate array into individual entities so HA can display decoded values
def add_single_irrigation_config_entities(builder: QuirkBuilder) -> QuirkBuilder:
    """Add config entities for the aggregate single irrigation attribute 0x501D."""

    return (
        builder.adds(SonoffSingleIrrigationConfigCluster)
        .enum(
            SonoffSingleIrrigationConfigCluster.AttributeDefs.irrigation_mode.name,
            ManualIrrigationMode,
            SonoffSingleIrrigationConfigCluster.cluster_id,
            entity_type=EntityType.CONFIG,
            translation_key="manual_single_irrigation_mode",
            fallback_name="3.1 Manual irrigation mode",
        )
        .number(
            SonoffSingleIrrigationConfigCluster.AttributeDefs.total_duration_min.name,
            SonoffSingleIrrigationConfigCluster.cluster_id,
            min_value=SINGLE_IRRIGATION_DURATION_MIN_MIN,
            max_value=SINGLE_IRRIGATION_DURATION_MAX_MIN,
            step=SINGLE_IRRIGATION_STEP_MIN,
            # entity_type=EntityType.CONFIG,
            device_class=NumberDeviceClass.DURATION,
            unit=UnitOfTime.MINUTES,
            mode="box",
            translation_key="manual_single_irrigation_total_duration",
            fallback_name="3.2 Manual irrigation duration",
        )
        # .number(
        #     SonoffSingleIrrigationConfigCluster.AttributeDefs.duration_min.name,
        #     SonoffSingleIrrigationConfigCluster.cluster_id,
        #     min_value=SINGLE_IRRIGATION_DURATION_MIN_MIN,
        #     max_value=SINGLE_IRRIGATION_DURATION_MAX_MIN,
        #     step=SINGLE_IRRIGATION_STEP_MIN,
        #     entity_type=EntityType.CONFIG,
        #     device_class=NumberDeviceClass.DURATION,
        #     unit=UnitOfTime.MINUTES,
        #     translation_key="single_irrigation_duration",
        #     fallback_name="Single irrigation duration",
        # )
        # .number(
        #     SonoffSingleIrrigationConfigCluster.AttributeDefs.interval_duration_min.name,
        #     SonoffSingleIrrigationConfigCluster.cluster_id,
        #     min_value=SINGLE_IRRIGATION_DURATION_MIN_MIN,
        #     max_value=SINGLE_IRRIGATION_DURATION_MAX_MIN,
        #     step=SINGLE_IRRIGATION_STEP_MIN,
        #     entity_type=EntityType.CONFIG,
        #     device_class=NumberDeviceClass.DURATION,
        #     unit=UnitOfTime.MINUTES,
        #     translation_key="single_irrigation_interval_duration",
        #     fallback_name="Single irrigation interval duration",
        # )
        # .enum(
        #     SonoffSingleIrrigationConfigCluster.AttributeDefs.amount_unit.name,
        #     IrrigationAmountUnit,
        #     SonoffSingleIrrigationConfigCluster.cluster_id,
        #     entity_type=EntityType.CONFIG,
        #     translation_key="single_irrigation_amount_unit",
        #     fallback_name="Single irrigation amount unit",
        # )
        .number(
            SonoffSingleIrrigationConfigCluster.AttributeDefs.amount.name,
            SonoffSingleIrrigationConfigCluster.cluster_id,
            min_value=SINGLE_IRRIGATION_AMOUNT_MIN,
            max_value=SINGLE_IRRIGATION_AMOUNT_MAX,
            step=1,
            mode="box",
            # entity_type=EntityType.CONFIG,
            translation_key="manual_single_irrigation_amount",
            fallback_name="3.3 Manual irrigation capacity",
        )
        .number(
            SonoffSingleIrrigationConfigCluster.AttributeDefs.fail_safe_duration_min.name,
            SonoffSingleIrrigationConfigCluster.cluster_id,
            min_value=SINGLE_IRRIGATION_FAIL_SAFE_MIN,
            max_value=SINGLE_IRRIGATION_FAIL_SAFE_MAX,
            step=SINGLE_IRRIGATION_STEP_MIN,
            # entity_type=EntityType.CONFIG,
            device_class=NumberDeviceClass.DURATION,
            unit=UnitOfTime.MINUTES,
            mode="box",
            translation_key="manual_single_irrigation_fail_safe_duration",
            fallback_name="3.4 Manual irrigation capacity-failsafe time",
        )
    )


# Channel 1 schedule entities
def add_irrigation_plan_config_entities(builder: QuirkBuilder) -> QuirkBuilder:
    """Add config entities for channel 1 irrigation plan attribute."""

    return (
        builder.adds(SonoffIrrigationPlanConfigCluster)
        .number(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.plan_index.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            min_value=0,
            max_value=5,
            step=1,
            mode="box",
            translation_key="schedule_ch1_irrigation_plan_index",
            fallback_name="5.1 CH1 Schedule irrigation plan index",
        )
        .number(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.effective_year.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            min_value=2000,
            max_value=2099,
            step=1,
            mode="box",
            translation_key="schedule_ch1_irrigation_plan_effective_year",
            fallback_name="5.2 CH1 Effective Year",
        )
        .number(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.effective_month.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            min_value=1,
            max_value=12,
            step=1,
            mode="box",
            translation_key="schedule_ch1_irrigation_plan_effective_month",
            fallback_name="5.3 CH1 Effective Month",
        )
        .number(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.effective_day.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            min_value=1,
            max_value=31,
            step=1,
            mode="box",
            translation_key="schedule_ch1_irrigation_plan_effective_day",
            fallback_name="5.4 CH1 Effective Day",
        )
        # Start time: hour
        .number(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.start_hour.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            min_value=0,
            max_value=23,
            step=1,
            mode="box",
            translation_key="schedule_ch1_irrigation_plan_start_hour",
            fallback_name="5.5 CH1 Effective Hour",
        )
        # Start time: minute
        .number(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.start_minute.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            min_value=0,
            max_value=59,
            step=1,
            mode="box",
            translation_key="schedule_ch1_irrigation_plan_start_minute",
            fallback_name="5.6 CH1 Effective Minute",
        )
        .enum(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.irrigation_mode.name,
            SingleIrrigationMode,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            translation_key="schedule_ch1_irrigation_mode",
            fallback_name="5.7 CH1 Schedule Irrigation Mode",
            unique_id_suffix="schedule_ch1_irrigation_mode",
        )
        .number(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.total_duration_min.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            min_value=SINGLE_IRRIGATION_DURATION_MIN_MIN,
            max_value=SINGLE_IRRIGATION_DURATION_MAX_MIN,
            step=SINGLE_IRRIGATION_STEP_MIN,
            device_class=NumberDeviceClass.DURATION,
            unit=UnitOfTime.MINUTES,
            mode="box",
            translation_key="schedule_ch1_total_duration",
            fallback_name="5.8 CH1 Scheduled Irrigation Total Duration",
            unique_id_suffix="schedule_ch1_total_duration",
        )
        .number(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.duration_min.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            min_value=SINGLE_IRRIGATION_DURATION_MIN_MIN,
            max_value=SINGLE_IRRIGATION_DURATION_MAX_MIN,
            step=SINGLE_IRRIGATION_STEP_MIN,
            device_class=NumberDeviceClass.DURATION,
            unit=UnitOfTime.MINUTES,
            mode="box",
            translation_key="schedule_ch1_irrigation_duration",
            fallback_name="5.9 CH1 Scheduled Irrigation Duration",
            unique_id_suffix="schedule_ch1_irrigation_duration",
        )
        .number(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.interval_duration_min.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            min_value=SINGLE_IRRIGATION_DURATION_MIN_MIN,
            max_value=SINGLE_IRRIGATION_DURATION_MAX_MIN,
            step=SINGLE_IRRIGATION_STEP_MIN,
            device_class=NumberDeviceClass.DURATION,
            unit=UnitOfTime.MINUTES,
            mode="box",
            translation_key="schedule_ch1_irrigation_interval_duration",
            fallback_name="5.10 CH1 Scheduled Irrigation Interval Duration",
            unique_id_suffix="schedule_ch1_irrigation_interval_duration",
        )
        .number(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.amount.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            min_value=SINGLE_IRRIGATION_AMOUNT_MIN,
            max_value=SINGLE_IRRIGATION_AMOUNT_MAX,
            step=1,
            mode="box",
            translation_key="schedule_ch1_amount",
            fallback_name="5.11 CH1 Scheduled Irrigation Capacity",
            unique_id_suffix="schedule_ch1_amount",
        )
        .number(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.fail_safe_duration_min.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            min_value=SINGLE_IRRIGATION_FAIL_SAFE_MIN,
            max_value=SINGLE_IRRIGATION_FAIL_SAFE_MAX,
            step=SINGLE_IRRIGATION_STEP_MIN,
            device_class=NumberDeviceClass.DURATION,
            unit=UnitOfTime.MINUTES,
            mode="box",
            translation_key="schedule_ch1_fail_safe_duration",
            fallback_name="5.12 CH1 Schedule irrigation capacity-failsafe time",
            unique_id_suffix="schedule_ch1_fail_safe_duration",
        )
        # Repeat mode
        .enum(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.repeat_mode.name,
            IrrigationPlanRepeat,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            translation_key="schedule_ch1_irrigation_plan_repeat_mode",
            fallback_name="5.13 CH1 Scheduled Irrigation Repeat Mode",
        )
        .number(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.repeat_value.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            min_value=0,
            max_value=30,
            step=1,
            mode="box",
            translation_key="schedule_ch1_irrigation_plan_repeat_value",
            fallback_name="5.14 CH1 Scheduled Irrigation Repeat Value",
        )
        .switch(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.weekday_monday.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            off_value=0,
            on_value=1,
            translation_key="schedule_ch1_irrigation_plan_monday",
            fallback_name="5.15 CH1 Schedule-Monday",
        )
        .switch(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.weekday_tuesday.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            off_value=0,
            on_value=1,
            translation_key="schedule_ch1_irrigation_plan_tuesday",
            fallback_name="5.16 CH1 Schedule-Tuesday",
        )
        .switch(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.weekday_wednesday.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            off_value=0,
            on_value=1,
            translation_key="schedule_ch1_irrigation_plan_wednesday",
            fallback_name="5.17 CH1 Schedule-Wednesday",
        )
        .switch(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.weekday_thursday.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            off_value=0,
            on_value=1,
            translation_key="schedule_ch1_irrigation_plan_thursday",
            fallback_name="5.18 CH1 Schedule-Thursday",
        )
        .switch(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.weekday_friday.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            off_value=0,
            on_value=1,
            translation_key="schedule_ch1_irrigation_plan_friday",
            fallback_name="5.19 CH1 Schedule-Friday",
        )
        .switch(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.weekday_saturday.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            off_value=0,
            on_value=1,
            translation_key="schedule_ch1_irrigation_plan_saturday",
            fallback_name="5.20 CH1 Schedule-Saturday",
        )
        .switch(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.weekday_sunday.name,
            SonoffIrrigationPlanConfigCluster.cluster_id,
            off_value=0,
            on_value=1,
            translation_key="schedule_ch1_irrigation_plan_sunday",
            fallback_name="5.21 CH1 Schedule-Sunday",
        )
        .write_attr_button(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.apply_plan.name,
            SonoffIrrigationPlanConfigCluster.AttributeDefs.apply_plan.id,
            cluster_id=SonoffIrrigationPlanConfigCluster.cluster_id,
            translation_key="schedule_ch1_irrigation_plan_set",
            fallback_name="5.22 CH1 Schedule Set",
        )
        .write_attr_button(
            SonoffIrrigationPlanConfigCluster.AttributeDefs.remove_plan.name,
            SonoffIrrigationPlanConfigCluster.AttributeDefs.remove_plan.id,
            cluster_id=SonoffIrrigationPlanConfigCluster.cluster_id,
            translation_key="schedule_ch1_irrigation_plan_remove",
            fallback_name="5.23 CH1 Schedule Remove",
        )
    )


# Channel 2 schedule entities
def add_irrigation_plan_config_entities_ch2(builder: QuirkBuilder) -> QuirkBuilder:
    """Add config entities for channel 2 irrigation plan attribute."""

    return (
        builder.adds(SonoffIrrigationPlanConfigClusterCh2, endpoint_id=2)
        .number(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.plan_index.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            min_value=0,
            max_value=5,
            step=1,
            mode="box",
            translation_key="schedule_ch2_irrigation_plan_index",
            fallback_name="6.1 CH2 Schedule irrigation plan index",
        )
        .number(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.effective_year.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            min_value=2000,
            max_value=2099,
            step=1,
            mode="box",
            translation_key="schedule_ch2_irrigation_plan_effective_year",
            fallback_name="6.2 CH2 Effective Year",
        )
        .number(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.effective_month.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            min_value=1,
            max_value=12,
            step=1,
            mode="box",
            translation_key="schedule_ch2_irrigation_plan_effective_month",
            fallback_name="6.3 CH2 Effective Month",
        )
        .number(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.effective_day.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            min_value=1,
            max_value=31,
            step=1,
            mode="box",
            translation_key="schedule_ch2_irrigation_plan_effective_day",
            fallback_name="6.4 CH2 Effective Day",
        )
        # Start time: hour
        .number(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.start_hour.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            min_value=0,
            max_value=23,
            step=1,
            mode="box",
            translation_key="schedule_ch2_irrigation_plan_start_hour",
            fallback_name="6.5 CH2 Effective Hour",
        )
        # Start time: minute
        .number(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.start_minute.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            min_value=0,
            max_value=59,
            step=1,
            mode="box",
            translation_key="schedule_ch2_irrigation_plan_start_minute",
            fallback_name="6.6 CH2 Effective Minute",
        )
        .enum(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.irrigation_mode.name,
            SingleIrrigationMode,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            translation_key="schedule_ch2_irrigation_mode",
            fallback_name="6.7 CH2 Schedule Irrigation Mode",
        )
        .number(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.total_duration_min.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            min_value=SINGLE_IRRIGATION_DURATION_MIN_MIN,
            max_value=SINGLE_IRRIGATION_DURATION_MAX_MIN,
            step=SINGLE_IRRIGATION_STEP_MIN,
            device_class=NumberDeviceClass.DURATION,
            unit=UnitOfTime.MINUTES,
            mode="box",
            translation_key="schedule_ch2_total_duration",
            fallback_name="6.8 CH2 Scheduled Irrigation Total Duration",
        )
        .number(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.duration_min.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            min_value=SINGLE_IRRIGATION_DURATION_MIN_MIN,
            max_value=SINGLE_IRRIGATION_DURATION_MAX_MIN,
            step=SINGLE_IRRIGATION_STEP_MIN,
            device_class=NumberDeviceClass.DURATION,
            unit=UnitOfTime.MINUTES,
            mode="box",
            translation_key="schedule_ch2_irrigation_duration",
            fallback_name="6.9 CH2 Scheduled Irrigation Duration",
        )
        .number(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.interval_duration_min.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            min_value=SINGLE_IRRIGATION_DURATION_MIN_MIN,
            max_value=SINGLE_IRRIGATION_DURATION_MAX_MIN,
            step=SINGLE_IRRIGATION_STEP_MIN,
            device_class=NumberDeviceClass.DURATION,
            unit=UnitOfTime.MINUTES,
            mode="box",
            translation_key="schedule_ch2_irrigation_interval_duration",
            fallback_name="6.10 CH2 Scheduled Irrigation Interval Duration",
        )
        .number(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.amount.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            min_value=SINGLE_IRRIGATION_AMOUNT_MIN,
            max_value=SINGLE_IRRIGATION_AMOUNT_MAX,
            step=1,
            mode="box",
            translation_key="schedule_ch2_amount",
            fallback_name="6.11 CH2 Scheduled Irrigation Capacity",
        )
        .number(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.fail_safe_duration_min.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            min_value=SINGLE_IRRIGATION_FAIL_SAFE_MIN,
            max_value=SINGLE_IRRIGATION_FAIL_SAFE_MAX,
            step=SINGLE_IRRIGATION_STEP_MIN,
            device_class=NumberDeviceClass.DURATION,
            unit=UnitOfTime.MINUTES,
            mode="box",
            translation_key="schedule_ch2_fail_safe_duration",
            fallback_name="6.12 CH2 Schedule irrigation capacity-failsafe time",
        )
        # Repeat mode
        .enum(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.repeat_mode.name,
            IrrigationPlanRepeat,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            translation_key="schedule_ch2_irrigation_plan_repeat_mode",
            fallback_name="6.13 CH2 Scheduled Irrigation Repeat Mode",
        )
        .number(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.repeat_value.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            min_value=0,
            max_value=30,
            step=1,
            mode="box",
            translation_key="schedule_ch2_irrigation_plan_repeat_value",
            fallback_name="6.14 CH2 Scheduled Irrigation Repeat Value",
        )
        .switch(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.weekday_monday.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            off_value=0,
            on_value=1,
            translation_key="schedule_ch2_irrigation_plan_monday",
            fallback_name="6.15 CH2 Schedule-Monday",
        )
        .switch(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.weekday_tuesday.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            off_value=0,
            on_value=1,
            translation_key="schedule_ch2_irrigation_plan_tuesday",
            fallback_name="6.16 CH2 Schedule-Tuesday",
        )
        .switch(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.weekday_wednesday.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            off_value=0,
            on_value=1,
            translation_key="schedule_ch2_irrigation_plan_wednesday",
            fallback_name="6.17 CH2 Schedule-Wednesday",
        )
        .switch(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.weekday_thursday.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            off_value=0,
            on_value=1,
            translation_key="schedule_ch2_irrigation_plan_thursday",
            fallback_name="6.18 CH2 Schedule-Thursday",
        )
        .switch(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.weekday_friday.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            off_value=0,
            on_value=1,
            translation_key="schedule_ch2_irrigation_plan_friday",
            fallback_name="6.19 CH2 Schedule-Friday",
        )
        .switch(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.weekday_saturday.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            off_value=0,
            on_value=1,
            translation_key="schedule_ch2_irrigation_plan_saturday",
            fallback_name="6.20 CH2 Schedule-Saturday",
        )
        .switch(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.weekday_sunday.name,
            SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            endpoint_id=2,
            off_value=0,
            on_value=1,
            translation_key="schedule_ch2_irrigation_plan_sunday",
            fallback_name="6.21 CH2 Schedule-Sunday",
        )
        .write_attr_button(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.apply_plan.name,
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.apply_plan.id,
            endpoint_id=2,
            cluster_id=SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            translation_key="schedule_ch2_irrigation_plan_set",
            fallback_name="6.22 CH2 Schedule Set",
        )
        .write_attr_button(
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.remove_plan.name,
            SonoffIrrigationPlanConfigClusterCh2.AttributeDefs.remove_plan.id,
            endpoint_id=2,
            cluster_id=SonoffIrrigationPlanConfigClusterCh2.cluster_id,
            translation_key="schedule_ch2_irrigation_plan_remove",
            fallback_name="6.23 CH2 Schedule Remove",
        )
    )


# Add user delay (rain delay) entities
def add_user_delay_config_entities(builder: QuirkBuilder) -> QuirkBuilder:
    """Add config entities for manual rain / user delay."""

    return (
        builder.adds(SonoffUserDelayConfigCluster)
        .number(
            SonoffUserDelayConfigCluster.AttributeDefs.timezone_offset_hours.name,
            SonoffUserDelayConfigCluster.cluster_id,
            min_value=-12,
            max_value=14,
            step=1,
            mode="box",
            translation_key="manual_user_delay_timezone_offset",
            fallback_name="4.2 Rain delay timezone offset",
        )
        .number(
            SonoffUserDelayConfigCluster.AttributeDefs.delay_hours.name,
            SonoffUserDelayConfigCluster.cluster_id,
            min_value=0,
            max_value=168,
            step=1,
            mode="box",
            device_class=NumberDeviceClass.DURATION,
            unit=UnitOfTime.HOURS,
            translation_key="manual_user_delay_hours",
            fallback_name="4.1 Rain delay hours",
        )
        .write_attr_button(
            SonoffUserDelayConfigCluster.AttributeDefs.apply_delay.name,
            SonoffUserDelayConfigCluster.AttributeDefs.apply_delay.id,
            cluster_id=SonoffUserDelayConfigCluster.cluster_id,
            translation_key="manual_user_delay_apply",
            fallback_name="4.3 Rain delay set",
        )
        .write_attr_button(
            SonoffUserDelayConfigCluster.AttributeDefs.clear_delay.name,
            SonoffUserDelayConfigCluster.AttributeDefs.clear_delay.id,
            cluster_id=SonoffUserDelayConfigCluster.cluster_id,
            translation_key="manual_user_delay_clear",
            fallback_name="4.4 Rain delay clear",
        )
    )


# Add common entities
def add_common_entities(builder: QuirkBuilder) -> QuirkBuilder:
    """Add shared SWV private-cluster entities."""

    builder = builder.replaces(SonoffWaterValveCluster).replaces(
        SonoffWaterValveCluster, endpoint_id=2
    )
    builder = add_single_irrigation_config_entities(builder)
    builder = add_irrigation_plan_config_entities(builder)
    builder = add_irrigation_plan_config_entities_ch2(builder)
    builder = add_user_delay_config_entities(builder)
    builder = add_amount_unit_config_entity(builder)
    builder = add_seasonal_adjustment_entities(builder)

    result = (
        builder
        # Child lock
        .switch(
            SonoffWaterValveCluster.AttributeDefs.child_lock.name,
            SonoffWaterValveCluster.cluster_id,
            translation_key="1.1_child_lock",
            fallback_name="1.1 Child lock",
        )
        # 1. Water leakage sensor (bit1)
        .binary_sensor(
            SonoffWaterValveCluster.AttributeDefs.valve_abnormal_state.name,
            SonoffWaterValveCluster.cluster_id,
            device_class=BinarySensorDeviceClass.MOISTURE,
            attribute_converter=lambda value: value & ValveState.Water_Leakage,
            unique_id_suffix="water_leak_status_v2",
            reporting_config=ReportingConfig(
                min_interval=30, max_interval=900, reportable_change=1
            ),
            translation_key="water_leak",
            fallback_name="Water leak",
        )
        # 2. Water shortage sensor (bit0)
        .binary_sensor(
            SonoffWaterValveCluster.AttributeDefs.valve_abnormal_state.name,
            SonoffWaterValveCluster.cluster_id,
            device_class=BinarySensorDeviceClass.PROBLEM,
            attribute_converter=lambda value: (
                value
                & (ValveState.Water_Shortage | ValveState.Water_Shortage_Channel_2)
            ),
            unique_id_suffix="water_shortage_status_v2",
            reporting_config=ReportingConfig(
                min_interval=30, max_interval=900, reportable_change=1
            ),
            translation_key="water_shortage",
            fallback_name="Water shortage",
        )
    )

    # User delay end time (0x5014) → converted to Unix epoch for HA display
    if ENABLE_USER_DELAY_END_DATETIME:
        result = result.sensor(
            SonoffWaterValveCluster.AttributeDefs.user_delay_end_datetime.name,
            SonoffWaterValveCluster.cluster_id,
            device_class=SensorDeviceClass.TIMESTAMP,
            state_class=SensorStateClass.MEASUREMENT,
            reporting_config=ReportingConfig(
                min_interval=30, max_interval=900, reportable_change=1
            ),
            attribute_converter=lambda v: (
                datetime.fromtimestamp(v + ZIGBEE_EPOCH_OFFSET, tz=UTC)
                if v != 0
                else None
            ),
            unique_id_suffix="user_delay_end_datetime_v2",
            translation_key="user_delay_end_datetime",
            fallback_name="User delay end time",
        )

    # Realtime irrigation duration
    if ENABLE_REALTIME_IRRIGATION_DURATION:
        result = result.sensor(
            attribute_name=SonoffWaterValveCluster.AttributeDefs.realtime_irrigation_duration.name,
            cluster_id=SonoffWaterValveCluster.cluster_id,
            device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.MEASUREMENT,
            unit=UnitOfTime.SECONDS,
            unique_id_suffix="realtime_irrigation_duration_v2",
            translation_key="realtime_irrigation_duration",
            fallback_name="Realtime irrigation duration",
            initially_disabled=True,
        )

    # Hourly irrigation duration
    if ENABLE_HOUR_IRRIGATION_DURATION:
        result = result.sensor(
            attribute_name=SonoffWaterValveCluster.AttributeDefs.hour_irrigation_duration.name,
            cluster_id=SonoffWaterValveCluster.cluster_id,
            device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.MEASUREMENT,
            unit=UnitOfTime.MINUTES,
            unique_id_suffix="hour_irrigation_duration_v2",
            reporting_config=ReportingConfig(
                min_interval=30, max_interval=900, reportable_change=1
            ),
            translation_key="hour_irrigation_duration",
            fallback_name="Hourly irrigation duration",
        )

    # Hourly irrigation volume
    if ENABLE_HOUR_IRRIGATION_VOLUME:
        result = result.sensor(
            attribute_name=SonoffWaterValveCluster.AttributeDefs.hour_irrigation_volume.name,
            cluster_id=SonoffWaterValveCluster.cluster_id,
            device_class=SensorDeviceClass.VOLUME,
            state_class=SensorStateClass.TOTAL_INCREASING,
            unit=UnitOfVolume.LITERS,
            unique_id_suffix="hour_irrigation_volume_v2",
            reporting_config=ReportingConfig(
                min_interval=30, max_interval=900, reportable_change=1
            ),
            translation_key="hour_irrigation_volume",
            fallback_name="Hourly irrigation volume",
        )

    # Hour irrigation duration (always enabled) - CH1
    result = result.sensor(
        attribute_name=SonoffWaterValveCluster.AttributeDefs.hour_irrigation_duration.name,
        cluster_id=SonoffWaterValveCluster.cluster_id,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.MINUTES,
        unique_id_suffix="hour_irrigation_duration_v2",
        translation_key="hour_irrigation_duration",
        fallback_name="CH1 Hour irrigation duration",
    )
    # Hour irrigation duration CH2 (always enabled)
    result = result.sensor(
        attribute_name=SonoffWaterValveCluster.AttributeDefs.hour_irrigation_duration.name,
        cluster_id=SonoffWaterValveCluster.cluster_id,
        endpoint_id=2,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.MINUTES,
        unique_id_suffix="hour_irrigation_duration_ch2_v2",
        translation_key="hour_irrigation_duration_ch2",
        fallback_name="CH2 Hour irrigation duration",
    )
    # Hour irrigation volume (always enabled)
    result = result.sensor(
        attribute_name=SonoffWaterValveCluster.AttributeDefs.hour_irrigation_volume.name,
        cluster_id=SonoffWaterValveCluster.cluster_id,
        device_class=SensorDeviceClass.VOLUME,
        state_class=SensorStateClass.TOTAL_INCREASING,
        # unit=UnitOfVolume.LITERS,
        unique_id_suffix="hour_irrigation_volume_v2",
        translation_key="hour_irrigation_volume",
        fallback_name="Hour irrigation volume",
    )

    return result


# Model definitions
add_common_entities(
    QuirkBuilder("SONOFF", "SWV-ZF2E")
    .also_applies_to("SONOFF", "SWV-ZF2U")
    .also_applies_to("SONOFF", "SWV-ZN2E")
    .also_applies_to("SONOFF", "SWV-ZN2U")
    .also_applies_to("SONOFF", "SWV-ZF2")
    .also_applies_to("SONOFF", "SWV-ZNE")
    .also_applies_to("SONOFF", "SWV-ZNU")
).add_to_registry()
