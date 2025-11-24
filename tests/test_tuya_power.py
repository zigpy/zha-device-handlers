"""Tests for Tuya quirks."""

import pytest
from zigpy.zcl import foundation

import zhaquirks
import zhaquirks.tuya

zhaquirks.setup()


@pytest.mark.parametrize(
    "msg,attr_suffix,expected_power,expected_current,expected_volt",
    [
        (b"\t0\x02\x00\xd3\x06\x00\x00\x08\tn\x00\nA\x00\x01\xa6", "", 422, 2625, 2414),
        (b"\t2\x02\x00Z\x06\x00\x00\x08\ts\x00\n9\x00\x01\xa5", "", 421, 2617, 2419),
        (b"\t2\x02\x00Z\x06\x00\x00\x08\ts\x00\n9\x00\x91\xa5", "", -2037, 2617, 2419),
        (
            b"\t0\x02\x00\xd3\x07\x00\x00\x08\tn\x00\nA\x00\x01\xa6",
            "_ph_b",
            422,
            2625,
            2414,
        ),
        (
            b"\t2\x02\x00Z\x07\x00\x00\x08\ts\x00\n9\x00\x01\xa5",
            "_ph_b",
            421,
            2617,
            2419,
        ),
        (
            b"\t0\x02\x00\xd3\x08\x00\x00\x08\tn\x00\nA\x00\x01\xa6",
            "_ph_c",
            422,
            2625,
            2414,
        ),
        (
            b"\t2\x02\x00Z\x08\x00\x00\x08\ts\x00\n9\x00\x01\xa5",
            "_ph_c",
            421,
            2617,
            2419,
        ),
    ],
)
async def test_ts0601_electrical_measurement_multi_dp_converter(
    zigpy_device_from_v2_quirk,
    msg,
    attr_suffix,
    expected_power,
    expected_current,
    expected_volt,
):
    """Test converter for multiple electrical attributes mapped to the same tuya datapoint."""

    quirked = zigpy_device_from_v2_quirk("_TZE200_nslr42tt", "TS0601")
    ep = quirked.endpoints[1]

    tuya_manufacturer = ep.tuya_manufacturer
    hdr, data = tuya_manufacturer.deserialize(msg)
    status = tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    electrical_meas_cluster = ep.electrical_measurement
    assert electrical_meas_cluster.get("active_power" + attr_suffix) == expected_power
    assert electrical_meas_cluster.get("rms_current" + attr_suffix) == expected_current
    assert electrical_meas_cluster.get("rms_voltage" + attr_suffix) == expected_volt


@pytest.mark.parametrize(
    "msg,expected_power",
    [
        (b"\x19\x8a\x02\x00\x0f\t\x02\x00\x04\x00\x00\x00\x80", 128),
        (b"\x19\x8a\x02\x00\x0f\t\x02\x00\x04\x19\x99\x99\x00", -156),
    ],
)
async def test_ts0601_power_converter(zigpy_device_from_v2_quirk, msg, expected_power):
    """Test converter for power."""

    quirked = zigpy_device_from_v2_quirk("_TZE200_nslr42tt", "TS0601")
    ep = quirked.endpoints[1]

    tuya_manufacturer = ep.tuya_manufacturer
    hdr, data = tuya_manufacturer.deserialize(msg)
    status = tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert tuya_manufacturer.get("power") == expected_power


@pytest.mark.parametrize(
    "manufacturer,power_a_msg,flow_a_msg,power_b_msg,flow_b_msg,expected_power_a,expected_power_b,expected_total",
    [
        # Forward flow for both CTs - _TZE204 model
        (
            "_TZE204_81yrt3lo",
            b"\x09\x1f\x02\x00\x04\x65\x02\x00\x04\x00\x00\x03\xe8",  # DP 101: power_a = 1000
            b"\x09\x11\x02\x00\x87\x66\x04\x00\x01\x00",  # DP 102: energy_flow_a = 0 (Forward)
            b"\x09\x1f\x02\x00\x04\x69\x02\x00\x04\x00\x00\x01\xf4",  # DP 105: power_b = 500
            b"\x09\x11\x02\x00\x87\x68\x04\x00\x01\x00",  # DP 104: energy_flow_b = 0 (Forward)
            1000,  # Expected power A (positive for forward)
            500,  # Expected power B (positive for forward)
            1500,  # Expected total
        ),
        # Reverse flow for both CTs - _TZE204 model
        (
            "_TZE204_81yrt3lo",
            b"\x09\x1f\x02\x00\x04\x65\x02\x00\x04\x00\x00\x03\xe8",  # DP 101: power_a = 1000
            b"\x09\x0a\x02\x00\x80\x66\x04\x00\x01\x01",  # DP 102: energy_flow_a = 1 (Reverse)
            b"\x09\x1f\x02\x00\x04\x69\x02\x00\x04\x00\x00\x01\xf4",  # DP 105: power_b = 500
            b"\x09\x0a\x02\x00\x80\x68\x04\x00\x01\x01",  # DP 104: energy_flow_b = 1 (Reverse)
            -1000,  # Expected power A (negative for reverse)
            -500,  # Expected power B (negative for reverse)
            -1500,  # Expected total
        ),
        # Mixed flow directions - _TZE204 model
        (
            "_TZE204_81yrt3lo",
            b"\x09\x1f\x02\x00\x04\x65\x02\x00\x04\x00\x00\x04\x00",  # DP 101: power_a = 1024
            b"\x09\x11\x02\x00\x87\x66\x04\x00\x01\x00",  # DP 102: energy_flow_a = 0 (Forward)
            b"\x09\x0a\x02\x00\x04\x69\x02\x00\x04\x00\x00\x02\x00",  # DP 105: power_b = 512
            b"\x09\x0a\x02\x00\x80\x68\x04\x00\x01\x01",  # DP 104: energy_flow_b = 1 (Reverse)
            1024,  # Expected power A (positive for forward)
            -512,  # Expected power B (negative for reverse)
            512,  # Expected total (1024 - 512)
        ),
        # Forward flow for both CTs - _TZE284 model
        (
            "_TZE284_81yrt3lo",
            b"\x09\x1f\x02\x00\x04\x65\x02\x00\x04\x00\x00\x03\xe8",  # DP 101: power_a = 1000
            b"\x09\x11\x02\x00\x87\x66\x04\x00\x01\x00",  # DP 102: energy_flow_a = 0 (Forward)
            b"\x09\x1f\x02\x00\x04\x69\x02\x00\x04\x00\x00\x01\xf4",  # DP 105: power_b = 500
            b"\x09\x11\x02\x00\x87\x68\x04\x00\x01\x00",  # DP 104: energy_flow_b = 0 (Forward)
            1000,  # Expected power A (positive for forward)
            500,  # Expected power B (positive for forward)
            1500,  # Expected total
        ),
    ],
)
async def test_matseeplus_power_reporting(
    zigpy_device_from_v2_quirk,
    manufacturer,
    power_a_msg,
    flow_a_msg,
    power_b_msg,
    flow_b_msg,
    expected_power_a,
    expected_power_b,
    expected_total,
):
    """Test power reporting using Tuya DP messages with default settings (late flow mitigation disabled)."""
    quirked = zigpy_device_from_v2_quirk(manufacturer, "TS0601")
    ep = quirked.endpoints[1]

    tuya_manufacturer = ep.tuya_manufacturer

    def send_dp_message(msg):
        """Send and verify a DP message."""
        hdr, data = tuya_manufacturer.deserialize(msg)
        status = tuya_manufacturer.handle_get_data(data.data)
        assert status == foundation.Status.SUCCESS

    # Send messages in order: flow first, then power (flow is sent first for correct sign application)
    send_dp_message(flow_a_msg)
    send_dp_message(power_a_msg)
    send_dp_message(flow_b_msg)
    send_dp_message(power_b_msg)

    # Check power values on electrical measurement clusters
    ep1_electrical = quirked.endpoints[1].electrical_measurement
    ep2_electrical = quirked.endpoints[2].electrical_measurement
    ep3_electrical = quirked.endpoints[3].electrical_measurement

    assert ep1_electrical.get("active_power") == expected_power_a
    assert ep2_electrical.get("active_power") == expected_power_b
    assert ep3_electrical.get("active_power") == expected_total


@pytest.mark.parametrize(
    "msg,endpoint_id,cluster_name,attr_name,expected_value",
    [
        # Metering DP messages
        (
            b"\x09\x1f\x02\x00\x04\x6a\x02\x00\x04\x00\x00\x30\x39",
            1,
            "smartenergy_metering",
            "current_summ_delivered",
            12345,
        ),  # DP 106: current_summ_delivered CT A
        (
            b"\x09\x1f\x02\x00\x04\x6b\x02\x00\x04\x00\x00\x1a\x85",
            1,
            "smartenergy_metering",
            "current_summ_received",
            6789,
        ),  # DP 107: current_summ_received CT A
        (
            b"\x09\x1f\x02\x00\x04\x6c\x02\x00\x04\x00\x00\xd4\x31",
            2,
            "smartenergy_metering",
            "current_summ_delivered",
            54321,
        ),  # DP 108: current_summ_delivered CT B
        (
            b"\x09\x1f\x02\x00\x04\x6d\x02\x00\x04\x00\x00\x26\x94",
            2,
            "smartenergy_metering",
            "current_summ_received",
            9876,
        ),  # DP 109: current_summ_received CT B
        # Electrical measurement DP messages
        (
            b"\x09\x1f\x02\x00\x04\x6e\x02\x00\x04\x00\x00\x03\xe8",
            1,
            "electrical_measurement",
            "power_factor",
            1000,
        ),  # DP 110: power_factor CT A
        (
            b"\x09\x1f\x02\x00\x04\x71\x02\x00\x04\x00\x00\x03\xe8",
            1,
            "electrical_measurement",
            "rms_current",
            1000,
        ),  # DP 113: rms_current CT A
        (
            b"\x09\x1f\x02\x00\x04\x72\x02\x00\x04\x00\x00\x07\xd0",
            2,
            "electrical_measurement",
            "rms_current",
            2000,
        ),  # DP 114: rms_current CT B
        (
            b"\x09\x1f\x02\x00\x04\x70\x02\x00\x04\x00\x00\x08\xfc",
            3,
            "electrical_measurement",
            "rms_voltage",
            2300,
        ),  # DP 112: rms_voltage (total)
        (
            b"\x09\x1f\x02\x00\x04\x6f\x02\x00\x04\x00\x00\x13\x88",
            3,
            "electrical_measurement",
            "ac_frequency",
            5000,
        ),  # DP 111: ac_frequency (total)
        (
            b"\x09\x1f\x02\x00\x04\x79\x02\x00\x04\x00\x00\x03\xe8",
            2,
            "electrical_measurement",
            "power_factor",
            1000,
        ),  # DP 121: power_factor CT B
    ],
)
async def test_matseeplus_electrical_and_metering(
    zigpy_device_from_v2_quirk,
    msg,
    endpoint_id,
    cluster_name,
    attr_name,
    expected_value,
):
    """Test electrical measurement and metering attributes."""
    quirked = zigpy_device_from_v2_quirk("_TZE204_81yrt3lo", "TS0601")
    ep = quirked.endpoints[1]

    tuya_manufacturer = ep.tuya_manufacturer
    hdr, data = tuya_manufacturer.deserialize(msg)
    status = tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    cluster = getattr(quirked.endpoints[endpoint_id], cluster_name)
    assert cluster.get(attr_name) == expected_value


@pytest.mark.parametrize(
    "late_flow_a,late_flow_b",
    [
        (False, False),  # Both late flow disabled (default behavior)
        (True, False),  # Only A late flow enabled
        (False, True),  # Only B late flow enabled
        (True, True),  # Both late flow enabled
    ],
)
async def test_matseeplus_power_signing(
    zigpy_device_from_v2_quirk, late_flow_a, late_flow_b
):
    """Test power sign application (positive/negative based on energy flow) with and without late flow mitigation."""
    quirked = zigpy_device_from_v2_quirk("_TZE204_81yrt3lo", "TS0601")
    ep = quirked.endpoints[1]

    # Set mitigation settings
    local_config = ep.local_config
    await local_config.write_attributes(
        {"late_energy_flow_a": late_flow_a, "late_energy_flow_b": late_flow_b}
    )

    tuya_manufacturer = ep.tuya_manufacturer
    ep1_electrical = quirked.endpoints[1].electrical_measurement
    ep2_electrical = quirked.endpoints[2].electrical_measurement
    ep3_electrical = quirked.endpoints[3].electrical_measurement

    def send_dp_message(msg):
        """Send and verify a DP message."""
        hdr, data = tuya_manufacturer.deserialize(msg)
        status = tuya_manufacturer.handle_get_data(data.data)
        assert status == foundation.Status.SUCCESS

    # Test mid-sequence startup: Simulate ZHA starting when device is mid-sequence
    # Receive power_b first (before interval is initialized)
    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x69\x02\x00\x04\x00\x00\x02\x58"
    )  # DP 105: power_b = 600

    # Power B should not be reported yet (interval not initialized)
    assert ep2_electrical.get("active_power") is None
    assert ep3_electrical.get("active_power") is None

    # Test with correct device sequence over two intervals
    # Interval 1: Establish baseline power values (stored but not reported with mitigation)
    send_dp_message(
        b"\x09\x11\x02\x00\x87\x66\x04\x00\x01\x00"
    )  # DP 102: energy_flow_a = 0 (Forward, for previous/initial)

    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x65\x02\x00\x04\x00\x00\x03\x20"
    )  # DP 101: power_a = 800 (for current interval)

    # With mitigation enabled, power_a is stored but not reported yet (waits for next interval's flow)
    # Without mitigation, power_a uses current flow and reports immediately
    if late_flow_a:
        assert ep1_electrical.get("active_power") is None
    else:
        assert ep1_electrical.get("active_power") == 800

    send_dp_message(
        b"\x09\x0a\x02\x00\x80\x68\x04\x00\x01\x01"
    )  # DP 104: energy_flow_b = 1 (Reverse, for previous/initial)

    # With mitigation enabled, receiving energy_flow_b triggers reporting of stored power_b (from mid-sequence startup)
    # Without mitigation, energy_flow_b doesn't trigger power_b reporting
    if late_flow_b:
        assert ep2_electrical.get("active_power") == -600
    else:
        assert ep2_electrical.get("active_power") is None

    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x69\x02\x00\x04\x00\x00\x02\x58"
    )  # DP 105: power_b = 600 (for current interval)

    # Check power B after receiving second power_b
    # With mitigation: power is stored for next interval (still showing -600 from energy_flow_b processing)
    # Without mitigation: power is computed with current flow and reported immediately as -600
    assert ep2_electrical.get("active_power") == -600

    # Total calculation
    # With late_flow_b=True, receiving energy_flow_b processes the mid-sequence power_b and sets report_interval_b=1
    # So total can be calculated when report_interval_a=1 and report_interval_b=1
    if late_flow_a and late_flow_b:
        # Both deferred to next interval: report_interval_a=2, report_interval_b=2
        assert ep3_electrical.get("active_power") is None
    elif late_flow_a:
        # A deferred (report_interval_a=2), B reported (report_interval_b=1), intervals don't match
        assert ep3_electrical.get("active_power") is None
    else:
        # A reported (report_interval_a=1)
        # If late_flow_b=True: B reported via energy_flow_b (report_interval_b=1), total=800+(-600)=200
        # If late_flow_b=False: B reported via second power_b (report_interval_b=1), total=800+(-600)=200
        assert ep3_electrical.get("active_power") == 200

    # Interval 2: Flow messages process powers from interval 1 (flow sent because interval 2 power ≠ 0)
    send_dp_message(
        b"\x09\x11\x02\x00\x87\x66\x04\x00\x01\x00"
    )  # DP 102: energy_flow_a = 0 (Forward, for interval 1)

    # If mitigation enabled, flow_a now processes stored power_a(800) from interval 1
    # Without mitigation, power was already reported in interval 1
    assert ep1_electrical.get("active_power") == 800

    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x65\x02\x00\x04\x00\x00\x03\x20"
    )  # DP 101: power_a = 800 (for interval 2, stored for next interval if mitigation enabled)

    send_dp_message(
        b"\x09\x0a\x02\x00\x80\x68\x04\x00\x01\x01"
    )  # DP 104: energy_flow_b = 1 (Reverse, for interval 1)

    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x69\x02\x00\x04\x00\x00\x02\x58"
    )  # DP 105: power_b = 600 (for interval 2, stored for next interval if mitigation enabled)

    # Check final power B and total after interval 2
    # If mitigation enabled, flow_b processes stored power_b(600) with reverse flow = -600
    # Without mitigation, power_b was already reported as -600
    assert ep2_electrical.get("active_power") == -600
    # Both channels now at interval 2, total calculated
    assert ep3_electrical.get("active_power") == 200  # 800 + (-600)


@pytest.mark.parametrize("late_flow_a,late_flow_b", [(True, True), (False, False)])
async def test_matseeplus_late_flow_non_power_attribute_delay(
    zigpy_device_from_v2_quirk, late_flow_a, late_flow_b
):
    """Test that non-power attributes are delayed when late flow mitigation is enabled."""
    quirked = zigpy_device_from_v2_quirk("_TZE204_81yrt3lo", "TS0601")
    ep = quirked.endpoints[1]

    # Set mitigation settings
    local_config = ep.local_config
    await local_config.write_attributes(
        {"late_energy_flow_a": late_flow_a, "late_energy_flow_b": late_flow_b}
    )

    tuya_manufacturer = ep.tuya_manufacturer
    ep1_electrical = quirked.endpoints[1].electrical_measurement
    ep2_electrical = quirked.endpoints[2].electrical_measurement
    ep3_electrical = quirked.endpoints[3].electrical_measurement

    def send_dp_message(msg):
        """Send and verify a DP message."""
        hdr, data = tuya_manufacturer.deserialize(msg)
        status = tuya_manufacturer.handle_get_data(data.data)
        assert status == foundation.Status.SUCCESS

    # Test CT A current (endpoint 1)
    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x71\x02\x00\x04\x00\x00\x03\xe8"
    )  # DP 113: rms_current CT A = 1000

    if late_flow_a:
        # Current is held
        assert ep1_electrical.get("rms_current") is None

        # Send another current message - releases the previous one
        send_dp_message(
            b"\x09\x1f\x02\x00\x04\x71\x02\x00\x04\x00\x00\x07\xd0"
        )  # DP 113: rms_current CT A = 2000

        # Previous current (1000) is now available
        assert ep1_electrical.get("rms_current") == 1000
    else:
        # Without mitigation, current is available immediately
        assert ep1_electrical.get("rms_current") == 1000

    # Test CT B current (endpoint 2)
    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x72\x02\x00\x04\x00\x00\x0b\xb8"
    )  # DP 114: rms_current CT B = 3000

    if late_flow_b:
        # Current is held
        assert ep2_electrical.get("rms_current") is None

        # Send another current message - releases the previous one
        send_dp_message(
            b"\x09\x1f\x02\x00\x04\x72\x02\x00\x04\x00\x00\x0f\xa0"
        )  # DP 114: rms_current CT B = 4000

        # Previous current (3000) is now available
        assert ep2_electrical.get("rms_current") == 3000
    else:
        # Without mitigation, current is available immediately
        assert ep2_electrical.get("rms_current") == 3000

    # Test voltage (endpoint 3 - total/shared)
    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x70\x02\x00\x04\x00\x00\x08\xfc"
    )  # DP 112: rms_voltage = 2300

    # Voltage is on endpoint 3 (total) and has no delay - always reported immediately
    assert ep3_electrical.get("rms_voltage") == 2300


@pytest.mark.parametrize(
    "late_flow_a,late_flow_b",
    [
        (False, False),  # Both late flow disabled (default behavior)
        (True, False),  # Only A late flow enabled
        (False, True),  # Only B late flow enabled
        (True, True),  # Both late flow enabled
    ],
)
async def test_matseeplus_late_flow_zero_power_deferral(
    zigpy_device_from_v2_quirk, late_flow_a, late_flow_b
):
    """Test zero power deferral when device omits flow DP.

    When power is zero, the device omits the energy flow DP. With late flow mitigation
    enabled, this causes the quirk to sign the last received power value and defer the
    actual zero to the next interval to maintain consistent timing.
    """
    quirked = zigpy_device_from_v2_quirk("_TZE204_81yrt3lo", "TS0601")
    ep = quirked.endpoints[1]

    # Set mitigation settings
    local_config = ep.local_config
    await local_config.write_attributes(
        {"late_energy_flow_a": late_flow_a, "late_energy_flow_b": late_flow_b}
    )

    tuya_manufacturer = ep.tuya_manufacturer
    ep1_electrical = quirked.endpoints[1].electrical_measurement
    ep2_electrical = quirked.endpoints[2].electrical_measurement
    ep3_electrical = quirked.endpoints[3].electrical_measurement

    def send_dp_message(msg):
        """Send and verify a DP message."""
        hdr, data = tuya_manufacturer.deserialize(msg)
        status = tuya_manufacturer.handle_get_data(data.data)
        assert status == foundation.Status.SUCCESS

    # Establish baseline: two normal intervals with non-zero power
    # Interval 1
    send_dp_message(b"\x09\x11\x02\x00\x87\x66\x04\x00\x01\x00")  # flow_a = Forward
    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x65\x02\x00\x04\x00\x00\x03\x20"
    )  # power_a = 800
    send_dp_message(b"\x09\x0a\x02\x00\x80\x68\x04\x00\x01\x01")  # flow_b = Reverse
    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x69\x02\x00\x04\x00\x00\x02\x58"
    )  # power_b = 600

    # Interval 2: Flow messages included because interval 2 has non-zero power
    send_dp_message(
        b"\x09\x11\x02\x00\x87\x66\x04\x00\x01\x00"
    )  # flow_a for interval 1
    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x65\x02\x00\x04\x00\x00\x03\x20"
    )  # power_a = 800
    send_dp_message(
        b"\x09\x0a\x02\x00\x80\x68\x04\x00\x01\x01"
    )  # flow_b for interval 1
    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x69\x02\x00\x04\x00\x00\x02\x58"
    )  # power_b = 600

    # Verify baseline established
    assert ep1_electrical.get("active_power") == 800
    assert ep2_electrical.get("active_power") == -600
    assert ep3_electrical.get("active_power") == 200  # 800 + (-600)

    # Interval 3: Zero power values (flow DPs omitted by device)
    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x65\x02\x00\x04\x00\x00\x00\x00"
    )  # power_a = 0 (no flow_a)

    # Check channel A behavior
    if late_flow_a:
        # Sign previous power (800), deferred zero to interval 4
        assert ep1_electrical.get("active_power") == 800
        assert ep3_electrical.get("active_power") == 200  # 800 + (-600), unchanged
    else:
        # Zero reported immediately
        assert ep1_electrical.get("active_power") == 0
        assert (
            ep3_electrical.get("active_power") == 200
        )  # B still at interval 2, no update

    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x69\x02\x00\x04\x00\x00\x00\x00"
    )  # power_b = 0 (no flow_b)

    # Check channel B behavior and total
    if late_flow_b:
        # Sign previous power (-600), deferred zero to interval 4
        assert ep2_electrical.get("active_power") == -600
        expected_total = 200 if late_flow_a else -600  # 800+(-600) or 0+(-600)
        assert ep3_electrical.get("active_power") == expected_total
    else:
        # Zero reported immediately
        assert ep2_electrical.get("active_power") == 0
        expected_total = 800 if late_flow_a else 0  # 800+0 or 0+0
        assert ep3_electrical.get("active_power") == expected_total

    # Interval 4: Non-zero power returns, flow DPs sent for interval 3
    send_dp_message(
        b"\x09\x11\x02\x00\x87\x66\x04\x00\x01\x00"
    )  # flow_a for interval 3
    assert ep1_electrical.get("active_power") == 0  # Deferred zero now released

    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x65\x02\x00\x04\x00\x00\x03\x84"
    )  # power_a = 900

    send_dp_message(
        b"\x09\x0a\x02\x00\x80\x68\x04\x00\x01\x00"
    )  # flow_b for interval 3
    assert ep2_electrical.get("active_power") == 0  # Deferred zero now released

    send_dp_message(
        b"\x09\x1f\x02\x00\x04\x69\x02\x00\x04\x00\x00\x02\x58"
    )  # power_b = 600

    # Verify final state at interval 4
    if late_flow_a and late_flow_b:
        # Both deferred to interval 5
        assert ep1_electrical.get("active_power") == 0
        assert ep2_electrical.get("active_power") == 0
        assert ep3_electrical.get("active_power") == 0  # 0 + 0
    elif late_flow_a:
        # A deferred, B reported
        assert ep1_electrical.get("active_power") == 0
        assert ep2_electrical.get("active_power") == 600
        assert ep3_electrical.get("active_power") == 600  # 0 + 600
    elif late_flow_b:
        # A reported, B deferred
        assert ep1_electrical.get("active_power") == 900
        assert ep2_electrical.get("active_power") == 0
        assert ep3_electrical.get("active_power") == 900  # 900 + 0
    else:
        # Both reported immediately
        assert ep1_electrical.get("active_power") == 900
        assert ep2_electrical.get("active_power") == 600
        assert ep3_electrical.get("active_power") == 1500  # 900 + 600
