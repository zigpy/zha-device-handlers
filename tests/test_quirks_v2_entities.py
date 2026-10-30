"""End-to-end tests for the quirks v2 entity APIs."""

from collections.abc import Iterator
import itertools
from typing import Any
from unittest import mock

import pytest
from zha.application import Platform
from zha.application.platforms import PlatformEntity
from zha.application.platforms.button import IdentifyButton
from zha.application.platforms.cover import Cover
from zha.application.platforms.light import HueLight, Light
from zha.application.platforms.number import OnLevelConfigurationEntity
from zha.application.platforms.sensor import BaseSensor, RSSISensor, Sensor, Temperature
from zha.application.platforms.sensor.device_class import SensorDeviceClass
from zha.quirks import DeviceRegistry
from zha.zigbee.device import ZigbeeDevice
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import LevelControl, OnOff, Ota
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
from zhaquirks.builder import EntityFilter, QuirkBuilder

IEEE = "00:0d:6f:00:05:65:83:f2"


class DeviceValueSensor(BaseSensor):
    """Sensor bound to the device, with a fixed value."""

    _unique_id_suffix = "device_value"

    def __init__(self, device, *, value: int, **kwargs: Any) -> None:
        """Initialize the sensor."""
        self._value = value
        super().__init__(device, **kwargs)

    @property
    def native_value(self) -> int:
        """Return the value."""
        return self._value


class CachedAttributeSensor(Sensor):
    """Sensor that is only supported if its attribute has a value."""

    def _is_supported(self) -> bool:
        if self._cluster.get(self._attribute_name) is None:
            return False

        return super()._is_supported()


class QuirkCover(Cover):
    """Cover subclass to replace the default one."""


class EffectLight(HueLight):
    """Hue light subclass to replace the default one."""


class QuirkOnLevel(OnLevelConfigurationEntity):
    """On level subclass to replace the default one."""


class QuirkRSSISensor(RSSISensor):
    """RSSI sensor subclass to replace the default device-bound one."""


class BrokenTemperature(Temperature):
    """Temperature sensor subclass that cannot be created."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Fail to initialize."""
        raise RuntimeError("Cannot create the entity")


class RenamedTemperature(Temperature):
    """Temperature sensor subclass with another unique ID suffix."""

    _unique_id_suffix = "renamed"


async def test_adds_device_entity() -> None:
    """Test adding an entity bound to the device."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .adds_entity(DeviceValueSensor, value=5, fallback_name="Device value")
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        entity = device.get_platform_entity(
            Platform.SENSOR, unique_id="00:0d:6f:00:05:65:83:f2-device_value"
        )

        assert type(entity) is DeviceValueSensor
        assert entity.native_value == 5
        assert entity.identifiers.endpoint_id is None


async def test_adds_entity_support_check() -> None:
    """Test that an added entity is only created if supported, unless force-created."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .adds_entity(
            CachedAttributeSensor,
            endpoint_id=1,
            cluster_id=TemperatureMeasurement.cluster_id,
            attribute_name=TemperatureMeasurement.AttributeDefs.measured_value.name,
            unique_id_suffix="cached",
            fallback_name="Cached",
        )
        .adds_entity(
            CachedAttributeSensor,
            endpoint_id=1,
            cluster_id=TemperatureMeasurement.cluster_id,
            attribute_name=TemperatureMeasurement.AttributeDefs.tolerance.name,
            unique_id_suffix="uncached",
            fallback_name="Uncached",
        )
        .adds_entity(
            CachedAttributeSensor,
            endpoint_id=1,
            cluster_id=TemperatureMeasurement.cluster_id,
            attribute_name=TemperatureMeasurement.AttributeDefs.tolerance.name,
            force_create=True,
            unique_id_suffix="uncached_forced",
            fallback_name="Uncached forced",
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        cluster = device.device.endpoints[1].temperature

        assert cluster.get(TemperatureMeasurement.AttributeDefs.tolerance.name) is None
        assert (
            Platform.SENSOR,
            "00:0d:6f:00:05:65:83:f2-1-cached",
        ) in device.platform_entities
        assert (
            Platform.SENSOR,
            "00:0d:6f:00:05:65:83:f2-1-uncached",
        ) not in device.platform_entities
        assert (
            Platform.SENSOR,
            "00:0d:6f:00:05:65:83:f2-1-uncached_forced",
        ) in device.platform_entities


async def test_adds_zcl_entity() -> None:
    """Test adding an entity bound to an endpoint and cluster."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .adds_entity(
            Sensor,
            endpoint_id=1,
            cluster_id=TemperatureMeasurement.cluster_id,
            attribute_name=TemperatureMeasurement.AttributeDefs.measured_value.name,
            unique_id_suffix="extra_temperature",
            fallback_name="Extra temperature",
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        entity = device.get_platform_entity(
            Platform.SENSOR,
            unique_id="00:0d:6f:00:05:65:83:f2-1-extra_temperature",
        )

        assert type(entity) is Sensor
        assert entity.cluster is device.device.endpoints[1].temperature


async def test_adds_entity_missing_cluster_fails(caplog) -> None:
    """Test that an added entity on a missing cluster does not stop later ones."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .adds_entity(
            Sensor,
            endpoint_id=1,
            cluster_id=OnOff.cluster_id,
            attribute_name=OnOff.AttributeDefs.on_off.name,
            unique_id_suffix="missing",
            fallback_name="Missing",
        )
        .adds_entity(DeviceValueSensor, value=5, fallback_name="Device value")
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )

        assert (
            Platform.SENSOR,
            "00:0d:6f:00:05:65:83:f2-1-missing",
        ) not in device.platform_entities
        assert (
            Platform.SENSOR,
            "00:0d:6f:00:05:65:83:f2-device_value",
        ) in device.platform_entities
        assert "Failed to create added entity" in caplog.text


async def test_replaces_entity() -> None:
    """Test replacing a default entity, keeping its unique ID."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("Philips", "LCT014")
        .replaces_entity(
            HueLight, EffectLight, endpoint_id=11, cluster_id=OnOff.cluster_id
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "philips-lct014-0x01001a02.json", registry
        )
        lights = [
            entity
            for entity in device.platform_entities.values()
            if entity.PLATFORM == Platform.LIGHT
        ]

        assert [(type(e), e.unique_id) for e in lights] == [
            (EffectLight, f"{device.ieee}-11")
        ]


async def test_replaces_entity_discovered_twice() -> None:
    """Test replacing an entity that discovery yields for both cluster directions."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("NodOn", "SIN-4-RS-20")
        .replaces_entity(
            Cover, QuirkCover, endpoint_id=1, cluster_id=WindowCovering.cluster_id
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "nodon-sin-4-rs-20-0x00030104.json", registry
        )
        covers = [
            entity
            for entity in device.platform_entities.values()
            if entity.PLATFORM == Platform.COVER
        ]

        assert [(type(e), e.unique_id) for e in covers] == [
            (QuirkCover, f"{device.ieee}-1-258")
        ]


async def test_replaces_entity_with_same_class() -> None:
    """Test replacing a default entity with one of the same class, keeping its ZCL unique ID."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .replaces_entity(
            Temperature,
            Temperature,
            cluster_id=TemperatureMeasurement.cluster_id,
            fallback_name="Replaced temperature",
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        entity = device.get_platform_entity(
            Platform.SENSOR, unique_id="00:0d:6f:00:05:65:83:f2-1-1026"
        )

        assert type(entity) is Temperature
        assert entity.fallback_name == "Replaced temperature"


async def test_replaces_device_entity() -> None:
    """Test replacing a default device-bound entity, keeping its unique ID."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .replaces_entity(RSSISensor, QuirkRSSISensor)
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        rssi_sensors = [
            entity
            for entity in device.platform_entities.values()
            if isinstance(entity, RSSISensor) and entity.unique_id.endswith("-rssi")
        ]

        assert [(type(e), e.unique_id) for e in rssi_sensors] == [
            (QuirkRSSISensor, "00:0d:6f:00:05:65:83:f2-1-0-rssi")
        ]


async def test_replaces_unsupported_entity() -> None:
    """Test that replacing an unsupported default entity creates no entity."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("Philips", "LCT014")
        .replaces_entity(
            OnLevelConfigurationEntity,
            QuirkOnLevel,
            endpoint_id=11,
            cluster_id=LevelControl.cluster_id,
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "philips-lct014-0x01001a02.json", registry
        )
        cluster = device.device.endpoints[11].level

        assert cluster.is_attribute_unsupported(
            LevelControl.AttributeDefs.on_level.name
        )
        assert not any(
            isinstance(e, OnLevelConfigurationEntity)
            for e in device.platform_entities.values()
        )


async def test_replaces_entity_no_match(caplog) -> None:
    """Test that a replacement matching no entity keeps the default one."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("Philips", "LCT014")
        .replaces_entity(Light, EffectLight, endpoint_id=11)
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "philips-lct014-0x01001a02.json", registry
        )
        entity = device.get_platform_entity(
            Platform.LIGHT, unique_id=f"{device.ieee}-11"
        )

        assert type(entity) is HueLight
        assert "must match one entity, matched 0" in caplog.text


async def test_replaces_entity_unique_id_change(caplog) -> None:
    """Test that a replacement changing the unique ID keeps the default entity."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .replaces_entity(Temperature, RenamedTemperature)
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        entity = device.get_platform_entity(
            Platform.SENSOR, unique_id="00:0d:6f:00:05:65:83:f2-1-1026"
        )

        assert type(entity) is Temperature
        assert "changes the unique ID" in caplog.text


async def test_removes_entity() -> None:
    """Test removing entities by class and by unique ID suffix."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .removes_entity(EntityFilter(entity_cls=IdentifyButton))
        .removes_entity(
            EntityFilter(platform=Platform.SENSOR, unique_id_suffix="1-1026")
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        assert not any(
            type(e) is IdentifyButton for e in device.platform_entities.values()
        )
        assert (
            Platform.SENSOR,
            "00:0d:6f:00:05:65:83:f2-1-1026",
        ) not in device.platform_entities
        assert (
            Platform.SENSOR,
            "00:0d:6f:00:05:65:83:f2-1-1",
        ) in device.platform_entities


def test_adds_entity_binding() -> None:
    """Test that the endpoint and cluster arguments match the entity binding."""
    builder = QuirkBuilder("CentraLite", "3405-L")

    with pytest.raises(ValueError):
        builder.adds_entity(Sensor, endpoint_id=1)

    with pytest.raises(ValueError):
        builder.adds_entity(DeviceValueSensor, endpoint_id=1, value=5)


def test_entity_unique_id_kwarg_rejected() -> None:
    """Test that added and replacement entities cannot set their own unique ID."""
    builder = QuirkBuilder("CentraLite", "3405-L")

    with pytest.raises(ValueError):
        builder.adds_entity(DeviceValueSensor, value=5, unique_id="custom")

    with pytest.raises(ValueError):
        builder.replaces_entity(Temperature, Temperature, unique_id="custom")


def test_replaces_entity_arguments() -> None:
    """Test that entities are replaced by the same kind, matched by one kind of filter."""
    builder = QuirkBuilder("CentraLite", "3405-L")

    with pytest.raises(TypeError):
        builder.replaces_entity(Sensor, DeviceValueSensor, value=5)

    with pytest.raises(ValueError):
        builder.replaces_entity(
            Temperature,
            Temperature,
            endpoint_id=1,
            filter=EntityFilter(cluster_id=TemperatureMeasurement.cluster_id),
        )


def test_entity_filter_cluster_type_requires_cluster_id() -> None:
    """Test that a filter cannot match on a cluster type alone."""
    with pytest.raises(ValueError):
        EntityFilter(cluster_type=ClusterType.Server)


async def test_default_discovery_failure_keeps_earlier_entities() -> None:
    """Test that entities discovered before a failure in ZHA's discovery are kept."""
    registry = DeviceRegistry()
    QuirkBuilder("CentraLite", "3405-L").replaces_entity(
        RSSISensor, QuirkRSSISensor
    ).add_to_registry(registry)

    discover_entities = ZigbeeDevice.discover_entities

    def failing_discovery(device: ZigbeeDevice) -> Iterator[PlatformEntity]:
        yield from itertools.islice(discover_entities(device), 2)
        raise RuntimeError("Discovery failed")

    with mock.patch.object(ZigbeeDevice, "discover_entities", failing_discovery):
        async with zha_gateway() as gateway:
            device = await join_device_from_diagnostics(
                gateway, "centralite-3405-l-0x10025310.json", registry
            )

            assert set(device.platform_entities) == {
                (Platform.SENSOR, "00:0d:6f:00:05:65:83:f2-1-0-rssi"),
                (Platform.SENSOR, "00:0d:6f:00:05:65:83:f2-1-0-lqi"),
            }
            # The replacement is applied to the entities kept before the failure
            assert (
                type(
                    device.get_platform_entity(
                        Platform.SENSOR, unique_id="00:0d:6f:00:05:65:83:f2-1-0-rssi"
                    )
                )
                is QuirkRSSISensor
            )


@pytest.mark.parametrize(
    ("entity_filter", "expected"),
    [
        (EntityFilter(), None),  # An empty filter matches everything
        (EntityFilter(entity_cls=Temperature), {f"{IEEE}-1-1026"}),
        # The class must match exactly, subclasses do not match
        (EntityFilter(entity_cls=BaseSensor), set()),
        (EntityFilter(platform=Platform.BINARY_SENSOR), {f"{IEEE}-1-1280"}),
        (EntityFilter(translation_key="rssi"), {f"{IEEE}-1-0-rssi"}),
        (EntityFilter(device_class=SensorDeviceClass.TEMPERATURE), {f"{IEEE}-1-1026"}),
        (
            EntityFilter(platform=Platform.SENSOR, endpoint_id=1, cluster_id=1),
            {f"{IEEE}-1-1"},
        ),
        # Only ZCL entities have an endpoint and a cluster
        (EntityFilter(endpoint_id=2), set()),
        (
            EntityFilter(cluster_id=1026, cluster_type=ClusterType.Server),
            {f"{IEEE}-1-1026"},
        ),
        (EntityFilter(cluster_id=1026, cluster_type=ClusterType.Client), set()),
        (EntityFilter(cluster_id=1026), {f"{IEEE}-1-1026"}),
        # The alarm control panel is bound to a client (output) cluster
        (
            EntityFilter(cluster_id=1281, cluster_type=ClusterType.Client),
            {f"{IEEE}-1-1281"},
        ),
        (EntityFilter(cluster_id=1281, cluster_type=ClusterType.Server), set()),
        # The suffix matches whole `-`-separated trailing parts, with or without `-`
        (EntityFilter(unique_id_suffix="1026"), {f"{IEEE}-1-1026"}),
        (EntityFilter(unique_id_suffix="-1026"), {f"{IEEE}-1-1026"}),
        (EntityFilter(unique_id_suffix="1-1026"), {f"{IEEE}-1-1026"}),
        (EntityFilter(unique_id_suffix="026"), set()),
        (
            EntityFilter(function=lambda entity: entity.unique_id.endswith("-lqi")),
            {f"{IEEE}-1-0-lqi"},
        ),
        # Every field that is set must match
        (
            EntityFilter(
                platform=Platform.SENSOR, translation_key="lqi", endpoint_id=1
            ),
            set(),
        ),
        (
            EntityFilter(platform=Platform.SENSOR, translation_key="rssi"),
            {f"{IEEE}-1-0-rssi"},
        ),
    ],
)
async def test_entity_filter_matches(
    entity_filter: EntityFilter, expected: set[str] | None
) -> None:
    """Test which of the default entities an entity filter matches."""
    registry = DeviceRegistry()
    QuirkBuilder("CentraLite", "3405-L").add_to_registry(registry)

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        matched = {
            entity.unique_id
            for entity in device.platform_entities.values()
            if entity_filter.matches(entity)
        }

        if expected is None:
            assert matched == {e.unique_id for e in device.platform_entities.values()}
        else:
            assert matched == expected


async def test_replaces_entity_with_filter_and_kwargs() -> None:
    """Test replacing an entity matched by a filter, creating it with the kwargs."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .replaces_entity(
            Temperature,
            Temperature,
            filter=EntityFilter(
                platform=Platform.SENSOR, device_class=SensorDeviceClass.TEMPERATURE
            ),
            fallback_name="Filtered temperature",
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        entity = device.get_platform_entity(Platform.SENSOR, unique_id=f"{IEEE}-1-1026")

        assert type(entity) is Temperature
        assert entity.fallback_name == "Filtered temperature"


async def test_replaces_entity_filter_excludes_entity(caplog) -> None:
    """Test that a replacement whose filter excludes the entity keeps the default."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .replaces_entity(Temperature, Temperature, endpoint_id=2, fallback_name="Nope")
        .replaces_entity(
            Temperature,
            Temperature,
            filter=EntityFilter(platform=Platform.BINARY_SENSOR),
            fallback_name="Nope",
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        entity = device.get_platform_entity(Platform.SENSOR, unique_id=f"{IEEE}-1-1026")

        assert entity.fallback_name != "Nope"
        # Each replacement is reported separately (the device initializes twice)
        records = [
            r.getMessage()
            for r in caplog.records
            if "must match one entity, matched 0" in r.getMessage()
        ]
        assert any("endpoint_id=2" in message for message in records)
        assert any("BINARY_SENSOR" in message for message in records)


async def test_replaces_entity_creation_failure(caplog) -> None:
    """Test that a replacement that cannot be created keeps the default entity."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .replaces_entity(Temperature, BrokenTemperature)
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        entity = device.get_platform_entity(Platform.SENSOR, unique_id=f"{IEEE}-1-1026")

        assert type(entity) is Temperature
        assert "Failed to create replacement" in caplog.text
        assert "Cannot create the entity" in caplog.text


async def test_removes_entity_cluster_type() -> None:
    """Test that removing by cluster only matches the given cluster direction."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        # The temperature cluster is a server cluster, so nothing is removed
        .removes_entity(
            EntityFilter(
                endpoint_id=1,
                cluster_id=TemperatureMeasurement.cluster_id,
                cluster_type=ClusterType.Client,
            )
        )
        # The alarm control panel is bound to a client cluster
        .removes_entity(
            EntityFilter(
                endpoint_id=1, cluster_id=1281, cluster_type=ClusterType.Client
            )
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )

        assert (Platform.SENSOR, f"{IEEE}-1-1026") in device.platform_entities
        assert (
            Platform.ALARM_CONTROL_PANEL,
            f"{IEEE}-1-1281",
        ) not in device.platform_entities


async def test_prevent_default_entity_creation_matches_both_directions() -> None:
    """Test that removing by cluster ID alone matches client clusters too."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .prevent_default_entity_creation(endpoint_id=1, cluster_id=1281)
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )

        assert (
            Platform.ALARM_CONTROL_PANEL,
            f"{IEEE}-1-1281",
        ) not in device.platform_entities
        assert (Platform.BINARY_SENSOR, f"{IEEE}-1-1280") in device.platform_entities


async def test_removes_entity_filters_combined() -> None:
    """Test removing with several filters, by function and by cluster."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .removes_entity(
            EntityFilter(
                endpoint_id=1,
                cluster_id=TemperatureMeasurement.cluster_id,
                cluster_type=ClusterType.Server,
            ),
            EntityFilter(function=lambda entity: entity.unique_id.endswith("-lqi")),
        )
        .prevent_default_entity_creation(endpoint_id=1, cluster_id=3)
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )

        assert (Platform.SENSOR, f"{IEEE}-1-1026") not in device.platform_entities
        assert (Platform.SENSOR, f"{IEEE}-1-0-lqi") not in device.platform_entities
        assert (Platform.BUTTON, f"{IEEE}-1-3") not in device.platform_entities
        assert (Platform.SENSOR, f"{IEEE}-1-0-rssi") in device.platform_entities
        assert (Platform.SENSOR, f"{IEEE}-1-1") in device.platform_entities


async def test_removed_entity_can_be_added_back() -> None:
    """Test removing a default entity and adding a replacement under the same ID."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .removes_entity(EntityFilter(entity_cls=Temperature))
        .adds_entity(
            Sensor,
            endpoint_id=1,
            cluster_id=TemperatureMeasurement.cluster_id,
            attribute_name=TemperatureMeasurement.AttributeDefs.measured_value.name,
            unique_id_suffix="1026",
            fallback_name="Added temperature",
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        entity = device.get_platform_entity(Platform.SENSOR, unique_id=f"{IEEE}-1-1026")

        assert type(entity) is Sensor
        assert entity.fallback_name == "Added temperature"


async def test_adds_entity_client_cluster() -> None:
    """Test adding an entity bound to a client (output) cluster."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .adds_entity(
            Sensor,
            endpoint_id=1,
            cluster_id=Ota.cluster_id,
            cluster_type=ClusterType.Client,
            attribute_name=Ota.AttributeDefs.current_file_version.name,
            unique_id_suffix="ota_client",
            fallback_name="OTA client",
            force_create=True,
        )
        .adds_entity(
            Sensor,
            endpoint_id=1,
            cluster_id=Ota.cluster_id,
            attribute_name=Ota.AttributeDefs.current_file_version.name,
            unique_id_suffix="ota_server",
            fallback_name="OTA server",
            force_create=True,
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        entity = device.get_platform_entity(
            Platform.SENSOR, unique_id=f"{IEEE}-1-ota_client"
        )

        assert entity.cluster is device.device.endpoints[1].out_clusters[Ota.cluster_id]
        # The cluster is not a server cluster, so the second entity cannot be created
        assert (Platform.SENSOR, f"{IEEE}-1-ota_server") not in device.platform_entities


def test_adds_entity_cluster_type_default() -> None:
    """Test that added entities default to the server cluster."""
    entity = (
        QuirkBuilder("CentraLite", "3405-L")
        .adds_entity(
            Sensor,
            endpoint_id=1,
            cluster_id=TemperatureMeasurement.cluster_id,
            attribute_name=TemperatureMeasurement.AttributeDefs.measured_value.name,
            fallback_name="Extra temperature",
        )
        .added_entities[0]
    )

    assert entity.cluster_type is ClusterType.Server
    assert entity.kwargs["fallback_name"] == "Extra temperature"

    with pytest.raises(TypeError):
        entity.kwargs["fallback_name"] = "Changed"  # The kwargs are frozen


async def test_change_entity_metadata_uses_entity_filter() -> None:
    """Test that metadata changes apply to the entities the filter matches only."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .change_entity_metadata(
            endpoint_id=1,
            cluster_id=TemperatureMeasurement.cluster_id,
            new_fallback_name="Changed temperature",
            new_translation_key="changed_temperature",
            new_primary=True,
        )
        .change_entity_metadata(
            endpoint_id=1,
            cluster_id=TemperatureMeasurement.cluster_id,
            cluster_type=ClusterType.Client,
            new_fallback_name="Not applied",
        )
        .change_entity_metadata(
            unique_id_suffix="1-1",
            new_fallback_name="Changed battery",
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        temperature = device.get_platform_entity(
            Platform.SENSOR, unique_id=f"{IEEE}-1-1026"
        )
        battery = device.get_platform_entity(Platform.SENSOR, unique_id=f"{IEEE}-1-1")
        rssi = device.get_platform_entity(Platform.SENSOR, unique_id=f"{IEEE}-1-0-rssi")

        assert temperature.fallback_name == "Changed temperature"
        assert temperature.translation_key == "changed_temperature"
        assert temperature.primary is True
        assert battery.fallback_name == "Changed battery"
        assert rssi.fallback_name != "Changed battery"


async def test_v2_entity_unique_id_omits_cluster_id() -> None:
    """Test that entities from quirk metadata use the endpoint-level unique ID base."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .sensor(
            TemperatureMeasurement.AttributeDefs.tolerance.name,
            TemperatureMeasurement.cluster_id,
            endpoint_id=1,
            translation_key="tolerance",
            fallback_name="Tolerance",
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        entity = device.get_platform_entity(
            Platform.SENSOR, unique_id=f"{IEEE}-1-tolerance"
        )

        assert entity.fallback_name == "Tolerance"
