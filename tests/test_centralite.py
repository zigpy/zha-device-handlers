"""Tests for CentraLite quirks."""

import pytest
from zigpy.zcl.clusters.general import PowerConfiguration

import zhaquirks
import zhaquirks.centralite.cl_3300S

zhaquirks.setup()

CENTRALITE_3300_NO_EP2_SIGNATURE = {
    "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=49887, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=0, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>)",
    "endpoints": {
        "1": {
            "profile_id": 260,
            "device_type": "0x0402",
            "in_clusters": [
                "0x0000",
                "0x0001",
                "0x0003",
                "0x0020",
                "0x0402",
                "0x0500",
                "0x0b05",
            ],
            "out_clusters": ["0x0019"],
        },
    },
    "manufacturer": "CentraLite",
    "model": "3300",
    "class": "zigpy.device.Device",
}


def test_centralite_3300_no_ep2_signature(assert_signature_matches_quirk):
    """Test a CentraLite 3300 without endpoint 2 is matched to its quirk."""
    assert_signature_matches_quirk(
        zhaquirks.centralite.cl_3300S.CentraLite3300SNoEP2,
        CENTRALITE_3300_NO_EP2_SIGNATURE,
    )


@pytest.mark.parametrize(
    "voltage, bpr",
    (
        (30, 200),  # above max
        (28, 200),  # max
        (24, 138),
        (15, 0),  # min
        (14, 0),  # below min
    ),
)
async def test_centralite_3300_no_ep2_battery(zigpy_device_from_quirk, voltage, bpr):
    """Test battery voltage is converted to % battery left."""
    device = zigpy_device_from_quirk(zhaquirks.centralite.cl_3300S.CentraLite3300SNoEP2)
    power_cluster = device.endpoints[1].power
    power_cluster.update_attribute(
        PowerConfiguration.AttributeDefs.battery_voltage.id, voltage
    )
    assert power_cluster["battery_percentage_remaining"] == bpr
