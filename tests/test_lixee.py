"""Tests for LiXee ZLinky tariff and three-phase reporting."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from zha.application import Platform
from zha.application.platforms.sensor import (
    BaseElectricalMeasurement,
    ElectricalMeasurementPoller,
    Sensor,
)
from zha.quirks import DEVICE_REGISTRY
from zha.zigbee.cluster_config import aggregate_cluster_configs
from zha.zigbee.device import Device as ZHADevice
from zha.zigbee.endpoint import Endpoint as ZHAEndpoint
from zigpy.exceptions import DeliveryError
from zigpy.profiles import zgp, zha
from zigpy.zcl.clusters.general import GreenPowerProxy, Ota, Time
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks
from zhaquirks.builder import SensorDeviceClass, SensorStateClass
from zhaquirks.builder.device import QuirkV2Device, QuirkV2Factory
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
    entity = next(e for e in entities if e.unique_id.endswith("-tariff_period"))
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


@pytest.fixture
def zha_zlinky(zlinky_v17):
    """Construct the actual ZHA device used by the v2 factory."""
    entry = DEVICE_REGISTRY.match_entry(zlinky_v17)
    device = DEVICE_REGISTRY.resolve(zlinky_v17)
    gateway = Mock()
    gateway.config.config.device_options.consider_unavailable_mains = 7200
    gateway.config.config.device_options.consider_unavailable_battery = 7200
    return entry.zha_device_factory(device, gateway)


@pytest.mark.parametrize(
    ("attribute", "attribute_id", "suffix", "unit", "device_class", "value"),
    [
        ("rms_current", 0x0508, "2820-rms_current", "A", SensorDeviceClass.CURRENT, 9),
        (
            "rms_current_ph_b",
            0x0908,
            "2820-rms_current_ph_b",
            "A",
            SensorDeviceClass.CURRENT,
            2,
        ),
        (
            "rms_current_ph_c",
            0x0A08,
            "2820-rms_current_ph_c",
            "A",
            SensorDeviceClass.CURRENT,
            3,
        ),
        (
            "rms_voltage",
            0x0505,
            "2820-rms_voltage",
            "V",
            SensorDeviceClass.VOLTAGE,
            230,
        ),
        (
            "rms_voltage_ph_b",
            0x0905,
            "2820-rms_voltage_ph_b",
            "V",
            SensorDeviceClass.VOLTAGE,
            224,
        ),
        (
            "rms_voltage_ph_c",
            0x0A05,
            "2820-rms_voltage_ph_c",
            "V",
            SensorDeviceClass.VOLTAGE,
            231,
        ),
        (
            "apparent_power",
            0x050F,
            "2820-apparent_power",
            "VA",
            SensorDeviceClass.APPARENT_POWER,
            69,
        ),
        (
            "apparent_power_ph_b",
            0x090F,
            "2820-apparent_power_ph_b",
            "VA",
            SensorDeviceClass.APPARENT_POWER,
            1148,
        ),
        (
            "apparent_power_ph_c",
            0x0A0F,
            "2820-apparent_power_ph_c",
            "VA",
            SensorDeviceClass.APPARENT_POWER,
            1964,
        ),
        (
            "total_apparent_power",
            0x0306,
            "2820-total_apparent_power",
            "VA",
            SensorDeviceClass.APPARENT_POWER,
            3181,
        ),
        ("active_power", 0x050B, "2820", "W", SensorDeviceClass.POWER, 2360),
        (
            "active_power_ph_b",
            0x090B,
            "2820-active_power_ph_b",
            "W",
            SensorDeviceClass.POWER,
            2296,
        ),
        (
            "active_power_max",
            0x050D,
            "2820-apparent_power_max_phase_1",
            "VA",
            SensorDeviceClass.APPARENT_POWER,
            1482,
        ),
        (
            "active_power_max_ph_b",
            0x090D,
            "2820-apparent_power_max_phase_2",
            "VA",
            SensorDeviceClass.APPARENT_POWER,
            2098,
        ),
        (
            "active_power_max_ph_c",
            0x0A0D,
            "2820-apparent_power_max_phase_3",
            "VA",
            SensorDeviceClass.APPARENT_POWER,
            2357,
        ),
        (
            "total_active_power",
            0x0304,
            "2820-apparent_power_max_total",
            "VA",
            SensorDeviceClass.APPARENT_POWER,
            5302,
        ),
    ],
)
async def test_zlinky_electrical_reports(
    zha_zlinky, attribute, attribute_id, suffix, unit, device_class, value
):
    """Decode raw TIC reports with correct units, preserved IDs and no reads/scaling."""
    private_cluster = zha_zlinky.endpoints[
        1
    ].zigpy_endpoint.zlinky_manufacturer_specific
    private_cluster.update_attribute("linky_mode", 3)
    entities = list(zha_zlinky.discover_entities())
    electrical = [
        e
        for e in entities
        if isinstance(e, Sensor)
        and not isinstance(e, BaseElectricalMeasurement)
        and e.targets_cluster(ElectricalMeasurement.cluster_id)
    ]
    assert len(electrical) == 16
    assert len({e.unique_id for e in electrical}) == 16
    entity = next(
        e for e in electrical if e.unique_id == f"{zha_zlinky.ieee}-1-{suffix}"
    )
    assert not zha_zlinky._is_entity_removed_by_quirk(entity)
    assert entity.native_unit_of_measurement == unit
    assert entity.device_class == device_class
    assert entity.state_class == SensorStateClass.MEASUREMENT
    assert entity.native_value is None
    cluster = zha_zlinky.endpoints[1].zigpy_endpoint.electrical_measurement
    cluster.read_attributes = AsyncMock()
    attr = cluster.find_attribute(attribute)
    assert attr.id == attribute_id
    config = entity._server_cluster_config[cluster.cluster_id]
    assert config.bind is True
    aggregated = aggregate_cluster_configs(entities)
    report = aggregated[(1, cluster.cluster_id, True)].attributes[attribute].reporting
    assert (report.min_interval, report.max_interval, report.reportable_change) == (
        60,
        900,
        1,
    )
    # Standard ZCL Report Attributes. TIC current/voltage/apparent values are
    # uint16; curve points and per-phase maxima int16; total power uses 32 bits.
    data_type = 0x21
    if attribute in (
        "active_power",
        "active_power_ph_b",
        "active_power_max",
        "active_power_max_ph_b",
        "active_power_max_ph_c",
    ):
        data_type = 0x29
    elif attribute == "total_active_power":
        data_type = 0x2B
    elif attribute == "total_apparent_power":
        data_type = 0x23
    frame = (
        b"\x18\x01\x0a"
        + attribute_id.to_bytes(2, "little")
        + bytes([data_type])
        + attr.type(value).serialize()
    )
    header, args = cluster.deserialize(frame)
    cluster.handle_message(header, args)
    assert entity.native_value == value
    cluster.read_attributes.assert_not_called()
    assert not any(
        e.unique_id == f"{zha_zlinky.ieee}-1-2820-total_active_power"
        for e in electrical
    )


@pytest.mark.parametrize("mode", [None, 0, 1, 2, 3, 5, 7])
def test_zlinky_electrical_mode_scope(zha_zlinky, mode):
    """Replace native sensors only in standard three-phase, including producer mode."""
    cluster = zha_zlinky.endpoints[1].zigpy_endpoint.zlinky_manufacturer_specific
    if mode is not None:
        cluster.update_attribute("linky_mode", mode)
    native = Mock(spec=BaseElectricalMeasurement)
    native.PLATFORM = Platform.SENSOR
    native.endpoint = zha_zlinky.endpoints[1]
    native.device = zha_zlinky
    native.targets_cluster.return_value = True
    poller = Mock(spec=ElectricalMeasurementPoller)
    with patch.object(
        ZHADevice, "discover_entities", return_value=iter([native, poller])
    ):
        entities = list(zha_zlinky.discover_entities())
    standard_three_phase = mode in (3, 7)
    assert zha_zlinky.standard_three_phase is standard_three_phase
    # Skip native sensors and their poller before config aggregation. This also
    # prevents old reporting intervals from overriding the TIC configuration.
    assert (native in entities) is not standard_three_phase
    assert (poller in entities) is not standard_three_phase
    assert len(entities) == (17 if standard_three_phase else 3)
    assert any(e.unique_id.endswith("-tariff_period") for e in entities)


@pytest.mark.parametrize("operation", ["async_configure", "async_initialize"])
async def test_zlinky_reads_mode_before_discovery(zha_zlinky, operation):
    """Identify the mode before discovery and reuse its cached value thereafter."""
    cluster = zha_zlinky.endpoints[1].zigpy_endpoint.zlinky_manufacturer_specific
    assert (
        cluster._get_effective_manufacturer_code(cluster.AttributeDefs.linky_mode)
        is None
    )

    async def read_mode(*args, **kwargs):
        cluster.update_attribute("linky_mode", 3)
        return {"linky_mode": 3}, {}

    cluster.read_attributes = AsyncMock(side_effect=read_mode)

    async def initialize(*args, **kwargs):
        assert zha_zlinky.standard_three_phase

    with patch.object(QuirkV2Device, operation, new=AsyncMock(side_effect=initialize)):
        await getattr(zha_zlinky, operation)()
        await getattr(zha_zlinky, operation)()
    cluster.read_attributes.assert_awaited_once_with(["linky_mode"], allow_cache=True)


@pytest.mark.parametrize("error", [TimeoutError(), DeliveryError("Mode read failed")])
async def test_zlinky_mode_read_failure(zha_zlinky, error):
    """Leave native discovery available if mode identification fails."""
    cluster = zha_zlinky.endpoints[1].zigpy_endpoint.zlinky_manufacturer_specific
    cluster.read_attributes = AsyncMock(side_effect=error)
    await zha_zlinky.read_linky_mode()
    assert not zha_zlinky.standard_three_phase
