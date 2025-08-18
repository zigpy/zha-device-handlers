"""Tests for Legrand."""

from unittest import mock

import pytest

import zhaquirks
from zhaquirks.legrand import LEGRAND

zhaquirks.setup()


@pytest.mark.parametrize(
    "voltage, bpr",
    (
        (32.00, 200),  # over the max
        (30.00, 200),  # max
        (29.0, 160),
        (28.0, 120),
        (27.50, 100),  # 50%
        (26.0, 40),
        (25.0, 0),  # min
        (24.0, 0),  # below min
    ),
)
async def test_legrand_battery(zigpy_device_from_quirk, voltage, bpr):
    """Test Legrand battery voltage to % battery left."""

    device = zigpy_device_from_quirk(zhaquirks.legrand.dimmer.RemoteDimmer)
    power_cluster = device.endpoints[1].power
    power_cluster.update_attribute(0x0020, voltage)
    assert power_cluster["battery_percentage_remaining"] == bpr


async def test_legrand_wire_pilot_cluster_write_attrs(zigpy_device_from_v2_quirk):
    """Test Legrand cable outlet pilot_wire_mode attr writing."""

    device = zigpy_device_from_v2_quirk(f" {LEGRAND}", " Cable outlet")

    cable_cluster = device.endpoints[1].legrand_cable_outlet_cluster
    cable_cluster._write_attributes = mock.AsyncMock()
    cable_cluster._read_attributes = mock.AsyncMock()
    cable_cluster.set_pilot_wire_mode = mock.AsyncMock()

    # test writing read-only pilot_wire_mode attribute, should call set_pilot_wire_mode
    await cable_cluster.write_attributes({0x00: 0x02}, manufacturer=0xFC40)

    cable_cluster.set_pilot_wire_mode.assert_awaited_with(
        0x02,
        manufacturer=0xFC40,
    )
    cable_cluster._write_attributes.assert_awaited_with(
        [],
        manufacturer=0xFC40,
    )


async def test_legrand_identify_command(zigpy_device_from_v2_quirk):
    """Test Legrand Identify cluster command handling."""

    device = zigpy_device_from_v2_quirk(f" {LEGRAND}", " Light switch with neutral")
    identify_cluster = device.endpoints[1].identify

    with mock.patch("zigpy.zcl.Cluster.request") as request:
        # Expected values for the mocked function calls
        IDENTIFY_TIME = 1234
        IDENTIFY_COMMAND = 0x00
        TRIGGER_EFFECT_COMMAND = 0x40
        EFFECT_ID = 0x00
        EFFECT_VARIANT = 0x00

        # Test the identify command
        await identify_cluster.identify(identify_time=IDENTIFY_TIME)

        # The identify command should produce two requests
        assert request.call_count == 2

        # The first call is for the trigger effect command
        assert request.call_args_list[0].args[1] == TRIGGER_EFFECT_COMMAND
        assert request.call_args_list[0].kwargs["effect_id"] == EFFECT_ID
        assert request.call_args_list[0].kwargs["effect_variant"] == EFFECT_VARIANT
        assert "identify_time" not in request.call_args_list[0].kwargs

        # The second call is for the identify command
        assert request.call_args_list[1].args[1] == IDENTIFY_COMMAND
        assert request.call_args_list[1].kwargs["identify_time"] == IDENTIFY_TIME
        assert "effect_id" not in request.call_args_list[1].kwargs
        assert "effect_variant" not in request.call_args_list[1].kwargs
