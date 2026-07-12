"""Tests for the SONOFF MINI-ZB1GP device."""

from unittest import mock

from zha.quirks import DEVICE_REGISTRY
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks
from zhaquirks.sonoff.mini_zb1gp import (
    SonoffExternalSwitchTriggerType,
    SonoffMiniZb1gpCluster,
    centi_to_value,
    metering_communication_error,
    milli_to_value,
    overheat_protection,
    overload_protection,
    protection_auto_recover,
    protection_external_switch_restore,
    protection_notification,
    protection_over_current,
    protection_over_voltage,
    protection_over_voltage_enabled,
    protection_overload,
    protection_under_voltage,
    protection_under_voltage_enabled,
    signed_int32_milli_to_value,
)

zhaquirks.setup()


def test_mini_zb1gp_cluster_replaced(zigpy_device_from_v2_quirk):
    """Test that the Sonoff manufacturer cluster is replaced for both models."""

    for model in ("MINI-ZB1GP", "MINI-ZB1GSP"):
        device = zigpy_device_from_v2_quirk(
            "SONOFF",
            model,
            cluster_ids={
                1: {
                    OnOff.cluster_id: ClusterType.Server,
                    Metering.cluster_id: ClusterType.Server,
                    ElectricalMeasurement.cluster_id: ClusterType.Server,
                    SonoffMiniZb1gpCluster.cluster_id: ClusterType.Server,
                }
            },
        )

        assert isinstance(
            device.endpoints[1].in_clusters[SonoffMiniZb1gpCluster.cluster_id],
            SonoffMiniZb1gpCluster,
        )


def test_mini_zb1gsp_relay_and_trigger_metadata(zigpy_device_from_v2_quirk):
    """Test model-specific relay suppression and trigger-mode metadata."""

    entries = {}
    for model in ("MINI-ZB1GP", "MINI-ZB1GSP"):
        device = zigpy_device_from_v2_quirk(
            "SONOFF",
            model,
            cluster_ids={
                1: {
                    OnOff.cluster_id: ClusterType.Server,
                    Metering.cluster_id: ClusterType.Server,
                    ElectricalMeasurement.cluster_id: ClusterType.Server,
                    SonoffMiniZb1gpCluster.cluster_id: ClusterType.Server,
                }
            },
        )
        entries[model] = DEVICE_REGISTRY.match_entry(device)

    gp_definition = entries["MINI-ZB1GP"].zha_device_factory.quirk_definition
    gsp_definition = entries["MINI-ZB1GSP"].zha_device_factory.quirk_definition

    assert any(
        metadata.cluster_id == OnOff.cluster_id
        for metadata in gp_definition.disabled_default_entities
    )
    assert all(
        metadata.cluster_id != OnOff.cluster_id
        for metadata in gsp_definition.disabled_default_entities
    )
    assert all(
        metadata.attribute_name != "external_trigger_mode"
        for metadata in gp_definition.entity_metadata
    )
    trigger_metadata = next(
        metadata
        for metadata in gsp_definition.entity_metadata
        if metadata.attribute_name == "external_trigger_mode"
    )
    assert trigger_metadata.enum is SonoffExternalSwitchTriggerType


def test_mini_zb1gp_attribute_definitions():
    """Test Sonoff manufacturer-specific attribute definitions."""

    assert SonoffMiniZb1gpCluster.AttributeDefs.current.id == 0x7004
    assert SonoffMiniZb1gpCluster.AttributeDefs.voltage.id == 0x7005
    assert SonoffMiniZb1gpCluster.AttributeDefs.power.id == 0x7006
    assert SonoffMiniZb1gpCluster.AttributeDefs.energy_today.id == 0x7009
    assert SonoffMiniZb1gpCluster.AttributeDefs.energy_month.id == 0x700A
    assert SonoffMiniZb1gpCluster.AttributeDefs.protection_configuration.id == 0x7016
    assert SonoffMiniZb1gpCluster.AttributeDefs.output_energy_today.id == 0x7018
    assert SonoffMiniZb1gpCluster.AttributeDefs.output_energy_month.id == 0x7019
    assert SonoffMiniZb1gpCluster.AttributeDefs.daily_run_time.id == 0x701C
    assert SonoffMiniZb1gpCluster.AttributeDefs.total_run_time.id == 0x701D
    assert SonoffMiniZb1gpCluster.AttributeDefs.total_energy.id == 0x701E
    assert SonoffMiniZb1gpCluster.AttributeDefs.total_output_energy.id == 0x701F
    assert SonoffMiniZb1gpCluster.AttributeDefs.voltage_frequency.id == 0x7029


def test_mini_zb1gp_milli_value_converters():
    """Test converters for raw Sonoff milli-unit values."""

    assert milli_to_value(483) == 0.483
    assert milli_to_value(238678) == 238.678
    assert signed_int32_milli_to_value(93255) == 93.255
    assert signed_int32_milli_to_value(0xFFFFFC18) == -1.0
    assert centi_to_value(5000) == 50.0


def test_mini_zb1gp_fault_code_converters():
    """Test MINI-ZB1GP fault code bit converters."""

    assert metering_communication_error(0x07020000) is False
    assert overheat_protection(0x07020000) is False
    assert overload_protection(0x07020000) is False
    assert metering_communication_error(0x07020002) is True
    assert overheat_protection(0x07020001) is True
    assert overload_protection(0x07020004) is True
    assert overheat_protection(0x07020005) is True
    assert metering_communication_error(0x00000002) is False


def _fast_scene_array(payload: list[int]) -> foundation.Array:
    """Wrap a fast-scene payload in its ZCL array representation."""

    return foundation.Array(
        type=foundation.DataTypeId.uint8,
        value=t.LVList[t.uint8_t, t.uint16_t](payload),
    )


def test_mini_zb1gp_protection_converters():
    """Test decoding the protection TLV from the composite attribute."""

    over_voltage = 250000 | 0x80000000
    under_voltage = 190000
    protection_data = bytes(
        [1]
        + list((16000).to_bytes(4, "little"))
        + list((3680000).to_bytes(4, "little"))
        + [1]
        + list(over_voltage.to_bytes(4, "little"))
        + list(under_voltage.to_bytes(4, "little"))
        + [1, 0]
    )
    value = _fast_scene_array(
        [1, 1, 1, 0x01, 2, 0xAA, 0xBB, 0x02, 20, *protection_data]
    )

    assert protection_over_current(value) == 16.0
    assert protection_overload(value) == 3680.0
    assert protection_external_switch_restore(value) is True
    assert protection_over_voltage(value) == 250.0
    assert protection_over_voltage_enabled(value) is True
    assert protection_under_voltage(value) == 190.0
    assert protection_under_voltage_enabled(value) is False
    assert protection_auto_recover(value) is True
    assert protection_notification(value) is False

    serialized = bytes(
        [foundation.DataTypeId.uint8, len(value.value), 0, *bytes(value.value)]
    )
    assert protection_over_current(serialized) == 16.0


def test_mini_zb1gp_protection_converters_reject_invalid_payloads():
    """Test malformed or incomplete protection payloads remain unavailable."""

    invalid_values = (
        None,
        b"\x01\x01",
        b"\x01\x01\x01\x02\x14\x00",
        b"\x01\x01\x01\x02\x13" + bytes(19),
        b"\x01\x01\x01\x01\x01\x00",
    )

    for value in invalid_values:
        assert protection_over_current(value) is None
        assert protection_auto_recover(value) is None


async def test_mini_zb1gp_reads_and_caches_raw_protection_configuration(
    zigpy_device_from_v2_quirk,
):
    """Test setup reads 0x7016 and a valid raw result is cached."""

    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "MINI-ZB1GP",
        cluster_ids={1: {SonoffMiniZb1gpCluster.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].in_clusters[SonoffMiniZb1gpCluster.cluster_id]
    attribute = SonoffMiniZb1gpCluster.AttributeDefs.protection_configuration
    payload = bytes([1, 1, 1, 2, 20, 1, *bytes(19)])

    with mock.patch.object(cluster, "read_attributes", mock.AsyncMock()) as read:
        await cluster.apply_custom_configuration()
    read.assert_awaited_once_with([attribute.id])

    event = mock.Mock(attribute_id=attribute.id, value=None, raw_value=payload)
    with mock.patch.object(cluster, "_update_attribute") as update:
        cluster._handle_attribute_read(event)
    update.assert_called_once_with(attribute.id, payload)

    event = mock.Mock(attribute_id=0x0001, value=None, raw_value=payload)
    with mock.patch.object(cluster, "_update_attribute") as update:
        cluster._handle_attribute_read(event)
    update.assert_not_called()

    event = mock.Mock(attribute_id=attribute.id, value=payload, raw_value=None)
    with mock.patch.object(cluster, "_update_attribute") as update:
        cluster._handle_attribute_read(event)
    update.assert_not_called()

    event = mock.Mock(attribute_id=attribute.id, value=None, raw_value=None)
    with mock.patch.object(cluster, "_update_attribute") as update:
        cluster._handle_attribute_read(event)
    update.assert_not_called()


def test_mini_zb1gp_replacement_sensor_unique_id_suffixes(zigpy_device_from_v2_quirk):
    """Test replacement sensors preserve legacy ZHA entity unique ID suffixes."""

    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "MINI-ZB1GP",
        cluster_ids={
            1: {
                OnOff.cluster_id: ClusterType.Server,
                Metering.cluster_id: ClusterType.Server,
                ElectricalMeasurement.cluster_id: ClusterType.Server,
                SonoffMiniZb1gpCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    entry = DEVICE_REGISTRY.match_entry(device)
    suffixes = {
        metadata.fallback_name: metadata.resolved_unique_id_suffix
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    }

    assert suffixes["Power"] == "2820-active_power"
    assert suffixes["Current"] == "2820-rms_current"
    assert suffixes["Voltage"] == "2820-rms_voltage"
    assert suffixes["Total energy"] == "1794-summation_delivered"

    power_metadata = next(
        metadata
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
        if metadata.fallback_name == "Power"
    )
    assert power_metadata.primary is not True


def test_mini_zb1gp_optional_entities(zigpy_device_from_v2_quirk):
    """Test optional measurement, protection, and fault entities."""

    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "MINI-ZB1GP",
        cluster_ids={
            1: {
                OnOff.cluster_id: ClusterType.Server,
                Metering.cluster_id: ClusterType.Server,
                ElectricalMeasurement.cluster_id: ClusterType.Server,
                SonoffMiniZb1gpCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    entry = DEVICE_REGISTRY.match_entry(device)
    metadata_by_name = {
        metadata.fallback_name: metadata
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    }

    assert all(
        metadata.translation_key is not None and metadata.fallback_name is not None
        for metadata in metadata_by_name.values()
    )

    assert metadata_by_name["Export energy today"].initially_disabled is True
    assert metadata_by_name["Export energy this month"].initially_disabled is True
    assert metadata_by_name["Total export energy"].initially_disabled is True
    assert metadata_by_name["Daily run time"].initially_disabled is True
    assert metadata_by_name["Total run time"].initially_disabled is True
    assert metadata_by_name["Voltage frequency"].initially_disabled is True
    assert (
        metadata_by_name["Protection over-current threshold"].initially_disabled is True
    )
    assert (
        metadata_by_name["Protection over-current threshold"].entity_type.value
        == "diagnostic"
    )
    assert metadata_by_name["Protection over-current threshold"].unit == "A"
    assert metadata_by_name["Protection overload threshold"].unit == "W"
    assert metadata_by_name["Protection over-voltage threshold"].unit == "V"
    assert metadata_by_name["Protection under-voltage threshold"].unit == "V"
    protection_metadata = [
        metadata
        for metadata in metadata_by_name.values()
        if metadata.attribute_name == "protection_configuration"
    ]
    assert len(protection_metadata) == 9
    assert all(
        metadata.attribute_initialized_from_cache is False
        for metadata in protection_metadata
    )
    assert all(
        metadata.entity_type.value == "diagnostic" for metadata in protection_metadata
    )
    assert "Protection scene enabled" not in metadata_by_name
    assert (
        metadata_by_name["Metering communication error"].resolved_unique_id_suffix
        == "metering_communication_error"
    )
    assert (
        metadata_by_name["Overload protection error"].resolved_unique_id_suffix
        == "overload_protection"
    )
    assert (
        metadata_by_name["Overheat protection error"].resolved_unique_id_suffix
        == "overheat_protection"
    )
    assert (
        metadata_by_name["Overheat protection error"].entity_type.value == "diagnostic"
    )
