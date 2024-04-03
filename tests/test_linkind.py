"""Test linkind."""

import pytest
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks

zhaquirks.setup()


@pytest.mark.parametrize("quirk", (zhaquirks.linkind.motion.LinkindD0003,))
async def test_linkind_motion_ignore_alarm_2(zigpy_device_from_quirk, quirk):
    """Test that the quirk for the Linkind motion sensor ignores the IasZone Alarm_2 bit."""
    device = zigpy_device_from_quirk(quirk)

    ias_zone_cluster = device.endpoints[1].ias_zone
    ias_zone_listener = ClusterListener(ias_zone_cluster)
    ias_zone_status_attr_id = IasZone.AttributeDefs.zone_status.id

    # ZHA calls update_attribute on the IasZone cluster when it receives a status_change_notification
    ias_zone_cluster.update_attribute(
        ias_zone_status_attr_id, IasZone.ZoneStatus.Alarm_2
    )

    # verify Alarm_2 bit was set to 0
    assert len(ias_zone_listener.attribute_updates) == 1
    assert ias_zone_listener.attribute_updates[0][0] == ias_zone_status_attr_id
    assert ias_zone_listener.attribute_updates[0][1] == 0

    # call again with Alarm_1
    ias_zone_cluster.update_attribute(
        ias_zone_status_attr_id, IasZone.ZoneStatus.Alarm_1
    )

    # verify Alarm_1 was not ignored
    assert len(ias_zone_listener.attribute_updates) == 2
    assert ias_zone_listener.attribute_updates[1][0] == ias_zone_status_attr_id
    assert ias_zone_listener.attribute_updates[1][1] == IasZone.ZoneStatus.Alarm_1
