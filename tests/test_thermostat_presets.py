"""Tests for the quirk-defined thermostat preset augmentation mechanism."""

from unittest import mock

import pytest
from zha.application.platforms import ENTITY_REGISTRY, PlatformFeatureGroup
from zha.application.platforms.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    Preset,
)
from zha.quirks import DeviceRegistry
from zigpy.zcl.clusters.hvac import Thermostat as ThermostatCluster

from zhaquirks.builder import QuirkBuilder, register_thermostat_presets
from zhaquirks.builder.climate import (
    QUIRK_THERMOSTAT_FEATURE_PRIORITY,
    QuirksThermostat,
)

# A representative Moes-style preset config (verbatim from the ZHA MoesThermostat).
MOES_PRESETS = {
    Preset.NONE: 2,
    Preset.AWAY: 0,
    Preset.SCHEDULE: 1,
    Preset.COMFORT: 3,
    Preset.ECO: 4,
    Preset.BOOST: 5,
    Preset.COMPLEX: 6,
}


def test_register_thermostat_presets_builds_class():
    """A registered class carries the resolved preset config and cluster match."""
    cls = register_thermostat_presets(
        manufacturers={"_TZE200_ckud7u2l"},
        attribute_name="operation_preset",
        presets=MOES_PRESETS,
        hvac_modes=[HVACMode.HEAT],
    )

    assert issubclass(cls, QuirksThermostat)
    assert cls in ENTITY_REGISTRY[ThermostatCluster.cluster_id]

    # Write map is as given; read map is its inverse; none value defaults to NONE.
    assert cls._preset_write_values == MOES_PRESETS
    assert cls._preset_read_values == {v: k for k, v in MOES_PRESETS.items()}
    assert cls._preset_none_value == MOES_PRESETS[Preset.NONE]
    assert cls._quirk_hvac_modes == [HVACMode.HEAT]

    match = cls._cluster_match
    assert match.manufacturers == frozenset({"_TZE200_ckud7u2l"})
    assert match.server_clusters == frozenset({ThermostatCluster.cluster_id})
    assert match.feature_priority == (
        PlatformFeatureGroup.THERMOSTAT_FAN,
        QUIRK_THERMOSTAT_FEATURE_PRIORITY,
    )


def test_register_thermostat_presets_read_overrides_and_none():
    """read_value_overrides add many-to-one reads; none_value is explicit."""
    cls = register_thermostat_presets(
        manufacturers={"_TZE200_hue3yfsn"},
        attribute_name="operation_preset",
        presets={Preset.SCHEDULE: 0, Preset.NONE: 1, "holiday": 3, "frost protect": 4},
        read_value_overrides={2: "holiday"},
        none_value=1,
    )
    # Both 2 and 3 read back as the holiday preset.
    assert cls._preset_read_values[2] == "holiday"
    assert cls._preset_read_values[3] == "holiday"
    assert cls._preset_none_value == 1


def test_register_thermostat_presets_requires_scope():
    """A scope (manufacturers and/or models) is required."""
    with pytest.raises(ValueError, match="manufacturers and/or models"):
        register_thermostat_presets(attribute_name="x", presets={Preset.NONE: 0})


def test_register_thermostat_presets_requires_attribute_for_presets():
    """Presets without a backing attribute are rejected."""
    with pytest.raises(ValueError, match="attribute_name is required"):
        register_thermostat_presets(manufacturers={"m"}, presets={Preset.AWAY: 0})


def test_builder_thermostat_presets_scopes_to_quirk_devices():
    """QuirkBuilder.thermostat_presets derives the scope from the quirk."""
    registry = DeviceRegistry()
    before = list(ENTITY_REGISTRY[ThermostatCluster.cluster_id])

    (
        QuirkBuilder("_TZE200_b6wax7g0", "TS0601", registry=registry)
        .applies_to("_TZE200_other", "TS0601")
        .thermostat_presets(
            attribute_name="operation_preset",
            presets={Preset.NONE: 2, Preset.AWAY: 0},
            hvac_modes=[HVACMode.HEAT],
        )
        .add_to_registry()
    )

    new = [c for c in ENTITY_REGISTRY[ThermostatCluster.cluster_id] if c not in before]
    assert len(new) == 1
    match = new[0]._cluster_match
    assert match.manufacturers == frozenset({"_TZE200_b6wax7g0", "_TZE200_other"})
    assert match.models == frozenset({"TS0601"})


def _make_instance(cls):
    """Build a bare entity instance, bypassing the full ZHA __init__."""
    inst = object.__new__(cls)
    inst._preset = Preset.NONE
    inst._presets = []
    inst._supported_features = ClimateEntityFeature(0)
    inst._fan_cluster = None
    inst._cluster = mock.MagicMock()
    inst._cluster.get.return_value = 0xFF  # unknown ctrl_sequence -> [OFF]
    inst._cluster.write_attributes = mock.AsyncMock(return_value=([], []))
    inst._device = mock.MagicMock()
    inst._device.manufacturer_code = 0x1234
    # The base handle_attribute_updated dispatches an async task; close the
    # coroutine instead of leaving it un-awaited.
    inst._device.gateway.async_create_task.side_effect = lambda coro: coro.close()
    return inst


def test_recompute_capabilities_sets_presets_and_feature():
    """recompute_capabilities exposes the presets and the PRESET_MODE feature."""
    cls = register_thermostat_presets(
        manufacturers={"recompute-test"},
        attribute_name="operation_preset",
        presets=MOES_PRESETS,
        hvac_modes=[HVACMode.HEAT],
    )
    inst = _make_instance(cls)
    inst.recompute_capabilities()

    assert inst._presets == list(MOES_PRESETS)
    assert inst._supported_features & ClimateEntityFeature.PRESET_MODE
    assert inst.hvac_modes == [HVACMode.HEAT]


def test_handle_attribute_updated_maps_value_to_preset():
    """A reported backing-attribute value updates the active preset."""
    cls = register_thermostat_presets(
        manufacturers={"handle-test"},
        attribute_name="operation_preset",
        presets=MOES_PRESETS,
    )
    inst = _make_instance(cls)

    event = mock.MagicMock(attribute_name="operation_preset", value=4)
    inst.handle_attribute_updated(event)
    assert inst._preset == Preset.ECO

    # An unrelated attribute leaves the preset unchanged.
    other = mock.MagicMock(attribute_name="local_temperature", value=2100)
    inst.handle_attribute_updated(other)
    assert inst._preset == Preset.ECO


async def test_async_preset_handler_writes_backing_attribute():
    """Selecting / clearing a preset writes the mapped value to the device."""
    cls = register_thermostat_presets(
        manufacturers={"write-test"},
        attribute_name="operation_preset",
        presets=MOES_PRESETS,
    )
    inst = _make_instance(cls)

    await inst.async_preset_handler(Preset.BOOST, enable=True)
    inst._cluster.write_attributes.assert_awaited_with(
        {"operation_preset": 5}, manufacturer=0x1234
    )

    # Disabling writes the none/reset value regardless of the preset passed.
    await inst.async_preset_handler(Preset.BOOST, enable=False)
    inst._cluster.write_attributes.assert_awaited_with(
        {"operation_preset": 2}, manufacturer=0x1234
    )


def test_quirk_thermostat_not_directly_registered():
    """The base augmentation class is never registered itself."""
    assert QuirksThermostat not in ENTITY_REGISTRY[ThermostatCluster.cluster_id]
