"""Tests for Sonoff SWV dual-channel Zigbee water valve quirk."""

from datetime import UTC, datetime

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
    IrrigationAmountUnit,
    IrrigationLoopType,
    IrrigationPlan,
    IrrigationPlanRepeat,
    ManualIrrigationMode,
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
    single_irrigation_payload_from_array,
)

zhaquirks.setup()

# ---------------------------------------------------------------------------
# Binary helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Single irrigation payload encode / decode
# ---------------------------------------------------------------------------


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

    def test_encode_duration_with_interval_defaults_to_duration(self):
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
                bytes(
                    [
                        SingleIrrigationMode.Duration,
                        0,
                        10,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                    ]
                )
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


# ---------------------------------------------------------------------------
# Irrigation plan payload encode
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Quarterly adjustment
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# IrrigationPlan dataclass
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Integration tests (v2 quirk fixture)
# ---------------------------------------------------------------------------


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
