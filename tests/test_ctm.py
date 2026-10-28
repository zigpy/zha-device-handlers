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


def entity_metadata(quirked_device):
    """Map unique_id suffix to the entity metadata of the device's quirk."""
    entry = DEVICE_REGISTRY.match_entry(quirked_device)
    return {
        metadata.resolved_unique_id_suffix: metadata
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    }


@pytest.fixture
def valve(zigpy_device_from_v2_quirk):
    """Return a quirked AX Valve Controller."""
    return zigpy_device_from_v2_quirk(
        CTM_MANUF_NAME,
        VALVE_MODEL,
        cluster_ids={2: {IasZone.cluster_id: ClusterType.Server}},
    )


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
    valve, zone_status, water_leak, active_water_leak, mains_power
):
    """Each binary sensor decodes its own bits out of the shared zone status."""
    entities = entity_metadata(valve)
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
    sensor, zone_status, active_water_leak, battery_low
):
    """Each binary sensor decodes its own bit out of the shared zone status."""
    sensor_entities = entity_metadata(sensor)
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
