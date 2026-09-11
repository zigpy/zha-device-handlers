"""Tests for Securifi quirks."""

from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zdo.types import NodeDescriptor

from zhaquirks.builder import SensorDeviceClass
from zhaquirks.securifi.peanut import PEANUT_SIGNATURE


def test_peanut_plug_quirk(MockAppController, ieee_mock):
    """Test Securifi Peanut Plug quirk matching and metadata."""

    device = MockAppController.add_device(ieee_mock, 0x1234)

    device.manufacturer = "Securifi Ltd."
    device.model = None
    device.node_desc = NodeDescriptor(
        manufacturer_code=4098,
    )

    endpoint = device.add_endpoint(1)
    endpoint.profile_id = PEANUT_SIGNATURE["endpoints"][1]["profile_id"]
    endpoint.device_type = PEANUT_SIGNATURE["endpoints"][1]["device_type"]

    for cluster_id in PEANUT_SIGNATURE["endpoints"][1]["input_clusters"]:
        endpoint.add_input_cluster(cluster_id)

    for cluster_id in PEANUT_SIGNATURE["endpoints"][1]["output_clusters"]:
        endpoint.add_output_cluster(cluster_id)

    quirked = DEVICE_REGISTRY.resolve(device)

    assert quirked is not device
    assert quirked.quirk_metadata is not None

    # Friendly device naming.
    assert quirked.quirk_metadata.friendly_name is not None
    assert quirked.quirk_metadata.friendly_name.manufacturer == "Securifi"
    assert quirked.quirk_metadata.friendly_name.model == "Peanut Plug PP-WHT-US"

    # Verify the quirk does not alter the actual Zigbee endpoint structure.
    assert set(quirked.endpoints[1].in_clusters) == set(
        PEANUT_SIGNATURE["endpoints"][1]["input_clusters"]
    )
    assert set(quirked.endpoints[1].out_clusters) == set(
        PEANUT_SIGNATURE["endpoints"][1]["output_clusters"]
    )

    # Verify the Electrical Measurement default-entity filter is installed.
    filters = quirked.quirk_metadata.disabled_default_entities

    assert len(filters) == 1

    entity_filter = filters[0]

    assert entity_filter.endpoint_id == 1
    assert entity_filter.cluster_id == ElectricalMeasurement.cluster_id
    assert entity_filter.function is not None

    class FakeEntity:
        """Minimal object for testing the entity-filter predicate."""

        def __init__(self, device_class):
            self.device_class = device_class

    # These two bogus entities should be suppressed.
    assert entity_filter.function(FakeEntity(SensorDeviceClass.FREQUENCY))
    assert entity_filter.function(FakeEntity(SensorDeviceClass.POWER_FACTOR))

    # Useful Electrical Measurement entities must remain enabled.
    assert not entity_filter.function(FakeEntity(SensorDeviceClass.POWER))
    assert not entity_filter.function(FakeEntity(SensorDeviceClass.VOLTAGE))
    assert not entity_filter.function(FakeEntity(SensorDeviceClass.CURRENT))
