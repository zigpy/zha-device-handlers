"""Tests for CTM Lyng quirks."""

import pytest
from zha.application import EntityType
from zha.application.platforms.binary_sensor import BinarySensor, IASZone
from zha.application.platforms.binary_sensor.device_class import BinarySensorDeviceClass
from zha.quirks import DEVICE_REGISTRY
from zigpy.profiles import zha
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.security import IasZone

import zhaquirks
from zhaquirks.ctm import CTM_MANUF_NAME

zhaquirks.setup()

VALVE_MODEL = "AX Valve Controller"

# Bits 4 and 5 are always set by the device, so every zone status builds on them.
IDLE = IasZone.ZoneStatus.Supervision_reports | IasZone.ZoneStatus.Restore_reports


@pytest.fixture
def valve(zigpy_device_from_v2_quirk):
    """Return a quirked AX Valve Controller."""
    return zigpy_device_from_v2_quirk(
        CTM_MANUF_NAME,
        VALVE_MODEL,
        endpoint_ids=[1, 2],
        cluster_ids={
            1: {OnOff.cluster_id: ClusterType.Server},
            2: {IasZone.cluster_id: ClusterType.Server},
        },
    )


@pytest.fixture
def definition():
    """Return the quirk definition registered for the AX Valve Controller."""
    for entry in DEVICE_REGISTRY:
        if any(
            model_info.manufacturer == CTM_MANUF_NAME
            and model_info.model == VALVE_MODEL
            for model_info in entry.device_match.applies_to
        ):
            return entry.zha_device_factory.quirk_definition
    pytest.fail(f"no v2 quirk registered for {CTM_MANUF_NAME} {VALVE_MODEL}")


@pytest.fixture
def entities(definition):
    """Map unique_id suffix to entity metadata for the valve quirk."""
    return {em.unique_id_suffix: em for em in definition.entity_metadata}


def test_valve_endpoint_device_type_replaced(valve):
    """The valve endpoint reports device type 0xffff, which the quirk replaces.

    ``ON_OFF_OUTPUT`` is deliberate: it is not one of the device types that make
    ZHA fall back to the legacy ``{ieee}-{endpoint_id}`` unique id, so the switch
    entity keeps its ``{ieee}-1-6`` unique id.
    """
    assert valve.endpoints[1].profile_id == zha.PROFILE_ID
    assert valve.endpoints[1].device_type == zha.DeviceType.ON_OFF_OUTPUT


def test_valve_zone_status_entities(entities):
    """The quirk splits the IAS zone status into three binary sensors."""
    assert set(entities) == {"water_leak", "valve_alarm", "mains_power"}

    for em in entities.values():
        assert em.endpoint_id == 2
        assert em.cluster_id == IasZone.cluster_id
        assert em.attribute_name == IasZone.AttributeDefs.zone_status.name

    assert entities["water_leak"].device_class == BinarySensorDeviceClass.MOISTURE
    assert entities["water_leak"].entity_type == EntityType.STANDARD

    valve_alarm = entities["valve_alarm"]
    assert valve_alarm.device_class == BinarySensorDeviceClass.PROBLEM
    assert valve_alarm.entity_type == EntityType.STANDARD

    assert entities["mains_power"].device_class == BinarySensorDeviceClass.POWER
    assert entities["mains_power"].entity_type == EntityType.DIAGNOSTIC


@pytest.mark.parametrize(
    ("zone_status", "water_leak", "valve_alarm", "mains_power"),
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
        (IDLE | IasZone.ZoneStatus.Alarm_2, False, True, True),
        # Mains lost.
        (IDLE | IasZone.ZoneStatus.AC_mains, False, False, False),
    ],
)
def test_valve_zone_status_converters(
    entities, zone_status, water_leak, valve_alarm, mains_power
):
    """Each binary sensor decodes its own bit out of the shared zone status.

    ``Alarm_2`` latching is the reason the leak and alarm bits are split: ZHA's
    default IAS zone entity reports ``Alarm_1 | Alarm_2``, so it stays on after
    the water is gone until someone presses the button on the device.
    """
    assert entities["water_leak"].attribute_converter(zone_status) is water_leak
    assert entities["valve_alarm"].attribute_converter(zone_status) is valve_alarm
    assert entities["mains_power"].attribute_converter(zone_status) is mains_power


def test_valve_default_ias_zone_entity_removed(definition):
    """The redundant default IAS zone entity is removed.

    The rule matches on endpoint and cluster, which also covers the quirk's own
    entities, so the filter has to discriminate on the entity class itself.
    """
    (rule,) = definition.disabled_default_entities
    assert rule.endpoint_id == 2
    assert rule.cluster_id == IasZone.cluster_id

    assert rule.function(object.__new__(IASZone))
    assert not rule.function(object.__new__(BinarySensor))
