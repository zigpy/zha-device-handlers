"""Tests for the SONOFF MINI-ZBRBS quirk."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.foundation import DataTypeId

import zhaquirks
from zhaquirks.sonoff import mini_zbrbs

zhaquirks.setup()


@pytest.fixture
def cluster():
    """Return a MINI-ZBRBS custom cluster with a mock endpoint."""
    return mini_zbrbs.SonoffCluster(mock.Mock(), is_server=True)


def _base_write_mock(result=None):
    """Patch the base write_attributes method."""
    return mock.patch.object(
        mini_zbrbs.CustomCluster,
        "write_attributes",
        new_callable=mock.AsyncMock,
        return_value=result if result is not None else [[mock.sentinel.write_ok]],
    )


def test_quirk_metadata():
    """Expose the expected quirk metadata."""
    assert mini_zbrbs.QUIRK_METADATA == {
        "name": "SONOFF MINI-ZBRBS",
        "model": "MINI-ZBRBS",
        "version": "1.0",
        "update_date": "2026-11-24",
        "author": "SONOFF",
        "manufacturer": "SONOFF",
        "description": (
            "SONOFF MINI-ZBRBS - Window covering roller shutter motor controller."
        ),
    }


@pytest.mark.parametrize(
    ("enum_class", "expected"),
    [
        (
            mini_zbrbs.SonoffCoverCalibrationStatus,
            {"not_calibrated": 0x00, "calibrated": 0x01},
        ),
        (
            mini_zbrbs.SonoffMotorState,
            {"stopped": 0x00, "opening": 0x01, "closing": 0x02},
        ),
        (
            mini_zbrbs.SonoffExternalSwitchTriggerType,
            {"edge_trigger": 0x00, "pulse_trigger": 0x01},
        ),
    ],
)
def test_enum_values(enum_class, expected):
    """Expose the expected enum values."""
    for name, value in expected.items():
        assert int(getattr(enum_class, name)) == value


def test_sonoff_cluster_id():
    """Use the SONOFF manufacturer-specific cluster ID."""
    assert mini_zbrbs.SonoffCluster.cluster_id == 0xFC11


@pytest.mark.parametrize(
    ("name", "attr_id", "attr_type"),
    [
        (
            "external_trigger_mode",
            0x0016,
            mini_zbrbs.SonoffExternalSwitchTriggerType,
        ),
        ("single_switch_mode", 0x6038, t.Bool),
        ("cover_calibrated", 0x5012, mini_zbrbs.SonoffCoverCalibrationStatus),
        ("motor_state", 0x5013, mini_zbrbs.SonoffMotorState),
        ("attrib_0010", 0x0010, t.uint32_t),
        ("attrib_0012", 0x0012, t.int16s),
        ("limits_calibration", 0x5001, t.uint8_t),
        ("cluster_revision", 0xFFFD, t.uint16_t),
    ],
)
def test_attribute_definitions(name, attr_id, attr_type):
    """Expose the expected attribute definitions."""
    attr_def = getattr(mini_zbrbs.SonoffCluster.AttributeDefs, name)

    assert attr_def.id == attr_id
    assert attr_def.type is attr_type
    assert attr_def.manufacturer_code is None


@pytest.mark.parametrize(
    ("name", "zcl_type"),
    [
        ("external_trigger_mode", DataTypeId.uint8),
        ("single_switch_mode", DataTypeId.bool_),
        ("cover_calibrated", DataTypeId.uint8),
        ("motor_state", DataTypeId.uint8),
    ],
)
def test_explicit_zcl_types(name, zcl_type):
    """Declare explicit ZCL types for custom attributes."""
    assert getattr(mini_zbrbs.SonoffCluster.AttributeDefs, name).zcl_type == zcl_type


@pytest.mark.parametrize("name", ["motor_state", "attrib_0010"])
def test_read_only_attributes(name):
    """Mark read-only attributes correctly."""
    access = getattr(mini_zbrbs.SonoffCluster.AttributeDefs, name).access
    assert access.name == "Read"


async def test_cluster_is_applied_to_device(zigpy_device_from_v2_quirk):
    """Apply the custom cluster to a MINI-ZBRBS device."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "MINI-ZBRBS",
        cluster_ids={
            1: {mini_zbrbs.SonoffCluster.cluster_id: ClusterType.Server},
        },
    )
    cluster = device.endpoints[1].in_clusters[mini_zbrbs.SonoffCluster.cluster_id]

    assert isinstance(cluster, mini_zbrbs.SonoffCluster)


async def test_write_attributes_normalizes_names_and_preserves_manufacturer(cluster):
    """Normalize attribute names and pass the manufacturer through."""
    attributes = {
        "single_switch_mode": False,
        mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
            mini_zbrbs.SonoffExternalSwitchTriggerType.pulse_trigger
        ),
        "unknown_attribute": 7,
    }

    with _base_write_mock() as write:
        result = await cluster.write_attributes(attributes, manufacturer=0x1234)

    assert result == [[mock.sentinel.write_ok]]
    write.assert_awaited_once_with(
        {
            0x6038: False,
            0x0016: mini_zbrbs.SonoffExternalSwitchTriggerType.pulse_trigger,
            "unknown_attribute": 7,
        },
        0x1234,
    )


@pytest.mark.parametrize(
    ("attributes", "expected"),
    [
        (
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.single_switch_mode.id: True,
            },
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.single_switch_mode.id: True,
                mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
                    mini_zbrbs.SonoffExternalSwitchTriggerType.pulse_trigger
                ),
            },
        ),
        (
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.single_switch_mode.id: True,
                mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
                    mini_zbrbs.SonoffExternalSwitchTriggerType.edge_trigger
                ),
            },
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.single_switch_mode.id: True,
                mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
                    mini_zbrbs.SonoffExternalSwitchTriggerType.pulse_trigger
                ),
            },
        ),
        (
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
                    mini_zbrbs.SonoffExternalSwitchTriggerType.edge_trigger
                ),
            },
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
                    mini_zbrbs.SonoffExternalSwitchTriggerType.edge_trigger
                ),
                mini_zbrbs.SonoffCluster.AttributeDefs.single_switch_mode.id: False,
            },
        ),
        (
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
                    mini_zbrbs.SonoffExternalSwitchTriggerType.pulse_trigger
                ),
                mini_zbrbs.SonoffCluster.AttributeDefs.single_switch_mode.id: False,
            },
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
                    mini_zbrbs.SonoffExternalSwitchTriggerType.pulse_trigger
                ),
                mini_zbrbs.SonoffCluster.AttributeDefs.single_switch_mode.id: False,
            },
        ),
    ],
)
async def test_write_attributes_trigger_mode_rules(cluster, attributes, expected):
    """Enforce single switch mode and external trigger compatibility."""
    with _base_write_mock() as write:
        await cluster.write_attributes(attributes)

    write.assert_awaited_once_with(expected, None)
