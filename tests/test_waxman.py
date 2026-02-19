"""Tests for WAXMAN leakSMART quirks."""

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.waxman.leaksmart import (
    WAXMANApplianceEventAlerts,
    WAXMANleakSMARTv2,
    WAXMANleakSMARTv2NOPOLL,
)

zhaquirks.setup()


@pytest.mark.parametrize("quirk", [WAXMANleakSMARTv2, WAXMANleakSMARTv2NOPOLL])
async def test_leaksmart_water_detected(zigpy_device_from_quirk, quirk):
    """Test that moisture alerts update the IAS zone status."""
    device = zigpy_device_from_quirk(quirk)

    app_cluster = device.endpoints[1].in_clusters[WAXMANApplianceEventAlerts.cluster_id]
    ias_zone_cluster = device.endpoints[1].ias_zone
    ias_zone_listener = ClusterListener(ias_zone_cluster)
    zone_status_id = IasZone.AttributeDefs.zone_status.id

    # Simulate water detected (bit 0x1000 set)
    hdr = foundation.ZCLHeader.cluster(
        tsn=1,
        command_id=WAXMANApplianceEventAlerts.ClientCommandDefs.alerts_notification.id,
    )
    app_cluster.handle_cluster_request(hdr, [0, 0x1000])

    assert len(ias_zone_listener.attribute_updates) == 1
    assert ias_zone_listener.attribute_updates[0][0] == zone_status_id
    assert ias_zone_listener.attribute_updates[0][1] == IasZone.ZoneStatus.Alarm_1

    # Simulate water cleared (bit 0x1000 not set)
    hdr = foundation.ZCLHeader.cluster(
        tsn=2,
        command_id=WAXMANApplianceEventAlerts.ClientCommandDefs.alerts_notification.id,
    )
    app_cluster.handle_cluster_request(hdr, [0, 0x0000])

    assert len(ias_zone_listener.attribute_updates) == 2
    assert ias_zone_listener.attribute_updates[1][0] == zone_status_id
    assert ias_zone_listener.attribute_updates[1][1] == 0
