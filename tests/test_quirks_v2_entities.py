"""End-to-end tests for the quirks v2 entity APIs."""

from typing import Any

import pytest
from zha.application import Platform
from zha.application.platforms.button import IdentifyButton
from zha.application.platforms.light import HueLight
from zha.application.platforms.sensor import BaseSensor, Sensor
from zha.quirks import DeviceRegistry
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
from zhaquirks.builder import EntityFilter, QuirkBuilder


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


class EffectLight(HueLight):
    """Hue light subclass to replace the default one."""


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
    """Test that an added entity on a missing cluster is not created."""
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
        assert "Failed to create entity during discovery" in caplog.text


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


async def test_removes_entity() -> None:
    """Test removing entities by class and by unique ID suffix."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .removes_entity(EntityFilter(entity_cls=IdentifyButton))
        .removes_entity(platform=Platform.SENSOR, unique_id_suffix="1-1026")
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
