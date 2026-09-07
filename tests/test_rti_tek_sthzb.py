"""Tests for the Rti-Tek STHZB quirk."""

from pathlib import Path
from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic, Identify, PollControl, PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

import zhaquirks
from zhaquirks.rti_tek import sthzb

zhaquirks.setup()


STHZB_DIAGNOSTIC_CLUSTERS = {
    1: {
        Basic.cluster_id: ClusterType.Server,
        PowerConfiguration.cluster_id: ClusterType.Server,
        Identify.cluster_id: ClusterType.Server,
        PollControl.cluster_id: ClusterType.Server,
        TemperatureMeasurement.cluster_id: ClusterType.Server,
        RelativeHumidity.cluster_id: ClusterType.Server,
        sthzb.RtiTekFd22Cluster.cluster_id: ClusterType.Server,
        0xEF00: ClusterType.Server,
        0xFC57: ClusterType.Server,
    }
}


async def test_sthzb_matches_and_replaces_private_cluster(zigpy_device_from_v2_quirk):
    """The exact Rti-Tek STHZB signature installs the FD22 cluster."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="STHZB",
        cluster_ids=STHZB_DIAGNOSTIC_CLUSTERS,
    )

    assert isinstance(
        device.endpoints[1].in_clusters[sthzb.RtiTekFd22Cluster.cluster_id],
        sthzb.RtiTekFd22Cluster,
    )


def test_sthzb_private_attribute_contract():
    """FD22 attributes retain their observed IDs and Zigbee types."""

    attributes = sthzb.RtiTekFd22Cluster.AttributeDefs

    assert {
        attribute.name: (attribute.id, attribute.zcl_type)
        for attribute in (
            attributes.temperature_unit,
            attributes.fault_code,
            attributes.product_name,
            attributes.internal_temperature_calibration,
            attributes.internal_humidity_calibration,
            attributes.sample_interval,
            attributes.temperature_alarm_upper,
            attributes.temperature_alarm_lower,
            attributes.humidity_alarm_upper,
            attributes.humidity_alarm_lower,
            attributes.temperature_alarm_status,
            attributes.humidity_alarm_status,
        )
    } == {
        "temperature_unit": (0x0000, foundation.DataTypeId.enum8),
        "fault_code": (0x0002, foundation.DataTypeId.map32),
        "product_name": (0x0003, foundation.DataTypeId.string),
        "internal_temperature_calibration": (0xE005, foundation.DataTypeId.int8),
        "internal_humidity_calibration": (0xE006, foundation.DataTypeId.int8),
        "sample_interval": (0xE009, foundation.DataTypeId.uint16),
        "temperature_alarm_upper": (0xE00A, foundation.DataTypeId.int16),
        "temperature_alarm_lower": (0xE00B, foundation.DataTypeId.int16),
        "humidity_alarm_upper": (0xE00C, foundation.DataTypeId.uint16),
        "humidity_alarm_lower": (0xE00D, foundation.DataTypeId.uint16),
        "temperature_alarm_status": (0xE00E, foundation.DataTypeId.enum8),
        "humidity_alarm_status": (0xE00F, foundation.DataTypeId.enum8),
    }


async def test_sthzb_v1_does_not_schedule_lifecycle_tasks(
    zigpy_device_from_v2_quirk,
):
    """The upstream candidate has no startup or rejoin lifecycle behavior."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="STHZB",
        cluster_ids=STHZB_DIAGNOSTIC_CLUSTERS,
    )
    cluster = device.endpoints[1].in_clusters[sthzb.RtiTekFd22Cluster.cluster_id]

    assert not hasattr(cluster, "_initial_read_task")
    assert not hasattr(cluster, "_initial_reporting_sync_task")
    assert not hasattr(cluster, "_rejoin_task")


def test_sthzb_attribute_converters():
    """Observed alarm and fault values map to stable diagnostic text."""

    assert sthzb.convert_alarm_status(0) == "Normal"
    assert sthzb.convert_alarm_status(1) == "Low"
    assert sthzb.convert_alarm_status(2) == "High"
    assert sthzb.convert_alarm_status(3) == "Unknown 0x03"
    assert sthzb.convert_alarm_status(None) == "Unknown"
    assert sthzb.convert_fault_code(0) == "No fault"
    assert sthzb.convert_fault_code(0b00101) == "Internal sensor fault, Low battery"
    assert sthzb.convert_fault_code(0x80) == "Unknown 0x00000080"
    assert sthzb.convert_fault_code(None) == "Unknown"


def test_sthzb_exposes_static_fd22_entities():
    """The quirk exposes verified FD22 controls and diagnostics."""

    entries = [
        entry
        for entry in DEVICE_REGISTRY
        if entry.source.file is not None
        and Path(entry.source.file).name == "sthzb.py"
        and "rti_tek" in Path(entry.source.file).parts
    ]
    assert len(entries) == 1

    metadata = entries[0].zha_device_factory.quirk_definition.entity_metadata
    attribute_names = {
        entry.attribute_name for entry in metadata if hasattr(entry, "attribute_name")
    }

    assert attribute_names == {
        "temperature_unit",
        "internal_temperature_calibration",
        "internal_humidity_calibration",
        "sample_interval",
        "temperature_alarm_upper",
        "temperature_alarm_lower",
        "humidity_alarm_upper",
        "humidity_alarm_lower",
        "temperature_alarm_status",
        "humidity_alarm_status",
        "fault_code",
        "product_name",
    }


async def test_sthzb_rejects_invalid_alarm_threshold_pairs(
    zigpy_device_from_v2_quirk,
):
    """Alarm thresholds retain the device-safe minimum separation."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="STHZB",
        cluster_ids=STHZB_DIAGNOSTIC_CLUSTERS,
    )
    cluster = device.endpoints[1].in_clusters[sthzb.RtiTekFd22Cluster.cluster_id]
    attributes = cluster.AttributeDefs
    cluster._update_attribute(attributes.temperature_alarm_lower.id, 2080)
    cluster._update_attribute(attributes.humidity_alarm_lower.id, 5600)

    with mock.patch.object(cluster, "request", new_callable=mock.AsyncMock) as request:
        with pytest.raises(ValueError, match="temperature alarm"):
            await cluster.write_attributes({"temperature_alarm_upper": 2090})

        with pytest.raises(ValueError, match="humidity alarm"):
            await cluster.write_attributes({"humidity_alarm_upper": 5700})

        with pytest.raises(ValueError, match="temperature alarm"):
            await cluster.write_attributes(
                {
                    "temperature_alarm_lower": 2210,
                    "temperature_alarm_upper": 2220,
                }
            )

    request.assert_not_awaited()

    valid_attributes = {
        "temperature_alarm_upper": 2239,
        "humidity_alarm_upper": 7701,
    }
    cluster._normalize_and_validate_alarm_limits(valid_attributes)

    assert valid_attributes == {
        "temperature_alarm_upper": 2230,
        "humidity_alarm_upper": 7700,
    }


async def test_sthzb_normalizes_only_alarm_attributes_and_writes(
    zigpy_device_from_v2_quirk,
):
    """Unrelated attributes bypass alarm handling and valid values are written."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="STHZB",
        cluster_ids=STHZB_DIAGNOSTIC_CLUSTERS,
    )
    cluster = device.endpoints[1].in_clusters[sthzb.RtiTekFd22Cluster.cluster_id]
    attributes = cluster.AttributeDefs
    cluster._update_attribute(attributes.temperature_alarm_lower.id, 2080)

    values = {"sample_interval": 60, 0xFFFF: 1}
    cluster._normalize_and_validate_alarm_limits(values)
    assert values == {"sample_interval": 60, 0xFFFF: 1}

    with mock.patch.object(
        sthzb.CustomCluster, "write_attributes", new_callable=mock.AsyncMock
    ) as write_attributes:
        await cluster.write_attributes({"temperature_alarm_upper": 2259})

    write_attributes.assert_awaited_once_with(
        {"temperature_alarm_upper": 2250}, manufacturer=None
    )
