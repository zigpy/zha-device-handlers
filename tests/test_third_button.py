import pytest
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks
import zhaquirks.thirdreality.button_v2
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


@pytest.mark.parametrize("manufacturer, model", [("Third Reality, Inc", "3RSB22BZ")])
async def test_third_reality_button_v2(zigpy_device_from_v2_quirk, manufacturer, model):
    """Test Third Reality button v2 device."""

    device = zigpy_device_from_v2_quirk(manufacturer, model)

    assert 1 in device.endpoints

    multistate_cluster = None
    for cluster in device.endpoints[1].in_clusters.values():
        if isinstance(cluster, zhaquirks.thirdreality.button_v2.MultistateInputCluster):
            multistate_cluster = cluster
            break

    assert multistate_cluster is not None, "MultistateInputCluster not found"

    class MockListener:
        def __init__(self):
            self.events = []

        def zha_send_event(self, cluster, command, args):
            self.events.append((command, args))

    mock_listener = MockListener()
    multistate_cluster.add_listener(mock_listener)

    test_values = [
        (0, "command_hold"),
        (1, "command_single"),
        (2, "command_double"),
        (255, "command_release"),
    ]

    for value, expected_command in test_values:
        mock_listener.events = []

        multistate_cluster._update_attribute(0x0055, value)

        assert len(mock_listener.events) == 1
        assert mock_listener.events[0][0] == expected_command
        assert mock_listener.events[0][1]["value"] == value

    private_cluster = None
    for cluster in device.endpoints[1].in_clusters.values():
        if isinstance(
            cluster, zhaquirks.thirdreality.button_v2.ThirdRealityButtonCluster
        ):
            private_cluster = cluster
            break

    assert private_cluster is not None, "ThirdRealityButtonCluster not found"
    assert private_cluster.cluster_id == 0xFF01
    assert hasattr(private_cluster.AttributeDefs, "cancel_bouble_click")
    assert private_cluster.AttributeDefs.cancel_bouble_click.id == 0x0000
