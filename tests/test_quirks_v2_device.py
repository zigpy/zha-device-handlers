"""Tests for `zhaquirks.builder.device`.

`QuirkV2Device` is the ZHA `Device` subclass that declarative (QuirkBuilder)
quirks resolve to. It overrides the hooks ZHA calls during entity discovery to
surface the quirk's `QuirkDefinition` metadata: friendly name, exposed features,
alerts, automation triggers, default-entity removal and metadata changes.

These tests build a `QuirkV2Device` via `__new__` (bypassing ZHA's heavy
`Device.__init__`, which needs a gateway) and exercise the quirk-specific hooks
in isolation against constructed metadata and stand-in entities.
"""

from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

from zha.application import EntityType, Platform
from zha.application.platforms.sensor.device_class import (
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.zcl import ClusterType

import zhaquirks

# `zhaquirks.builder.device` imports the ZHA platform modules in the order needed
# to avoid a circular import with `zha.zigbee.device`; import it (and reach `Device`
# through it) rather than importing `zha.zigbee.device` directly.
import zhaquirks.builder.device as device_module
from zhaquirks.builder.device import QuirkV2Device, QuirkV2Factory
from zhaquirks.builder.metadata import (
    ChangedEntityMetadata,
    DeviceAlertMetadata,
    ExposesFeatureMetadata,
    FriendlyNameMetadata,
    PreventDefaultEntityCreationMetadata,
    QuirkDefinition,
)

# Reach ZHA's `Device` base through the module above so the platform modules it
# pulls in are loaded first (a direct `from zha.zigbee.device import Device` here
# trips the circular import the module's import ordering exists to avoid).
Device = device_module.Device

zhaquirks.setup()


def _device(definition: QuirkDefinition) -> QuirkV2Device:
    """Build a `QuirkV2Device` without running ZHA's `Device.__init__`."""
    device = QuirkV2Device.__new__(QuirkV2Device)
    device._quirk_definition = definition
    return device


def _entity(
    *,
    platform: Platform = Platform.SWITCH,
    unique_id: str = "ieee-1-6-led_enable",
    endpoint_id: int = 1,
    targets: int = 6,
):
    """Return a stand-in `PlatformEntity` for removal/change matching."""
    return SimpleNamespace(
        PLATFORM=platform,
        unique_id=unique_id,
        endpoint=SimpleNamespace(id=endpoint_id),
        targets_cluster=lambda cid, cluster_type=None: cid == targets,
        _attr_primary=False,
        _unique_id=unique_id,
        _attr_translation_key=None,
        _attr_translation_placeholders=None,
        _attr_device_class=None,
        _attr_state_class=None,
        _attr_entity_category=None,
        _attr_entity_registry_enabled_default=None,
        _attr_fallback_name=None,
    )


# ---------------------------------------------------------------------------
# Simple metadata-backed hooks
# ---------------------------------------------------------------------------


def test_quirk_metadata_property() -> None:
    """`quirk_metadata` returns the bound definition."""
    definition = QuirkDefinition()
    assert _device(definition).quirk_metadata is definition


def test_quirk_exposes_features() -> None:
    """Exposed-feature metadata is reduced to a set of feature names."""
    definition = QuirkDefinition(
        exposes_features=(
            ExposesFeatureMetadata(feature="fan"),
            ExposesFeatureMetadata(feature="light"),
        )
    )
    assert _device(definition)._quirk_exposes_features() == {"fan", "light"}


def test_quirk_skip_configuration() -> None:
    """`_quirk_skip_configuration` reflects the definition flag."""
    assert _device(QuirkDefinition(skip_configuration=True))._quirk_skip_configuration()
    assert not _device(QuirkDefinition())._quirk_skip_configuration()


def test_quirk_device_automation_triggers() -> None:
    """Automation triggers are returned as a plain dict copy."""
    definition = QuirkDefinition(
        device_automation_triggers={("remote_button_short_press", "turn_on"): {}}
    )
    triggers = _device(definition)._quirk_device_automation_triggers()
    assert ("remote_button_short_press", "turn_on") in triggers


def test_device_alerts() -> None:
    """Device alerts are surfaced from the definition."""
    alert = DeviceAlertMetadata(level="warning", message="firmware too old")
    assert _device(QuirkDefinition(device_alerts=(alert,))).device_alerts == (alert,)


# ---------------------------------------------------------------------------
# Friendly-name resolution
# ---------------------------------------------------------------------------


def test_resolve_friendly_name_override() -> None:
    """A friendly name overrides manufacturer/model resolution."""
    definition = QuirkDefinition(
        friendly_name=FriendlyNameMetadata(model="Nice model", manufacturer="Acme")
    )
    device = _device(definition)
    assert device._resolve_manufacturer() == "Acme"
    assert device._resolve_model() == "Nice model"


def test_resolve_without_friendly_name_falls_back_to_super() -> None:
    """Without a friendly name, resolution defers to the zigpy device values."""
    device = _device(QuirkDefinition())
    device._zigpy_device = SimpleNamespace(manufacturer="RawMfg", model="RawModel")
    with patch.object(
        QuirkV2Device,
        "is_active_coordinator",
        new_callable=PropertyMock,
        return_value=False,
    ):
        assert device._resolve_manufacturer() == "RawMfg"
        assert device._resolve_model() == "RawModel"


# ---------------------------------------------------------------------------
# Default-entity removal
# ---------------------------------------------------------------------------


def test_entity_removed_when_all_criteria_match() -> None:
    """An entity matching every criterion of a removal rule is removed."""
    definition = QuirkDefinition(
        disabled_default_entities=(
            PreventDefaultEntityCreationMetadata(
                endpoint_id=1,
                cluster_id=6,
                cluster_type=ClusterType.Server,
                unique_id_suffix="led_enable",
                function=None,
            ),
        )
    )
    assert _device(definition)._is_entity_removed_by_quirk(_entity()) is True


def test_entity_not_removed_when_suffix_mismatch() -> None:
    """A removal rule whose suffix does not match leaves the entity in place."""
    definition = QuirkDefinition(
        disabled_default_entities=(
            PreventDefaultEntityCreationMetadata(
                endpoint_id=None,
                cluster_id=None,
                cluster_type=None,
                unique_id_suffix="other",
                function=None,
            ),
        )
    )
    assert _device(definition)._is_entity_removed_by_quirk(_entity()) is False


def test_entity_not_removed_when_endpoint_mismatch() -> None:
    """A removal rule for a different endpoint does not match."""
    definition = QuirkDefinition(
        disabled_default_entities=(
            PreventDefaultEntityCreationMetadata(
                endpoint_id=2,
                cluster_id=None,
                cluster_type=None,
                unique_id_suffix=None,
                function=None,
            ),
        )
    )
    assert _device(definition)._is_entity_removed_by_quirk(_entity()) is False


def test_entity_not_removed_when_cluster_mismatch() -> None:
    """A removal rule targeting a different cluster does not match."""
    definition = QuirkDefinition(
        disabled_default_entities=(
            PreventDefaultEntityCreationMetadata(
                endpoint_id=None,
                cluster_id=8,
                cluster_type=None,
                unique_id_suffix=None,
                function=None,
            ),
        )
    )
    assert _device(definition)._is_entity_removed_by_quirk(_entity()) is False


def test_entity_removed_by_function() -> None:
    """A removal rule with only a function predicate is honored."""
    definition = QuirkDefinition(
        disabled_default_entities=(
            PreventDefaultEntityCreationMetadata(
                endpoint_id=None,
                cluster_id=None,
                cluster_type=None,
                unique_id_suffix=None,
                function=lambda entity: True,
            ),
        )
    )
    assert _device(definition)._is_entity_removed_by_quirk(_entity()) is True


def test_entity_not_removed_when_function_returns_false() -> None:
    """A removal rule whose function predicate fails does not match."""
    definition = QuirkDefinition(
        disabled_default_entities=(
            PreventDefaultEntityCreationMetadata(
                endpoint_id=None,
                cluster_id=None,
                cluster_type=None,
                unique_id_suffix=None,
                function=lambda entity: False,
            ),
        )
    )
    assert _device(definition)._is_entity_removed_by_quirk(_entity()) is False


def test_virtual_entity_never_removed() -> None:
    """Virtual entities are never removed regardless of rules."""
    definition = QuirkDefinition(
        disabled_default_entities=(
            PreventDefaultEntityCreationMetadata(
                endpoint_id=None,
                cluster_id=None,
                cluster_type=None,
                unique_id_suffix=None,
                function=lambda entity: True,
            ),
        )
    )
    entity = _entity(platform=Platform.VIRTUAL)
    assert _device(definition)._is_entity_removed_by_quirk(entity) is False


# ---------------------------------------------------------------------------
# Default-entity metadata changes
# ---------------------------------------------------------------------------


def test_apply_entity_metadata_changes() -> None:
    """A matching change rule rewrites every targeted entity attribute."""
    definition = QuirkDefinition(
        changed_entity_metadata=(
            ChangedEntityMetadata(
                endpoint_id=1,
                cluster_id=6,
                cluster_type=ClusterType.Server,
                unique_id_suffix="led_enable",
                function=lambda entity: True,
                new_primary=True,
                new_unique_id="ieee-1-6-renamed",
                new_translation_key="renamed",
                new_translation_placeholders={"foo": "bar"},
                new_device_class=SensorDeviceClass.TEMPERATURE,
                new_state_class=SensorStateClass.MEASUREMENT,
                new_entity_category=EntityType.DIAGNOSTIC,
                new_entity_registry_enabled_default=False,
                new_fallback_name="Renamed",
            ),
        )
    )
    entity = _entity()
    _device(definition)._apply_entity_metadata_changes(entity)
    assert entity._attr_primary is True
    assert entity._unique_id == "ieee-1-6-renamed"
    assert entity._attr_translation_key == "renamed"
    assert entity._attr_translation_placeholders == {"foo": "bar"}
    assert entity._attr_device_class is SensorDeviceClass.TEMPERATURE
    assert entity._attr_state_class is SensorStateClass.MEASUREMENT
    assert entity._attr_entity_category is EntityType.DIAGNOSTIC
    assert entity._attr_entity_registry_enabled_default is False
    assert entity._attr_fallback_name == "Renamed"


def test_apply_entity_metadata_changes_skips_on_suffix_cluster_function() -> None:
    """Each non-matching criterion (suffix, cluster, function) skips the rule."""
    base = {
        "endpoint_id": None,
        "cluster_type": ClusterType.Server,
        "new_primary": True,
    }
    rules = (
        # suffix mismatch
        ChangedEntityMetadata(
            cluster_id=None, unique_id_suffix="nope", function=None, **base
        ),
        # cluster mismatch
        ChangedEntityMetadata(
            cluster_id=8, unique_id_suffix=None, function=None, **base
        ),
        # function predicate fails
        ChangedEntityMetadata(
            cluster_id=None,
            unique_id_suffix=None,
            function=lambda entity: False,
            **base,
        ),
    )
    for rule in rules:
        entity = _entity()
        _device(
            QuirkDefinition(changed_entity_metadata=(rule,))
        )._apply_entity_metadata_changes(entity)
        assert entity._attr_primary is False


def test_apply_entity_metadata_changes_skips_non_matching() -> None:
    """A change rule that does not match leaves the entity untouched."""
    definition = QuirkDefinition(
        changed_entity_metadata=(
            ChangedEntityMetadata(
                endpoint_id=99,
                cluster_id=None,
                cluster_type=None,
                unique_id_suffix=None,
                function=None,
                new_primary=True,
            ),
        )
    )
    entity = _entity()
    _device(definition)._apply_entity_metadata_changes(entity)
    assert entity._attr_primary is False


def test_apply_entity_metadata_changes_ignores_virtual() -> None:
    """Virtual entities are exempt from metadata changes."""
    definition = QuirkDefinition(
        changed_entity_metadata=(
            ChangedEntityMetadata(
                endpoint_id=None,
                cluster_id=None,
                cluster_type=None,
                unique_id_suffix=None,
                function=None,
                new_primary=True,
            ),
        )
    )
    entity = _entity(platform=Platform.VIRTUAL)
    _device(definition)._apply_entity_metadata_changes(entity)
    assert entity._attr_primary is False


# ---------------------------------------------------------------------------
# QuirkV2Factory
# ---------------------------------------------------------------------------


def test_quirk_v2_factory_builds_bound_device() -> None:
    """The factory constructs its base bound to the quirk definition."""
    definition = QuirkDefinition()
    built = {}

    class FakeBase:
        def __init__(self, zigpy_device, gateway, *, quirk_definition) -> None:
            built["args"] = (zigpy_device, gateway, quirk_definition)

    factory = QuirkV2Factory(base=FakeBase, quirk_definition=definition)
    sentinel_device = object()
    sentinel_gateway = object()
    result = factory(sentinel_device, sentinel_gateway)

    assert isinstance(result, FakeBase)
    assert built["args"] == (sentinel_device, sentinel_gateway, definition)


# ---------------------------------------------------------------------------
# Construction and discovery wiring
# ---------------------------------------------------------------------------


def test_init_stores_definition_and_calls_super() -> None:
    """`__init__` records the definition and defers to ZHA's Device init."""
    definition = QuirkDefinition()
    zigpy_device = object()
    gateway = object()
    with patch.object(Device, "__init__", return_value=None) as mock_init:
        device = QuirkV2Device(zigpy_device, gateway, quirk_definition=definition)
    assert device._quirk_definition is definition
    mock_init.assert_called_once_with(zigpy_device, gateway)


def test_discover_entities_chains_default_and_quirk_entities() -> None:
    """`discover_entities` yields ZHA's default entities then the quirk's."""
    device = _device(QuirkDefinition())
    default_entity = object()
    quirk_entity = object()
    with (
        patch.object(Device, "discover_entities", return_value=iter([default_entity])),
        patch.object(
            device_module,
            "discover_quirks_v2_entities",
            return_value=iter([quirk_entity]),
        ) as mock_discover,
    ):
        result = list(device.discover_entities())
    assert result == [default_entity, quirk_entity]
    mock_discover.assert_called_once_with(device)
