"""Tests for EpsilonRT Pilot Wire quirk."""

from zhaquirks.epsilonrt.pilot_wire import (
    EpsilonRTPilotWireCluster,
    EpsilonRTPilotWireMode,
)


def test_epsilonrt_pilot_wire_cluster():
    """Test EpsilonRTPilotWireCluster attributes and types."""
    cluster = EpsilonRTPilotWireCluster(None)

    # Check if pilot_wire_mode attribute exists (ID 0x0000)
    attr_id = 0x0000
    assert attr_id in cluster.attributes

    # Check attribute name and type
    assert cluster.attributes[attr_id].name == "pilot_wire_mode"
    assert cluster.attributes[attr_id].type is EpsilonRTPilotWireMode


def test_epsilonrt_enum_values():
    """Test EpsilonRTPilotWireMode enum mapping."""
    assert EpsilonRTPilotWireMode.Off == 0
    assert EpsilonRTPilotWireMode.Comfort == 1
    assert EpsilonRTPilotWireMode.Eco == 2
    assert EpsilonRTPilotWireMode.FrostProtection == 3
    assert EpsilonRTPilotWireMode.ComfortMinus1 == 4
    assert EpsilonRTPilotWireMode.ComfortMinus2 == 5
