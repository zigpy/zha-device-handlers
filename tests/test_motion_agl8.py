"""Tests for Aqara FP300 (lumi.sensor_occupy.agl8)."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, PowerConfiguration

from tests.common import ClusterListener
from zhaquirks.xiaomi import (
    AQARA,
    BATTERY_PERCENTAGE_REMAINING_ATTRIBUTE,
    BATTERY_VOLTAGE_MV,
    XIAOMI_AQARA_ATTRIBUTE_E1,
)
from zhaquirks.xiaomi.aqara.motion_agl8 import (
    AQARA_MANUFACTURER_CODE,
    MANU_ATTR_BATTERY_PERCENT,
    MANU_ATTR_BATTERY_VOLTAGE,
    AqaraFP300ManuCluster,
    FP300DetectionRangeCluster,
    FP300LedScheduleCluster,
    FP300PowerConfigurationVoltage,
)


def create_aqara_attr_report(attributes):
    """Create an Aqara E1 TLV report payload."""
    serialized_data = b""
    for key, value in attributes.items():
        tv = foundation.TypeValue(0x39, t.Single(value))
        serialized_data += bytes([key]) + tv.serialize()
    return serialized_data


def test_fp300_device_creation(zigpy_device_from_v2_quirk):
    """Test that the FP300 quirked device is created as expected."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")

    assert device.manufacturer == AQARA
    assert device.model == "lumi.sensor_occupy.agl8"
    assert 1 in device.endpoints
    assert Basic.cluster_id in device.endpoints[1].in_clusters


def test_fp300_endpoint_clusters_present(zigpy_device_from_v2_quirk):
    """Test that endpoint 1 contains all FP300 custom clusters."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    endpoint = device.endpoints[1]

    assert AqaraFP300ManuCluster.cluster_id in endpoint.in_clusters
    assert isinstance(endpoint.aqara_fp300_manu, AqaraFP300ManuCluster)

    assert FP300DetectionRangeCluster.cluster_id in endpoint.in_clusters
    assert isinstance(endpoint.fp300_detection_range, FP300DetectionRangeCluster)

    assert FP300LedScheduleCluster.cluster_id in endpoint.in_clusters
    assert isinstance(endpoint.fp300_led_schedule, FP300LedScheduleCluster)


def test_fp300_power_configuration_cluster_present(zigpy_device_from_v2_quirk):
    """Test that endpoint 1 exposes FP300 power configuration cluster."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    endpoint = device.endpoints[1]

    assert PowerConfiguration.cluster_id in endpoint.in_clusters
    assert isinstance(
        endpoint.in_clusters[PowerConfiguration.cluster_id],
        FP300PowerConfigurationVoltage,
    )


def test_aqara_fp300_battery_from_e1_tlv(zigpy_device_from_v2_quirk):
    """Test battery updates from Aqara E1 TLV report."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")

    manu_cluster = device.endpoints[1].in_clusters[AqaraFP300ManuCluster.cluster_id]
    power_cluster = device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)

    zcl_power_voltage_id = PowerConfiguration.AttributeDefs.battery_voltage.id
    zcl_power_percent_id = (
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
    )

    manu_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE_E1,
        create_aqara_attr_report({23: 306, 24: 100}),
    )

    assert len(power_listener.attribute_updates) == 2
    assert power_listener.attribute_updates[0][0] == zcl_power_voltage_id
    assert power_listener.attribute_updates[0][1] == pytest.approx(30.6)
    assert power_listener.attribute_updates[1][0] == zcl_power_percent_id
    assert power_listener.attribute_updates[1][1] == 200


@pytest.mark.parametrize(
    "tlv_voltage, expected_voltage, expected_percent",
    (
        (306, 30.6, 200),
        (320, 32.0, 200),
        (2950, 29.5, 150),
        (2750, 27.5, 0),
    ),
)
def test_aqara_fp300_battery_tlv_scaling(
    zigpy_device_from_v2_quirk, tlv_voltage, expected_voltage, expected_percent
):
    """Test TLV voltage scaling in units of 10 mV and mV plausibility window."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")

    manu_cluster = device.endpoints[1].in_clusters[AqaraFP300ManuCluster.cluster_id]
    power_cluster = device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)

    manu_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE_E1,
        create_aqara_attr_report({23: tlv_voltage}),
    )

    assert len(power_listener.attribute_updates) == 2
    assert power_listener.attribute_updates[0][1] == pytest.approx(expected_voltage)
    assert power_listener.attribute_updates[1][1] == expected_percent


def test_aqara_fp300_drops_device_battery_reports(zigpy_device_from_v2_quirk):
    """Test that standard power cluster battery reports do not override TLV values."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")

    manu_cluster = device.endpoints[1].in_clusters[AqaraFP300ManuCluster.cluster_id]
    power_cluster = device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)

    zcl_power_voltage_id = PowerConfiguration.AttributeDefs.battery_voltage.id
    zcl_power_percent_id = (
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
    )

    manu_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE_E1,
        create_aqara_attr_report({23: 320}),
    )
    assert len(power_listener.attribute_updates) == 2

    power_cluster.update_attribute(zcl_power_voltage_id, 3)
    power_cluster.update_attribute(zcl_power_percent_id, 200)

    assert len(power_listener.attribute_updates) == 2
    assert power_listener.attribute_updates[0][1] == pytest.approx(32.0)
    assert power_listener.attribute_updates[1][1] == 200


@pytest.mark.parametrize("tlv_voltage", (0, 50, 100, 4500))
def test_aqara_fp300_battery_tlv_out_of_window(zigpy_device_from_v2_quirk, tlv_voltage):
    """Test that implausible TLV voltages leave the cache untouched."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")

    manu_cluster = device.endpoints[1].in_clusters[AqaraFP300ManuCluster.cluster_id]
    power_cluster = device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)

    manu_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE_E1,
        create_aqara_attr_report({23: tlv_voltage}),
    )

    assert len(power_listener.attribute_updates) == 0


@pytest.mark.parametrize(
    "raw_payload, expected_segments",
    (
        (t.LVBytes(bytes.fromhex("0003ffffff")), [True, True, True, True, True, True]),
        (t.LVBytes(bytes.fromhex("0003f0ffff")), [False, True, True, True, True, True]),
        (
            t.LVBytes(bytes.fromhex("000300ffff")),
            [False, False, True, True, True, True],
        ),
        (
            t.LVBytes(bytes.fromhex("000300f0ff")),
            [False, False, False, True, True, True],
        ),
        (
            t.LVBytes(bytes.fromhex("00030000ff")),
            [False, False, False, False, True, True],
        ),
        (
            t.LVBytes(bytes.fromhex("00030000f0")),
            [False, False, False, False, False, True],
        ),
        (
            t.LVBytes(bytes.fromhex("0003000000")),
            [False, False, False, False, False, False],
        ),
    ),
)
def test_fp300_detection_range_apply_raw(
    zigpy_device_from_v2_quirk, raw_payload, expected_segments
):
    """Test detection range raw payload decoding."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    dr_cluster = device.endpoints[1].fp300_detection_range

    dr_cluster.apply_raw(raw_payload)

    seg_ids = [
        FP300DetectionRangeCluster.AttributeDefs.range_0_1m.id,
        FP300DetectionRangeCluster.AttributeDefs.range_1_2m.id,
        FP300DetectionRangeCluster.AttributeDefs.range_2_3m.id,
        FP300DetectionRangeCluster.AttributeDefs.range_3_4m.id,
        FP300DetectionRangeCluster.AttributeDefs.range_4_5m.id,
        FP300DetectionRangeCluster.AttributeDefs.range_5_6m.id,
    ]
    actual = [bool(dr_cluster._attr_cache.get(attr_id, False)) for attr_id in seg_ids]
    assert actual == expected_segments


def test_fp300_detection_range_apply_raw_invalid_length_keeps_state(
    zigpy_device_from_v2_quirk,
):
    """Test invalid detection payload length leaves current values unchanged."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    dr_cluster = device.endpoints[1].fp300_detection_range
    seg_ids = [
        FP300DetectionRangeCluster.AttributeDefs.range_0_1m.id,
        FP300DetectionRangeCluster.AttributeDefs.range_1_2m.id,
        FP300DetectionRangeCluster.AttributeDefs.range_2_3m.id,
        FP300DetectionRangeCluster.AttributeDefs.range_3_4m.id,
        FP300DetectionRangeCluster.AttributeDefs.range_4_5m.id,
        FP300DetectionRangeCluster.AttributeDefs.range_5_6m.id,
    ]

    dr_cluster.apply_raw(t.LVBytes(bytes.fromhex("0003ffffff")))
    before = [dr_cluster.get(attr_id) for attr_id in seg_ids]

    dr_cluster.apply_raw(b"\x00\x03\xff\xff")

    assert [dr_cluster.get(attr_id) for attr_id in seg_ids] == before


@pytest.mark.asyncio
async def test_fp300_detection_range_write_attributes_uses_cached_mask(
    zigpy_device_from_v2_quirk,
):
    """Test range writes are merged into the cached raw mask."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu
    dr_cluster = device.endpoints[1].fp300_detection_range

    initial_mask = 0xE00303
    manu_cluster._update_attribute(
        AqaraFP300ManuCluster.AttributeDefs.detection_range_raw.id,
        t.LVBytes(b"\x00\x03" + initial_mask.to_bytes(3, "little")),
    )

    manu_cluster.write_attributes = mock.AsyncMock(
        return_value=[
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]
    )

    target_attr = FP300DetectionRangeCluster.AttributeDefs.range_2_3m.id
    await dr_cluster.write_attributes({target_attr: False})

    expected_mask = initial_mask & ~(0xF << 8)
    expected_raw = t.LVBytes(b"\x00\x03" + expected_mask.to_bytes(3, "little"))

    manu_cluster.write_attributes.assert_awaited_once_with(
        {AqaraFP300ManuCluster.AttributeDefs.detection_range_raw.id: expected_raw},
        manufacturer=AQARA_MANUFACTURER_CODE,
    )


@pytest.mark.asyncio
async def test_fp300_detection_range_write_attributes_without_cache_uses_full_mask(
    zigpy_device_from_v2_quirk,
):
    """Test range writes default to full mask when no raw cache is present."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu
    dr_cluster = device.endpoints[1].fp300_detection_range

    manu_cluster.write_attributes = mock.AsyncMock(
        return_value=[
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]
    )

    target_attr = FP300DetectionRangeCluster.AttributeDefs.range_0_1m.id
    await dr_cluster.write_attributes({target_attr: False})

    expected_mask = 0xFFFFF0
    expected_raw = t.LVBytes(b"\x00\x03" + expected_mask.to_bytes(3, "little"))
    manu_cluster.write_attributes.assert_awaited_once_with(
        {AqaraFP300ManuCluster.AttributeDefs.detection_range_raw.id: expected_raw},
        manufacturer=AQARA_MANUFACTURER_CODE,
    )


@pytest.mark.asyncio
async def test_fp300_detection_range_write_attributes_enable_segment(
    zigpy_device_from_v2_quirk,
):
    """Test enabling a segment restores its nibble in the outgoing mask."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu
    dr_cluster = device.endpoints[1].fp300_detection_range

    initial_mask = 0xFFFF0F
    manu_cluster._update_attribute(
        AqaraFP300ManuCluster.AttributeDefs.detection_range_raw.id,
        t.LVBytes(b"\x00\x03" + initial_mask.to_bytes(3, "little")),
    )

    manu_cluster.write_attributes = mock.AsyncMock(
        return_value=[
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]
    )

    target_attr = FP300DetectionRangeCluster.AttributeDefs.range_1_2m.id
    await dr_cluster.write_attributes({target_attr: True})

    expected_raw = t.LVBytes(bytes.fromhex("0003ffffff"))
    manu_cluster.write_attributes.assert_awaited_once_with(
        {AqaraFP300ManuCluster.AttributeDefs.detection_range_raw.id: expected_raw},
        manufacturer=AQARA_MANUFACTURER_CODE,
    )


def test_fp300_led_schedule_apply_raw_unpacks_hours(zigpy_device_from_v2_quirk):
    """Test LED schedule raw value is unpacked into start/end hour."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    led_cluster = device.endpoints[1].fp300_led_schedule

    led_cluster.apply_raw(0x00090015)

    assert (
        led_cluster.get(
            FP300LedScheduleCluster.AttributeDefs.led_off_schedule_start_hour.id
        )
        == 21
    )
    assert (
        led_cluster.get(
            FP300LedScheduleCluster.AttributeDefs.led_off_schedule_end_hour.id
        )
        == 9
    )


@pytest.mark.asyncio
async def test_fp300_led_schedule_write_updates_start_only(zigpy_device_from_v2_quirk):
    """Test LED schedule write updates one field and preserves the other."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu
    led_cluster = device.endpoints[1].fp300_led_schedule

    manu_cluster._update_attribute(
        AqaraFP300ManuCluster.AttributeDefs.led_schedule_time_raw.id,
        0x00090015,
    )
    manu_cluster.write_attributes = mock.AsyncMock(
        return_value=[
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]
    )

    await led_cluster.write_attributes(
        {FP300LedScheduleCluster.AttributeDefs.led_off_schedule_start_hour.id: 18}
    )

    manu_cluster.write_attributes.assert_awaited_once_with(
        {AqaraFP300ManuCluster.AttributeDefs.led_schedule_time_raw.id: 0x00090012},
        manufacturer=AQARA_MANUFACTURER_CODE,
    )


@pytest.mark.asyncio
async def test_fp300_led_schedule_write_updates_both_values(zigpy_device_from_v2_quirk):
    """Test LED schedule write updates start and end in one call."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu
    led_cluster = device.endpoints[1].fp300_led_schedule

    manu_cluster._update_attribute(
        AqaraFP300ManuCluster.AttributeDefs.led_schedule_time_raw.id,
        0x00090015,
    )
    manu_cluster.write_attributes = mock.AsyncMock(
        return_value=[
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]
    )

    await led_cluster.write_attributes(
        {
            FP300LedScheduleCluster.AttributeDefs.led_off_schedule_start_hour.id: 20,
            FP300LedScheduleCluster.AttributeDefs.led_off_schedule_end_hour.id: 8,
        }
    )

    manu_cluster.write_attributes.assert_awaited_once_with(
        {AqaraFP300ManuCluster.AttributeDefs.led_schedule_time_raw.id: 0x00080014},
        manufacturer=AQARA_MANUFACTURER_CODE,
    )


@pytest.mark.asyncio
async def test_fp300_led_schedule_write_uses_default_when_missing(
    zigpy_device_from_v2_quirk,
):
    """Test LED schedule write uses default packed value when raw cache is empty."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu
    led_cluster = device.endpoints[1].fp300_led_schedule

    manu_cluster.write_attributes = mock.AsyncMock(
        return_value=[
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]
    )

    await led_cluster.write_attributes(
        {FP300LedScheduleCluster.AttributeDefs.led_off_schedule_end_hour.id: 8}
    )

    manu_cluster.write_attributes.assert_awaited_once_with(
        {AqaraFP300ManuCluster.AttributeDefs.led_schedule_time_raw.id: 0x00080015},
        manufacturer=AQARA_MANUFACTURER_CODE,
    )


def test_manu_cluster_forwards_raw_updates_to_local_helper_clusters(
    zigpy_device_from_v2_quirk,
):
    """Test manufacturer cluster forwards range and LED raw updates to local clusters."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    endpoint = device.endpoints[1]

    manu_cluster = endpoint.aqara_fp300_manu
    dr_cluster = endpoint.fp300_detection_range
    led_cluster = endpoint.fp300_led_schedule

    manu_cluster._update_attribute(
        AqaraFP300ManuCluster.AttributeDefs.detection_range_raw.id,
        t.LVBytes(bytes.fromhex("0003f0ffff")),
    )
    assert (
        dr_cluster.get(FP300DetectionRangeCluster.AttributeDefs.range_0_1m.id) is False
    )
    assert (
        dr_cluster.get(FP300DetectionRangeCluster.AttributeDefs.range_1_2m.id) is True
    )

    manu_cluster._update_attribute(
        AqaraFP300ManuCluster.AttributeDefs.led_schedule_time_raw.id,
        0x00070014,
    )
    assert (
        led_cluster.get(
            FP300LedScheduleCluster.AttributeDefs.led_off_schedule_start_hour.id
        )
        == 20
    )
    assert (
        led_cluster.get(
            FP300LedScheduleCluster.AttributeDefs.led_off_schedule_end_hour.id
        )
        == 7
    )


def test_fp300_parse_aqara_attributes_maps_fp300_battery_keys(
    zigpy_device_from_v2_quirk,
):
    """Test FP300-specific battery keys are remapped from Aqara TLV output."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu

    base_attrs = {
        MANU_ATTR_BATTERY_VOLTAGE: 2950,
        MANU_ATTR_BATTERY_PERCENT: 87,
        "keep_me": 123,
    }
    with mock.patch.object(
        AqaraFP300ManuCluster.__bases__[0],
        "_parse_aqara_attributes",
        return_value=base_attrs.copy(),
    ):
        result = manu_cluster._parse_aqara_attributes(b"ignored")

    assert result[BATTERY_VOLTAGE_MV] == 2950
    assert result[BATTERY_PERCENTAGE_REMAINING_ATTRIBUTE] == 87
    assert MANU_ATTR_BATTERY_VOLTAGE not in result
    assert MANU_ATTR_BATTERY_PERCENT not in result
    assert result["keep_me"] == 123


@pytest.mark.asyncio
async def test_fp300_manu_cluster_bind_reads_initial_attrs(zigpy_device_from_v2_quirk):
    """Test manufacturer bind reads detection-range and LED schedule raw attributes."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu

    with mock.patch.object(
        AqaraFP300ManuCluster.__bases__[0], "bind", new_callable=mock.AsyncMock
    ) as mock_bind:
        mock_bind.return_value = foundation.Status.SUCCESS
        manu_cluster.read_attributes = mock.AsyncMock(return_value={})

        result = await manu_cluster.bind()

    assert result == foundation.Status.SUCCESS
    assert manu_cluster.read_attributes.await_count == 2
    manu_cluster.read_attributes.assert_any_await(
        [AqaraFP300ManuCluster.AttributeDefs.detection_range_raw.id],
        allow_cache=False,
        manufacturer=AQARA_MANUFACTURER_CODE,
    )
    manu_cluster.read_attributes.assert_any_await(
        [AqaraFP300ManuCluster.AttributeDefs.led_schedule_time_raw.id],
        allow_cache=False,
        manufacturer=AQARA_MANUFACTURER_CODE,
    )


@pytest.mark.asyncio
async def test_fp300_manu_cluster_bind_logs_read_errors(zigpy_device_from_v2_quirk):
    """Test manufacturer bind continues when initial read raises exceptions."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu

    with mock.patch.object(
        AqaraFP300ManuCluster.__bases__[0], "bind", new_callable=mock.AsyncMock
    ) as mock_bind:
        mock_bind.return_value = foundation.Status.SUCCESS
        manu_cluster.read_attributes = mock.AsyncMock(
            side_effect=[RuntimeError("first"), RuntimeError("second")]
        )
        manu_cluster.debug = mock.Mock()

        result = await manu_cluster.bind()

    assert result == foundation.Status.SUCCESS
    assert manu_cluster.read_attributes.await_count == 2
    assert manu_cluster.debug.call_count == 2
