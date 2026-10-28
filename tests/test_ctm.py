"""Tests for CTM Lyng quirks."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

import zhaquirks
from zhaquirks.ctm import CTM_MANUF_NAME

zhaquirks.setup()

VALVE_MODEL = "AX Valve Controller"
SENSOR_MODEL = "AX Water Sensor"

# Bits 4 and 5 are always set by the device, so every zone status builds on them.
IDLE = IasZone.ZoneStatus.Supervision_reports | IasZone.ZoneStatus.Restore_reports


def quirk_definition(model):
    """Return the quirk definition registered for a CTM Lyng model."""
    for entry in DEVICE_REGISTRY:
        if any(
            model_info.manufacturer == CTM_MANUF_NAME and model_info.model == model
            for model_info in entry.device_match.applies_to
        ):
            return entry.zha_device_factory.quirk_definition
    pytest.fail(f"no v2 quirk registered for {CTM_MANUF_NAME} {model}")


@pytest.fixture
def definition():
    """Return the quirk definition registered for the AX Valve Controller."""
    return quirk_definition(VALVE_MODEL)


@pytest.fixture
def entities(definition):
    """Map unique_id suffix to entity metadata for the valve quirk."""
    return {em.unique_id_suffix: em for em in definition.entity_metadata}


WATER_LEAK = str(IasZone.cluster_id)


@pytest.mark.parametrize(
    ("zone_status", "water_leak", "active_water_leak", "mains_power"),
    [
        # No leak, mains present.
        (IDLE, False, False, True),
        # Leak detected: Alarm_1 and Alarm_2 are both set.
        (
            IDLE | IasZone.ZoneStatus.Alarm_1 | IasZone.ZoneStatus.Alarm_2,
            True,
            True,
            True,
        ),
        # Leak gone, but Alarm_2 stays latched until acknowledged on the device.
        (IDLE | IasZone.ZoneStatus.Alarm_2, True, False, True),
        # Mains lost.
        (IDLE | IasZone.ZoneStatus.AC_mains, False, False, False),
    ],
)
def test_valve_zone_status_converters(
    entities, zone_status, water_leak, active_water_leak, mains_power
):
    """Each binary sensor decodes its own bits out of the shared zone status."""
    assert entities[WATER_LEAK].attribute_converter(zone_status) is water_leak
    active = entities["active_water_leak"]
    assert active.attribute_converter(zone_status) is active_water_leak
    assert entities["mains_power"].attribute_converter(zone_status) is mains_power


@pytest.fixture
def sensor(zigpy_device_from_v2_quirk):
    """Return a quirked AX Water Sensor."""
    return zigpy_device_from_v2_quirk(
        CTM_MANUF_NAME,
        SENSOR_MODEL,
        cluster_ids={
            1: {
                PowerConfiguration.cluster_id: ClusterType.Server,
                IasZone.cluster_id: ClusterType.Server,
            },
        },
    )


@pytest.fixture
def sensor_entities():
    """Map unique_id suffix to entity metadata for the water sensor quirk."""
    definition = quirk_definition(SENSOR_MODEL)
    return {em.unique_id_suffix: em for em in definition.entity_metadata}


@pytest.mark.parametrize(
    ("zone_status", "active_water_leak", "battery_low"),
    [
        # Bit 6 (Trouble) is always set by the sensor.
        (IDLE | IasZone.ZoneStatus.Trouble, False, False),
        (
            IDLE
            | IasZone.ZoneStatus.Trouble
            | IasZone.ZoneStatus.Alarm_1
            | IasZone.ZoneStatus.Alarm_2,
            True,
            False,
        ),
        # Leak gone, alarm not yet acknowledged.
        (IDLE | IasZone.ZoneStatus.Trouble | IasZone.ZoneStatus.Alarm_2, False, False),
        (IDLE | IasZone.ZoneStatus.Trouble | IasZone.ZoneStatus.Battery, False, True),
    ],
)
def test_sensor_zone_status_converters(
    sensor_entities, zone_status, active_water_leak, battery_low
):
    """Each binary sensor decodes its own bit out of the shared zone status."""
    active = sensor_entities["active_water_leak"]
    assert active.attribute_converter(zone_status) is active_water_leak
    assert (
        sensor_entities["battery_low"].attribute_converter(zone_status) is battery_low
    )


@pytest.mark.parametrize(
    ("voltage", "percentage"),
    [(33, 200), (32, 200), (29, 114), (25, 0), (24, 0)],
)
def test_sensor_battery_percentage(sensor, voltage, percentage):
    """The battery percentage is derived from the reported voltage."""
    power = sensor.endpoints[1].power
    power.update_attribute(PowerConfiguration.AttributeDefs.battery_voltage.id, voltage)
    attr = PowerConfiguration.AttributeDefs.battery_percentage_remaining.name
    assert power.get(attr) == percentage
