"""Test for EpsilonRT pilot wire heating module quirk."""

import pytest
from zhaquirks.epsilonrt.pilot_wire import (
    EpsilonRTPilotWireCluster,
    EpsilonRTPilotWireMode,
    EPSILONRT_MANUFACTURER_ID,
)
from zigpy.quirks.v2 import CustomDeviceV2

def test_epsilonrt_pilot_wire_cluster():
    """Test the custom cluster definition."""
    cluster = EpsilonRTPilotWireCluster(None)
    
    # Verify cluster configuration
    assert cluster.cluster_id == 0xFC00
    assert cluster.name == "PilotWireCluster"
    assert cluster.manufacturer_id_override == EPSILONRT_MANUFACTURER_ID
    
    # Verify attribute definition
    assert "pilot_wire_mode" in cluster.attributes
    attr_def = cluster.attributes_by_name["pilot_wire_mode"]
    assert attr_def.id == 0x0000
    assert attr_def.type is EpsilonRTPilotWireMode

def test_epsilonrt_pilot_wire_mode_enum():
    """Test the enum values and names (PascalCase)."""
    assert EpsilonRTPilotWireMode.Off == 0x00
    assert EpsilonRTPilotWireMode.Comfort == 0x01
    assert EpsilonRTPilotWireMode.Eco == 0x02
    assert EpsilonRTPilotWireMode.FrostProtection == 0x03
    assert EpsilonRTPilotWireMode.ComfortMinus1 == 0x04
    assert EpsilonRTPilotWireMode.ComfortMinus2 == 0x05