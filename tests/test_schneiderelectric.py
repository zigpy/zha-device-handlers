"""Tests for Schneider Electric devices."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.clusters.measurement import OccupancySensing, TemperatureMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
from zhaquirks.schneiderelectric import SE_MANUF_NAME
import zhaquirks.schneiderelectric.outlet
from zhaquirks.schneiderelectric.thermostat import (
    SECycleTime,
    SEHeatingCoolingOutput,
    SEMetering,
    SEPilotWireHeatingOutputMode,
    SERelayHeatingOutputMode,
    SETemperatureMeasurementExternal,
)

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


THERMOSTAT_EP1_CLUSTERS = (
    Thermostat.cluster_id,
    UserInterface.cluster_id,
    SECycleTime.cluster_id,
    SEHeatingCoolingOutput.cluster_id,
)


def thermostat_cluster_ids(with_floor_sensor: bool) -> dict:
    """Return the endpoint layout of the thermostats, as in the ZHA diagnostics."""
    cluster_ids = {
        1: dict.fromkeys(THERMOSTAT_EP1_CLUSTERS, ClusterType.Server),
        2: {
            Basic.cluster_id: ClusterType.Server,
            TemperatureMeasurement.cluster_id: ClusterType.Server,
        },
        4: {
            Basic.cluster_id: ClusterType.Server,
            OccupancySensing.cluster_id: ClusterType.Server,
        },
        5: {
            Basic.cluster_id: ClusterType.Server,
            Metering.cluster_id: ClusterType.Server,
        },
    }
    if with_floor_sensor:
        cluster_ids[3] = {
            Basic.cluster_id: ClusterType.Server,
            TemperatureMeasurement.cluster_id: ClusterType.Server,
        }
    return cluster_ids


@pytest.mark.parametrize(
    "model, with_floor_sensor, heating_output_mode_enum",
    (
        ("EKO07259", True, SERelayHeatingOutputMode),
        ("WDE002497", True, SERelayHeatingOutputMode),
        ("WDE011680", True, SEPilotWireHeatingOutputMode),
        ("S520619", False, SEPilotWireHeatingOutputMode),
    ),
)
async def test_thermostat_entities(
    zigpy_device_from_v2_quirk,
    caplog,
    model,
    with_floor_sensor,
    heating_output_mode_enum,
):
    """Test the thermostat quirk applies and exposes entities on existing endpoints."""
    device = zigpy_device_from_v2_quirk(
        SE_MANUF_NAME,
        model,
        endpoint_ids=[1, 2, 4, 5] + ([3] if with_floor_sensor else []),
        cluster_ids=thermostat_cluster_ids(with_floor_sensor),
    )

    assert isinstance(device.endpoints[5].smartenergy_metering, SEMetering)
    if with_floor_sensor:
        assert isinstance(
            device.endpoints[3].temperature, SETemperatureMeasurementExternal
        )
    else:
        assert 3 not in device.endpoints
        assert "missing endpoint" not in caplog.text

    entry = DEVICE_REGISTRY.match_entry(device)
    entities = {
        (metadata.endpoint_id, metadata.attribute_name): metadata
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    }

    assert (5, SEMetering.AttributeDefs.se_fixed_load_demand.name) in entities

    regulator_level = entities[(1, SECycleTime.AttributeDefs.se_demand_percentage.name)]
    assert regulator_level.translation_key == "regulator_level"
    assert regulator_level.min == 0
    assert regulator_level.max == 100
    assert regulator_level.step == 10

    heating_output_mode = entities[
        (1, SEHeatingCoolingOutput.AttributeDefs.se_heating_output_mode.name)
    ]
    assert heating_output_mode.enum == heating_output_mode_enum

    has_ep3_entities = any(endpoint_id == 3 for endpoint_id, _ in entities)
    assert has_ep3_entities is with_floor_sensor


async def test_thermostat_regulator_level_write(zigpy_device_from_v2_quirk):
    """Test the regulator level is written as a manufacturer specific attribute."""
    device = zigpy_device_from_v2_quirk(
        SE_MANUF_NAME,
        "S520619",
        endpoint_ids=[1, 2, 4, 5],
        cluster_ids=thermostat_cluster_ids(with_floor_sensor=False),
    )
    cycle_time_cluster = device.endpoints[1].in_clusters[SECycleTime.cluster_id]
    assert isinstance(cycle_time_cluster, SECycleTime)

    with mock.patch.object(
        cycle_time_cluster,
        "_write_attributes",
        mock.AsyncMock(
            return_value=(
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],
            )
        ),
    ) as write_mock:
        await cycle_time_cluster.write_attributes(
            {SECycleTime.AttributeDefs.se_demand_percentage.name: 40}
        )

    assert write_mock.call_count == 1
    (record,) = write_mock.call_args.args[0]
    assert record.attrid == SECycleTime.AttributeDefs.se_demand_percentage.id
    assert record.value.value == 40
    assert write_mock.call_args.kwargs["manufacturer"] == device.manufacturer_id
