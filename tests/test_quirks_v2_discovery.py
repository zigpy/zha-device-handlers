"""Tests for `zhaquirks.builder.discovery`.

`discover_quirks_v2_entities` turns the declarative `EntityMetadata` carried by a
quirk's `QuirkDefinition` into ZHA platform entities. The logic used to live in
ZHA's discovery module (exercised there by `tests/test_discover.py` via a full
`zha_gateway`); it now lives in the quirks layer and is driven by `QuirkV2Device`.

The ZHA test infrastructure (`zha_gateway`, `create_mock_zigpy_device`,
`join_zigpy_device`) does not ship with the installed `zha` package, so these tests
drive the discovery logic directly: real `QuirkDefinition`/metadata fed to the
function with a lightweight stand-in `Device` and the entity classes replaced by
recording stubs. That isolates the branching and keyword-assembly logic of
`discovery.py` itself, which is what moved into this repo.
"""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from zha.application import EntityPlatform, EntityType, Platform
from zha.application.platforms import AttrConfig, ClusterConfig
from zigpy.zcl import ClusterType

import zhaquirks
from zhaquirks.builder import discovery
from zhaquirks.builder.discovery import (
    _generic_kwargs,
    _platform_kwargs,
    discover_quirks_v2_entities,
)
from zhaquirks.builder.metadata import (
    BinarySensorMetadata,
    NumberMetadata,
    QuirkDefinition,
    ReportingConfig,
    SwitchMetadata,
    WriteAttributeButtonMetadata,
    ZCLCommandButtonMetadata,
    ZCLEnumMetadata,
    ZCLSensorMetadata,
)

zhaquirks.setup()


class _Color(int):
    """Minimal enum stand-in for ZCLEnumMetadata."""


def _identity(value):
    """Stand-in attribute converter used to assert pass-through."""
    return value


def _number_metadata(**overrides):
    """Return a `NumberMetadata` with sensible defaults, overridable per test."""
    kwargs = {
        "entity_platform": EntityPlatform.NUMBER,
        "entity_type": EntityType.CONFIG,
        "cluster_id": 6,
        "attribute_name": "off_wait_time",
        "fallback_name": "Off wait time",
        "translation_key": "off_wait_time",
        "min": 1,
        "max": 100,
        "step": 1,
        "multiplier": 1,
        "mode": "box",
        "unit": "s",
    }
    kwargs.update(overrides)
    return NumberMetadata(**kwargs)


def _mock_cluster(cluster_id: int) -> Mock:
    """Return a stand-in zigpy cluster exposing only `cluster_id`."""
    cluster = Mock()
    cluster.cluster_id = cluster_id
    return cluster


def _mock_device(
    quirk_definition: QuirkDefinition | None,
    endpoints: dict[int, dict[str, dict[int, Mock]]] | None = None,
):
    """Return a stand-in ZHA `Device` for discovery.

    `endpoints` maps endpoint_id -> {"in": {cluster_id: cluster}, "out": {...}}.
    """
    device_endpoints = {}
    for ep_id, clusters in (endpoints or {}).items():
        device_endpoints[ep_id] = SimpleNamespace(
            zigpy_endpoint=SimpleNamespace(
                in_clusters=clusters.get("in", {}),
                out_clusters=clusters.get("out", {}),
            )
        )
    return SimpleNamespace(
        quirk_metadata=quirk_definition,
        ieee="00:11:22:33:44:55:66:77",
        name="Test Device",
        endpoints=device_endpoints,
    )


class RecordingEntity:
    """Entity-class stand-in that records the kwargs it is constructed with."""

    def __init__(self, **kwargs) -> None:
        """Record the construction kwargs."""
        self.init_kwargs = kwargs


@pytest.fixture
def patch_number_entity(monkeypatch):
    """Map (NUMBER, NumberMetadata) to a recording entity class for one test."""
    monkeypatch.setitem(
        discovery.QUIRKS_ENTITY_META_TO_ENTITY_CLASS,
        (Platform.NUMBER, NumberMetadata),
        RecordingEntity,
    )
    return RecordingEntity


# ---------------------------------------------------------------------------
# _generic_kwargs
# ---------------------------------------------------------------------------


def test_generic_kwargs_basic() -> None:
    """Common kwargs are copied straight from the metadata."""
    meta = _number_metadata(
        entity_type=EntityType.DIAGNOSTIC,
        primary=True,
        initially_disabled=True,
    )
    kwargs = _generic_kwargs(meta)
    assert kwargs["from_quirk"] is True
    assert kwargs["fallback_name"] == "Off wait time"
    assert kwargs["translation_key"] == "off_wait_time"
    assert kwargs["entity_type"] is EntityType.DIAGNOSTIC
    assert kwargs["primary"] is True
    assert kwargs["initially_disabled"] is True


def test_generic_kwargs_empty_translation_placeholders_become_none() -> None:
    """An empty translation_placeholders frozendict is normalized to None."""
    assert _generic_kwargs(_number_metadata())["translation_placeholders"] is None


def test_generic_kwargs_translation_placeholders_passed_through() -> None:
    """A populated translation_placeholders mapping is preserved."""
    meta = _number_metadata(translation_placeholders={"foo": "bar"})
    placeholders = _generic_kwargs(meta)["translation_placeholders"]
    assert placeholders == {"foo": "bar"}


def test_generic_kwargs_unique_id_suffix_falls_back_to_attribute_name() -> None:
    """Without an explicit suffix, the attribute name is used."""
    meta = _number_metadata(unique_id_suffix=None)
    assert _generic_kwargs(meta)["unique_id_suffix"] == "off_wait_time"


def test_generic_kwargs_explicit_unique_id_suffix_wins() -> None:
    """An explicit unique_id_suffix overrides the attribute-name fallback."""
    meta = _number_metadata(unique_id_suffix="64704-off_wait_time")
    assert _generic_kwargs(meta)["unique_id_suffix"] == "64704-off_wait_time"


# ---------------------------------------------------------------------------
# _platform_kwargs
# ---------------------------------------------------------------------------


def test_platform_kwargs_sensor() -> None:
    """Sensor metadata maps to the sensor-specific kwargs."""
    converter = _identity
    meta = ZCLSensorMetadata(
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        cluster_id=1026,
        attribute_name="measured_value",
        attribute_converter=converter,
        divisor=100,
        multiplier=2,
        device_class=None,
        state_class=None,
        unit="°C",
        translation_key="temperature",
        fallback_name="Temperature",
    )
    kwargs = _platform_kwargs(meta)
    assert kwargs == {
        "attribute_name": "measured_value",
        "attribute_converter": converter,
        "divisor": 100,
        "multiplier": 2,
        "device_class": None,
        "state_class": None,
        "unit": "°C",
    }


def test_platform_kwargs_number() -> None:
    """Number metadata maps min/max/step/multiplier/mode through."""
    kwargs = _platform_kwargs(_number_metadata())
    assert kwargs == {
        "attribute_name": "off_wait_time",
        "min_value": 1,
        "max_value": 100,
        "step": 1,
        "multiplier": 1,
        "device_class": None,
        "unit": "s",
        "mode": "box",
    }


def test_platform_kwargs_switch() -> None:
    """Switch metadata maps the invert/on/off attributes through."""
    meta = SwitchMetadata(
        entity_platform=EntityPlatform.SWITCH,
        entity_type=EntityType.CONFIG,
        cluster_id=6,
        attribute_name="led_enable",
        force_inverted=True,
        invert_attribute_name="inverted",
        off_value=0,
        on_value=1,
        translation_key="led_enable",
        fallback_name="LED enable",
    )
    assert _platform_kwargs(meta) == {
        "attribute_name": "led_enable",
        "invert_attribute_name": "inverted",
        "force_inverted": True,
        "off_value": 0,
        "on_value": 1,
    }


def test_platform_kwargs_binary_sensor() -> None:
    """Binary sensor metadata maps attribute/converter/device_class through."""
    converter = _identity
    meta = BinarySensorMetadata(
        entity_platform=EntityPlatform.BINARY_SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        cluster_id=1280,
        attribute_name="zone_status",
        attribute_converter=converter,
        device_class=None,
        translation_key="tamper",
        fallback_name="Tamper",
    )
    assert _platform_kwargs(meta) == {
        "attribute_name": "zone_status",
        "attribute_converter": converter,
        "device_class": None,
    }


def test_platform_kwargs_enum() -> None:
    """Enum metadata maps attribute_name and the enum class through."""
    meta = ZCLEnumMetadata(
        entity_platform=EntityPlatform.SELECT,
        entity_type=EntityType.CONFIG,
        cluster_id=6,
        attribute_name="mode",
        enum=_Color,
        translation_key="mode",
        fallback_name="Mode",
    )
    assert _platform_kwargs(meta) == {"attribute_name": "mode", "enum": _Color}


def test_platform_kwargs_write_attribute_button() -> None:
    """Write-attribute button metadata maps attribute name and value through."""
    meta = WriteAttributeButtonMetadata(
        entity_platform=EntityPlatform.BUTTON,
        entity_type=EntityType.CONFIG,
        cluster_id=6,
        attribute_name="reset",
        attribute_value=1,
        translation_key="reset",
        fallback_name="Reset",
    )
    assert _platform_kwargs(meta) == {
        "attribute_name": "reset",
        "attribute_value": 1,
    }


def test_platform_kwargs_command_button() -> None:
    """Command button metadata maps command name/args/kwargs through."""
    meta = ZCLCommandButtonMetadata(
        entity_platform=EntityPlatform.BUTTON,
        entity_type=EntityType.CONFIG,
        cluster_id=0,
        command_name="reset_to_factory_defaults",
        args=(1, 2),
        kwargs={"foo": "bar"},
        translation_key="factory_reset",
        fallback_name="Factory reset",
    )
    kwargs = _platform_kwargs(meta)
    assert kwargs["command_name"] == "reset_to_factory_defaults"
    assert kwargs["command_args"] == (1, 2)
    assert kwargs["command_kwargs"] == {"foo": "bar"}


def test_platform_kwargs_unknown_metadata_returns_empty() -> None:
    """An unrecognized metadata type yields no platform-specific kwargs."""
    assert _platform_kwargs(object()) == {}


# ---------------------------------------------------------------------------
# discover_quirks_v2_entities
# ---------------------------------------------------------------------------


def test_discover_no_quirk_metadata(caplog) -> None:
    """A device without quirk metadata yields nothing and logs at debug."""
    device = _mock_device(None)
    with caplog.at_level("DEBUG"):
        assert list(discover_quirks_v2_entities(device)) == []
    assert "does not expose any quirks v2 entities" in caplog.text


def test_discover_empty_entity_metadata(caplog) -> None:
    """A device whose quirk exposes no entities yields nothing."""
    device = _mock_device(QuirkDefinition(entity_metadata=()))
    with caplog.at_level("DEBUG"):
        assert list(discover_quirks_v2_entities(device)) == []
    assert "does not expose any quirks v2 entities" in caplog.text


def test_discover_missing_endpoint_skips(caplog) -> None:
    """Metadata pointing at a missing endpoint is skipped with a warning."""
    meta = _number_metadata(endpoint_id=3)
    device = _mock_device(
        QuirkDefinition(entity_metadata=(meta,)),
        endpoints={1: {"in": {6: _mock_cluster(6)}}},
    )
    assert list(discover_quirks_v2_entities(device)) == []
    assert "does not have an endpoint with id: 3" in caplog.text


def test_discover_missing_server_cluster_skips(caplog) -> None:
    """Metadata pointing at a missing server cluster is skipped with a warning."""
    meta = _number_metadata(cluster_id=6)
    device = _mock_device(
        QuirkDefinition(entity_metadata=(meta,)),
        endpoints={1: {"in": {}}},
    )
    assert list(discover_quirks_v2_entities(device)) == []
    assert "does not have a cluster with id: 6" in caplog.text


def test_discover_missing_client_cluster_skips(caplog) -> None:
    """A client-cluster entity only resolves against out_clusters."""
    meta = _number_metadata(cluster_type=ClusterType.Client)
    # cluster present on the server side only -> still missing for a client entity
    device = _mock_device(
        QuirkDefinition(entity_metadata=(meta,)),
        endpoints={1: {"in": {6: _mock_cluster(6)}, "out": {}}},
    )
    assert list(discover_quirks_v2_entities(device)) == []
    assert "does not have a cluster with id: 6" in caplog.text


def test_discover_no_entity_class_mapping_skips(caplog) -> None:
    """Metadata with no (platform, type) mapping is skipped with a warning."""
    # NumberMetadata on the SENSOR platform has no registered entity class
    meta = _number_metadata(entity_platform=EntityPlatform.SENSOR)
    device = _mock_device(
        QuirkDefinition(entity_metadata=(meta,)),
        endpoints={1: {"in": {6: _mock_cluster(6)}}},
    )
    assert list(discover_quirks_v2_entities(device)) == []
    assert "does not have an entity class mapping" in caplog.text


def test_discover_creates_entity_with_expected_kwargs(patch_number_entity) -> None:
    """The happy path builds the mapped entity class with the assembled kwargs."""
    cluster = _mock_cluster(6)
    meta = _number_metadata()
    device = _mock_device(
        QuirkDefinition(entity_metadata=(meta,)),
        endpoints={1: {"in": {6: cluster}}},
    )

    entities = list(discover_quirks_v2_entities(device))
    assert len(entities) == 1
    entity = entities[0]
    assert isinstance(entity, patch_number_entity)

    kwargs = entity.init_kwargs
    assert kwargs["device"] is device
    assert kwargs["cluster"] is cluster
    assert kwargs["endpoint"] is device.endpoints[1]
    # generic kwargs
    assert kwargs["from_quirk"] is True
    assert kwargs["fallback_name"] == "Off wait time"
    # platform kwargs
    assert kwargs["attribute_name"] == "off_wait_time"
    assert kwargs["min_value"] == 1
    assert kwargs["mode"] == "box"


def test_discover_attribute_read_on_startup_when_not_cached(
    patch_number_entity,
) -> None:
    """Without reporting config, the attribute is read on startup unless cached."""
    cluster = _mock_cluster(6)
    meta = _number_metadata(attribute_initialized_from_cache=False)
    device = _mock_device(
        QuirkDefinition(entity_metadata=(meta,)),
        endpoints={1: {"in": {6: cluster}}},
    )

    entity = next(iter(discover_quirks_v2_entities(device)))
    config = entity._server_cluster_config
    cluster_config = config[6]
    assert isinstance(cluster_config, ClusterConfig)
    assert cluster_config.bind is False
    attr_config = cluster_config.attributes["off_wait_time"]
    assert isinstance(attr_config, AttrConfig)
    assert attr_config.read_on_startup is True
    assert attr_config.reporting is None


def test_discover_cached_attribute_not_read_on_startup(patch_number_entity) -> None:
    """A cache-initialized attribute is not read on startup."""
    cluster = _mock_cluster(6)
    meta = _number_metadata(attribute_initialized_from_cache=True)
    device = _mock_device(
        QuirkDefinition(entity_metadata=(meta,)),
        endpoints={1: {"in": {6: cluster}}},
    )
    entity = next(iter(discover_quirks_v2_entities(device)))
    attr_config = entity._server_cluster_config[6].attributes["off_wait_time"]
    assert attr_config.read_on_startup is False
    assert entity._server_cluster_config[6].bind is False


def test_discover_reporting_config_binds_and_reports(patch_number_entity) -> None:
    """Reporting config produces a binding cluster config with a ReportingConfig."""
    cluster = _mock_cluster(6)
    meta = _number_metadata(
        reporting_config=ReportingConfig(
            min_interval=60, max_interval=120, reportable_change=1
        )
    )
    device = _mock_device(
        QuirkDefinition(entity_metadata=(meta,)),
        endpoints={1: {"in": {6: cluster}}},
    )

    entity = next(iter(discover_quirks_v2_entities(device)))
    cluster_config = entity._server_cluster_config[6]
    assert cluster_config.bind is True
    attr_config = cluster_config.attributes["off_wait_time"]
    assert attr_config.read_on_startup is False
    assert attr_config.reporting.min_interval == 60
    assert attr_config.reporting.max_interval == 120
    assert attr_config.reporting.reportable_change == 1


def test_discover_client_cluster_sets_client_config(monkeypatch) -> None:
    """A client-cluster entity resolves via out_clusters and sets the client config."""
    monkeypatch.setitem(
        discovery.QUIRKS_ENTITY_META_TO_ENTITY_CLASS,
        (Platform.NUMBER, NumberMetadata),
        RecordingEntity,
    )
    cluster = _mock_cluster(6)
    meta = _number_metadata(cluster_type=ClusterType.Client)
    device = _mock_device(
        QuirkDefinition(entity_metadata=(meta,)),
        endpoints={1: {"out": {6: cluster}}},
    )

    entity = next(iter(discover_quirks_v2_entities(device)))
    assert hasattr(entity, "_client_cluster_config")
    assert not hasattr(entity, "_server_cluster_config")
    assert entity._client_cluster_config[6].attributes["off_wait_time"]


def test_discover_command_button_sets_no_cluster_config(monkeypatch) -> None:
    """A command button has no attribute_name, so no cluster config is attached."""
    recording = RecordingEntity
    monkeypatch.setitem(
        discovery.QUIRKS_ENTITY_META_TO_ENTITY_CLASS,
        (Platform.BUTTON, ZCLCommandButtonMetadata),
        recording,
    )
    cluster = _mock_cluster(0)
    meta = ZCLCommandButtonMetadata(
        entity_platform=EntityPlatform.BUTTON,
        entity_type=EntityType.CONFIG,
        cluster_id=0,
        command_name="reset_to_factory_defaults",
        translation_key="factory_reset",
        fallback_name="Factory reset",
    )
    device = _mock_device(
        QuirkDefinition(entity_metadata=(meta,)),
        endpoints={1: {"in": {0: cluster}}},
    )

    entity = next(iter(discover_quirks_v2_entities(device)))
    assert not hasattr(entity, "_server_cluster_config")
    assert not hasattr(entity, "_client_cluster_config")


def test_discover_multiple_entities_and_partial_failures(patch_number_entity) -> None:
    """Valid entities are yielded even when other metadata entries are skipped."""
    good = _number_metadata()
    missing_cluster = _number_metadata(cluster_id=999)
    device = _mock_device(
        QuirkDefinition(entity_metadata=(good, missing_cluster)),
        endpoints={1: {"in": {6: _mock_cluster(6)}}},
    )
    entities = list(discover_quirks_v2_entities(device))
    assert len(entities) == 1
    assert entities[0].init_kwargs["attribute_name"] == "off_wait_time"
