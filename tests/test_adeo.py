"""Tests for Adeo quirks."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.security import IasZone

import zhaquirks.adeo.sensor_ldsenk08  # noqa: F401
from zhaquirks.builder.device import QuirkV2Factory


def _ldsenk08_definition():
    """Return the quirk definition registered for the LDSENK08."""
    (definition,) = {
        entry.zha_device_factory.quirk_definition
        for entry in DEVICE_REGISTRY
        if isinstance(entry.zha_device_factory, QuirkV2Factory)
        and str(entry.source.file).endswith("sensor_ldsenk08.py")
    }
    return definition


@pytest.mark.parametrize(
    ("unique_id_suffix", "zone_status_bit"),
    [
        (str(IasZone.cluster_id), IasZone.ZoneStatus.Alarm_1),
        ("vibration", IasZone.ZoneStatus.Alarm_2),
        ("tamper", IasZone.ZoneStatus.Tamper),
    ],
)
def test_adeo_ldsenk08_zone_status_binary_sensors(unique_id_suffix, zone_status_bit):
    """Test each binary sensor only reflects its own zone_status bit."""
    (entity,) = (
        em
        for em in _ldsenk08_definition().entity_metadata
        if em.unique_id_suffix == unique_id_suffix
    )
    all_bits = (
        IasZone.ZoneStatus.Alarm_1
        | IasZone.ZoneStatus.Alarm_2
        | IasZone.ZoneStatus.Tamper
        | IasZone.ZoneStatus.Battery
    )

    assert entity.attribute_converter(zone_status_bit) is True
    assert entity.attribute_converter(all_bits & ~zone_status_bit) is False


def test_adeo_ldsenk08_only_removes_default_ias_zone_entity():
    """Test only ZHA's default IAS Zone entity is removed, not the Contact sensor."""
    (rule,) = _ldsenk08_definition().disabled_default_entities

    class IASZone:
        pass

    assert rule.cluster_id == IasZone.cluster_id
    assert rule.function(IASZone()) is True
    assert rule.function(mock.Mock()) is False
