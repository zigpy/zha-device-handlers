"""Tests for Elivco quirks."""

from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType

import zhaquirks
from zhaquirks.elivco.elc_sp02 import ElivcoElectricalMeasurementCluster

zhaquirks.setup()


async def test_elivco_elc_sp02_quirk_applied(zigpy_device_from_v2_quirk):
    """Test Elivco ELC-SP02 quirk is applied and creates power monitoring sensors."""
    device = zigpy_device_from_v2_quirk(
        "eWeLink",
        "CK-BL702-SWP-01(7020)",
        cluster_ids={1: {0xFC11: ClusterType.Server}},
    )

    # Verify the custom cluster replaces the generic one
    assert isinstance(
        device.endpoints[1].elivco_electrical_measurement,
        ElivcoElectricalMeasurementCluster,
    )

    # Verify that 3 sensor entities are defined (voltage, current, power)
    entry = DEVICE_REGISTRY.match_entry(device)
    entity_metadata = entry.zha_device_factory.quirk_definition.entity_metadata
    assert len(entity_metadata) == 3

    # Verify sensor attribute names
    sensor_attrs = {m.attribute_name for m in entity_metadata}
    assert sensor_attrs == {"voltage", "current", "power"}
