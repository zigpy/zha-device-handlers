"""Tests for Legrand."""

from unittest import mock

import pytest
from zigpy.zcl import foundation

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


def test_light_switch_with_neutral_signature(assert_signature_matches_quirk):
    """Test signature."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=1, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4129, maximum_buffer_size=89, maximum_incoming_transfer_size=63, server_mask=10752, maximum_outgoing_transfer_size=63, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0100",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x000f",
                    "0xfc01",
                ],
                "out_clusters": ["0x0000", "0x0019", "0xfc01"],
            }
        },
        "manufacturer": " Legrand",
        "model": " Light switch with neutral",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(
        zhaquirks.legrand.switch.LightSwitchWithNeutral, signature
    )


async def test_legrand_wire_pilot_cluster_write_attrs(zigpy_device_from_v2_quirk):
    """Test Legrand cable outlet heat mode attr writing."""

    device = zigpy_device_from_v2_quirk(f" {LEGRAND}", " Cable outlet")
    legrand_wire_pilot_cluster = device.endpoints[1].legrand_wire_pilot_cluster
    legrand_wire_pilot_cluster._write_attributes = mock.AsyncMock()
    legrand_wire_pilot_cluster.set_heat_mode = mock.AsyncMock()

    await legrand_wire_pilot_cluster.write_attributes({0x00: 0x02}, manufacturer=0xFC40)

    legrand_wire_pilot_cluster.set_heat_mode.assert_awaited_with(
        0x02,
        manufacturer=0xFC40,
    )
    legrand_wire_pilot_cluster._write_attributes.assert_awaited_with(
        [],
        manufacturer=0xFC40,
    )

@pytest.mark.parametrize(
    "value, expected_value",
    [
        (False, [1, 0]),
        (True, [2, 0]),
    ],
)
async def test_legrand_wire_pilot_mode_write_attrs(zigpy_device_from_v2_quirk, value, expected_value):
    """Test Legrand cable outlet heat mode attr writing."""

    device = zigpy_device_from_v2_quirk(f" {LEGRAND}", " Cable outlet")
    legrand_cluster = device.endpoints[1].legrand_cluster
    legrand_cluster._write_attributes = mock.AsyncMock()

    await legrand_cluster.write_attributes({ 0x4000: value }, manufacturer=0xFC40)

    expected = foundation.Attribute(0x0000, foundation.TypeValue())
    expected_attr_def = legrand_cluster.find_attribute(0x0000)
    expected.value.type = foundation.DATA_TYPES.pytype_to_datatype_id(
        expected_attr_def.type
    )
    expected.value.value = expected_attr_def.type(expected_value)

    legrand_cluster._write_attributes.assert_awaited_with(
        [expected],
        manufacturer=0xFC40,
    )

