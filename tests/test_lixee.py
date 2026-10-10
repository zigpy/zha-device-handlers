"""Tests for LiXee ZLinky tariff reporting."""

from unittest.mock import AsyncMock, Mock

import pytest
from zha.application.platforms.sensor import Sensor
from zha.quirks import DEVICE_REGISTRY
from zha.zigbee.device import Device as ZHADevice
from zha.zigbee.endpoint import Endpoint as ZHAEndpoint
from zigpy.profiles import zgp, zha
from zigpy.zcl.clusters.general import GreenPowerProxy, Ota, Time
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks
from zhaquirks.builder.device import QuirkV2Factory
from zhaquirks.builder.discovery import discover_quirks_v2_entities
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.lixee.zlinky import (
    ZLinkyTIC,
    ZLinkyTICFWV12,
    ZLinkyTICFWV14,
    ZLinkyTICMetering,
    ZLinkyTICTariffCluster,
    tariff_period,
)
from zhaquirks.tuya import TuyaManufCluster

zhaquirks.setup()


@pytest.fixture
def zlinky_v17(zigpy_device_mock):
    """Build the original signature captured from a standard three-phase v17 device."""
    device = zigpy_device_mock()
    device.manufacturer = "LiXee"
    device.model = "ZLinky_TIC"
    ep = device.add_endpoint(1)
    ep.profile_id = zha.PROFILE_ID
    ep.device_type = zha.DeviceType.DIMMABLE_LIGHT
    for cluster_id in (
        0x0000,
        0x0001,
        0x0003,
        0x000A,
        0x0702,
        0x0B04,
        0x0B01,
        0xFF66,
        0xEF00,
    ):
        ep.add_input_cluster(cluster_id)
    for cluster_id in (0x0019, 0xEF00):
        ep.add_output_cluster(cluster_id)
    ep.out_clusters[Ota.cluster_id].update_attribute(
        Ota.AttributeDefs.current_file_version.id, 0x11
    )
    ep = device.add_endpoint(242)
    ep.profile_id = zgp.PROFILE_ID
    ep.device_type = zgp.DeviceType.PROXY_BASIC
    ep.add_input_cluster(GreenPowerProxy.cluster_id)
    ep.add_output_cluster(GreenPowerProxy.cluster_id)
    return device


def test_zlinky_v17_selection_and_metering(zlinky_v17):
    """Resolve the v2 quirk without losing energy scaling or existing endpoints."""
    entry = DEVICE_REGISTRY.match_entry(zlinky_v17)
    assert isinstance(entry.zha_device_factory, QuirkV2Factory)
    device = DEVICE_REGISTRY.resolve(zlinky_v17)
    assert isinstance(device, CustomZigpyDevice)
    assert set(device.endpoints) == set(zlinky_v17.endpoints)
    assert device.endpoints[1].device_type == zha.DeviceType.DIMMABLE_LIGHT
    assert Time.cluster_id in device.endpoints[1].in_clusters
    assert isinstance(device.endpoints[1].smartenergy_metering, ZLinkyTICMetering)
    assert device.endpoints[1].smartenergy_metering.get("multiplier") == 1
    assert device.endpoints[1].smartenergy_metering.get("divisor") == 1000
    assert set(device.endpoints[1].in_clusters) == (
        set(zlinky_v17.endpoints[1].in_clusters) - {TuyaManufCluster.cluster_id}
    )
    assert set(device.endpoints[1].out_clusters) == {Ota.cluster_id}
    assert set(device.endpoints[242].in_clusters) == {GreenPowerProxy.cluster_id}
    assert set(device.endpoints[242].out_clusters) == {GreenPowerProxy.cluster_id}


@pytest.mark.parametrize("quirk", [ZLinkyTIC, ZLinkyTICFWV12, ZLinkyTICFWV14])
def test_zlinky_older_firmware_unchanged(quirk, zigpy_device_from_quirk):
    """Keep the original quirks for signatures predating firmware v15."""
    raw_device = zigpy_device_from_quirk(quirk, apply_quirk=False)
    assert isinstance(DEVICE_REGISTRY.resolve(raw_device), quirk)


def test_zlinky_signature_filter(zlinky_v17):
    """Do not apply the tariff quirk to an unrelated endpoint layout."""
    zlinky_v17.endpoints[1].in_clusters.pop(Metering.cluster_id)
    assert DEVICE_REGISTRY.resolve(zlinky_v17) is zlinky_v17


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" HEURE  PLEINE", "HEURE PLEINE"),
        (" HEURE  CREUSE\x00", "HEURE CREUSE"),
        ("HC..", "HC.."),
        ("HP..", "HP.."),
        ("HCJB", "HCJB"),
        ("HPJR", "HPJR"),
        ("BASE", "BASE"),
        (" Supplier  label ", "Supplier label"),
        (b" HC..\x00", "HC.."),
        (" \x00 ", None),
        (None, None),
    ],
)
def test_tariff_period(raw, expected):
    """Normalize padded values without discarding supplier or Tempo information."""
    assert tariff_period(raw) == expected


async def test_zlinky_tariff_entity_updates_from_reports(zlinky_v17):
    """Create the sensor and update its state from ordinary ZCL reports without reads."""
    entry = DEVICE_REGISTRY.match_entry(zlinky_v17)
    device = DEVICE_REGISTRY.resolve(zlinky_v17)
    cluster = device.endpoints[1].zlinky_manufacturer_specific
    assert isinstance(cluster, ZLinkyTICTariffCluster)
    attribute = cluster.AttributeDefs.linky_tariff_period
    assert attribute.id == 0x0010
    assert cluster._get_effective_manufacturer_code(attribute) is None
    cluster.read_attributes = AsyncMock()

    zha_device = Mock(
        spec=ZHADevice,
        ieee=device.ieee,
        unique_id=str(device.ieee),
        name="ZLinky_TIC",
        quirk_metadata=entry.zha_device_factory.quirk_definition,
    )
    zha_device.endpoints = {1: ZHAEndpoint(device.endpoints[1], zha_device)}
    entities = list(discover_quirks_v2_entities(zha_device))
    assert len(entities) == 1
    entity = entities[0]
    assert isinstance(entity, Sensor)
    assert entity.unique_id == f"{device.ieee}-1-tariff_period"
    assert entity.native_value is None
    config = entity._server_cluster_config[cluster.cluster_id]
    assert config.bind is True
    report = config.attributes[attribute.name].reporting
    assert (report.min_interval, report.max_interval, report.reportable_change) == (
        0,
        3600,
        0,
    )

    # Global server-to-client Report Attributes, no manufacturer code, attribute
    # 0x0010, ZCL character string. Exercise the real wire decoding/cache path.
    for raw, expected in (
        (" HEURE  PLEINE", "HEURE PLEINE"),
        (" HEURE  CREUSE", "HEURE CREUSE"),
        ("HPJR", "HPJR"),
    ):
        value = raw.encode("utf-8")
        frame = b"\x18\x01\x0a\x10\x00\x42" + bytes([len(value)]) + value
        header, args = cluster.deserialize(frame)
        assert header.manufacturer is None
        cluster.handle_message(header, args)
        assert entity.native_value == expected

    cluster.read_attributes.assert_not_called()
