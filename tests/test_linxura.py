"""Tests for Linxura quirks."""

import pytest
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import ZCLHeader

from tests.common import ClusterListener
import zhaquirks
import zhaquirks.linxura

zhaquirks.setup()


# ZCL_LINXURA_BUTTON_1_SINGLE_PRESS = b"\t\x01\x00\x01\x00\x00\x00\x00\x00"
# ZCL_LINXURA_BUTTON_1_DOUBLE_PRESS = b"\t\x02\x00\x02\x00\x00\x00\x00\x00"
# ZCL_LINXURA_BUTTON_1_LONG_PRESS = b"\t\x03\x00\x03\x00\x00\x00\x00\x00"
# ZCL_LINXURA_BUTTON_2_SINGLE_PRESS = b"\tN\x06\x01\x1f\x02\x04\x00\x01\x00"
# ZCL_LINXURA_BUTTON_2_DOUBLE_PRESS = b"\tj\x06\x03\x10\x02\x04\x00\x01\x01"
# ZCL_LINXURA_BUTTON_2_LONG_PRESS = b"\tl\x06\x03\x12\x02\x04\x00\x01\x02"
# ZCL_LINXURA_BUTTON_3_SINGLE_PRESS = b"\tT\x06\x01$\x01\x04\x00\x01\x00"
# ZCL_LINXURA_BUTTON_3_DOUBLE_PRESS = b"\tU\x06\x01%\x01\x04\x00\x01\x01"
# ZCL_LINXURA_BUTTON_3_LONG_PRESS = b"\tk\x06\x03\x11\x01\x04\x00\x01\x02"
# ZCL_LINXURA_BUTTON_4_SINGLE_PRESS = b"\tT\x06\x01$\x01\x04\x00\x01\x00"
# ZCL_LINXURA_BUTTON_4_DOUBLE_PRESS = b"\tU\x06\x01%\x01\x04\x00\x01\x01"
# ZCL_LINXURA_BUTTON_4_LONG_PRESS = b"\tk\x06\x03\x11\x01\x04\x00\x01\x02"


@pytest.mark.parametrize("quirk", (zhaquirks.linxura.button.LinxuraButton,))
async def test_Linxura_button(zigpy_device_from_quirk, quirk):
    """Test Linxura button remotes."""

    device = zigpy_device_from_quirk(quirk)

    # endpoint 1
    cluster = device.endpoints[1].ias_zone
    ias_zone_listener = ClusterListener(cluster)
    ias_zone_status_attr_id = IasZone.AttributeDefs.zone_status.id

    # single press
    # ZHA calls update_attribute on the IasZone cluster when it receives a status_change_notification
    cluster.update_attribute(ias_zone_status_attr_id, 1)

    # button 1 single press
    assert len(ias_zone_listener.attribute_updates) == 1
    assert ias_zone_listener.attribute_updates[0][0] == ias_zone_status_attr_id
    assert ias_zone_listener.attribute_updates[0][1] == 1

    # button1 double press
    # ZHA calls update_attribute on the IasZone cluster when it receives a status_change_notification
    cluster.update_attribute(ias_zone_status_attr_id, 2)

    # button 1 double press
    assert len(ias_zone_listener.attribute_updates) == 2
    assert ias_zone_listener.attribute_updates[1][0] == ias_zone_status_attr_id
    assert ias_zone_listener.attribute_updates[1][1] == 2

    # button1 long press
    # ZHA calls update_attribute on the IasZone cluster when it receives a status_change_notification
    cluster.update_attribute(ias_zone_status_attr_id, 3)

    # button 1 long press
    assert len(ias_zone_listener.attribute_updates) == 3
    assert ias_zone_listener.attribute_updates[2][0] == ias_zone_status_attr_id
    assert ias_zone_listener.attribute_updates[2][1] == 3

    # endpoint 2
    cluster2 = device.endpoints[2].ias_zone
    ias_zone_listener2 = ClusterListener(cluster2)
    ias_zone_status_attr_id = IasZone.AttributeDefs.zone_status.id

    # single press
    # ZHA calls update_attribute on the IasZone cluster when it receives a status_change_notification
    cluster2.update_attribute(ias_zone_status_attr_id, 1)

    # button 2 single press
    assert len(ias_zone_listener2.attribute_updates) == 1
    assert ias_zone_listener2.attribute_updates[0][0] == ias_zone_status_attr_id
    assert ias_zone_listener2.attribute_updates[0][1] == 1

    # button 2 double press
    cluster2.update_attribute(ias_zone_status_attr_id, 2)
    assert len(ias_zone_listener2.attribute_updates) == 2
    assert ias_zone_listener2.attribute_updates[1][0] == ias_zone_status_attr_id
    assert ias_zone_listener2.attribute_updates[1][1] == 2

    # button 2 long press
    cluster2.update_attribute(ias_zone_status_attr_id, 3)
    assert len(ias_zone_listener2.attribute_updates) == 3
    assert ias_zone_listener2.attribute_updates[2][0] == ias_zone_status_attr_id
    assert ias_zone_listener2.attribute_updates[2][1] == 3

    # endpoint 3
    cluster3 = device.endpoints[3].ias_zone
    ias_zone_listener3 = ClusterListener(cluster3)
    ias_zone_status_attr_id = IasZone.AttributeDefs.zone_status.id

    # single press
    # ZHA calls update_attribute on the IasZone cluster when it receives a status_change_notification
    cluster3.update_attribute(ias_zone_status_attr_id, 1)

    # button 3 single press
    assert len(ias_zone_listener3.attribute_updates) == 1
    assert ias_zone_listener3.attribute_updates[0][0] == ias_zone_status_attr_id
    assert ias_zone_listener3.attribute_updates[0][1] == 1

    # button 3 double press
    cluster3.update_attribute(ias_zone_status_attr_id, 2)
    assert len(ias_zone_listener3.attribute_updates) == 2
    assert ias_zone_listener3.attribute_updates[1][0] == ias_zone_status_attr_id
    assert ias_zone_listener3.attribute_updates[1][1] == 2

    # button 3 long press
    cluster3.update_attribute(ias_zone_status_attr_id, 3)
    assert len(ias_zone_listener3.attribute_updates) == 3
    assert ias_zone_listener3.attribute_updates[2][0] == ias_zone_status_attr_id
    assert ias_zone_listener3.attribute_updates[2][1] == 3

    # endpoint 4
    cluster4 = device.endpoints[4].ias_zone
    ias_zone_listener4 = ClusterListener(cluster4)
    ias_zone_status_attr_id = IasZone.AttributeDefs.zone_status.id

    # single press
    # ZHA calls update_attribute on the IasZone cluster when it receives a status_change_notification
    cluster4.update_attribute(ias_zone_status_attr_id, 1)

    # button 4 single press
    assert len(ias_zone_listener4.attribute_updates) == 1
    assert ias_zone_listener4.attribute_updates[0][0] == ias_zone_status_attr_id
    assert ias_zone_listener4.attribute_updates[0][1] == 1

    # button 4 double press
    cluster4.update_attribute(ias_zone_status_attr_id, 2)
    assert len(ias_zone_listener4.attribute_updates) == 2
    assert ias_zone_listener4.attribute_updates[1][0] == ias_zone_status_attr_id
    assert ias_zone_listener4.attribute_updates[1][1] == 2

    # button 4 long press
    cluster4.update_attribute(ias_zone_status_attr_id, 3)
    assert len(ias_zone_listener4.attribute_updates) == 3
    assert ias_zone_listener4.attribute_updates[2][0] == ias_zone_status_attr_id
    assert ias_zone_listener4.attribute_updates[2][1] == 3


@pytest.mark.parametrize("quirk", (zhaquirks.linxura.button.LinxuraButton,))
async def test_handle_cluster_request(zigpy_device_from_quirk, quirk):
    device = zigpy_device_from_quirk(quirk)
    cluster = device.endpoints[1].ias_zone

    # hdr = ZCLHeader.command_id  # Simulate command ID 0 (used in handle_cluster_request)
    hdr = ZCLHeader
    args = [1]  # Simulate single press state
    cluster.handle_cluster_request(hdr, args)
    # Validate event listener triggers the right event


# Test Edge Cases
@pytest.mark.parametrize("quirk", (zhaquirks.linxura.button.LinxuraButton,))
async def test_edge_case_request(zigpy_device_from_quirk, quirk):
    """Test Linxura button remotes."""

    device = zigpy_device_from_quirk(quirk)

    # endpoint 1
    cluster = device.endpoints[1].ias_zone
    ias_zone_listener = ClusterListener(cluster)
    ias_zone_status_attr_id = IasZone.AttributeDefs.zone_status.id

    cluster.update_attribute(ias_zone_status_attr_id, 4)
    assert (
        len(ias_zone_listener.attribute_updates) == 1
    )  # No update should occur for state >= 4
