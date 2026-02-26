"""Tests for Third Reality quirks."""

from unittest import mock

import pytest
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.thirdreality.button import MultistateInputCluster
import zhaquirks.thirdreality.night_light

zhaquirks.setup()


@pytest.mark.parametrize("quirk", (zhaquirks.thirdreality.night_light.Nightlight,))
async def test_third_reality_nightlight(zigpy_device_from_quirk, quirk):
    """Test Third Reality night light forwarding motion attribute to IasZone cluster."""

    device = zigpy_device_from_quirk(quirk)

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


@pytest.mark.parametrize(
    ("attr_value", "expected_action"),
    [
        (1, "single"),  # 1 corresponds to single click
        (2, "double"),  # 2 corresponds to double click
        (0, "hold"),  # 0 corresponds to hold
        (255, "release"),  # 255 corresponds to release
    ],
)
@pytest.mark.parametrize(
    ("manufacturer", "model"),
    [("Third Reality, Inc", "3RSB22BZ")],
)
async def test_third_reality_button_v2(
    zigpy_device_from_v2_quirk, manufacturer, model, attr_value, expected_action
):
    """Test Third Reality button event conversion and triggering functionality."""
    device = zigpy_device_from_v2_quirk(manufacturer, model)
    multistate_cluster = device.endpoints[1].in_clusters[
        MultistateInputCluster.cluster_id
    ]

    # Create mock listener and register it with the cluster
    listener = mock.MagicMock()
    multistate_cluster.add_listener(listener)

    multistate_cluster.update_attribute(
        0x0055, attr_value
    )  # 1 corresponds to single click
    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args_list[0] == mock.call(
        expected_action, {"value": attr_value}
    )
