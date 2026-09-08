"""Tests for the SONOFF S60ZBTPF device."""

import pytest
from zha.quirks import QUIRK_REGISTRY_ENTRY_ATTR
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

import zhaquirks
from zhaquirks.builder import EntityPlatform, EntityType
from zhaquirks.sonoff.s60zbtpf import (
    S60_POWER_FIX_FW_VERSION,
    SonoffEwelinkCluster,
    SonoffS60ElectricalMeasurement,
    SonoffS60OnOff,
)

zhaquirks.setup()

POWER_ID = ElectricalMeasurement.AttributeDefs.active_power.id
CURRENT_ID = ElectricalMeasurement.AttributeDefs.rms_current.id
VOLTAGE_ID = ElectricalMeasurement.AttributeDefs.rms_voltage.id
ON_OFF_ID = OnOff.AttributeDefs.on_off.id
NETWORK_LED_ID = SonoffEwelinkCluster.AttributeDefs.network_led.id

# the quirk for the fixed firmware does not replace these clusters,
# so the test device needs to provide them itself
S60_CLUSTERS = {
    1: {
        OnOff.cluster_id: ClusterType.Server,
        ElectricalMeasurement.cluster_id: ClusterType.Server,
        SonoffEwelinkCluster.cluster_id: ClusterType.Server,
    }
}


@pytest.mark.parametrize(
    ("firmware_version", "power_fix_applied"),
    [
        # a device that does not report a firmware version gets the workaround
        (None, True),
        (0x00002002, True),  # v2.0.2, still affected
        (S60_POWER_FIX_FW_VERSION, False),  # v2.0.3 fixed the bug
        (S60_POWER_FIX_FW_VERSION + 1, False),
    ],
)
def test_sonoff_plug_quirk_selection(
    zigpy_device_from_v2_quirk, firmware_version, power_fix_applied
):
    """Test the power measurement workaround is only used on affected firmware."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "S60ZBTPF",
        cluster_ids=S60_CLUSTERS,
        firmware_version=firmware_version,
    )

    on_off_cluster = device.endpoints[1].on_off
    electrical_cluster = device.endpoints[1].electrical_measurement

    assert isinstance(on_off_cluster, SonoffS60OnOff) is power_fix_applied
    assert (
        isinstance(electrical_cluster, SonoffS60ElectricalMeasurement)
        is power_fix_applied
    )
    ewelink_cluster = device.endpoints[1].sonoff_ewelink
    assert isinstance(ewelink_cluster, SonoffEwelinkCluster)
    assert ewelink_cluster.find_attribute(NETWORK_LED_ID).id == NETWORK_LED_ID


def test_sonoff_plug_power_fix(zigpy_device_from_v2_quirk):
    """Test Sonoff plug power measurement overrides."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF", "S60ZBTPF", cluster_ids=S60_CLUSTERS, firmware_version=0x00002002
    )

    electrical_cluster = device.endpoints[1].electrical_measurement
    on_off_cluster = device.endpoints[1].on_off

    electrical_cluster.update_attribute(POWER_ID, 300)
    electrical_cluster.update_attribute(CURRENT_ID, 13)
    electrical_cluster.update_attribute(VOLTAGE_ID, 263)
    assert electrical_cluster.get(POWER_ID) == 300
    assert electrical_cluster.get(CURRENT_ID) == 13
    assert electrical_cluster.get(VOLTAGE_ID) == 263

    # turning the socket off resets the power readings
    on_off_cluster.update_attribute(ON_OFF_ID, t.Bool.false)
    assert electrical_cluster.get(POWER_ID) == 0
    assert electrical_cluster.get(CURRENT_ID) == 0
    assert electrical_cluster.get(VOLTAGE_ID) == foundation.DataType.uint16.non_value

    # updates are blocked while the socket stays off
    electrical_cluster.update_attribute(POWER_ID, 300)
    electrical_cluster.update_attribute(CURRENT_ID, 13)
    electrical_cluster.update_attribute(VOLTAGE_ID, 263)
    assert electrical_cluster.get(POWER_ID) == 0
    assert electrical_cluster.get(CURRENT_ID) == 0
    assert electrical_cluster.get(VOLTAGE_ID) == foundation.DataType.uint16.non_value

    # turning the socket back on does not restore readings on its own
    on_off_cluster.update_attribute(ON_OFF_ID, t.Bool.true)
    assert electrical_cluster.get(POWER_ID) == 0
    assert electrical_cluster.get(CURRENT_ID) == 0
    assert electrical_cluster.get(VOLTAGE_ID) == foundation.DataType.uint16.non_value

    # the next report is passed through again
    electrical_cluster.update_attribute(POWER_ID, 300)
    electrical_cluster.update_attribute(CURRENT_ID, 13)
    electrical_cluster.update_attribute(VOLTAGE_ID, 263)
    assert electrical_cluster.get(POWER_ID) == 300
    assert electrical_cluster.get(CURRENT_ID) == 13
    assert electrical_cluster.get(VOLTAGE_ID) == 263


def test_sonoff_plug_network_indicator_entity(zigpy_device_from_v2_quirk):
    """Test that the network indicator is exposed as a configuration switch."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "S60ZBTPF",
        cluster_ids=S60_CLUSTERS,
        firmware_version=S60_POWER_FIX_FW_VERSION,
    )

    entry = getattr(device, QUIRK_REGISTRY_ENTRY_ATTR)
    network_indicator = next(
        metadata
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
        if metadata.attribute_name
        == SonoffEwelinkCluster.AttributeDefs.network_led.name
    )

    assert network_indicator.entity_type == EntityType.CONFIG
    assert network_indicator.entity_platform == EntityPlatform.SWITCH
