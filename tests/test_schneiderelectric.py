"""Tests for Schneider Electric devices."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
from zhaquirks.builder import BinarySensorDeviceClass, EntityType
from zhaquirks.builder.metadata import BinarySensorMetadata
from zhaquirks.schneiderelectric import SE_MANUF_NAME
import zhaquirks.schneiderelectric.outlet

zhaquirks.setup()

SHUTTER_MODELS = ("1GANG/SHUTTER/1", "NHPB/SHUTTER/1", "PUCK/SHUTTER/1")


async def test_1gang_shutter_1_go_to_lift_percentage_cmd(zigpy_device_from_v2_quirk):
    """Asserts that the go_to_lift_percentage command inverts the percentage value."""

    device = zigpy_device_from_v2_quirk(
        manufacturer=SE_MANUF_NAME,
        model="1GANG/SHUTTER/1",
        endpoint_ids=[5, 21],
    )
    window_covering_cluster = device.endpoints[5].window_covering

    p = mock.patch.object(window_covering_cluster, "request", mock.AsyncMock())
    with p as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        await window_covering_cluster.go_to_lift_percentage(58)

        assert request_mock.call_count == 1
        assert request_mock.call_args[0][1] == (
            WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
        )
        assert request_mock.call_args[0][3] == 42  # 100 - 58


async def test_1gang_shutter_1_unpatched_cmd(zigpy_device_from_v2_quirk):
    """Asserts that unpatched ZCL commands keep working."""

    device = zigpy_device_from_v2_quirk(
        manufacturer=SE_MANUF_NAME,
        model="1GANG/SHUTTER/1",
        endpoint_ids=[5, 21],
    )
    window_covering_cluster = device.endpoints[5].window_covering

    p = mock.patch.object(window_covering_cluster, "request", mock.AsyncMock())
    with p as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        await window_covering_cluster.up_open()

        assert request_mock.call_count == 1
        assert request_mock.call_args[0][1] == (
            WindowCovering.ServerCommandDefs.up_open.id
        )


async def test_1gang_shutter_1_lift_percentage_updates(zigpy_device_from_v2_quirk):
    """Asserts that updates to the ``current_position_lift_percentage`` attribute.

    (e.g., by the device) invert the reported percentage value.
    """

    device = zigpy_device_from_v2_quirk(
        manufacturer=SE_MANUF_NAME,
        model="1GANG/SHUTTER/1",
        endpoint_ids=[5, 21],
    )
    window_covering_cluster = device.endpoints[5].window_covering
    cluster_listener = ClusterListener(window_covering_cluster)

    window_covering_cluster.update_attribute(
        WindowCovering.AttributeDefs.current_position_lift_percentage.id,
        77,
    )

    assert len(cluster_listener.attribute_updates) == 1
    assert cluster_listener.attribute_updates[0] == (
        WindowCovering.AttributeDefs.current_position_lift_percentage.id,
        23,  # 100 - 77
    )
    assert len(cluster_listener.cluster_commands) == 0


@pytest.mark.parametrize("model", SHUTTER_MODELS)
async def test_shutter_reversed_flag_mirrored(zigpy_device_from_v2_quirk, model):
    """Window covering mode bit 0 is mirrored into config status bit 2.

    ZHA's inversion switch writes window_covering_mode but reads config_status.
    """
    device = zigpy_device_from_v2_quirk(
        manufacturer=SE_MANUF_NAME, model=model, endpoint_ids=[5, 21]
    )
    cluster = device.endpoints[5].window_covering
    attrs = WindowCovering.AttributeDefs
    reversed_flag = WindowCovering.ConfigStatus.Open_up_commands_reversed

    # config status without a known mode is left untouched
    cluster.update_attribute(attrs.config_status.id, 0b0000_0011)
    assert cluster.get(attrs.config_status.id) == 0b0000_0011

    # device default mode: LED feedback on, not reversed
    cluster.update_attribute(attrs.window_covering_mode.id, 0b0000_1000)
    assert cluster.get(attrs.config_status.id) == 0b0000_0011

    # reversed: bit 2 set, other config status bits kept, mode stored as reported
    cluster.update_attribute(attrs.window_covering_mode.id, 0b0000_1001)
    assert cluster.get(attrs.window_covering_mode.id) == 0b0000_1001
    assert cluster.get(attrs.config_status.id) == 0b0000_0011 | reversed_flag

    # a later config status report without bit 2 keeps the reversed state
    cluster.update_attribute(attrs.config_status.id, 0b0000_0011)
    assert cluster.get(attrs.config_status.id) == 0b0000_0011 | reversed_flag

    # back to normal: bit 2 cleared, other bits kept
    cluster.update_attribute(attrs.window_covering_mode.id, 0b0000_1000)
    assert cluster.get(attrs.config_status.id) == 0b0000_0011

    # a config status report with bit 2 set is corrected from the mode
    cluster.update_attribute(attrs.config_status.id, 0b0000_0111)
    assert cluster.get(attrs.config_status.id) == 0b0000_0011


@pytest.mark.parametrize("model", SHUTTER_MODELS)
def test_shutter_sun_protection_entities(zigpy_device_from_v2_quirk, model):
    """Sun protection status and sensor attributes are exposed as diagnostics."""
    device = zigpy_device_from_v2_quirk(
        manufacturer=SE_MANUF_NAME, model=model, endpoint_ids=[5, 21]
    )
    entry = DEVICE_REGISTRY.match_entry(device)
    entities = {
        metadata.resolved_unique_id_suffix: metadata
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    }

    status = entities["se_sun_protection_status"]
    sensor = entities["se_sun_protection_sensor"]
    for metadata in (status, sensor):
        assert isinstance(metadata, BinarySensorMetadata)
        assert metadata.endpoint_id == 5
        assert metadata.cluster_id == WindowCovering.cluster_id
        assert metadata.entity_type == EntityType.DIAGNOSTIC
    assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY


@pytest.mark.parametrize("quirk", (zhaquirks.schneiderelectric.outlet.SocketOutlet,))
async def test_schneider_device_temp(zigpy_device_from_quirk, quirk):
    """Test that instant demand is divided by 1000."""
    device = zigpy_device_from_quirk(quirk)

    metering_cluster = device.endpoints[6].smartenergy_metering
    metering_listener = ClusterListener(metering_cluster)
    instantaneous_demand_attr_id = Metering.AttributeDefs.instantaneous_demand.id
    summation_delivered_attr_id = Metering.AttributeDefs.current_summ_delivered.id

    # verify instant demand is divided by 1000
    metering_cluster.update_attribute(instantaneous_demand_attr_id, 25000)
    assert len(metering_listener.attribute_updates) == 1
    assert metering_listener.attribute_updates[0][0] == instantaneous_demand_attr_id
    assert metering_listener.attribute_updates[0][1] == 25  # divided by 1000

    # verify other attributes are not modified
    metering_cluster.update_attribute(summation_delivered_attr_id, 25)
    assert len(metering_listener.attribute_updates) == 2
    assert metering_listener.attribute_updates[1][0] == summation_delivered_attr_id
    assert metering_listener.attribute_updates[1][1] == 25  # not modified
