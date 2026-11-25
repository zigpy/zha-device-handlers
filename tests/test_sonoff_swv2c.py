"""Tests for Sonoff SWV dual-channel Zigbee water valve quirk."""

from datetime import UTC, datetime
from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.sonoff.sonoff_swv2c import (
    IRRIGATION_PLAN_MAX_COUNT,
    IRRIGATION_PLAN_PAYLOAD_LEN,
    QUARTERLY_ADJUSTMENT_DEFAULT_VALUE,
    QUARTERLY_ADJUSTMENT_PAYLOAD_LEN,
    SINGLE_IRRIGATION_DEFAULT_AMOUNT,
    SINGLE_IRRIGATION_DEFAULT_FAIL_SAFE_DURATION_MIN,
    SINGLE_IRRIGATION_DEFAULT_TOTAL_DURATION_MIN,
    SINGLE_IRRIGATION_PAYLOAD_LEN,
    SINGLE_IRRIGATION_ZB_AMOUNT_UNIT_LITER,
    USER_DELAY_MAX_HOURS,
    ZIGBEE_EPOCH_OFFSET,
    DelayTimestampPayload,
    IrrigationAmountUnit,
    IrrigationLoopType,
    IrrigationPlan,
    IrrigationPlanPayload,
    IrrigationPlanRepeat,
    ManualIrrigationMode,
    QuarterlyAdjustmentPayload,
    QuarterlyAdjustmentState,
    SingleIrrigationMode,
    SingleIrrigationPayload,
    SingleIrrigationState,
    SonoffAmountUnitConfigCluster,
    SonoffIrrigationPlanConfigCluster,
    SonoffIrrigationPlanConfigClusterCh2,
    SonoffSeasonalAdjustmentConfigCluster,
    SonoffSingleIrrigationConfigCluster,
    SonoffUserDelayConfigCluster,
    SonoffWaterValveCluster,
    ValveState,
    _local_timezone_offset_seconds,
    _put_u16_be,
    _put_u32_be,
    _repeat_to_loop_info,
    _seconds_from_midnight,
    _u16_be,
    _validate_irrigation_plan_index,
    _zigbee_date_timestamp,
    _zigbee_now_timestamp,
    _zigbee_timestamp_to_ymd,
    decode_single_irrigation_payload,
    encode_irrigation_plan_payload,
    encode_single_irrigation_payload,
    quarterly_adjustment_array_from_payload,
    quarterly_adjustment_payload_from_value,
    single_irrigation_array_from_payload,
    single_irrigation_array_from_payload_test,
    single_irrigation_payload_from_array,
)

zhaquirks.setup()


# ============================================================================
# Binary helpers
# ============================================================================


class TestBinaryHelpers:
    """Tests for u16/u32 encode/decode helpers."""

    def test_u16_be(self):
        """Decode unsigned big-endian uint16."""
        assert _u16_be(b"\x01\x02") == 0x0102
        assert _u16_be(b"\xff\xff") == 65535
        assert _u16_be(b"\x00\x00") == 0

    def test_put_u16_be(self):
        """Encode unsigned big-endian uint16."""
        assert _put_u16_be(0x0102) == [0x01, 0x02]
        assert _put_u16_be(0) == [0x00, 0x00]
        assert _put_u16_be(65535) == [0xFF, 0xFF]

    def test_put_u32_be(self):
        """Encode unsigned big-endian uint32."""
        assert _put_u32_be(0x01020304) == [0x01, 0x02, 0x03, 0x04]
        assert _put_u32_be(0) == [0x00, 0x00, 0x00, 0x00]


# ============================================================================
# Time helpers
# ============================================================================


class TestTimeHelpers:
    """Tests for time conversion helpers."""

    def test_seconds_from_midnight(self):
        """Seconds elapsed since midnight."""
        assert _seconds_from_midnight(0, 0) == 0
        assert _seconds_from_midnight(1, 0) == 3600
        assert _seconds_from_midnight(0, 1) == 60
        assert _seconds_from_midnight(23, 59) == 23 * 3600 + 59 * 60

    def test_zigbee_date_timestamp(self):
        """Convert year/month/day to Zigbee epoch timestamp."""
        ts = _zigbee_date_timestamp(2000, 1, 1)
        expected = int(
            datetime(2000, 1, 1, tzinfo=UTC).timestamp() - ZIGBEE_EPOCH_OFFSET
        )
        assert ts == expected

    def test_zigbee_timestamp_to_ymd(self):
        """Convert Zigbee epoch timestamp back to year/month/day."""
        ts = _zigbee_date_timestamp(2025, 6, 15)
        y, m, d = _zigbee_timestamp_to_ymd(ts)
        assert (y, m, d) == (2025, 6, 15)

    def test_zigbee_now_timestamp_is_recent(self):
        """Now timestamp should be close to current time."""
        now_ts = _zigbee_now_timestamp()
        expected = int(datetime.now(tz=UTC).timestamp() - ZIGBEE_EPOCH_OFFSET)
        assert abs(now_ts - expected) <= 5

    def test_local_timezone_offset_seconds(self):
        """Local timezone offset should be an integer."""
        offset = _local_timezone_offset_seconds()
        assert isinstance(offset, int)
        assert -86400 < offset < 86400


# ============================================================================
# Validation helpers
# ============================================================================


class TestValidationHelpers:
    """Tests for validation helpers."""

    def test_validate_irrigation_plan_index_valid(self):
        """Valid indices should not raise."""
        for idx in range(IRRIGATION_PLAN_MAX_COUNT):
            _validate_irrigation_plan_index(idx)

    def test_validate_irrigation_plan_index_invalid(self):
        """Out-of-range indices should raise ValueError."""
        with pytest.raises(ValueError):
            _validate_irrigation_plan_index(-1)
        with pytest.raises(ValueError):
            _validate_irrigation_plan_index(IRRIGATION_PLAN_MAX_COUNT)

    def test_repeat_to_loop_info_odd_day(self):
        """Odd day repeat mode."""
        loop_type, loop_opt = _repeat_to_loop_info(IrrigationPlanRepeat.Odd_Day, 0)
        assert loop_type == IrrigationLoopType.Odd_Day
        assert loop_opt == 0

    def test_repeat_to_loop_info_even_day(self):
        """Even day repeat mode."""
        loop_type, loop_opt = _repeat_to_loop_info(IrrigationPlanRepeat.Even_Day, 0)
        assert loop_type == IrrigationLoopType.Even_Day
        assert loop_opt == 0

    def test_repeat_to_loop_info_interval(self):
        """Interval repeat mode."""
        loop_type, loop_opt = _repeat_to_loop_info(IrrigationPlanRepeat.Interval, 3)
        assert loop_type == IrrigationLoopType.Days
        assert loop_opt == 3

    def test_repeat_to_loop_info_interval_invalid(self):
        """Interval must be 1..30."""
        with pytest.raises(ValueError):
            _repeat_to_loop_info(IrrigationPlanRepeat.Interval, 0)
        with pytest.raises(ValueError):
            _repeat_to_loop_info(IrrigationPlanRepeat.Interval, 31)

    def test_repeat_to_loop_info_custom(self):
        """Custom repeat mode (weekday mask)."""
        loop_type, loop_opt = _repeat_to_loop_info(IrrigationPlanRepeat.Custom, 0x7F)
        assert loop_type == IrrigationLoopType.Week
        assert loop_opt == 0x7F

    def test_repeat_to_loop_info_custom_mask_0(self):
        """Custom with mask 0."""
        loop_type, loop_opt = _repeat_to_loop_info(IrrigationPlanRepeat.Custom, 0)
        assert loop_type == IrrigationLoopType.Week
        assert loop_opt == 0

    def test_repeat_to_loop_info_custom_invalid(self):
        """Custom mask must be 0..127."""
        with pytest.raises(ValueError):
            _repeat_to_loop_info(IrrigationPlanRepeat.Custom, 128)
        with pytest.raises(ValueError):
            _repeat_to_loop_info(IrrigationPlanRepeat.Custom, -1)


# ============================================================================
# Single irrigation payload encode / decode
# ============================================================================


class TestSingleIrrigationPayload:
    """Tests for single irrigation payload encode/decode."""

    def test_decode_duration_mode(self):
        """Decode a duration-mode single irrigation payload."""
        payload = bytes(
            [
                SingleIrrigationMode.Duration,
                0x00,
                0x0A,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
            ]
        )
        state = decode_single_irrigation_payload(payload)
        assert state.irrigation_mode == SingleIrrigationMode.Duration
        assert state.total_duration_min == 10
        assert state.amount_unit == 0
        assert state.amount == 0
        assert state.fail_safe_duration_min == 0

    def test_decode_volume_mode(self):
        """Decode a volume-mode single irrigation payload."""
        payload = bytes(
            [
                SingleIrrigationMode.Volume,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                IrrigationAmountUnit.Liter,
                0x00,
                0x64,
                0x00,
                0x0A,
            ]
        )
        state = decode_single_irrigation_payload(payload)
        assert state.irrigation_mode == SingleIrrigationMode.Volume
        assert state.amount_unit == IrrigationAmountUnit.Liter
        assert state.amount == 100
        assert state.fail_safe_duration_min == 10

    def test_encode_duration_mode(self):
        """Encode a duration-mode single irrigation state."""
        state = SingleIrrigationState(
            irrigation_mode=SingleIrrigationMode.Duration,
            total_duration_min=30,
            amount_unit=0,
            amount=0,
            fail_safe_duration_min=0,
        )
        payload = encode_single_irrigation_payload(state)
        assert len(payload) == SINGLE_IRRIGATION_PAYLOAD_LEN
        decoded = decode_single_irrigation_payload(payload)
        assert decoded.total_duration_min == 30
        assert decoded.amount == 0
        assert decoded.fail_safe_duration_min == 0

    def test_encode_volume_mode(self):
        """Encode a volume-mode single irrigation state."""
        state = SingleIrrigationState(
            irrigation_mode=SingleIrrigationMode.Volume,
            total_duration_min=0,
            amount_unit=IrrigationAmountUnit.Liter,
            amount=500,
            fail_safe_duration_min=15,
        )
        payload = encode_single_irrigation_payload(state)
        decoded = decode_single_irrigation_payload(payload)
        assert decoded.amount == 500
        assert decoded.fail_safe_duration_min == 15
        assert decoded.total_duration_min == 0

    def test_encode_dwi_defaults_to_duration(self):
        """Duration_With_Interval should fall back to Duration."""
        state = SingleIrrigationState(
            irrigation_mode=SingleIrrigationMode.Duration_With_Interval,
            total_duration_min=60,
            amount_unit=0,
            amount=0,
            fail_safe_duration_min=0,
        )
        payload = encode_single_irrigation_payload(state)
        decoded = decode_single_irrigation_payload(payload)
        assert decoded.irrigation_mode == SingleIrrigationMode.Duration

    def test_decode_short_payload_raises(self):
        """Payload shorter than 12 bytes should raise ValueError."""
        with pytest.raises(ValueError):
            decode_single_irrigation_payload(b"\x00\x01\x02")

    def test_payload_from_array_zcl_array(self):
        """Extract from a ZCL foundation.Array."""
        arr = foundation.Array(
            type=foundation.DataTypeId.uint8,
            value=t.LVList[t.uint8_t, t.uint16_t](
                bytes([SingleIrrigationMode.Duration, 0, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0])
            ),
        )
        result = single_irrigation_payload_from_array(arr)
        assert isinstance(result, bytes)
        assert len(result) == SINGLE_IRRIGATION_PAYLOAD_LEN

    def test_payload_from_array_raw_bytes(self):
        """Extract from raw bytes."""
        raw = bytes([SingleIrrigationMode.Duration] + [0] * 11)
        result = single_irrigation_payload_from_array(raw)
        assert len(result) == SINGLE_IRRIGATION_PAYLOAD_LEN


class TestSingleIrrigationState:
    """Tests for the SingleIrrigationState dataclass."""

    def test_defaults(self):
        """Default values should be set correctly."""
        state = SingleIrrigationState()
        assert state.irrigation_mode == SingleIrrigationMode.Duration
        assert state.total_duration_min == SINGLE_IRRIGATION_DEFAULT_TOTAL_DURATION_MIN
        assert state.amount == SINGLE_IRRIGATION_DEFAULT_AMOUNT
        assert (
            state.fail_safe_duration_min
            == SINGLE_IRRIGATION_DEFAULT_FAIL_SAFE_DURATION_MIN
        )
        assert state.amount_unit == SINGLE_IRRIGATION_ZB_AMOUNT_UNIT_LITER


class TestSingleIrrigationPayloadLVList:
    """Tests for the SingleIrrigationPayload LVList type."""

    def test_create_empty(self):
        """Create with empty value."""
        obj = SingleIrrigationPayload()
        assert len(obj) == 0

    def test_create_from_bytes(self):
        """Create from bytes."""
        payload = bytes([SingleIrrigationMode.Duration] + [0] * 11)
        obj = SingleIrrigationPayload(payload)
        assert len(obj) == SINGLE_IRRIGATION_PAYLOAD_LEN

    def test_create_from_list(self):
        """Create from list."""
        values = [SingleIrrigationMode.Duration] + [0] * 11
        obj = SingleIrrigationPayload(values)
        assert len(obj) == SINGLE_IRRIGATION_PAYLOAD_LEN


# ============================================================================
# Irrigation plan payload encode
# ============================================================================


class TestIrrigationPlanPayload:
    """Tests for irrigation plan payload encoding."""

    def test_encode_basic_duration_plan(self):
        """Encode a basic duration-type irrigation plan."""
        plan = IrrigationPlan(
            index=0,
            enabled=1,
            enable_datetime=_zigbee_date_timestamp(2025, 1, 1),
            irrigation_mode=SingleIrrigationMode.Duration,
            start_datetime=_seconds_from_midnight(8, 0),
            total_duration_min=30,
            duration_min=0,
            interval_duration_min=0,
            amount_unit=IrrigationAmountUnit.Liter,
            amount=0,
            fail_safe_duration_min=0,
            create_datetime=_zigbee_now_timestamp(),
            repeat_mode=IrrigationPlanRepeat.Custom,
            repeat_value=0x7F,
        )
        payload = encode_irrigation_plan_payload(plan)
        assert isinstance(payload, bytes)
        assert len(payload) == IRRIGATION_PLAN_PAYLOAD_LEN
        assert payload[0] == 0
        assert payload[1] == 1

    def test_encode_volume_plan(self):
        """Encode a volume-type irrigation plan."""
        plan = IrrigationPlan(
            index=3,
            enabled=1,
            enable_datetime=_zigbee_date_timestamp(2025, 6, 1),
            irrigation_mode=SingleIrrigationMode.Volume,
            start_datetime=_seconds_from_midnight(18, 30),
            total_duration_min=0,
            duration_min=0,
            interval_duration_min=0,
            amount_unit=IrrigationAmountUnit.Liter,
            amount=200,
            fail_safe_duration_min=30,
            create_datetime=_zigbee_now_timestamp(),
            repeat_mode=IrrigationPlanRepeat.Odd_Day,
            repeat_value=0,
        )
        payload = encode_irrigation_plan_payload(plan)
        assert len(payload) == IRRIGATION_PLAN_PAYLOAD_LEN
        assert payload[0] == 3

    def test_encode_invalid_index_raises(self):
        """Index out of range should raise."""
        plan = IrrigationPlan(index=10)
        with pytest.raises(ValueError):
            encode_irrigation_plan_payload(plan)


# ============================================================================
# Quarterly adjustment
# ============================================================================


class TestQuarterlyAdjustmentState:
    """Tests for QuarterlyAdjustmentState."""

    def test_default_values(self):
        """Default fills 12 elements."""
        state = QuarterlyAdjustmentState()
        assert len(state.values) == QUARTERLY_ADJUSTMENT_PAYLOAD_LEN
        assert all(v == QUARTERLY_ADJUSTMENT_DEFAULT_VALUE for v in state.values)

    def test_custom_values(self):
        """Accept custom 12-element list."""
        values = list(range(1, 13))
        state = QuarterlyAdjustmentState(values)
        assert state.values == values

    def test_too_short_raises(self):
        """Wrong number of values should raise ValueError."""
        with pytest.raises(ValueError):
            QuarterlyAdjustmentState([1, 2, 3])

    def test_too_long_raises(self):
        """More than 12 values should raise ValueError."""
        with pytest.raises(ValueError):
            QuarterlyAdjustmentState(list(range(13)))

    def test_to_payload(self):
        """to_payload returns bytes representation."""
        values = [1] * 12
        state = QuarterlyAdjustmentState(values)
        payload = state.to_payload()
        assert isinstance(payload, bytes)
        assert len(payload) == QUARTERLY_ADJUSTMENT_PAYLOAD_LEN
        assert payload == b"\x01" * 12


class TestQuarterlyAdjustmentPayload:
    """Tests for quarterly adjustment payload conversion functions."""

    def test_payload_from_list(self):
        """Convert list to raw bytes."""
        values = [1] * 12
        data = quarterly_adjustment_payload_from_value(values)
        assert isinstance(data, bytes)
        assert len(data) == QUARTERLY_ADJUSTMENT_PAYLOAD_LEN

    def test_payload_from_bytes(self):
        """Pass-through raw bytes."""
        raw = b"\x01" * 12
        data = quarterly_adjustment_payload_from_value(raw)
        assert data == raw

    def test_payload_invalid_type_raises(self):
        """Invalid type should raise TypeError."""
        with pytest.raises(TypeError, match="Unsupported quarterly"):
            quarterly_adjustment_payload_from_value("invalid")

    def test_payload_wrong_length_raises(self):
        """Wrong length should raise ValueError."""
        with pytest.raises(ValueError, match="must be 12 bytes"):
            quarterly_adjustment_payload_from_value(b"\x01\x02")

    def test_array_from_payload(self):
        """Wrap in ZCL array."""
        arr = quarterly_adjustment_array_from_payload(b"\x01" * 12)
        assert isinstance(arr, foundation.Array)


# ============================================================================
# Enums
# ============================================================================


class TestEnums:
    """Tests for enum / bitmask types."""

    def test_single_irrigation_mode(self):
        """SingleIrrigationMode values."""
        assert SingleIrrigationMode.Duration == 0x00
        assert SingleIrrigationMode.Volume == 0x01
        assert SingleIrrigationMode.Duration_With_Interval == 0x02

    def test_manual_irrigation_mode(self):
        """ManualIrrigationMode values."""
        assert ManualIrrigationMode.Duration == 0x00
        assert ManualIrrigationMode.Volume == 0x01

    def test_irrigation_amount_unit(self):
        """IrrigationAmountUnit values."""
        assert IrrigationAmountUnit.Liter == 0x00
        assert IrrigationAmountUnit.US_Gallon == 0x01
        assert IrrigationAmountUnit.Imperial_Gallon == 0x02

    def test_valve_state_bitmask(self):
        """ValveState bitmask values."""
        assert ValveState.Normal == 0
        assert ValveState.Water_Shortage == 1
        assert ValveState.Water_Leakage == 2
        assert ValveState.Anti_Frost_Alarm == 4
        assert ValveState.Water_Shortage_Channel_2 == 16

    def test_irrigation_loop_type(self):
        """IrrigationLoopType values."""
        assert IrrigationLoopType.Odd_Day == 0x00
        assert IrrigationLoopType.Even_Day == 0x01
        assert IrrigationLoopType.Days == 0x02
        assert IrrigationLoopType.Week == 0x03
        assert IrrigationLoopType.Only == 0x04

    def test_irrigation_plan_repeat(self):
        """IrrigationPlanRepeat values."""
        assert IrrigationPlanRepeat.Odd_Day == 0x00
        assert IrrigationPlanRepeat.Even_Day == 0x01
        assert IrrigationPlanRepeat.Interval == 0x02
        assert IrrigationPlanRepeat.Custom == 0x03


# ============================================================================
# IrrigationPlan dataclass
# ============================================================================


class TestIrrigationPlanDataClass:
    """Tests for the IrrigationPlan dataclass."""

    def test_defaults(self):
        """Default values are sensible."""
        plan = IrrigationPlan()
        assert plan.index == 0
        assert plan.enabled == 1
        assert plan.irrigation_mode == SingleIrrigationMode.Duration
        assert plan.total_duration_min == SINGLE_IRRIGATION_DEFAULT_TOTAL_DURATION_MIN
        assert plan.amount == SINGLE_IRRIGATION_DEFAULT_AMOUNT
        assert plan.repeat_mode == IrrigationPlanRepeat.Custom
        assert plan.amount_unit == SINGLE_IRRIGATION_ZB_AMOUNT_UNIT_LITER


# ============================================================================
# Payload types
# ============================================================================


class TestPayloadTypes:
    """Tests for payload FixedList types."""

    def test_delay_timestamp_payload(self):
        """DelayTimestampPayload is 4 bytes."""
        obj = DelayTimestampPayload([0x00, 0x01, 0x02, 0x03])
        assert len(obj) == 4
        assert bytes(obj) == b"\x00\x01\x02\x03"

    def test_irrigation_plan_payload(self):
        """IrrigationPlanPayload is 28 bytes."""
        obj = IrrigationPlanPayload([0] * IRRIGATION_PLAN_PAYLOAD_LEN)
        assert len(obj) == IRRIGATION_PLAN_PAYLOAD_LEN

    def test_quarterly_adjustment_payload(self):
        """QuarterlyAdjustmentPayload is 12 bytes."""
        obj = QuarterlyAdjustmentPayload([0] * QUARTERLY_ADJUSTMENT_PAYLOAD_LEN)
        assert len(obj) == QUARTERLY_ADJUSTMENT_PAYLOAD_LEN


# ============================================================================
# Array wrapper helpers
# ============================================================================


class TestArrayWrapperHelpers:
    """Tests for array wrapper functions."""

    def test_single_irrigation_array_from_payload(self):
        """Wrap payload in SingleIrrigationPayload."""
        payload = bytes([SingleIrrigationMode.Duration] + [0] * 11)
        result = single_irrigation_array_from_payload(payload)
        assert isinstance(result, SingleIrrigationPayload)

    def test_single_irrigation_array_from_payload_test(self):
        """Wrap payload in foundation.Array."""
        payload = bytes([SingleIrrigationMode.Duration] + [0] * 11)
        result = single_irrigation_array_from_payload_test(payload)
        assert isinstance(result, foundation.Array)

    def test_quarterly_adjustment_from_array(self):
        """Extract from foundation.Array in quarterly_adjustment_payload_from_value."""
        arr = foundation.Array(
            type=foundation.DataTypeId.uint8,
            value=t.LVList[t.uint8_t, t.uint16_t](b"\x01" * 12),
        )
        data = quarterly_adjustment_payload_from_value(arr)
        assert isinstance(data, bytes)
        assert len(data) == 12


# ============================================================================
# _coerce_value edge cases
# ============================================================================


class TestCoerceValueEdgeCases:
    """Tests for SingleIrrigationPayload._coerce_value edge cases."""

    def test_coerce_from_lvlist(self):
        """Coerce from an existing LVList."""
        lv = t.LVList[t.uint8_t, t.uint16_t]([0, 1, 2])
        result = SingleIrrigationPayload._coerce_value(lv)
        assert isinstance(result, list)

    def test_coerce_from_tuple(self):
        """Coerce from a tuple."""
        result = SingleIrrigationPayload._coerce_value((10, 20, 30))
        assert result == [10, 20, 30]

    def test_nested_value_attr(self):
        """Coerce a value with nested .value attrs."""

        class Inner:
            value = 42

        class Outer:
            value = Inner()

        result = SingleIrrigationPayload._coerce_value(Outer())
        assert result == 42  # type: ignore[comparison-overlap]

    def test_value_is_self_break_out(self):
        """Coerce where value is its own .value."""

        class SelfRef:
            @property
            def value(self):
                return self

        obj = SelfRef()
        result = SingleIrrigationPayload._coerce_value(obj)
        assert result is obj  # type: ignore[comparison-overlap]

    def test_bytes_with_array_prefix(self):
        """Coerce bytes with array type prefix."""
        inner = bytes([SingleIrrigationMode.Duration] + [0] * 11)
        prefixed = bytes([foundation.DataTypeId.uint8])
        prefixed += len(inner).to_bytes(2, "little") + inner
        result = SingleIrrigationPayload._coerce_value(prefixed)
        assert isinstance(result, bytes)
        assert len(result) == SINGLE_IRRIGATION_PAYLOAD_LEN


# ============================================================================
# payload_from_array edge cases
# ============================================================================


class TestPayloadFromArrayEdgeCases:
    """Tests for single_irrigation_payload_from_array edge cases."""

    def test_empty_array_raises(self):
        """Empty foundation.Array raises ValueError."""
        arr = foundation.Array(type=foundation.DataTypeId.uint8, value=None)
        with pytest.raises(ValueError):
            single_irrigation_payload_from_array(arr)

    def test_from_list(self):
        """Decode from a plain list."""
        result = single_irrigation_payload_from_array(
            [SingleIrrigationMode.Duration] + [0] * 11
        )
        assert isinstance(result, bytes)
        assert len(result) == SINGLE_IRRIGATION_PAYLOAD_LEN

    def test_from_lvlist(self):
        """Decode from an LVList."""
        lv = t.LVList[t.uint8_t, t.uint16_t]([SingleIrrigationMode.Duration] + [0] * 11)
        result = single_irrigation_payload_from_array(lv)
        assert isinstance(result, bytes)

    def test_from_bytes_with_array_prefix(self):
        """Decode bytes prefixed with array type marker."""
        inner = bytes([SingleIrrigationMode.Duration] + [0] * 11)
        prefixed = bytes([foundation.DataTypeId.uint8])
        prefixed += len(inner).to_bytes(2, "little") + inner
        result = single_irrigation_payload_from_array(prefixed)
        assert isinstance(result, bytes)

    def test_unsupported_type_raises(self):
        """Unsupported type raises ValueError."""
        with pytest.raises(ValueError):
            single_irrigation_payload_from_array(42)


# ============================================================================
# Integration tests (v2 quirk fixture) — cluster presence
# ============================================================================


class TestSonoffWaterValveQuirk:
    """Integration tests using the v2 quirk fixture."""

    @pytest.fixture(autouse=True)
    def _setup(self, zigpy_device_from_v2_quirk):
        """Create a quirked device with the Sonoff SWV clusters."""
        self.device = zigpy_device_from_v2_quirk(
            manufacturer="SONOFF",
            model="SWV-ZF2E",
            endpoint_ids=[1, 2],
            cluster_ids={
                1: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
                2: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
            },
        )

    @property
    def ep1(self):
        """Shortcut for device endpoint 1."""
        return self.device.endpoints[1]

    @property
    def ep2(self):
        """Shortcut for device endpoint 2."""
        return self.device.endpoints[2]

    def test_swv_cluster_registered(self):
        """SonoffWaterValveCluster is registered on both endpoints."""
        assert hasattr(self.ep1, "sonoff_cluster")
        assert isinstance(self.ep1.sonoff_cluster, SonoffWaterValveCluster)
        assert hasattr(self.ep2, "sonoff_cluster")
        assert isinstance(self.ep2.sonoff_cluster, SonoffWaterValveCluster)

    def test_amount_unit_cluster(self):
        """Global amount unit cluster is present on ep 1."""
        assert hasattr(self.ep1, "sonoff_amount_unit_config")
        cluster = self.ep1.sonoff_amount_unit_config
        assert isinstance(cluster, SonoffAmountUnitConfigCluster)

    def test_amount_unit_update(self):
        """Update amount unit updates the local attribute."""
        cluster = self.ep1.sonoff_amount_unit_config
        listener = ClusterListener(cluster)
        cluster.update_amount_unit(IrrigationAmountUnit.US_Gallon)
        assert len(listener.attribute_updates) == 1
        assert listener.attribute_updates[0] == (
            cluster.AttributeDefs.amount_unit.id,
            IrrigationAmountUnit.US_Gallon,
        )

    def test_single_irrigation_config_cluster(self):
        """Single irrigation config cluster is present on ep 1."""
        assert hasattr(self.ep1, "sonoff_single_irrigation_config")
        cluster = self.ep1.sonoff_single_irrigation_config
        assert isinstance(cluster, SonoffSingleIrrigationConfigCluster)

    def test_single_irrigation_update_duration_state(self):
        """Updating single irrigation state with duration mode syncs attributes."""
        cluster = self.ep1.sonoff_single_irrigation_config
        listener = ClusterListener(cluster)
        state = SingleIrrigationState(
            irrigation_mode=SingleIrrigationMode.Duration,
            total_duration_min=45,
            amount_unit=IrrigationAmountUnit.Liter,
            amount=0,
            fail_safe_duration_min=0,
        )
        cluster.update_single_irrigation_state(state)
        updates = dict(listener.attribute_updates)
        assert (
            updates[cluster.AttributeDefs.irrigation_mode.id]
            == SingleIrrigationMode.Duration
        )
        assert updates[cluster.AttributeDefs.total_duration_min.id] == 45

    def test_single_irrigation_update_volume_state(self):
        """Updating single irrigation state with volume mode propagates amount."""
        cluster = self.ep1.sonoff_single_irrigation_config
        listener = ClusterListener(cluster)
        state = SingleIrrigationState(
            irrigation_mode=SingleIrrigationMode.Volume,
            total_duration_min=0,
            amount_unit=IrrigationAmountUnit.Liter,
            amount=300,
            fail_safe_duration_min=20,
        )
        cluster.update_single_irrigation_state(state)
        updates = dict(listener.attribute_updates)
        assert (
            updates[cluster.AttributeDefs.irrigation_mode.id]
            == SingleIrrigationMode.Volume
        )
        assert updates[cluster.AttributeDefs.amount.id] == 300
        assert updates[cluster.AttributeDefs.fail_safe_duration_min.id] == 20

    def test_irrigation_plan_cluster_ch1(self):
        """Channel 1 irrigation plan config cluster is present on ep 1."""
        assert hasattr(self.ep1, "sonoff_irrigation_plan_config")
        cluster = self.ep1.sonoff_irrigation_plan_config
        assert isinstance(cluster, SonoffIrrigationPlanConfigCluster)
        assert cluster._plan_index == 0

    def test_irrigation_plan_cluster_ch2(self):
        """Channel 2 irrigation plan config cluster is on ep 2."""
        assert hasattr(self.ep2, "sonoff_irrigation_plan_config_ch2")
        cluster = self.ep2.sonoff_irrigation_plan_config_ch2
        assert isinstance(cluster, SonoffIrrigationPlanConfigClusterCh2)

    def test_user_delay_config_cluster(self):
        """User delay config cluster is present on ep 1."""
        assert hasattr(self.ep1, "sonoff_user_delay_config")
        cluster = self.ep1.sonoff_user_delay_config
        assert isinstance(cluster, SonoffUserDelayConfigCluster)
        assert hasattr(cluster, "_delay_hours")

    def test_user_delay_update_timestamp(self):
        """Update delay end timestamp from device report."""
        cluster = self.ep1.sonoff_user_delay_config
        listener = ClusterListener(cluster)
        cluster.update_delay_end_timestamp(1234567890)
        assert cluster._delay_end_timestamp == 1234567890
        assert len(listener.attribute_updates) == 1

    def test_seasonal_adjustment_cluster(self):
        """Seasonal adjustment cluster is present on ep 1."""
        assert hasattr(self.ep1, "sonoff_seasonal_adjustment_config")
        cluster = self.ep1.sonoff_seasonal_adjustment_config
        assert isinstance(cluster, SonoffSeasonalAdjustmentConfigCluster)
        assert cluster._quarterly_adjustment is not None

    def test_seasonal_adjustment_update(self):
        """Update seasonal adjustment from device report."""
        cluster = self.ep1.sonoff_seasonal_adjustment_config
        listener = ClusterListener(cluster)
        values = [5, 5, 8, 10, 12, 15, 15, 12, 10, 8, 5, 5]
        cluster.update_quarterly_adjustment(values)
        assert cluster._quarterly_adjustment.values == values
        assert len(listener.attribute_updates) == 12

    def test_max_delay_hours(self):
        """User delay max is 7 days in hours."""
        assert USER_DELAY_MAX_HOURS == 7 * 24


# ============================================================================
# Event handler tests via update_attribute
# ============================================================================


class TestEventHandlers:
    """Tests for SonoffWaterValveCluster event handlers via update_attribute."""

    @pytest.fixture(autouse=True)
    def _setup(self, zigpy_device_from_v2_quirk):
        """Create device."""
        self.device = zigpy_device_from_v2_quirk(
            manufacturer="SONOFF",
            model="SWV-ZF2E",
            endpoint_ids=[1, 2],
            cluster_ids={
                1: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
                2: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
            },
        )
        self.swv = self.device.endpoints[1].sonoff_cluster

    def test_single_irrigation_change(self):
        """update_attribute on single_irrigation_set syncs to local config cluster."""
        local = self.device.endpoints[1].sonoff_single_irrigation_config
        listener = ClusterListener(local)
        vol_mode_int = int(SingleIrrigationMode.Volume)
        payload = SingleIrrigationPayload(
            bytes([vol_mode_int, 0, 0, 0, 0, 0, 0, 0, 0, 100, 0, 20])
        )
        self.swv.update_attribute(
            SonoffWaterValveCluster.AttributeDefs.single_irrigation_set.id, payload
        )
        updates = dict(listener.attribute_updates)
        assert (
            updates[local.AttributeDefs.irrigation_mode.id]
            == SingleIrrigationMode.Volume
        )
        assert updates[local.AttributeDefs.amount.id] == 100

    def test_unit_of_water_flow_change(self):
        """update_attribute on unit_of_water_flow syncs to amount unit config."""
        amount = self.device.endpoints[1].sonoff_amount_unit_config
        listener = ClusterListener(amount)
        self.swv.update_attribute(
            SonoffWaterValveCluster.AttributeDefs.unit_of_water_flow.id,
            int(IrrigationAmountUnit.US_Gallon),
        )
        assert len(listener.attribute_updates) == 1
        assert listener.attribute_updates[0][1] == IrrigationAmountUnit.US_Gallon

    def test_unit_of_water_flow_on_ep2(self):
        """unit_of_water_flow on ep2 falls back to ep1 global cluster."""
        swv2 = self.device.endpoints[2].sonoff_cluster
        amount = self.device.endpoints[1].sonoff_amount_unit_config
        swv2.update_attribute(
            SonoffWaterValveCluster.AttributeDefs.unit_of_water_flow.id,
            int(IrrigationAmountUnit.Imperial_Gallon),
        )
        assert amount._amount_unit == IrrigationAmountUnit.Imperial_Gallon

    def test_quarterly_adjustment_change(self):
        """update_attribute on quarterly_adjustment syncs to seasonal config."""
        seasonal = self.device.endpoints[1].sonoff_seasonal_adjustment_config
        listener = ClusterListener(seasonal)
        arr = quarterly_adjustment_array_from_payload(bytes([3] * 12))
        self.swv.update_attribute(
            SonoffWaterValveCluster.AttributeDefs.quarterly_adjustment.id, arr
        )
        assert len(listener.attribute_updates) == 12
        assert seasonal._quarterly_adjustment.values == [3] * 12

    def test_user_delay_change(self):
        """update_attribute on user_delay_end_datetime syncs to delay config."""
        delay = self.device.endpoints[1].sonoff_user_delay_config
        listener = ClusterListener(delay)
        self.swv.update_attribute(
            SonoffWaterValveCluster.AttributeDefs.user_delay_end_datetime.id, 999888777
        )
        assert delay._delay_end_timestamp == 999888777
        assert len(listener.attribute_updates) == 1

    def test_irrelevant_attribute_id(self):
        """update_attribute on unrelated attribute id does nothing to SWV local clusters."""
        local = self.device.endpoints[1].sonoff_single_irrigation_config
        listener = ClusterListener(local)
        self.swv.update_attribute(0x9999, 123)
        assert len(listener.attribute_updates) == 0


# ============================================================================
# apply_custom_configuration
# ============================================================================


class TestApplyCustomConfiguration:
    """Tests for SonoffWaterValveCluster.apply_custom_configuration."""

    @pytest.fixture(autouse=True)
    def _setup(self, zigpy_device_from_v2_quirk):
        """Create device."""
        self.device = zigpy_device_from_v2_quirk(
            manufacturer="SONOFF",
            model="SWV-ZF2E",
            endpoint_ids=[1, 2],
            cluster_ids={
                1: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
                2: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
            },
        )
        self.swv = self.device.endpoints[1].sonoff_cluster

    async def test_apply_custom_configuration_reads_attributes(self):
        """apply_custom_configuration reads unit_of_water_flow and user_delay_end_datetime."""
        uow_attr = SonoffWaterValveCluster.AttributeDefs.unit_of_water_flow
        ude_attr = SonoffWaterValveCluster.AttributeDefs.user_delay_end_datetime
        read_response = [
            foundation.ReadAttributeRecord(
                attrid=uow_attr.id,
                status=foundation.Status.SUCCESS,
                value=foundation.TypeValue(
                    type=uow_attr.zcl_type, value=IrrigationAmountUnit.Liter
                ),
            ),
            foundation.ReadAttributeRecord(
                attrid=ude_attr.id,
                status=foundation.Status.SUCCESS,
                value=foundation.TypeValue(
                    type=ude_attr.zcl_type, value=t.uint32_t(12345)
                ),
            ),
        ]
        with mock.patch.object(
            self.swv, "_read_attributes", mock.AsyncMock(return_value=[read_response])
        ) as mock_read:
            await self.swv.apply_custom_configuration()
        assert mock_read.call_count == 1


# ============================================================================
# Write attributes — SonoffAmountUnitConfigCluster
# ============================================================================


class TestAmountUnitConfigWrite:
    """Tests for SonoffAmountUnitConfigCluster.write_attributes."""

    @pytest.fixture(autouse=True)
    def _setup(self, zigpy_device_from_v2_quirk):
        """Create device."""
        self.device = zigpy_device_from_v2_quirk(
            manufacturer="SONOFF",
            model="SWV-ZF2E",
            endpoint_ids=[1, 2],
            cluster_ids={
                1: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
                2: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
            },
        )

    async def test_write_amount_unit(self):
        """Writing amount_unit calls write_attributes_raw on sonoff_cluster."""
        cluster = self.device.endpoints[1].sonoff_amount_unit_config
        swv = self.device.endpoints[1].sonoff_cluster
        write_response = [
            [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
        ]
        with mock.patch.object(
            swv, "write_attributes_raw", mock.AsyncMock(return_value=write_response)
        ) as mock_write:
            await cluster.write_attributes(
                {cluster.AttributeDefs.amount_unit.name: IrrigationAmountUnit.US_Gallon}
            )
        assert mock_write.call_count == 1
        assert cluster._amount_unit == IrrigationAmountUnit.US_Gallon


# ============================================================================
# Write attributes — SonoffSingleIrrigationConfigCluster
# ============================================================================


class TestSingleIrrigationConfigWrite:
    """Tests for SonoffSingleIrrigationConfigCluster.write_attributes."""

    @pytest.fixture(autouse=True)
    def _setup(self, zigpy_device_from_v2_quirk):
        """Create device."""
        self.device = zigpy_device_from_v2_quirk(
            manufacturer="SONOFF",
            model="SWV-ZF2E",
            endpoint_ids=[1, 2],
            cluster_ids={
                1: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
                2: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
            },
        )

    async def test_write_duration_mode_total_duration(self):
        """Write total_duration_min in duration mode."""
        cluster = self.device.endpoints[1].sonoff_single_irrigation_config
        cluster._single_irrigation_state = SingleIrrigationState(
            irrigation_mode=SingleIrrigationMode.Duration,
            total_duration_min=10,
            amount_unit=IrrigationAmountUnit.Liter,
            amount=0,
            fail_safe_duration_min=0,
        )
        swv = self.device.endpoints[1].sonoff_cluster
        write_response = [
            [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
        ]
        with mock.patch.object(
            swv, "write_attributes_raw", mock.AsyncMock(return_value=write_response)
        ):
            await cluster.write_attributes(
                {cluster.AttributeDefs.total_duration_min.name: 30}
            )
        assert cluster._single_irrigation_state.total_duration_min == 30

    async def test_write_volume_mode_amount(self):
        """Write amount in volume mode."""
        cluster = self.device.endpoints[1].sonoff_single_irrigation_config
        cluster._single_irrigation_state = SingleIrrigationState(
            irrigation_mode=SingleIrrigationMode.Volume,
            total_duration_min=0,
            amount_unit=IrrigationAmountUnit.Liter,
            amount=100,
            fail_safe_duration_min=20,
        )
        swv = self.device.endpoints[1].sonoff_cluster
        write_response = [
            [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
        ]
        with mock.patch.object(
            swv, "write_attributes_raw", mock.AsyncMock(return_value=write_response)
        ):
            await cluster.write_attributes({cluster.AttributeDefs.amount.name: 500})
        assert cluster._single_irrigation_state.amount == 500

    async def test_write_amount_in_duration_mode_raises(self):
        """Writing amount in duration mode should raise ValueError."""
        cluster = self.device.endpoints[1].sonoff_single_irrigation_config
        cluster._single_irrigation_state = SingleIrrigationState(
            irrigation_mode=SingleIrrigationMode.Duration,
            total_duration_min=10,
            amount_unit=IrrigationAmountUnit.Liter,
            amount=0,
            fail_safe_duration_min=0,
        )
        with pytest.raises(ValueError):
            await cluster.write_attributes({cluster.AttributeDefs.amount.name: 100})

    async def test_write_total_duration_in_volume_mode_raises(self):
        """Writing total_duration in volume mode should raise ValueError."""
        cluster = self.device.endpoints[1].sonoff_single_irrigation_config
        cluster._single_irrigation_state = SingleIrrigationState(
            irrigation_mode=SingleIrrigationMode.Volume,
            total_duration_min=0,
            amount_unit=IrrigationAmountUnit.Liter,
            amount=100,
            fail_safe_duration_min=20,
        )
        with pytest.raises(ValueError):
            await cluster.write_attributes(
                {cluster.AttributeDefs.total_duration_min.name: 30}
            )

    async def test_write_failed_returns_failure(self):
        """Failed write returns failure status."""
        cluster = self.device.endpoints[1].sonoff_single_irrigation_config
        cluster._single_irrigation_state = SingleIrrigationState(
            irrigation_mode=SingleIrrigationMode.Volume,
            total_duration_min=0,
            amount_unit=IrrigationAmountUnit.Liter,
            amount=100,
            fail_safe_duration_min=20,
        )
        swv = self.device.endpoints[1].sonoff_cluster
        write_response = [
            [foundation.WriteAttributesStatusRecord(status=foundation.Status.FAILURE)]
        ]
        with mock.patch.object(
            swv, "write_attributes_raw", mock.AsyncMock(return_value=write_response)
        ):
            result = await cluster.write_attributes(
                {cluster.AttributeDefs.amount.name: 500}
            )
        assert result[0][0].status == foundation.Status.FAILURE

    async def test_write_mode_change_in_same_batch(self):
        """Writing mode + amount in same batch uses final mode for validation."""
        cluster = self.device.endpoints[1].sonoff_single_irrigation_config
        cluster._single_irrigation_state = SingleIrrigationState(
            irrigation_mode=SingleIrrigationMode.Duration,
            total_duration_min=10,
            amount_unit=IrrigationAmountUnit.Liter,
            amount=0,
            fail_safe_duration_min=0,
        )
        swv = self.device.endpoints[1].sonoff_cluster
        write_response = [
            [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
        ]
        with mock.patch.object(
            swv, "write_attributes_raw", mock.AsyncMock(return_value=write_response)
        ):
            await cluster.write_attributes(
                {
                    cluster.AttributeDefs.irrigation_mode.name: SingleIrrigationMode.Volume,
                    cluster.AttributeDefs.amount.name: 999,
                }
            )
        assert (
            cluster._single_irrigation_state.irrigation_mode
            == SingleIrrigationMode.Volume
        )
        assert cluster._single_irrigation_state.amount == 999

    def test_update_amount_unit_delegates(self):
        """update_amount_unit delegates to global cluster."""
        single = self.device.endpoints[1].sonoff_single_irrigation_config
        single.update_amount_unit(IrrigationAmountUnit.Imperial_Gallon)
        assert (
            self.device.endpoints[1].sonoff_amount_unit_config._amount_unit
            == IrrigationAmountUnit.Imperial_Gallon
        )


# ============================================================================
# Write attributes — SonoffIrrigationPlanConfigCluster
# ============================================================================


class TestIrrigationPlanConfigWrite:
    """Tests for SonoffIrrigationPlanConfigCluster.write_attributes."""

    @pytest.fixture(autouse=True)
    def _setup(self, zigpy_device_from_v2_quirk):
        """Create device."""
        self.device = zigpy_device_from_v2_quirk(
            manufacturer="SONOFF",
            model="SWV-ZF2E",
            endpoint_ids=[1, 2],
            cluster_ids={
                1: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
                2: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
            },
        )

    async def test_write_plan_index(self):
        """Write plan_index updates local state."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        await cluster.write_attributes({cluster.AttributeDefs.plan_index.name: 3})
        assert cluster._plan_index == 3

    async def test_write_invalid_plan_index_raises(self):
        """Write plan_index with invalid value raises ValueError."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        with pytest.raises(ValueError):
            await cluster.write_attributes({cluster.AttributeDefs.plan_index.name: 99})

    async def test_write_effective_date(self):
        """Write effective year/month/day."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        await cluster.write_attributes(
            {
                cluster.AttributeDefs.effective_year.name: 2026,
                cluster.AttributeDefs.effective_month.name: 7,
                cluster.AttributeDefs.effective_day.name: 15,
            }
        )
        assert cluster._effective_year == 2026
        assert cluster._effective_month == 7
        assert cluster._effective_day == 15

    async def test_write_repeat_mode_and_value(self):
        """Write repeat_mode and repeat_value."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        await cluster.write_attributes(
            {
                cluster.AttributeDefs.repeat_mode.name: IrrigationPlanRepeat.Interval,
                cluster.AttributeDefs.repeat_value.name: 5,
            }
        )
        assert cluster._repeat_mode == IrrigationPlanRepeat.Interval
        assert cluster._repeat_value == 5

    async def test_write_weekday_masks(self):
        """Write weekday masks toggles bits."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        await cluster.write_attributes({cluster.AttributeDefs.weekday_monday.name: 1})
        assert cluster._weekday_mask & 0x02

    async def test_write_amount_in_duration_mode_raises(self):
        """Writing amount in Duration mode raises ValueError."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        cluster._irrigation_mode = SingleIrrigationMode.Duration
        with pytest.raises(ValueError):
            await cluster.write_attributes({cluster.AttributeDefs.amount.name: 100})

    async def test_write_total_duration_in_volume_mode_raises(self):
        """Writing total_duration in Volume mode raises ValueError."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        cluster._irrigation_mode = SingleIrrigationMode.Volume
        with pytest.raises(ValueError):
            await cluster.write_attributes(
                {cluster.AttributeDefs.total_duration_min.name: 30}
            )

    async def test_write_duration_not_in_dwi_mode_raises(self):
        """Writing duration_min when not in DWI mode raises ValueError."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        cluster._irrigation_mode = SingleIrrigationMode.Duration
        with pytest.raises(ValueError):
            await cluster.write_attributes(
                {cluster.AttributeDefs.duration_min.name: 10}
            )

    async def test_write_duration_exceeds_total_raises(self):
        """Duration > total should raise ValueError."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        cluster._irrigation_mode = SingleIrrigationMode.Duration_With_Interval
        cluster._total_duration_min = 30
        with pytest.raises(ValueError):
            await cluster.write_attributes(
                {
                    cluster.AttributeDefs.duration_min.name: 50,
                    cluster.AttributeDefs.total_duration_min.name: 30,
                }
            )

    async def test_apply_plan_triggers_command(self):
        """Writing apply_plan sends ZCL command."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        swv = self.device.endpoints[1].sonoff_cluster
        cluster._plan_index = 0
        cluster._irrigation_mode = SingleIrrigationMode.Duration
        cluster._repeat_mode = IrrigationPlanRepeat.Odd_Day
        cluster._repeat_value = 0
        with mock.patch.object(swv, "command", mock.AsyncMock()) as mock_cmd:
            await cluster.write_attributes({cluster.AttributeDefs.apply_plan.name: 1})
        assert mock_cmd.call_count == 1

    async def test_remove_plan_triggers_command(self):
        """Writing remove_plan sends ZCL command."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        swv = self.device.endpoints[1].sonoff_cluster
        cluster._plan_index = 2
        with mock.patch.object(swv, "command", mock.AsyncMock()) as mock_cmd:
            await cluster.write_attributes({cluster.AttributeDefs.remove_plan.name: 1})
        assert mock_cmd.call_count == 1

    def test_plan_from_current_config_duration(self):
        """Build firmware plan — Duration mode."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        cluster._plan_index = 1
        cluster._irrigation_mode = SingleIrrigationMode.Duration
        cluster._total_duration_min = 45
        cluster._repeat_mode = IrrigationPlanRepeat.Odd_Day
        cluster._repeat_value = 0
        plan = cluster._plan_from_current_config()
        assert plan.index == 1
        assert plan.irrigation_mode == SingleIrrigationMode.Duration
        assert plan.total_duration_min == 45
        assert plan.amount == 0
        assert plan.fail_safe_duration_min == 0

    def test_plan_from_current_config_volume(self):
        """Build firmware plan — Volume mode."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        cluster._plan_index = 2
        cluster._irrigation_mode = SingleIrrigationMode.Volume
        cluster._amount = 300
        cluster._fail_safe_duration_min = 25
        cluster._repeat_mode = IrrigationPlanRepeat.Even_Day
        cluster._repeat_value = 0
        plan = cluster._plan_from_current_config()
        assert plan.irrigation_mode == SingleIrrigationMode.Volume
        assert plan.total_duration_min == 0
        assert plan.amount == 300
        assert plan.fail_safe_duration_min == 25

    def test_plan_from_current_config_dwi(self):
        """Build firmware plan — Duration_With_Interval mode."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        cluster._plan_index = 3
        cluster._irrigation_mode = SingleIrrigationMode.Duration_With_Interval
        cluster._total_duration_min = 60
        cluster._duration_min = 20
        cluster._interval_duration_min = 10
        cluster._repeat_mode = IrrigationPlanRepeat.Custom
        cluster._weekday_mask = 0x7F
        plan = cluster._plan_from_current_config()
        assert plan.irrigation_mode == SingleIrrigationMode.Duration_With_Interval
        assert plan.total_duration_min == 60
        assert plan.duration_min == 20
        assert plan.interval_duration_min == 10
        assert plan.repeat_value == 0x7F

    async def test_write_start_time(self):
        """Write start_hour and start_minute."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        await cluster.write_attributes({cluster.AttributeDefs.start_hour.name: 16})
        assert cluster._start_hour == 16
        await cluster.write_attributes({cluster.AttributeDefs.start_minute.name: 45})
        assert cluster._start_minute == 45

    async def test_write_irrigation_mode_plan(self):
        """Write irrigation_mode for plan."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        cluster._irrigation_mode = SingleIrrigationMode.Duration
        await cluster.write_attributes(
            {cluster.AttributeDefs.irrigation_mode.name: SingleIrrigationMode.Volume}
        )
        assert cluster._irrigation_mode == SingleIrrigationMode.Volume

    async def test_write_total_duration_plan(self):
        """Write total_duration_min for plan."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        await cluster.write_attributes(
            {cluster.AttributeDefs.total_duration_min.name: 60}
        )
        assert cluster._total_duration_min == 60

    async def test_write_duration_plan(self):
        """Write duration_min for plan (in DWI mode)."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        cluster._irrigation_mode = SingleIrrigationMode.Duration_With_Interval
        cluster._total_duration_min = 60
        await cluster.write_attributes({cluster.AttributeDefs.duration_min.name: 25})
        assert cluster._duration_min == 25

    async def test_write_interval_plan(self):
        """Write interval_duration_min for plan (in DWI mode)."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        cluster._irrigation_mode = SingleIrrigationMode.Duration_With_Interval
        cluster._total_duration_min = 60
        await cluster.write_attributes(
            {cluster.AttributeDefs.interval_duration_min.name: 10}
        )
        assert cluster._interval_duration_min == 10

    async def test_write_amount_plan(self):
        """Write amount for plan (in Volume mode)."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        cluster._irrigation_mode = SingleIrrigationMode.Volume
        await cluster.write_attributes({cluster.AttributeDefs.amount.name: 600})
        assert cluster._amount == 600

    async def test_write_fail_safe_plan(self):
        """Write fail_safe_duration_min for plan (in Volume mode)."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        cluster._irrigation_mode = SingleIrrigationMode.Volume
        await cluster.write_attributes(
            {cluster.AttributeDefs.fail_safe_duration_min.name: 40}
        )
        assert cluster._fail_safe_duration_min == 40

    async def test_write_all_weekdays(self):
        """Write all weekday masks."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        await cluster.write_attributes({cluster.AttributeDefs.weekday_monday.name: 1})
        assert cluster._weekday_mask & 0x02
        await cluster.write_attributes({cluster.AttributeDefs.weekday_tuesday.name: 0})
        await cluster.write_attributes(
            {cluster.AttributeDefs.weekday_wednesday.name: 1}
        )
        assert cluster._weekday_mask & 0x08
        await cluster.write_attributes({cluster.AttributeDefs.weekday_thursday.name: 0})
        await cluster.write_attributes({cluster.AttributeDefs.weekday_friday.name: 1})
        assert cluster._weekday_mask & 0x20
        await cluster.write_attributes({cluster.AttributeDefs.weekday_saturday.name: 0})
        await cluster.write_attributes({cluster.AttributeDefs.weekday_sunday.name: 1})
        assert cluster._weekday_mask & 0x01

    async def test_dwi_interval_exceeds_total(self):
        """Interval > total raises in DWI mode."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        cluster._irrigation_mode = SingleIrrigationMode.Duration_With_Interval
        cluster._total_duration_min = 30
        cluster._interval_duration_min = 0
        with pytest.raises(ValueError):
            await cluster.write_attributes(
                {cluster.AttributeDefs.interval_duration_min.name: 50}
            )

    async def test_dwi_sum_exceeds_total(self):
        """Duration + interval > total raises in DWI mode."""
        cluster = self.device.endpoints[1].sonoff_irrigation_plan_config
        cluster._irrigation_mode = SingleIrrigationMode.Duration_With_Interval
        cluster._total_duration_min = 30
        cluster._duration_min = 25
        cluster._interval_duration_min = 25
        with pytest.raises(ValueError):
            await cluster.write_attributes(
                {
                    cluster.AttributeDefs.duration_min.name: 25,
                    cluster.AttributeDefs.interval_duration_min.name: 25,
                }
            )


# ============================================================================
# Write attributes — SonoffIrrigationPlanConfigClusterCh2
# ============================================================================


class TestIrrigationPlanConfigCh2Write:
    """Tests for SonoffIrrigationPlanConfigClusterCh2.write_attributes."""

    @pytest.fixture(autouse=True)
    def _setup(self, zigpy_device_from_v2_quirk):
        """Create device."""
        self.device = zigpy_device_from_v2_quirk(
            manufacturer="SONOFF",
            model="SWV-ZF2E",
            endpoint_ids=[1, 2],
            cluster_ids={
                1: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
                2: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
            },
        )

    async def test_write_plan_index(self):
        """Write plan_index for ch2."""
        cluster = self.device.endpoints[2].sonoff_irrigation_plan_config_ch2
        await cluster.write_attributes({cluster.AttributeDefs.plan_index.name: 4})
        assert cluster._plan_index == 4

    def test_plan_from_current_config_uses_ep1_unit(self):
        """Ch2 plan reads amount_unit from endpoint 1 global cluster."""
        cluster = self.device.endpoints[2].sonoff_irrigation_plan_config_ch2
        self.device.endpoints[1].sonoff_amount_unit_config.update_amount_unit(
            IrrigationAmountUnit.US_Gallon
        )
        cluster._irrigation_mode = SingleIrrigationMode.Volume
        plan = cluster._plan_from_current_config()
        assert plan.amount_unit == IrrigationAmountUnit.US_Gallon

    async def test_apply_plan_triggers_command(self):
        """apply_plan triggers ZCL command for ch2."""
        cluster = self.device.endpoints[2].sonoff_irrigation_plan_config_ch2
        swv = self.device.endpoints[2].sonoff_cluster
        cluster._plan_index = 0
        cluster._irrigation_mode = SingleIrrigationMode.Duration
        cluster._repeat_mode = IrrigationPlanRepeat.Odd_Day
        cluster._repeat_value = 0
        with mock.patch.object(swv, "command", mock.AsyncMock()) as mock_cmd:
            await cluster.write_attributes({cluster.AttributeDefs.apply_plan.name: 1})
        assert mock_cmd.call_count == 1

    async def test_remove_plan_triggers_command(self):
        """remove_plan triggers ZCL command for ch2."""
        cluster = self.device.endpoints[2].sonoff_irrigation_plan_config_ch2
        swv = self.device.endpoints[2].sonoff_cluster
        cluster._plan_index = 5
        with mock.patch.object(swv, "command", mock.AsyncMock()) as mock_cmd:
            await cluster.write_attributes({cluster.AttributeDefs.remove_plan.name: 1})
        assert mock_cmd.call_count == 1


class TestIrrigationPlanConfigCh2WriteFull:
    """Full branch coverage for ch2 write_attributes individual attrs."""

    @pytest.fixture(autouse=True)
    def _setup(self, zigpy_device_from_v2_quirk):
        """Create device."""
        self.device = zigpy_device_from_v2_quirk(
            manufacturer="SONOFF",
            model="SWV-ZF2E",
            endpoint_ids=[1, 2],
            cluster_ids={
                1: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
                2: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
            },
        )

    @property
    def c(self):
        """Shortcut for ch2 plan config cluster."""
        return self.device.endpoints[2].sonoff_irrigation_plan_config_ch2

    async def test_write_ch2_amount_in_duration_raises(self):
        """Amount in Duration mode raises."""
        self.c._irrigation_mode = SingleIrrigationMode.Duration
        with pytest.raises(ValueError):
            await self.c.write_attributes({self.c.AttributeDefs.amount.name: 100})

    async def test_write_ch2_total_duration_in_volume_raises(self):
        """total_duration in Volume mode raises."""
        self.c._irrigation_mode = SingleIrrigationMode.Volume
        with pytest.raises(ValueError):
            await self.c.write_attributes(
                {self.c.AttributeDefs.total_duration_min.name: 30}
            )

    async def test_write_ch2_duration_not_dwi_raises(self):
        """duration_min in non-DWI mode raises."""
        self.c._irrigation_mode = SingleIrrigationMode.Duration
        with pytest.raises(ValueError):
            await self.c.write_attributes({self.c.AttributeDefs.duration_min.name: 10})

    async def test_write_ch2_individual_attrs(self):
        """Write each individual ch2 attribute."""
        c = self.c

        await c.write_attributes({c.AttributeDefs.plan_index.name: 2})
        assert c._plan_index == 2

        await c.write_attributes({c.AttributeDefs.effective_year.name: 2027})
        assert c._effective_year == 2027

        await c.write_attributes({c.AttributeDefs.effective_month.name: 8})
        assert c._effective_month == 8

        await c.write_attributes({c.AttributeDefs.effective_day.name: 20})
        assert c._effective_day == 20

        await c.write_attributes(
            {c.AttributeDefs.repeat_mode.name: IrrigationPlanRepeat.Interval}
        )
        assert c._repeat_mode == IrrigationPlanRepeat.Interval

        await c.write_attributes({c.AttributeDefs.repeat_value.name: 7})
        assert c._repeat_value == 7

        # Switch to Duration to allow total_duration write
        c._irrigation_mode = SingleIrrigationMode.Duration
        await c.write_attributes({c.AttributeDefs.total_duration_min.name: 50})
        assert c._total_duration_min == 50

        c._irrigation_mode = SingleIrrigationMode.Duration_With_Interval
        await c.write_attributes({c.AttributeDefs.duration_min.name: 15})
        assert c._duration_min == 15

        await c.write_attributes({c.AttributeDefs.interval_duration_min.name: 5})
        assert c._interval_duration_min == 5

    async def test_write_ch2_weekdays(self):
        """Write weekday masks for ch2."""
        c = self.c
        await c.write_attributes({c.AttributeDefs.weekday_monday.name: 1})
        assert c._weekday_mask & 0x02
        await c.write_attributes({c.AttributeDefs.weekday_tuesday.name: 1})
        assert c._weekday_mask & 0x04
        await c.write_attributes({c.AttributeDefs.weekday_wednesday.name: 0})
        await c.write_attributes({c.AttributeDefs.weekday_thursday.name: 1})
        assert c._weekday_mask & 0x10
        await c.write_attributes({c.AttributeDefs.weekday_friday.name: 0})
        await c.write_attributes({c.AttributeDefs.weekday_saturday.name: 1})
        assert c._weekday_mask & 0x40
        await c.write_attributes({c.AttributeDefs.weekday_sunday.name: 1})
        assert c._weekday_mask & 0x01

    async def test_write_ch2_start_time(self):
        """Write start_hour and start_minute for ch2."""
        c = self.c
        await c.write_attributes({c.AttributeDefs.start_hour.name: 14})
        assert c._start_hour == 14
        await c.write_attributes({c.AttributeDefs.start_minute.name: 30})
        assert c._start_minute == 30

    async def test_ch2_dwi_validation_interval_exceeds_total(self):
        """Interval > total raises in DWI mode for ch2."""
        c = self.c
        c._irrigation_mode = SingleIrrigationMode.Duration_With_Interval
        c._total_duration_min = 30
        c._interval_duration_min = 0
        c._duration_min = 0
        with pytest.raises(ValueError):
            await c.write_attributes({c.AttributeDefs.interval_duration_min.name: 40})

    async def test_ch2_dwi_validation_sum_exceeds_total(self):
        """Duration + interval > total raises in DWI mode for ch2."""
        c = self.c
        c._irrigation_mode = SingleIrrigationMode.Duration_With_Interval
        c._total_duration_min = 30
        c._interval_duration_min = 20
        c._duration_min = 20
        with pytest.raises(ValueError):
            await c.write_attributes(
                {
                    c.AttributeDefs.duration_min.name: 20,
                    c.AttributeDefs.interval_duration_min.name: 20,
                }
            )


# ============================================================================
# Write attributes — SonoffUserDelayConfigCluster
# ============================================================================


class TestUserDelayConfigWrite:
    """Tests for SonoffUserDelayConfigCluster.write_attributes."""

    @pytest.fixture(autouse=True)
    def _setup(self, zigpy_device_from_v2_quirk):
        """Create device."""
        self.device = zigpy_device_from_v2_quirk(
            manufacturer="SONOFF",
            model="SWV-ZF2E",
            endpoint_ids=[1, 2],
            cluster_ids={
                1: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
                2: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
            },
        )

    async def test_write_delay_hours(self):
        """Write delay_hours clamps to valid range."""
        cluster = self.device.endpoints[1].sonoff_user_delay_config
        await cluster.write_attributes({cluster.AttributeDefs.delay_hours.name: 48})
        assert cluster._delay_hours == 48

    async def test_write_delay_hours_clamped_to_max(self):
        """delay_hours clamped to USER_DELAY_MAX_HOURS."""
        cluster = self.device.endpoints[1].sonoff_user_delay_config
        await cluster.write_attributes({cluster.AttributeDefs.delay_hours.name: 99999})
        assert cluster._delay_hours == USER_DELAY_MAX_HOURS

    async def test_write_delay_hours_clamped_to_min(self):
        """delay_hours clamped to 0."""
        cluster = self.device.endpoints[1].sonoff_user_delay_config
        await cluster.write_attributes({cluster.AttributeDefs.delay_hours.name: -5})
        assert cluster._delay_hours == 0

    async def test_write_timezone_offset(self):
        """Write timezone_offset_hours."""
        cluster = self.device.endpoints[1].sonoff_user_delay_config
        await cluster.write_attributes(
            {cluster.AttributeDefs.timezone_offset_hours.name: 8}
        )
        assert cluster._timezone_offset_hours == 8

    async def test_write_timezone_offset_clamped(self):
        """timezone_offset_hours clamped to -12..14."""
        cluster = self.device.endpoints[1].sonoff_user_delay_config
        await cluster.write_attributes(
            {cluster.AttributeDefs.timezone_offset_hours.name: 20}
        )
        assert cluster._timezone_offset_hours == 14

    async def test_apply_delay_sends_command(self):
        """apply_delay sends user_delay_set command."""
        cluster = self.device.endpoints[1].sonoff_user_delay_config
        swv = self.device.endpoints[1].sonoff_cluster
        cluster._delay_hours = 24
        with mock.patch.object(swv, "command", mock.AsyncMock()) as mock_cmd:
            await cluster.write_attributes({cluster.AttributeDefs.apply_delay.name: 1})
        assert mock_cmd.call_count == 1

    async def test_clear_delay_sends_zero_timestamp(self):
        """clear_delay sends command with 0 delay_end_timestamp."""
        cluster = self.device.endpoints[1].sonoff_user_delay_config
        swv = self.device.endpoints[1].sonoff_cluster
        with mock.patch.object(swv, "command", mock.AsyncMock()) as mock_cmd:
            await cluster.write_attributes({cluster.AttributeDefs.clear_delay.name: 1})
        assert mock_cmd.call_count == 1


# ============================================================================
# Write attributes — SonoffSeasonalAdjustmentConfigCluster
# ============================================================================


class TestSeasonalAdjustmentConfigWrite:
    """Tests for SonoffSeasonalAdjustmentConfigCluster.write_attributes."""

    @pytest.fixture(autouse=True)
    def _setup(self, zigpy_device_from_v2_quirk):
        """Create device."""
        self.device = zigpy_device_from_v2_quirk(
            manufacturer="SONOFF",
            model="SWV-ZF2E",
            endpoint_ids=[1, 2],
            cluster_ids={
                1: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
                2: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
            },
        )

    async def test_write_single_month(self):
        """Write a single month's adjustment."""
        cluster = self.device.endpoints[1].sonoff_seasonal_adjustment_config
        swv = self.device.endpoints[1].sonoff_cluster
        write_response = [
            [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
        ]
        with mock.patch.object(
            swv, "write_attributes", mock.AsyncMock(return_value=write_response)
        ):
            await cluster.write_attributes(
                {cluster.AttributeDefs.seasonal_adjustment_january.name: 8}
            )
        assert cluster._quarterly_adjustment.values[0] == 8
        assert (
            cluster._quarterly_adjustment.values[1]
            == QUARTERLY_ADJUSTMENT_DEFAULT_VALUE
        )


# ============================================================================
# _write_succeeded
# ============================================================================


class TestWriteSucceeded:
    """Tests for SonoffSingleIrrigationConfigCluster._write_succeeded."""

    def test_success_with_status_record_list(self):
        """Success with list of status records."""
        result = SonoffSingleIrrigationConfigCluster._write_succeeded(
            [[foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]]
        )
        assert result is True

    def test_failure_with_status_record(self):
        """Failure with a FAILURE status record."""
        result = SonoffSingleIrrigationConfigCluster._write_succeeded(
            [[foundation.WriteAttributesStatusRecord(status=foundation.Status.FAILURE)]]
        )
        assert result is False

    def test_empty_result(self):
        """Empty result returns False."""
        result = SonoffSingleIrrigationConfigCluster._write_succeeded([])
        assert result is False

    def test_with_status_records_attr(self):
        """WriteAttributesResponse with status_records attribute."""
        record = foundation.WriteAttributesStatusRecord(
            status=foundation.Status.SUCCESS
        )
        response = type("WriteAttributesResponse", (), {"status_records": [record]})()
        result = SonoffSingleIrrigationConfigCluster._write_succeeded([response])
        assert result is True

    def test_typeerror_in_iteration(self):
        """TypeError during record iteration returns False."""
        result = SonoffSingleIrrigationConfigCluster._write_succeeded([[42]])
        assert result is False


# ============================================================================
# Quirk model variants
# ============================================================================


class TestQuirkModelVariants:
    """Verify multiple SWV models can be instantiated."""

    @pytest.mark.parametrize(
        "model",
        [
            "SWV-ZF2E",
            "SWV-ZF2U",
            "SWV-ZN2E",
            "SWV-ZN2U",
            "SWV-ZF2",
            "SWV-ZNE",
            "SWV-ZNU",
        ],
    )
    def test_all_models(self, zigpy_device_from_v2_quirk, model):
        """All seven SWV models should create a valid quirked device."""
        device = zigpy_device_from_v2_quirk(
            manufacturer="SONOFF",
            model=model,
            endpoint_ids=[1, 2],
            cluster_ids={
                1: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
                2: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
            },
        )
        assert hasattr(device.endpoints[1], "sonoff_cluster")
        assert hasattr(device.endpoints[1], "sonoff_single_irrigation_config")
        assert hasattr(device.endpoints[1], "sonoff_irrigation_plan_config")
        assert hasattr(device.endpoints[1], "sonoff_user_delay_config")
        assert hasattr(device.endpoints[1], "sonoff_amount_unit_config")
        assert hasattr(device.endpoints[1], "sonoff_seasonal_adjustment_config")
        assert hasattr(device.endpoints[2], "sonoff_irrigation_plan_config_ch2")


# ============================================================================
# Sensor/binary_sensor entities from add_common_entities
# ============================================================================


class TestCommonEntities:
    """Verify entities created by add_common_entities."""

    @pytest.fixture(autouse=True)
    def _setup(self, zigpy_device_from_v2_quirk):
        """Create device."""
        self.device = zigpy_device_from_v2_quirk(
            manufacturer="SONOFF",
            model="SWV-ZF2E",
            endpoint_ids=[1, 2],
            cluster_ids={
                1: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
                2: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
            },
        )
        self.swv = self.device.endpoints[1].sonoff_cluster

    def test_valve_state_leak_detection(self):
        """ValveState Water_Leakage bit triggers binary_sensor."""
        listener = ClusterListener(self.swv)
        self.swv.update_attribute(
            SonoffWaterValveCluster.AttributeDefs.valve_abnormal_state.id,
            ValveState.Water_Leakage,
        )
        assert len(listener.attribute_updates) >= 1

    def test_valve_state_water_shortage(self):
        """ValveState Water_Shortage triggers binary_sensor."""
        listener = ClusterListener(self.swv)
        self.swv.update_attribute(
            SonoffWaterValveCluster.AttributeDefs.valve_abnormal_state.id,
            ValveState.Water_Shortage,
        )
        assert len(listener.attribute_updates) >= 1

    def test_child_lock_switch(self):
        """Child lock attribute update."""
        listener = ClusterListener(self.swv)
        self.swv.update_attribute(
            SonoffWaterValveCluster.AttributeDefs.child_lock.id, True
        )
        assert len(listener.attribute_updates) >= 1

    def test_valve_state_normal(self):
        """ValveState Normal triggers binary_sensor."""
        listener = ClusterListener(self.swv)
        self.swv.update_attribute(
            SonoffWaterValveCluster.AttributeDefs.valve_abnormal_state.id,
            ValveState.Normal,
        )
        assert len(listener.attribute_updates) >= 1

    def test_daily_irrigation_volume(self):
        """Daily irrigation volume attribute triggers sensor."""
        listener = ClusterListener(self.swv)
        self.swv.update_attribute(
            SonoffWaterValveCluster.AttributeDefs.daily_irrigation_volume.id, 12345
        )
        assert len(listener.attribute_updates) >= 1

    def test_weather_delay(self):
        """Weather delay duration attribute triggers sensor."""
        listener = ClusterListener(self.swv)
        self.swv.update_attribute(
            SonoffWaterValveCluster.AttributeDefs.weather_delay_duration.id, 120
        )
        assert len(listener.attribute_updates) >= 1

    def test_daily_irrigation_duration(self):
        """Daily irrigation duration attribute triggers sensor."""
        listener = ClusterListener(self.swv)
        self.swv.update_attribute(
            SonoffWaterValveCluster.AttributeDefs.daily_irrigation_duration.id, 3600
        )
        assert len(listener.attribute_updates) >= 1


# ============================================================================
# Unsupported repeat mode
# ============================================================================


class TestRepeatModeUnsupported:
    """Tests for unsupported repeat mode."""

    def test_unsupported_repeat_mode_raises(self):
        """An unsupported repeat_mode should raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported"):
            _repeat_to_loop_info(99, 0)


# ============================================================================
# More edge cases
# ============================================================================


class TestMoreEdgeCases:
    """Additional edge case tests."""

    def test_single_irrigation_array_wrapper_direct(self):
        """Call single_irrigation_array_from_payload directly."""
        payload = bytes([SingleIrrigationMode.Duration] + [0] * 11)
        result = single_irrigation_array_from_payload(payload)
        assert isinstance(result, SingleIrrigationPayload)

    def test_payload_from_array_with_bytes_value(self):
        """Array where value.value is bytes."""
        arr = foundation.Array(
            type=foundation.DataTypeId.uint8,
            value=bytes(
                [SingleIrrigationMode.Duration, 0, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            ),
        )
        result = single_irrigation_payload_from_array(arr)
        assert isinstance(result, bytes)
        assert len(result) == SINGLE_IRRIGATION_PAYLOAD_LEN

    def test_lvlist_with_bytearray(self):
        """Coerce from bytearray."""
        result = SingleIrrigationPayload._coerce_value(
            bytearray([SingleIrrigationMode.Duration] + [0] * 11)
        )
        assert isinstance(result, bytes)


class TestCh2WriteMore:
    """More branch coverage for ch2 write_attributes."""

    @pytest.fixture(autouse=True)
    def _setup(self, zigpy_device_from_v2_quirk):
        """Create device."""
        self.device = zigpy_device_from_v2_quirk(
            manufacturer="SONOFF",
            model="SWV-ZF2E",
            endpoint_ids=[1, 2],
            cluster_ids={
                1: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
                2: {SonoffWaterValveCluster.cluster_id: ClusterType.Server},
            },
        )

    @property
    def c(self):
        """Shortcut for ch2 plan config cluster."""
        return self.device.endpoints[2].sonoff_irrigation_plan_config_ch2

    async def test_write_ch2_irrigation_mode(self):
        """Write irrigation_mode for ch2."""
        self.c._irrigation_mode = SingleIrrigationMode.Duration
        await self.c.write_attributes(
            {self.c.AttributeDefs.irrigation_mode.name: SingleIrrigationMode.Volume}
        )
        assert self.c._irrigation_mode == SingleIrrigationMode.Volume

    async def test_write_ch2_amount(self):
        """Write amount for ch2 in Volume mode."""
        self.c._irrigation_mode = SingleIrrigationMode.Volume
        await self.c.write_attributes({self.c.AttributeDefs.amount.name: 700})
        assert self.c._amount == 700

    async def test_write_ch2_fail_safe(self):
        """Write fail_safe_duration_min for ch2 in Volume mode."""
        self.c._irrigation_mode = SingleIrrigationMode.Volume
        await self.c.write_attributes(
            {self.c.AttributeDefs.fail_safe_duration_min.name: 45}
        )
        assert self.c._fail_safe_duration_min == 45

    async def test_ch2_dwi_duration_exceeds_total(self):
        """Duration > total raises in DWI mode for ch2."""
        c = self.c
        c._irrigation_mode = SingleIrrigationMode.Duration_With_Interval
        c._total_duration_min = 30
        c._duration_min = 0
        with pytest.raises(ValueError):
            await c.write_attributes(
                {
                    c.AttributeDefs.duration_min.name: 50,
                    c.AttributeDefs.total_duration_min.name: 30,
                }
            )
