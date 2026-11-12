"""Tests for Schneider Electric devices."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
from zhaquirks.schneiderelectric import SE_MANUF_NAME
from zhaquirks.schneiderelectric.motion import (
    AMBIENCE_LIGHT_THRESHOLD_MAX_LUX,
    AMBIENCE_LIGHT_THRESHOLD_MIN_LUX,
    SEAmbienceLightThreshold,
    lux_to_raw,
    raw_to_lux,
)
import zhaquirks.schneiderelectric.outlet
from zhaquirks.schneiderelectric.thermostat import SEControlStatus, SEThermostat

zhaquirks.setup()


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


@pytest.mark.parametrize("model", ("EKO07259", "WDE002497", "WDE011680"))
async def test_thermostat_control_status_off(zigpy_device_from_v2_quirk, model):
    """Test that control status 0x80, reported while switched off, is known."""

    device = zigpy_device_from_v2_quirk(
        manufacturer=SE_MANUF_NAME,
        model=model,
        endpoint_ids=[1, 2, 3, 5],
    )
    thermostat_cluster = device.endpoints[1].in_clusters[SEThermostat.cluster_id]
    assert isinstance(thermostat_cluster, SEThermostat)

    control_status_attr_id = SEThermostat.AttributeDefs.se_control_status.id
    thermostat_cluster.update_attribute(control_status_attr_id, 0x80)

    # ZHA's enum sensor formats the cached raw value as ``enum(value).name``;
    # without an ``Off`` member this would be "undefined_0x80", which Home
    # Assistant rejects as not being one of the sensor's options.
    value = thermostat_cluster.get(control_status_attr_id)
    assert SEControlStatus(value) is SEControlStatus.Off
    assert SEControlStatus(value).name == "Off"


@pytest.mark.parametrize(
    ("lux", "raw"), ((1, 1), (10, 10001), (100, 20001), (1000, 30001), (2000, 33011))
)
def test_nhmotion_lux_conversion(lux, raw):
    """Test the ambience light threshold lux encoding."""
    assert lux_to_raw(lux) == raw
    assert raw_to_lux(raw) == lux


def test_nhmotion_lux_round_trip():
    """Test that every lux value in the entity range survives a write and read."""
    for lux in range(
        AMBIENCE_LIGHT_THRESHOLD_MIN_LUX, AMBIENCE_LIGHT_THRESHOLD_MAX_LUX + 1
    ):
        assert raw_to_lux(lux_to_raw(lux)) == lux


async def test_nhmotion_ambience_light_threshold_entity():
    """Test that the threshold entity shows lux and writes the encoded value."""
    cluster = mock.MagicMock()
    entity = SEAmbienceLightThreshold.__new__(SEAmbienceLightThreshold)
    entity._cluster = cluster

    values = []
    for raw in (30001, None):
        cluster.get.return_value = raw
        values.append(entity.native_value)
    assert values == [1000, None]

    with (
        mock.patch(
            "zha.application.platforms.number.write_attributes_safe"
        ) as write_mock,
        mock.patch.object(entity, "maybe_emit_state_changed_event"),
    ):
        await entity.async_set_native_value(100)

    write_mock.assert_awaited_once_with(cluster, {"ambience_light_threshold": 20001})
