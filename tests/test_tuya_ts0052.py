"""Tests for the Tuya TS0052 2-channel dimmer quirk."""

from zhaquirks.tuya.ts0052 import SwitchType, TuyaSwitchTypeCluster


def test_switch_type_cluster_definition() -> None:
    """Test the TS0052 external switch type cluster definition."""

    assert TuyaSwitchTypeCluster.cluster_id == 0xE001

    attribute = TuyaSwitchTypeCluster.AttributeDefs.switch_type
    assert attribute.id == 0xD030
    assert attribute.type is SwitchType

    assert SwitchType.Toggle == 0
    assert SwitchType.State == 1
    assert SwitchType.Momentary == 2
