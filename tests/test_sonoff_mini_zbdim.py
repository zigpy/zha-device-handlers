"""Tests for Sonoff MINI-ZBDIM quirks."""

import importlib
from unittest import mock

import pytest
from zigpy.quirks.v2 import EntityPlatform
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import LevelControl

from tests.common import ClusterListener
import zhaquirks

mini_zbdim = importlib.import_module("zhaquirks.sonoff.mini_zbdim")
SonoffCluster = mini_zbdim.SonoffCluster
SonoffLevelControl = mini_zbdim.SonoffLevelControl

zhaquirks.setup()

PERCENT_ATTRIBUTES = (
    SonoffCluster.AttributeDefs.min_brightness_threshold,
    SonoffCluster.AttributeDefs.max_brightness_threshold,
    SonoffCluster.AttributeDefs.level_for_calibration,
)


@pytest.fixture
def sonoff_cluster(zigpy_device_from_v2_quirk):
    """Create a MINI-ZBDIM manufacturer-specific cluster."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBDIM",
        cluster_ids={1: {SonoffCluster.cluster_id: ClusterType.Server}},
    )
    return device.endpoints[1].sonoff_cluster


@pytest.mark.parametrize("attribute", PERCENT_ATTRIBUTES, ids=lambda attr: attr.name)
@pytest.mark.parametrize("use_name", [False, True], ids=["id", "name"])
@pytest.mark.parametrize(
    ("raw_value", "expected_percent"),
    [
        (0, 0),
        (2, 1),
        (3, 1),
        (25, 10),
        (127, 50),
        (128, 50),
        (252, 99),
        (254, 100),
        (255, 100),
    ],
)
def test_sonoff_mini_zbdim_percent_display(
    sonoff_cluster, attribute, use_name, raw_value, expected_percent
):
    """Round displayed percentages without changing cached or reported raw values."""
    listener = ClusterListener(sonoff_cluster)
    sonoff_cluster.update_attribute(attribute.id, t.uint8_t(raw_value))
    key = attribute.name if use_name else attribute.id

    value = sonoff_cluster.get(key)
    assert isinstance(value, mini_zbdim.RoundedPercentRaw)
    assert int(value) == raw_value
    assert value * (100 / 255) == expected_percent
    assert isinstance(value * (100 / 255), int)
    assert value * 0.5 == raw_value * 0.5
    assert listener.attribute_updates == [(attribute.id, raw_value)]
    assert sonoff_cluster._attr_cache[attribute.id] == raw_value
    assert not isinstance(
        sonoff_cluster._attr_cache[attribute.id], mini_zbdim.RoundedPercentRaw
    )


@pytest.mark.parametrize("attribute", PERCENT_ATTRIBUTES, ids=lambda attr: attr.name)
@pytest.mark.parametrize("default", [None, True, False, 12.5])
def test_sonoff_mini_zbdim_percent_missing_value(sonoff_cluster, attribute, default):
    """Leave missing, boolean, and non-integer default values unchanged."""
    assert sonoff_cluster.get(attribute.name, default) is default


def test_sonoff_mini_zbdim_non_percent_value(sonoff_cluster):
    """Do not apply percentage rounding to other attributes."""
    attribute = SonoffCluster.AttributeDefs.transition_time
    sonoff_cluster.update_attribute(attribute.id, t.uint32_t(25))
    value = sonoff_cluster.get(attribute.name)
    assert not isinstance(value, mini_zbdim.RoundedPercentRaw)
    assert value * 0.1 == 2.5


def test_sonoff_mini_zbdim_entity_metadata(sonoff_cluster):
    """Expose the LED switch and use the correct brightness percentage multiplier."""
    device = sonoff_cluster.endpoint.device
    metadata = device.exposes_metadata[
        (1, SonoffCluster.cluster_id, ClusterType.Server)
    ]
    entities = {entity.attribute_name: entity for entity in metadata}
    for attribute in PERCENT_ATTRIBUTES:
        entity = entities[attribute.name]
        assert entity.entity_platform is EntityPlatform.NUMBER
        assert entity.cluster_id == SonoffCluster.cluster_id
        assert entity.endpoint_id == 1
        assert entity.multiplier == 100 / 255
        assert entity.unit == "%"
        assert entity.step == 1

    led = entities[SonoffCluster.AttributeDefs.network_led.name]
    assert led.entity_platform is EntityPlatform.SWITCH
    assert led.cluster_id == SonoffCluster.cluster_id
    assert led.endpoint_id == 1
    assert led.translation_key == "network_led"


@pytest.mark.parametrize("enabled", [False, True])
async def test_sonoff_mini_zbdim_network_led_write(sonoff_cluster, enabled):
    """Write LED state to the real boolean attribute without calibration remapping."""
    write_response = [
        [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
    ]
    with mock.patch.object(
        sonoff_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ) as mock_write:
        await sonoff_cluster.write_attributes(
            {SonoffCluster.AttributeDefs.network_led.name: enabled}
        )

    mock_write.assert_awaited_once()
    (written_attribute,) = mock_write.call_args[0][0]
    assert written_attribute.attrid == 0x0001
    assert isinstance(written_attribute.value.value, t.Bool)
    assert written_attribute.value.value == t.Bool(enabled)


@pytest.mark.parametrize("attribute", PERCENT_ATTRIBUTES, ids=lambda attr: attr.name)
@pytest.mark.parametrize("raw_value", [3, 128, 255])
async def test_sonoff_mini_zbdim_percent_raw_write(
    sonoff_cluster, attribute, raw_value
):
    """Serialize the raw brightness byte rather than the rounded display percentage."""
    sonoff_cluster.update_attribute(attribute.id, t.uint8_t(raw_value))
    value = sonoff_cluster.get(attribute.name)
    write_response = [
        [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
    ]
    with mock.patch.object(
        sonoff_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ) as mock_write:
        await sonoff_cluster.write_attributes({attribute.name: value})

    mock_write.assert_awaited_once()
    (written_attribute,) = mock_write.call_args[0][0]
    assert written_attribute.attrid == attribute.id
    assert written_attribute.value.value == raw_value
    assert written_attribute.value.value.serialize() == bytes([raw_value])


async def test_sonoff_mini_zbdim_write_attributes_maps_virtual_actions(
    zigpy_device_from_v2_quirk,
):
    """Virtual calibration action attributes should map to the real device attribute."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBDIM",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    write_response = [
        [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
    ]

    with mock.patch.object(
        sonoff_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ) as mock_write:
        start_value = bytes([0x01, 0x01, 0x01]).decode("latin-1")
        await sonoff_cluster.write_attributes(
            {SonoffCluster.AttributeDefs.set_calibration_action_start.name: start_value}
        )

        written_attrs = mock_write.call_args[0][0]
        assert len(written_attrs) == 1
        assert (
            written_attrs[0].attrid
            == SonoffCluster.AttributeDefs.set_calibration_action.id
        )
        assert written_attrs[0].value.value == start_value

        stop_value = bytes([0x01, 0x01, 0x02]).decode("latin-1")
        await sonoff_cluster.write_attributes(
            {
                SonoffCluster.AttributeDefs.set_calibration_action_stop.name: stop_value,
                SonoffCluster.AttributeDefs.delayed_power_on_state.name: True,
            }
        )

        written_attrs = mock_write.call_args[0][0]
        assert len(written_attrs) == 2
        assert (
            written_attrs[0].attrid
            == SonoffCluster.AttributeDefs.set_calibration_action.id
        )
        assert written_attrs[0].value.value == stop_value
        assert (
            written_attrs[1].attrid
            == SonoffCluster.AttributeDefs.delayed_power_on_state.id
        )
        assert written_attrs[1].value.value == t.Bool.true


async def test_sonoff_mini_zbdim_apply_custom_configuration_reads_backed_attributes(
    zigpy_device_from_v2_quirk,
):
    """Pairing configuration should read the attributes behind exposed entities."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBDIM",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster

    with mock.patch.object(
        sonoff_cluster,
        "read_attributes",
        mock.AsyncMock(),
    ) as mock_read:
        await sonoff_cluster.apply_custom_configuration()

    mock_read.assert_awaited_once_with(
        [
            SonoffCluster.AttributeDefs.delayed_power_on_state.id,
            SonoffCluster.AttributeDefs.delayed_power_on_time.id,
            SonoffCluster.AttributeDefs.external_trigger_mode.id,
            SonoffCluster.AttributeDefs.calibration_status.id,
            SonoffCluster.AttributeDefs.calibration_progress.id,
            SonoffCluster.AttributeDefs.transition_time.id,
            SonoffCluster.AttributeDefs.min_brightness_threshold.id,
            SonoffCluster.AttributeDefs.dimming_light_rate.id,
            SonoffCluster.AttributeDefs.max_brightness_threshold.id,
            SonoffCluster.AttributeDefs.level_for_calibration.id,
        ]
    )


async def test_sonoff_mini_zbdim_level_control_clamps_minimum_level(
    zigpy_device_from_v2_quirk,
):
    """Current level values below the device minimum should be clamped to 2."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBDIM",
        cluster_ids={
            1: {
                LevelControl.cluster_id: ClusterType.Server,
            }
        },
    )

    level_cluster = device.endpoints[1].level
    listener = ClusterListener(level_cluster)
    current_level_id = SonoffLevelControl.AttributeDefs.current_level.id

    level_cluster.update_attribute(current_level_id, 1)
    assert listener.attribute_updates[-1] == (current_level_id, 2)
    assert level_cluster.get(current_level_id) == 2

    level_cluster.update_attribute(current_level_id, 3)
    assert listener.attribute_updates[-1] == (current_level_id, 3)
    assert level_cluster.get(current_level_id) == 3
