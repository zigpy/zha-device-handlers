"""Tests for AduroSmart quirks."""

import pytest
from zha.quirks import QUIRK_REGISTRY_ENTRY_ATTR
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    RelativeHumidity,
    TemperatureMeasurement,
)

import zhaquirks
from zhaquirks.aduro.csw_82909 import ADUROLIGHT_ACCEL_CLUSTER_ID
from zhaquirks.builder import ReportingConfig

zhaquirks.setup()


CONTACT_REPORTING = {
    (
        PowerConfiguration.cluster_id,
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.name,
    ): ReportingConfig(min_interval=3600, max_interval=65000, reportable_change=2),
    (
        TemperatureMeasurement.cluster_id,
        TemperatureMeasurement.AttributeDefs.measured_value.name,
    ): ReportingConfig(min_interval=10, max_interval=3600, reportable_change=100),
    (
        RelativeHumidity.cluster_id,
        RelativeHumidity.AttributeDefs.measured_value.name,
    ): ReportingConfig(min_interval=10, max_interval=3600, reportable_change=100),
}

MOTION_REPORTING = {
    **CONTACT_REPORTING,
    (
        OccupancySensing.cluster_id,
        OccupancySensing.AttributeDefs.occupancy.name,
    ): ReportingConfig(min_interval=1, max_interval=3600, reportable_change=0),
    (
        IlluminanceMeasurement.cluster_id,
        IlluminanceMeasurement.AttributeDefs.measured_value.name,
    ): ReportingConfig(min_interval=5, max_interval=3600, reportable_change=100),
}


@pytest.mark.parametrize(
    ("manufacturer", "model", "cluster_ids", "expected"),
    [
        pytest.param(
            manufacturer,
            "CSW_81909",
            {
                PowerConfiguration.cluster_id,
                TemperatureMeasurement.cluster_id,
                RelativeHumidity.cluster_id,
                ADUROLIGHT_ACCEL_CLUSTER_ID,
            },
            CONTACT_REPORTING,
            id=f"81910-{manufacturer}",
        )
        for manufacturer in ("AduroSmart ERIA", "AduroSmart Eria", "ERIA")
    ]
    + [
        pytest.param(
            manufacturer,
            "VMS_ADUROLIGHT",
            {
                PowerConfiguration.cluster_id,
                IlluminanceMeasurement.cluster_id,
                TemperatureMeasurement.cluster_id,
                RelativeHumidity.cluster_id,
                OccupancySensing.cluster_id,
            },
            MOTION_REPORTING,
            id=f"81915-{manufacturer}",
        )
        for manufacturer in ("AduroSmart ERIA", "ERIA")
    ],
)
def test_multi_sensor_reporting_config(
    zigpy_device_from_v2_quirk,
    manufacturer,
    model,
    cluster_ids,
    expected,
) -> None:
    """Multi sensors use their device-specific reporting parameters."""
    device = zigpy_device_from_v2_quirk(
        manufacturer,
        model,
        cluster_ids={1: dict.fromkeys(cluster_ids, ClusterType.Server)},
    )

    entry = getattr(device, QUIRK_REGISTRY_ENTRY_ATTR)
    metadata = entry.zha_device_factory.quirk_definition.entity_metadata
    actual = {
        (entity.cluster_id, entity.attribute_name): entity.reporting_config
        for entity in metadata
        if getattr(entity, "attribute_name", None) is not None
        and entity.cluster_id in {cluster_id for cluster_id, _ in expected}
    }

    assert actual == expected
    for entity in metadata:
        if entity.cluster_id in {cluster_id for cluster_id, _ in expected}:
            assert entity.unique_id_suffix == str(entity.cluster_id)
