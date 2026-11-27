"""Tests for the Sonoff SNZT-04P quirk."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.security import IasZone

import zhaquirks

zhaquirks.setup()


@pytest.mark.parametrize(
    ("zone_status", "tamper"),
    [
        (0, False),
        (IasZone.ZoneStatus.Alarm_1, False),
        (IasZone.ZoneStatus.Battery, False),
        (IasZone.ZoneStatus.Tamper, True),
        (IasZone.ZoneStatus.Tamper | IasZone.ZoneStatus.Alarm_1, True),
        (IasZone.ZoneStatus.Tamper | IasZone.ZoneStatus.Battery, True),
    ],
)
def test_sonoff_snzt04p_tamper_bit(zone_status, tamper):
    """Contact and battery status bits must not affect the tamper state."""
    entry = next(
        entry
        for entry in DEVICE_REGISTRY
        if any(
            model.manufacturer == "SONOFF" and model.model == "SNZT-04P"
            for model in entry.device_match.applies_to
        )
    )
    (entity,) = entry.zha_device_factory.quirk_definition.entity_metadata
    assert entity.attribute_converter(zone_status) is tamper
