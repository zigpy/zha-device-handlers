"""Tests for the ROBB/Sunricher floor thermostat quirk."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import Cluster, ClusterType
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

import zhaquirks
from zhaquirks.sunricher.robb_200_040_0_fw_1033 import (
    ATTR_CONTROL_TYPE,
    ATTR_FLOOR_SENSOR_CALIBRATION,
    ATTR_LOCAL_TEMP,
    ATTR_LOCAL_TEMP_CALIBRATION,
    ATTR_OUTDOOR_TEMP,
    ChildLockEnum,
    ControlTypeEnum,
    SunricherFloorProbeCluster,
    SunricherThermostatCluster,
    SunricherUserInterfaceCluster,
    TempUnitEnum,
)

zhaquirks.setup()

MANUFACTURER = "ROBB smarrt"
MODEL = "ROB_200-040-0"


@pytest.fixture
def thermostat(zigpy_device_from_v2_quirk):
    """Return a quirked ROBB floor thermostat."""
    return zigpy_device_from_v2_quirk(
        MANUFACTURER,
        MODEL,
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                UserInterface.cluster_id: ClusterType.Server,
                TemperatureMeasurement.cluster_id: ClusterType.Server,
            },
        },
    )


def test_user_interface_attributes_are_normalized(thermostat):
    """Temperature scale is typed and every nonzero lock value means locked."""
    cluster = thermostat.endpoints[1].in_clusters[UserInterface.cluster_id]
    assert isinstance(cluster, SunricherUserInterfaceCluster)

    cluster._update_attribute(0x0000, 0)
    assert cluster.get("temperature_unit_scale") is TempUnitEnum.Celsius
    cluster._update_attribute(0x0000, 1)
    assert cluster.get("temperature_unit_scale") is TempUnitEnum.Fahrenheit

    cluster._update_attribute(0x0001, 0)
    assert cluster.get("keypad_lock_active") is ChildLockEnum.No
    cluster._update_attribute(0x0001, 7)
    assert cluster.get("keypad_lock_active") is ChildLockEnum.Yes


@pytest.mark.asyncio
async def test_user_interface_writes_are_normalized(thermostat):
    """The UI cluster writes standard attribute IDs and binary lock values."""
    cluster = thermostat.endpoints[1].in_clusters[UserInterface.cluster_id]

    with mock.patch.object(
        Cluster, "write_attributes", new_callable=mock.AsyncMock
    ) as write_attributes:
        await cluster.write_attributes(
            {"temperature_unit_scale": 1, "keypad_lock_active": 7}
        )
        write_attributes.assert_awaited_once_with(
            {0x0000: TempUnitEnum.Fahrenheit, 0x0001: 1}, manufacturer=None
        )

        write_attributes.reset_mock()
        await cluster.write_attributes({"keypad_lockout": 0})
        write_attributes.assert_awaited_once_with({0x0001: 0}, manufacturer=None)


def test_floor_probe_updates_thermostat_floor_temperature(thermostat):
    """The measured floor temperature is routed to thermostat outdoor/local temp."""
    endpoint = thermostat.endpoints[1]
    thermostat_cluster = endpoint.in_clusters[Thermostat.cluster_id]
    probe_cluster = endpoint.in_clusters[TemperatureMeasurement.cluster_id]

    assert isinstance(thermostat_cluster, SunricherThermostatCluster)
    assert isinstance(probe_cluster, SunricherFloorProbeCluster)

    probe_cluster._update_attribute(
        TemperatureMeasurement.AttributeDefs.measured_value.id, 2150
    )

    assert thermostat_cluster.get(ATTR_OUTDOOR_TEMP) == 2150
    assert thermostat_cluster.get(ATTR_LOCAL_TEMP) == 2150

    thermostat_cluster._update_attribute(ATTR_LOCAL_TEMP_CALIBRATION, 50)
    thermostat_cluster._update_attribute(ATTR_FLOOR_SENSOR_CALIBRATION, -50)
    assert thermostat_cluster.get(ATTR_LOCAL_TEMP_CALIBRATION) == 30
    assert thermostat_cluster.get(ATTR_FLOOR_SENSOR_CALIBRATION) == -30


def test_quirk_entities_and_default_entity_filter(thermostat):
    """The app version and config controls target the expected ZCL attributes."""
    entry = DEVICE_REGISTRY.match_entry(thermostat)
    assert entry is not None
    definition = entry.zha_device_factory.quirk_definition
    entities = {
        metadata.resolved_unique_id_suffix: metadata
        for metadata in definition.entity_metadata
    }

    app_version = entities["app_version"]
    assert app_version.cluster_id == Basic.cluster_id
    assert app_version.attribute_name == Basic.AttributeDefs.app_version.name
    assert app_version.attribute_initialized_from_cache is False

    assert entities["temperature_unit_scale"].entity_type.name == "CONFIG"
    assert entities["keypad_lock_active"].entity_type.name == "CONFIG"

    (default_filter,) = definition.disabled_default_entities
    assert default_filter.endpoint_id == 1
    assert default_filter.unique_id_suffix == "keypad_lockout"
    assert default_filter.cluster_id == UserInterface.cluster_id


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, "Off"), (1, "Low"), (255, "Off")],
)
def test_vibration_sensor_converter(thermostat, value, expected):
    """The vibration sensor translates known values and uses its configured fallback."""
    entry = DEVICE_REGISTRY.match_entry(thermostat)
    assert entry is not None
    entities = {
        metadata.resolved_unique_id_suffix: metadata
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    }

    assert entities["vibration_level_text"].attribute_converter(value) == expected


def test_floor_sensor_control_type_keeps_room_temperature(thermostat):
    """Room-sensor mode does not replace local temperature with floor readings."""
    endpoint = thermostat.endpoints[1]
    thermostat_cluster = endpoint.in_clusters[Thermostat.cluster_id]
    probe_cluster = endpoint.in_clusters[TemperatureMeasurement.cluster_id]

    thermostat_cluster._update_attribute(ATTR_CONTROL_TYPE, ControlTypeEnum.Room_Sensor)
    thermostat_cluster._update_attribute(ATTR_LOCAL_TEMP, 2200)
    probe_cluster._update_attribute(
        TemperatureMeasurement.AttributeDefs.measured_value.id, 1800
    )

    assert thermostat_cluster.get(ATTR_OUTDOOR_TEMP) == 1800
    assert thermostat_cluster.get(ATTR_LOCAL_TEMP) == 2200
