"""Tests for Rti-Tek quirks."""

from unittest.mock import AsyncMock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.hvac import Thermostat

import zhaquirks
from zhaquirks.rti_tek.etrv_zb02 import (
    ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS,
    ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS,
    RtiTekEtrvZb02PrivateCluster,
    RtiTekEtrvZb02Thermostat,
)

zhaquirks.setup()


@pytest.mark.parametrize(
    ("attribute_name", "attribute_id", "type_name", "access"),
    [
        ("child_lock", 0x0001, "Bool", 0x0B),
        ("fault_code", 0x0002, "bitmap32", 0x09),
        ("product_name", 0x0003, "CharacterString", 0x01),
        ("screen_direction", 0x0008, "uint8_t", 0x0B),
        ("screen_display_duration", 0x0009, "uint16_t", 0x0B),
        ("screen_brightness", 0x000A, "uint8_t", 0x0B),
        ("open_window_detection", 0x1000, "Bool", 0x0B),
        ("window_state", 0x1001, "uint8_t", 0x09),
        ("valve_opening", 0x1002, "uint16_t", 0x09),
        ("temperature_control_mode", 0x1004, "EtrvZb02TemperatureControlMode", 0x0B),
        ("valve_switching_difference", 0x1005, "int16s", 0x0B),
        ("frost_protection_enabled", 0x1007, "Bool", 0x0B),
        ("frost_temperature", 0x100A, "int16s", 0x0B),
        ("low_battery_valve_state", 0x1013, "uint8_t", 0x0B),
        ("motor_travel_calibration", 0x1016, "Bool", 0x02),
        ("motor_travel_calibration_status", 0x1017, "uint8_t", 0x09),
        ("holiday_duration", 0x1018, "uint32_t", 0x0B),
        ("boost_duration", 0x1019, "uint32_t", 0x0B),
        ("temporary_manual_mode", 0x101F, "uint8_t", 0x09),
    ],
)
def test_etrv_zb02_private_attribute_definitions(
    attribute_name,
    attribute_id,
    type_name,
    access,
):
    """Each exposed FD22 attribute retains its verified wire contract."""
    attribute = getattr(RtiTekEtrvZb02PrivateCluster.AttributeDefs, attribute_name)

    assert attribute.id == attribute_id
    assert attribute.type.__name__ == type_name
    assert attribute.access.value == access


async def test_etrv_zb02_replaces_private_and_thermostat_clusters(
    zigpy_device_from_v2_quirk,
):
    """The exact Rti-Tek model receives the custom FD22 and Thermostat clusters."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                RtiTekEtrvZb02PrivateCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    assert isinstance(
        device.endpoints[1].in_clusters[Thermostat.cluster_id],
        RtiTekEtrvZb02Thermostat,
    )
    assert isinstance(
        device.endpoints[1].in_clusters[RtiTekEtrvZb02PrivateCluster.cluster_id],
        RtiTekEtrvZb02PrivateCluster,
    )


async def test_etrv_zb02_private_attribute_contract(
    zigpy_device_from_v2_quirk,
):
    """FD22 uses the documented IDs, raw types, and full-report command."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={1: {RtiTekEtrvZb02PrivateCluster.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].rti_tek_etrv_zb02_private

    assert cluster.AttributeDefs.frost_temperature.id == 0x100A
    assert cluster.AttributeDefs.frost_temperature.type.__name__ == "int16s"
    assert cluster.AttributeDefs.boost_duration.id == 0x1019
    assert cluster.AttributeDefs.boost_duration.type.__name__ == "uint32_t"
    assert cluster.ServerCommandDefs.request_all_attributes.id == 0x00


async def test_etrv_zb02_registers_entities_without_a_full_report_button(
    zigpy_device_from_v2_quirk,
):
    """The internal synchronization command is deliberately not user-facing."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                RtiTekEtrvZb02PrivateCluster.cluster_id: ClusterType.Server,
            }
        },
    )
    entry = DEVICE_REGISTRY.match_entry(device)
    assert entry is not None
    attributes = {
        metadata.attribute_name
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
        if hasattr(metadata, "attribute_name")
    }

    assert {
        "child_lock",
        "frost_temperature",
        "boost_duration",
        "holiday_duration",
        "temporary_manual_mode",
        "weekly_schedule_day",
        "weekly_schedule_period_12_temperature",
    } <= attributes
    assert "request_all_attributes" not in attributes


async def test_etrv_zb02_requests_a_full_report_once_for_missing_report_values(
    zigpy_device_from_v2_quirk,
):
    """A missing device-reported value yields one FD22 full-report command."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={1: {RtiTekEtrvZb02PrivateCluster.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].rti_tek_etrv_zb02_private
    cluster.request_all_attributes = AsyncMock()

    assert await cluster.request_reported_attributes_if_needed() is True
    cluster.request_all_attributes.assert_awaited_once_with(expect_reply=False)
    assert await cluster.request_reported_attributes_if_needed() is True
    cluster.request_all_attributes.assert_awaited_once()


async def test_etrv_zb02_allows_retry_when_the_full_report_request_fails(
    zigpy_device_from_v2_quirk,
):
    """A failed send does not consume the initialization cycle's one request."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={1: {RtiTekEtrvZb02PrivateCluster.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].rti_tek_etrv_zb02_private
    cluster.request_all_attributes = AsyncMock(side_effect=RuntimeError("no route"))

    with pytest.raises(RuntimeError, match="no route"):
        await cluster.request_reported_attributes_if_needed()

    cluster.request_all_attributes = AsyncMock()
    assert await cluster.request_reported_attributes_if_needed() is True
    cluster.request_all_attributes.assert_awaited_once_with(expect_reply=False)


async def test_etrv_zb02_builds_a_twelve_transition_heating_schedule(
    zigpy_device_from_v2_quirk,
):
    """Disabled editor rows are padded for the device's 12-transition command."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB02",
        cluster_ids={1: {Thermostat.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].thermostat
    cluster.update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[1], 360)
    cluster.update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[1], 2000)
    cluster.update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_TIME_ATTRS[2], 1320)
    cluster.update_attribute(ETRV_ZB02_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[2], 1800)

    _day, transitions, values = cluster.build_weekly_schedule()

    assert isinstance(cluster, RtiTekEtrvZb02Thermostat)
    assert len(transitions) == 12
    assert transitions[:2] == [(360, 2000), (1320, 1800)]
    assert transitions[-1] == (1320, 1800)
    assert len(values) == 24
