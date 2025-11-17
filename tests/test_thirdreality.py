"""Tests for Third Reality quirks."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks

zhaquirks.setup()


async def test_third_reality_nightlight(zigpy_device_from_v2_quirk):
    """Test Third Reality night light forwarding motion attribute to IasZone cluster."""

    device = zigpy_device_from_v2_quirk(
        "Third Reality, Inc",
        "3RSNL02043Z",
        cluster_ids={1: {0xFC00: ClusterType.Server}},
    )

    ias_zone_cluster = device.endpoints[1].ias_zone
    ias_zone_listener = ClusterListener(ias_zone_cluster)

    ias_zone_status_id = IasZone.AttributeDefs.zone_status.id

    third_reality_cluster = device.endpoints[1].in_clusters[0xFC00]

    # 0x0002 is also used on manufacturer specific cluster for motion events
    third_reality_cluster.update_attribute(0x0002, IasZone.ZoneStatus.Alarm_1)

    assert len(ias_zone_listener.attribute_updates) == 1
    assert ias_zone_listener.attribute_updates[0][0] == ias_zone_status_id
    assert ias_zone_listener.attribute_updates[0][1] == IasZone.ZoneStatus.Alarm_1

    # turn off motion alarm
    third_reality_cluster.update_attribute(0x0002, 0)

    assert len(ias_zone_listener.attribute_updates) == 2
    assert ias_zone_listener.attribute_updates[1][0] == ias_zone_status_id
    assert ias_zone_listener.attribute_updates[1][1] == 0
