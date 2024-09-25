"""Tests for Tuya Smoke Detector."""

import pytest
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks.tuya.ts0205

zhaquirks.setup()


def test_ts0205_signature(assert_signature_matches_quirk):
    """Test signature."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4417, maximum_buffer_size=66, maximum_incoming_transfer_size=66, server_mask=10752, maximum_outgoing_transfer_size=66, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 0x0104,
                "device_type": "0x0402",
                "in_clusters": ["0x0000", "0x0001", "0x0004", "0x0005", "0x0500"],
                "out_clusters": [
                    "0x0003",
                    "0x0004",
                    "0x0006",
                    "0x000a",
                    "0x0019",
                    "0x1000",
                ],
            }
        },
        "manufacturer": "_TZ3210_up3pngle",
        "model": "TS0205",
        "class": "ts0205.TuyaSmokeDetectorTS0205",
    }
    assert_signature_matches_quirk(
        zhaquirks.tuya.ts0205.TuyaSmokeDetectorTS0205, signature
    )


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0205.TuyaSmokeDetectorTS0205,))
async def test_tuya_smoke_sensor_attribute_update(zigpy_device_from_quirk, quirk):
    """Test update_attribute on Tuya smoke sensor."""

    device = zigpy_device_from_quirk(quirk)

    opple_cluster = device.endpoints[1].tuya_manufacturer
    opple_listener = ClusterListener(opple_cluster)

    ias_cluster = device.endpoints[1].ias_zone
    ias_listener = ClusterListener(ias_cluster)

    zone_status_id = IasZone.AttributeDefs.zone_status.id

    # check that updating smoke attribute also updates zone status on the Ias Zone cluster

    # turn on smoke alarm
    opple_cluster.update_attribute(0x0401, 1)
    assert len(opple_listener.attribute_updates) == 1
    assert len(ias_listener.attribute_updates) == 1
    assert ias_listener.attribute_updates[0][0] == zone_status_id
    assert ias_listener.attribute_updates[0][1] == 0
    # turn off smoke alarm
    opple_cluster.update_attribute(0x0401, 0)
    assert len(opple_listener.attribute_updates) == 2
    assert len(ias_listener.attribute_updates) == 2
    assert ias_listener.attribute_updates[1][0] == zone_status_id
    assert ias_listener.attribute_updates[1][1] == IasZone.ZoneStatus.Alarm_1
