"""Tests for the thermostat presets ported from the ZHA library into quirks."""

import pytest
from zha.application.platforms import ENTITY_REGISTRY
from zha.application.platforms.climate.const import HVACMode, Preset
from zigpy.zcl.clusters.hvac import Thermostat as ThermostatCluster

import zhaquirks
from zhaquirks.builder.climate import QuirksThermostat

zhaquirks.setup()


def _registered(name):
    """Return the registered quirk thermostat class with the given name."""
    matches = [
        cls
        for cls in ENTITY_REGISTRY[ThermostatCluster.cluster_id]
        if issubclass(cls, QuirksThermostat) and cls.__name__ == name
    ]
    assert len(matches) == 1, f"expected one {name}, found {len(matches)}"
    return matches[0]


def test_moes_presets_ported():
    """Moes valves expose heat-only HVAC with the full preset set."""
    cls = _registered("MoesThermostat")
    assert "_TZE200_ckud7u2l" in cls._cluster_match.manufacturers
    assert "_TYST11_ckud7u2l" in cls._cluster_match.manufacturers
    assert cls._quirk_hvac_modes == [HVACMode.HEAT]
    # Verbatim from the former ZHA MoesThermostat.
    assert {k: int(v) for k, v in cls._preset_write_values.items()} == {
        Preset.NONE: 2,
        Preset.AWAY: 0,
        Preset.SCHEDULE: 1,
        Preset.COMFORT: 3,
        Preset.ECO: 4,
        Preset.BOOST: 5,
        Preset.COMPLEX: 6,
    }
    assert int(cls._preset_none_value) == 2


def test_beca_presets_ported():
    """Beca uses its own value layout, including 7 for temporary manual."""
    cls = _registered("BecaThermostat")
    assert cls._cluster_match.manufacturers == frozenset({"_TZE200_b6wax7g0"})
    assert cls._quirk_hvac_modes == [HVACMode.HEAT]
    assert {k: int(v) for k, v in cls._preset_write_values.items()} == {
        Preset.NONE: 2,
        Preset.AWAY: 0,
        Preset.SCHEDULE: 1,
        Preset.ECO: 4,
        Preset.BOOST: 5,
        Preset.TEMP_MANUAL: 7,
    }


def test_zonnsmart_presets_ported():
    """Zonnsmart maps two reported values to the single holiday preset."""
    cls = _registered("ZONNSMARTThermostat")
    assert "_TZE200_hue3yfsn" in cls._cluster_match.manufacturers
    assert cls._quirk_hvac_modes is None  # uses the device's ctrl sequence
    assert {k: int(v) for k, v in cls._preset_write_values.items()} == {
        Preset.SCHEDULE: 0,
        Preset.NONE: 1,
        "holiday": 3,
        "frost protect": 4,
    }
    # Reported values 2 and 3 both map back to the holiday preset.
    assert cls._preset_read_values[2] == "holiday"
    assert cls._preset_read_values[3] == "holiday"
    assert int(cls._preset_none_value) == 1


def test_stelpro_heat_only_ported():
    """Stelpro SORB is heat-only with no presets."""
    cls = _registered("StelproFanHeater")
    assert cls._cluster_match.manufacturers == frozenset({"Stelpro"})
    assert cls._cluster_match.models == frozenset({"SORB"})
    assert cls._quirk_hvac_modes == [HVACMode.HEAT]
    assert cls._preset_write_values == {}


@pytest.mark.parametrize(
    "name", ["MoesThermostat", "BecaThermostat", "ZONNSMARTThermostat"]
)
def test_ported_classes_use_priority_three(name):
    """Ported classes outrank the generic and hardcoded thermostat classes."""
    cls = _registered(name)
    _group, priority = cls._cluster_match.feature_priority
    assert priority == 3
