"""Exercise the quirks-to-ZHA entity discovery boundary."""

from unittest.mock import Mock

import attrs
import pytest
from zha.application import Platform
from zha.application.platforms import (
    binary_sensor,
    button,
    number,
    select,
    sensor,
    switch,
)
from zha.quirks import DeviceRegistry
from zigpy.profiles import zha
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff

from zhaquirks.builder import EntityPlatform, EntityType, QuirkBuilder, ReportingConfig
from zhaquirks.builder.discovery import discover_quirks_v2_entities
from zhaquirks.builder.metadata import EntityMetadata


@pytest.fixture
def make_device(zigpy_device_mock):
    """Build a real quirk-bound ZHA device with server and client clusters."""
    registry = DeviceRegistry()
    builder = QuirkBuilder("test manufacturer", "test model", registry=registry)

    def create(builder=builder):
        entry = builder.add_to_registry(registry)
        raw = zigpy_device_mock()
        raw.manufacturer = "test manufacturer"
        raw.model = "test model"
        endpoint = raw.add_endpoint(1)
        endpoint.profile_id = zha.PROFILE_ID
        endpoint.device_type = zha.DeviceType.DIMMABLE_LIGHT
        endpoint.add_input_cluster(OnOff.cluster_id)
        endpoint.add_output_cluster(OnOff.cluster_id)
        endpoint.add_input_cluster(LevelControl.cluster_id)
        device = entry.zha_device_factory(registry.resolve(raw), Mock())
        return device

    return builder, create


async def test_entity_platforms_and_unique_ids(make_device):
    """Every supported metadata kind creates its real ZHA entity with a stable ID."""
    builder, create = make_device
    builder.sensor(
        "current_level",
        LevelControl.cluster_id,
        divisor=2,
        multiplier=3,
        translation_key="level",
        fallback_name="Level",
    ).number(
        "on_time",
        OnOff.cluster_id,
        min_value=1,
        max_value=100,
        step=1,
        translation_key="on_time",
        fallback_name="On time",
    ).switch(
        "on_off",
        OnOff.cluster_id,
        force_inverted=True,
        unique_id_suffix="inverted_switch",
        translation_key="switch",
        fallback_name="Switch",
    ).binary_sensor(
        "on_off",
        OnOff.cluster_id,
        unique_id_suffix="status",
        translation_key="status",
        fallback_name="Status",
    ).enum(
        "start_up_on_off",
        OnOff.StartUpOnOff,
        OnOff.cluster_id,
        translation_key="startup",
        fallback_name="Startup",
    ).enum(
        "start_up_on_off",
        OnOff.StartUpOnOff,
        OnOff.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        unique_id_suffix="startup_sensor",
        translation_key="startup",
        fallback_name="Startup",
    ).write_attr_button(
        "on_time",
        10,
        OnOff.cluster_id,
        unique_id_suffix="reset_time",
        translation_key="reset_time",
        fallback_name="Reset time",
    ).command_button(
        "off",
        OnOff.cluster_id,
        translation_key="off",
        fallback_name="Off",
    )
    device = create()
    device.device.endpoints[1].level.update_attribute(
        LevelControl.AttributeDefs.current_level.id, 20
    )
    device.device.endpoints[1].on_off.update_attribute(
        OnOff.AttributeDefs.on_off.id, True
    )
    device.device.endpoints[1].on_off.update_attribute(
        OnOff.AttributeDefs.start_up_on_off.id, OnOff.StartUpOnOff.On
    )
    entities = list(discover_quirks_v2_entities(device))
    expected = [
        (sensor.Sensor, "current_level"),
        (number.NumberConfigurationEntity, "on_time"),
        (switch.ConfigurableAttributeSwitch, "inverted_switch"),
        (binary_sensor.BinarySensor, "status"),
        (select.ZCLEnumSelectEntity, "start_up_on_off"),
        (sensor.EnumSensor, "startup_sensor"),
        (button.WriteAttributeButton, "reset_time"),
        (button.Button, "off"),
    ]
    assert len(entities) == len(expected)
    for entity, (entity_class, suffix) in zip(entities, expected, strict=True):
        assert isinstance(entity, entity_class)
        assert entity.unique_id == f"{device.ieee}-1-{suffix}"
        assert entity.device is device
    assert entities[0].native_value == 30
    assert entities[2].is_on is False
    assert entities[3].is_on is True
    assert entities[4].current_option == "On"
    assert entities[5].native_value == "On"


@pytest.mark.parametrize("cluster_type", [ClusterType.Server, ClusterType.Client])
@pytest.mark.parametrize("reporting", [True, False])
@pytest.mark.parametrize("cached", [True, False])
async def test_entity_reporting_and_initialization(
    make_device, cluster_type, reporting, cached
):
    """Reporting and startup-read policies reach the correct cluster direction."""
    builder, create = make_device
    builder.switch(
        "on_off",
        OnOff.cluster_id,
        cluster_type=cluster_type,
        attribute_initialized_from_cache=cached,
        reporting_config=ReportingConfig(
            min_interval=5, max_interval=60, reportable_change=1
        )
        if reporting
        else None,
        translation_key="switch",
        fallback_name="Switch",
    )
    device = create()
    (entity,) = discover_quirks_v2_entities(device)
    endpoint = device.device.endpoints[1]
    clusters = (
        endpoint.in_clusters
        if cluster_type is ClusterType.Server
        else endpoint.out_clusters
    )
    assert entity.cluster is clusters[OnOff.cluster_id]
    config = (
        entity._server_cluster_config
        if cluster_type is ClusterType.Server
        else entity._client_cluster_config
    )
    config = config[OnOff.cluster_id]
    assert config.bind is reporting
    attr = config.attributes["on_off"]
    assert attr.read_on_startup is (not cached and not reporting)
    if reporting:
        assert attr.reporting.min_interval == 5
        assert attr.reporting.max_interval == 60
        assert attr.reporting.reportable_change == 1
    else:
        assert attr.reporting is None


@pytest.mark.parametrize("invalid", ["endpoint", "cluster", "metadata"])
async def test_invalid_metadata_does_not_hide_valid_entities(
    make_device, invalid, caplog
):
    """An invalid declaration is skipped while the next entity is still created."""
    builder, create = make_device
    builder.switch(
        "on_off", OnOff.cluster_id, translation_key="switch", fallback_name="Switch"
    )
    device = create()
    (valid,) = device.quirk_metadata.entity_metadata
    if invalid == "endpoint":
        broken = attrs.evolve(valid, endpoint_id=99)
    elif invalid == "cluster":
        broken = attrs.evolve(valid, cluster_id=0xFFFF)
    else:
        broken = EntityMetadata(
            entity_platform=EntityPlatform.SWITCH,
            entity_type=EntityType.CONFIG,
            cluster_id=OnOff.cluster_id,
            translation_key="unknown",
            fallback_name="Unknown",
        )
    device._quirk_definition = attrs.evolve(
        device.quirk_metadata, entity_metadata=(broken, valid)
    )
    (entity,) = discover_quirks_v2_entities(device)
    assert entity.unique_id == f"{device.ieee}-1-on_off"
    assert "unable to create entity" in caplog.text


async def test_device_without_exposed_entities(make_device):
    """An empty quirk exposes no extra entities and preserves default discovery."""
    _, create = make_device
    device = create()
    assert list(discover_quirks_v2_entities(device)) == []
    assert any(
        entity.PLATFORM == Platform.LIGHT for entity in device.discover_entities()
    )
    assert device.manufacturer == "test manufacturer"
    assert device.model == "test model"


async def test_matching_entity_metadata_changes(make_device):
    """Apply a matched override without changing the other exposed entity."""
    builder, create = make_device
    builder.switch(
        "on_off",
        OnOff.cluster_id,
        translation_key="switch",
        fallback_name="Switch",
    ).number(
        "on_time",
        OnOff.cluster_id,
        translation_key="on_time",
        fallback_name="On time",
    ).change_entity_metadata(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        unique_id_suffix="on_off",
        new_primary=True,
        new_unique_id="preserved-id",
        new_translation_key="custom_switch",
        new_fallback_name="Custom switch",
        new_entity_registry_enabled_default=False,
    )
    device = create()
    first, second = discover_quirks_v2_entities(device)
    second_id = second.unique_id
    device._apply_entity_metadata_changes(first)
    device._apply_entity_metadata_changes(second)
    assert first.unique_id == "preserved-id"
    assert first.primary is True
    assert first.translation_key == "custom_switch"
    assert first.fallback_name == "Custom switch"
    assert first.entity_registry_enabled_default is False
    assert second.unique_id == second_id
    assert second.fallback_name == "On time"


@pytest.mark.parametrize(
    ("filters", "removed"),
    [
        (
            {
                "endpoint_id": 1,
                "cluster_id": OnOff.cluster_id,
                "unique_id_suffix": "on_off",
            },
            True,
        ),
        ({"endpoint_id": 2}, False),
        ({"cluster_id": LevelControl.cluster_id}, False),
        ({"unique_id_suffix": "other"}, False),
        ({"function": lambda entity: entity.PLATFORM == Platform.SWITCH}, True),
        ({"function": lambda entity: entity.PLATFORM == Platform.NUMBER}, False),
    ],
)
async def test_default_entity_filters(make_device, filters, removed):
    """Only entities matching all supplied removal criteria are hidden."""
    builder, create = make_device
    builder.switch(
        "on_off",
        OnOff.cluster_id,
        translation_key="switch",
        fallback_name="Switch",
    ).prevent_default_entity_creation(**filters)
    device = create()
    (entity,) = discover_quirks_v2_entities(device)
    assert device._is_entity_removed_by_quirk(entity) is removed
