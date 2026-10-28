"""Tests for the SONOFF MINI-ZB1GP device."""

import asyncio
from dataclasses import replace
from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
import zigpy.types as t
from zigpy.zcl import (
    AttributeReadEvent,
    AttributeReportedEvent,
    AttributeUpdatedEvent,
    AttributeWrittenEvent,
    ClusterType,
    foundation,
)
from zigpy.zcl.clusters.general import KeepAlive, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks
from zhaquirks.sonoff.mini_zb1gp import (
    EXTERNAL_SWITCH,
    EXTERNAL_TRIGGER_AUTOMATION_MAP,
    EXTERNAL_TRIGGER_EVENT_MAP,
    SonoffExternalSwitchTriggerType,
    SonoffExternalTriggerEvent,
    SonoffMiniZb1gpCluster,
    SonoffProtectionConfigCluster,
    SonoffProtectionState,
    _write_succeeded,
    centi_to_value,
    decode_protection_state,
    encode_protection_modify_array,
    fast_scene_payload,
    metering_communication_error,
    milli_to_value,
    overheat_protection,
    overload_protection,
    signed_int32_milli_to_value,
)

zhaquirks.setup()


REAL_FAST_SCENE_PAYLOAD = bytes.fromhex(
    "01 01 01 "
    "01 05 01 00 00 03 28 "
    "02 14 01 80 3e 00 00 00 98 3a 00 00 08 3a 04 80 88 84 02 80 00 00 "
    "03 12 01 00 14 00 00 00 40 7e 05 00 00 00 00 00 40 7e 05 00 "
    "04 06 01 00 80 51 01 00 "
    "00 00 00"
)

REAL_PROTECTION_STATE = SonoffProtectionState(
    scene_switch=1,
    over_current_ma=16000,
    overload_mw=3840000,
    external_switch_only_recovery=False,
    over_voltage_mv=277000,
    over_voltage_enabled=True,
    under_voltage_mv=165000,
    under_voltage_enabled=True,
    auto_recovery=False,
    notification=False,
)


def test_mini_zb1gp_cluster_replaced(zigpy_device_from_v2_quirk):
    """Test shared cluster changes for both models."""

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
        assert isinstance(
            device.endpoints[1].out_clusters[KeepAlive.cluster_id], KeepAlive
        )
        assert KeepAlive.aps_encryption is True


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
    assert all(
        metadata.attribute_name != "detach_relay"
        for metadata in gp_definition.entity_metadata
    )
    trigger_metadata = next(
        metadata
        for metadata in gsp_definition.entity_metadata
        if metadata.attribute_name == "external_trigger_mode"
    )
    assert trigger_metadata.enum is SonoffExternalSwitchTriggerType
    detach_relay_metadata = next(
        metadata
        for metadata in gsp_definition.entity_metadata
        if metadata.attribute_name == "detach_relay"
    )
    assert detach_relay_metadata.entity_type.value == "config"
    assert detach_relay_metadata.off_value == 0
    assert detach_relay_metadata.on_value == 1


def test_mini_zb1gp_attribute_definitions():
    """Test Sonoff manufacturer-specific attribute definitions."""

    assert SonoffMiniZb1gpCluster.AttributeDefs.current.id == 0x7004
    assert SonoffMiniZb1gpCluster.AttributeDefs.voltage.id == 0x7005
    assert SonoffMiniZb1gpCluster.AttributeDefs.power.id == 0x7006
    assert SonoffMiniZb1gpCluster.AttributeDefs.detach_relay.id == 0x0019
    assert (
        SonoffMiniZb1gpCluster.AttributeDefs.external_trigger_mode.zcl_type
        == foundation.DataTypeId.uint8
    )
    assert SonoffMiniZb1gpCluster.AttributeDefs.external_trigger_event.id == 0x0028
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


def _report_attributes(cluster, values: dict[int, int]) -> None:
    """Send a Report Attributes command to a cluster."""

    reports = [
        foundation.Attribute(
            attrid=attrid,
            value=foundation.TypeValue(
                type=cluster.find_attribute(attrid).type,
                value=value,
            ),
        )
        for attrid, value in values.items()
    ]
    args = foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Report_Attributes
    ].schema(attribute_reports=reports)
    hdr = foundation.ZCLHeader.general(
        tsn=1,
        command_id=foundation.GeneralCommand.Report_Attributes,
        direction=foundation.Direction.Server_to_Client,
    )
    cluster.handle_cluster_general_request(hdr, args)


def test_mini_zb1gp_ignores_all_zero_startup_energy_report(
    zigpy_device_from_v2_quirk,
):
    """Test the known all-zero startup report preserves energy counters."""

    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "MINI-ZB1GP",
        cluster_ids={1: {SonoffMiniZb1gpCluster.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].in_clusters[SonoffMiniZb1gpCluster.cluster_id]

    initial_energy = {
        attribute_id: 1000 + index
        for index, attribute_id in enumerate(cluster.energy_attribute_ids)
    }
    _report_attributes(cluster, initial_energy)
    _report_attributes(
        cluster, {**dict.fromkeys(cluster.energy_attribute_ids, 0), 0x7006: 0}
    )

    for attribute_id, value in initial_energy.items():
        assert cluster.get(attribute_id) == value
    assert cluster.get(cluster.AttributeDefs.power.id) == 0


def test_mini_zb1gp_accepts_valid_zero_energy_reports(zigpy_device_from_v2_quirk):
    """Test midnight, month-boundary, and initial zero reports are accepted."""

    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "MINI-ZB1GP",
        cluster_ids={1: {SonoffMiniZb1gpCluster.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].in_clusters[SonoffMiniZb1gpCluster.cluster_id]
    daily = cluster.AttributeDefs.energy_today.id
    monthly = cluster.AttributeDefs.energy_month.id

    _report_attributes(cluster, {daily: 1000, monthly: 2000})
    _report_attributes(cluster, {daily: 0})
    assert cluster.get(daily) == 0
    assert cluster.get(monthly) == 2000

    _report_attributes(cluster, {daily: 1000, monthly: 2000})
    _report_attributes(cluster, {daily: 0, monthly: 0})
    assert cluster.get(daily) == 0
    assert cluster.get(monthly) == 0

    fresh_device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "MINI-ZB1GP",
        cluster_ids={1: {SonoffMiniZb1gpCluster.cluster_id: ClusterType.Server}},
    )
    fresh_cluster = fresh_device.endpoints[1].in_clusters[
        SonoffMiniZb1gpCluster.cluster_id
    ]
    _report_attributes(fresh_cluster, dict.fromkeys(cluster.energy_attribute_ids, 0))
    for attribute_id in fresh_cluster.energy_attribute_ids:
        assert fresh_cluster.get(attribute_id) == 0


def test_mini_zb1gsp_external_switch_events(zigpy_device_from_v2_quirk):
    """Test MINI-ZB1GSP external switch reports emit automation events."""

    devices = {
        model: zigpy_device_from_v2_quirk(
            "SONOFF",
            model,
            cluster_ids={1: {SonoffMiniZb1gpCluster.cluster_id: ClusterType.Server}},
        )
        for model in ("MINI-ZB1GP", "MINI-ZB1GSP")
    }
    expected_triggers = {
        (trigger, EXTERNAL_SWITCH): {
            "command": command,
            "endpoint_id": 1,
            "cluster_id": SonoffMiniZb1gpCluster.cluster_id,
        }
        for command, trigger in EXTERNAL_TRIGGER_AUTOMATION_MAP.items()
    }

    for trigger, metadata in expected_triggers.items():
        assert devices["MINI-ZB1GSP"].device_automation_triggers[trigger] == metadata
    assert (
        not expected_triggers.keys()
        & getattr(devices["MINI-ZB1GP"], "device_automation_triggers", {}).keys()
    )

    cluster = (
        devices["MINI-ZB1GSP"]
        .endpoints[1]
        .in_clusters[SonoffMiniZb1gpCluster.cluster_id]
    )
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    for value, command in EXTERNAL_TRIGGER_EVENT_MAP.items():
        _report_attributes(
            cluster,
            {cluster.AttributeDefs.external_trigger_event.id: value},
        )
        listener.zha_send_event.assert_called_once_with(command, {"value": int(value)})
        listener.reset_mock()

    _report_attributes(
        cluster,
        {
            cluster.AttributeDefs.external_trigger_event.id: SonoffExternalTriggerEvent(
                0xFF
            )
        },
    )
    listener.zha_send_event.assert_not_called()

    cluster.update_attribute(
        cluster.AttributeDefs.external_trigger_event.id,
        SonoffExternalTriggerEvent.Single_click,
    )
    listener.zha_send_event.assert_not_called()


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


def _read_event(
    cluster: SonoffMiniZb1gpCluster,
    attribute_id: int,
    *,
    value,
    raw_value,
) -> AttributeReadEvent:
    """Build an attribute-read event for direct event-handler tests."""

    return AttributeReadEvent(
        device_ieee=str(cluster.endpoint.device.ieee),
        endpoint_id=cluster.endpoint.endpoint_id,
        cluster_type=ClusterType.Server,
        cluster_id=cluster.cluster_id,
        attribute_name=cluster.find_attribute(attribute_id).name,
        attribute_id=attribute_id,
        manufacturer_code=None,
        raw_value=raw_value,
        value=value,
    )


def _protection_clusters(zigpy_device_from_v2_quirk, model="MINI-ZB1GP"):
    """Create a device and return its real and local protection clusters."""

    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        model,
        cluster_ids={1: {SonoffMiniZb1gpCluster.cluster_id: ClusterType.Server}},
    )
    return (
        device.endpoints[1].in_clusters[SonoffMiniZb1gpCluster.cluster_id],
        device.endpoints[1].in_clusters[SonoffProtectionConfigCluster.cluster_id],
    )


def _success_write_result():
    """Return a successful Zigpy write response."""

    return [[foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]]


def test_mini_zb1gp_decodes_captured_protection_payload():
    """Test decoding the protection TLV from a captured composite value."""

    value = _fast_scene_array(list(REAL_FAST_SCENE_PAYLOAD))

    assert decode_protection_state(value) == REAL_PROTECTION_STATE

    serialized = bytes(
        [foundation.DataTypeId.uint8, len(value.value), 0, *bytes(value.value)]
    )
    assert decode_protection_state(serialized) == REAL_PROTECTION_STATE


def test_mini_zb1gp_encodes_exact_protection_modify_packet():
    """Test encoding emits only the type-2 TLV with voltage enable bits."""

    encoded = encode_protection_modify_array(REAL_PROTECTION_STATE)

    assert fast_scene_payload(encoded) == bytes.fromhex(
        "00 01 01 02 14 01 80 3e 00 00 00 98 3a 00 00 08 3a 04 80 88 84 02 80 00 00"
    )
    assert decode_protection_state(encoded) == REAL_PROTECTION_STATE


def test_mini_zb1gp_protection_decoder_rejects_invalid_payloads():
    """Test malformed or incomplete protection payloads remain unavailable."""

    invalid_values = (
        None,
        foundation.Array(type=foundation.DataTypeId.uint8, value=None),
        b"\x01\x01",
        b"\x01\x01\x01\x02\x14\x00",
        b"\x01\x01\x01\x02\x13" + bytes(19),
        b"\x01\x01\x01\x01\x01\x00",
    )

    for value in invalid_values:
        assert decode_protection_state(value) is None


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
    read.assert_awaited_once_with([attribute.id], allow_cache=False)

    raw_value = _fast_scene_array(list(payload))
    event = _read_event(cluster, attribute.id, value=None, raw_value=raw_value)
    with mock.patch.object(cluster, "_update_attribute") as update:
        cluster._handle_protection_change(event)
    update.assert_called_once_with(attribute.id, payload)

    event = _read_event(cluster, 0x0001, value=None, raw_value=payload)
    with mock.patch.object(cluster, "_update_attribute") as update:
        cluster._handle_protection_change(event)
    update.assert_not_called()

    event = _read_event(cluster, attribute.id, value=payload, raw_value=None)
    with mock.patch.object(cluster, "_update_attribute") as update:
        cluster._handle_protection_change(event)
    update.assert_not_called()

    event = _read_event(cluster, attribute.id, value=None, raw_value=None)
    with mock.patch.object(cluster, "_update_attribute") as update:
        cluster._handle_protection_change(event)
    update.assert_not_called()


async def test_mini_zb1gp_setup_falls_back_to_valid_cached_protection_state(
    zigpy_device_from_v2_quirk,
):
    """Test setup initializes controls from cache when the device read fails."""

    cluster, local_cluster = _protection_clusters(zigpy_device_from_v2_quirk)
    attribute = cluster.AttributeDefs.protection_configuration
    cluster._attr_cache[attribute.id] = REAL_FAST_SCENE_PAYLOAD

    with mock.patch.object(
        cluster,
        "read_attributes",
        mock.AsyncMock(side_effect=RuntimeError),
    ) as read:
        await cluster.apply_custom_configuration()

    read.assert_awaited_once_with([attribute.id], allow_cache=False)
    assert cluster._protection_state == REAL_PROTECTION_STATE
    assert local_cluster._protection_state == REAL_PROTECTION_STATE
    assert (
        local_cluster.get(local_cluster.AttributeDefs.protection_over_current.id)
        == 16000
    )


def test_mini_zb1gp_local_values_lazily_initialize_from_parent_cache(
    zigpy_device_from_v2_quirk,
):
    """Test entity reads recover state restored after custom configuration."""

    cluster, local_cluster = _protection_clusters(zigpy_device_from_v2_quirk)
    attribute = cluster.AttributeDefs.protection_configuration
    cluster._attr_cache[attribute.id] = REAL_FAST_SCENE_PAYLOAD

    assert (
        local_cluster.get(local_cluster.AttributeDefs.protection_over_current.id)
        == 16000
    )
    assert cluster._protection_state == REAL_PROTECTION_STATE
    assert local_cluster._protection_state == REAL_PROTECTION_STATE
    assert (
        local_cluster.get(
            local_cluster.AttributeDefs.protection_over_voltage_enabled.id
        )
        is True
    )


def test_mini_zb1gp_synchronizes_protection_attribute_events(
    zigpy_device_from_v2_quirk,
):
    """Test protection read, report, update, and successful write events sync locally."""

    cluster, local_cluster = _protection_clusters(zigpy_device_from_v2_quirk)
    attribute = cluster.AttributeDefs.protection_configuration
    common = {
        "device_ieee": str(cluster.endpoint.device.ieee),
        "endpoint_id": cluster.endpoint.endpoint_id,
        "cluster_type": ClusterType.Server,
        "cluster_id": cluster.cluster_id,
        "attribute_name": attribute.name,
        "attribute_id": attribute.id,
        "manufacturer_code": None,
    }

    states_and_events = (
        (
            replace(REAL_PROTECTION_STATE, over_current_ma=15000),
            lambda value: _read_event(
                cluster, attribute.id, value=value, raw_value=value
            ),
        ),
        (
            replace(REAL_PROTECTION_STATE, over_current_ma=14000),
            lambda value: AttributeReportedEvent(
                **common, raw_value=value, value=value
            ),
        ),
        (
            replace(REAL_PROTECTION_STATE, over_current_ma=13000),
            lambda value: AttributeUpdatedEvent(**common, value=value),
        ),
        (
            replace(REAL_PROTECTION_STATE, over_current_ma=12000),
            lambda value: AttributeWrittenEvent(
                **common, value=value, status=foundation.Status.SUCCESS
            ),
        ),
    )

    for state, event_factory in states_and_events:
        value = encode_protection_modify_array(state)
        cluster._handle_protection_change(event_factory(value))
        assert cluster._protection_state == state
        assert local_cluster._protection_state == state
        assert (
            local_cluster.get(local_cluster.AttributeDefs.protection_over_current.id)
            == state.over_current_ma
        )

    failed_state = replace(REAL_PROTECTION_STATE, over_current_ma=11000)
    cluster._handle_protection_change(
        AttributeWrittenEvent(
            **common,
            value=encode_protection_modify_array(failed_state),
            status=foundation.Status.FAILURE,
        )
    )
    assert cluster._protection_state.over_current_ma == 12000


async def test_mini_zb1gp_writes_fresh_merged_protection_state(
    zigpy_device_from_v2_quirk,
):
    """Test a multi-attribute write preserves fresh unmodified type-2 fields."""

    cluster, local_cluster = _protection_clusters(
        zigpy_device_from_v2_quirk, "MINI-ZB1GSP"
    )
    attribute = cluster.AttributeDefs.protection_configuration
    fresh_value = _fast_scene_array(list(REAL_FAST_SCENE_PAYLOAD))
    success = _success_write_result()

    with (
        mock.patch.object(
            cluster,
            "read_attributes",
            mock.AsyncMock(return_value=({attribute.id: fresh_value}, {})),
        ) as read,
        mock.patch.object(
            cluster, "write_attributes", mock.AsyncMock(return_value=success)
        ) as write,
    ):
        result = await local_cluster.write_attributes(
            {
                local_cluster.AttributeDefs.protection_over_current.id: 15000,
                local_cluster.AttributeDefs.protection_under_voltage.id: 166000,
                local_cluster.AttributeDefs.protection_over_voltage_enabled.id: False,
                local_cluster.AttributeDefs.protection_external_switch_restore.id: True,
                local_cluster.AttributeDefs.protection_auto_recover.id: True,
            }
        )

    assert result is success
    assert read.await_count == 2
    assert all(
        call.args == ([attribute.id],) and call.kwargs == {"allow_cache": False}
        for call in read.await_args_list
    )
    write.assert_awaited_once()
    written = write.await_args.args[0][attribute.id]
    assert fast_scene_payload(written)[:5] == bytes([0, 1, 1, 2, 20])
    assert decode_protection_state(written) == replace(
        REAL_PROTECTION_STATE,
        over_current_ma=15000,
        under_voltage_mv=166000,
        over_voltage_enabled=False,
        external_switch_only_recovery=True,
        auto_recovery=True,
    )
    assert local_cluster._protection_state.scene_switch == 1
    assert local_cluster._protection_state.notification is False


async def test_mini_zb1gp_write_uses_raw_state_from_same_fresh_read(
    zigpy_device_from_v2_quirk,
):
    """Test a malformed decoded array can use its valid raw read event."""

    cluster, local_cluster = _protection_clusters(zigpy_device_from_v2_quirk)
    attribute = cluster.AttributeDefs.protection_configuration
    decoded_value = foundation.Array(type=None, value=None)

    async def read_attributes(*args, **kwargs):
        cluster._handle_protection_change(
            _read_event(
                cluster,
                attribute.id,
                value=decoded_value,
                raw_value=_fast_scene_array(list(REAL_FAST_SCENE_PAYLOAD)),
            )
        )
        return {attribute.id: decoded_value}, {}

    with (
        mock.patch.object(cluster, "read_attributes", side_effect=read_attributes),
        mock.patch.object(
            cluster,
            "write_attributes",
            mock.AsyncMock(return_value=_success_write_result()),
        ) as write,
    ):
        result = await local_cluster.write_attributes(
            {local_cluster.AttributeDefs.protection_over_current.id: 15000}
        )

    assert result[0][0].status == foundation.Status.SUCCESS
    written = write.await_args.args[0][attribute.id]
    assert decode_protection_state(written) == replace(
        REAL_PROTECTION_STATE, over_current_ma=15000
    )


@pytest.mark.parametrize(
    ("attribute_name", "value"),
    (
        ("protection_over_current", 99),
        ("protection_over_current", 16001),
        ("protection_overload", 1999),
        ("protection_overload", 3840001),
        ("protection_over_voltage", 84999),
        ("protection_under_voltage", 277001),
    ),
)
async def test_mini_zb1gp_rejects_out_of_range_protection_values(
    zigpy_device_from_v2_quirk,
    attribute_name,
    value,
):
    """Test raw milli-unit protection values are validated before device reads."""

    cluster, local_cluster = _protection_clusters(zigpy_device_from_v2_quirk)
    with mock.patch.object(cluster, "read_attributes", mock.AsyncMock()) as read:
        result = await local_cluster.write_attributes({attribute_name: value})

    assert result[0][0].status == foundation.Status.INVALID_VALUE
    read.assert_not_awaited()


async def test_mini_zb1gp_rejects_empty_and_invalid_boolean_writes(
    zigpy_device_from_v2_quirk,
):
    """Test empty writes and non-Boolean switch values are rejected locally."""

    cluster, local_cluster = _protection_clusters(zigpy_device_from_v2_quirk)
    with mock.patch.object(cluster, "read_attributes", mock.AsyncMock()) as read:
        assert await local_cluster.write_attributes({}) == [[]]
        result = await local_cluster.write_attributes(
            {local_cluster.AttributeDefs.protection_over_voltage_enabled.id: 2}
        )

    assert result[0][0].status == foundation.Status.INVALID_VALUE
    read.assert_not_awaited()


async def test_mini_zb1gp_rejects_relay_specific_and_notification_writes(
    zigpy_device_from_v2_quirk,
):
    """Test unsupported protection fields remain read-only on each model."""

    _, gp_local_cluster = _protection_clusters(zigpy_device_from_v2_quirk)
    _, gsp_local_cluster = _protection_clusters(
        zigpy_device_from_v2_quirk, "MINI-ZB1GSP"
    )

    for local_cluster, attribute in (
        (
            gp_local_cluster,
            gp_local_cluster.AttributeDefs.protection_external_switch_restore,
        ),
        (gp_local_cluster, gp_local_cluster.AttributeDefs.protection_auto_recover),
        (gsp_local_cluster, gsp_local_cluster.AttributeDefs.protection_notification),
    ):
        result = await local_cluster.write_attributes({attribute.id: True})
        assert result[0][0].status == foundation.Status.READ_ONLY


async def test_mini_zb1gp_requires_a_valid_fresh_protection_read(
    zigpy_device_from_v2_quirk,
):
    """Test an invalid fresh read cannot fall back to a valid cached payload."""

    cluster, local_cluster = _protection_clusters(zigpy_device_from_v2_quirk)
    attribute = cluster.AttributeDefs.protection_configuration
    cluster.update_attribute(
        attribute.id, _fast_scene_array(list(REAL_FAST_SCENE_PAYLOAD))
    )
    invalid = _fast_scene_array([1, 1, 1, 2, 19, *bytes(19)])

    with (
        mock.patch.object(
            cluster,
            "read_attributes",
            mock.AsyncMock(return_value=({attribute.id: invalid}, {})),
        ) as read,
        mock.patch.object(cluster, "write_attributes", mock.AsyncMock()) as write,
    ):
        result = await local_cluster.write_attributes(
            {local_cluster.AttributeDefs.protection_over_current.id: 15000}
        )

    assert result[0][0].status == foundation.Status.FAILURE
    read.assert_awaited_once_with([attribute.id], allow_cache=False)
    write.assert_not_awaited()


async def test_mini_zb1gp_handles_failed_fresh_protection_reads(
    zigpy_device_from_v2_quirk,
):
    """Test exceptions and missing values in fresh reads fail closed."""

    cluster, local_cluster = _protection_clusters(zigpy_device_from_v2_quirk)
    read = mock.AsyncMock(side_effect=(RuntimeError("read failed"), ({}, {})))
    write = mock.AsyncMock()

    with (
        mock.patch.object(cluster, "read_attributes", read),
        mock.patch.object(cluster, "write_attributes", write),
    ):
        for _ in range(2):
            result = await local_cluster.write_attributes(
                {local_cluster.AttributeDefs.protection_over_current.id: 15000}
            )
            assert result[0][0].status == foundation.Status.FAILURE

    assert read.await_count == 2
    write.assert_not_awaited()


@pytest.mark.parametrize("write_raises", (False, True))
async def test_mini_zb1gp_write_failure_does_not_update_local_state(
    zigpy_device_from_v2_quirk,
    write_raises,
):
    """Test failed protection writes do not publish the requested local value."""

    cluster, local_cluster = _protection_clusters(zigpy_device_from_v2_quirk)
    attribute = cluster.AttributeDefs.protection_configuration
    local_cluster.update_protection_state(REAL_PROTECTION_STATE)
    failure = [
        [foundation.WriteAttributesStatusRecord(status=foundation.Status.FAILURE)]
    ]

    async def failed_write(*args, **kwargs):
        if write_raises:
            raise RuntimeError("write failed")
        return failure

    write = mock.AsyncMock(side_effect=failed_write)

    with (
        mock.patch.object(
            cluster,
            "read_attributes",
            mock.AsyncMock(
                return_value=(
                    {attribute.id: _fast_scene_array(list(REAL_FAST_SCENE_PAYLOAD))},
                    {},
                )
            ),
        ),
        mock.patch.object(cluster, "write_attributes", write),
    ):
        result = await local_cluster.write_attributes(
            {local_cluster.AttributeDefs.protection_over_current.id: 15000}
        )

    assert result[0][0].status == foundation.Status.FAILURE
    assert local_cluster._protection_state == REAL_PROTECTION_STATE
    assert (
        local_cluster.get(local_cluster.AttributeDefs.protection_over_current.id)
        == 16000
    )


@pytest.mark.parametrize("result", (None, []))
def test_mini_zb1gp_rejects_malformed_write_results(result):
    """Test malformed Zigpy write responses are not treated as successful."""

    assert _write_succeeded(result) is False


async def test_mini_zb1gp_serializes_concurrent_protection_writes(
    zigpy_device_from_v2_quirk,
):
    """Test concurrent writes each merge into the latest device state."""

    cluster, local_cluster = _protection_clusters(zigpy_device_from_v2_quirk)
    attribute = cluster.AttributeDefs.protection_configuration
    device_state = REAL_PROTECTION_STATE
    first_read_started = asyncio.Event()
    release_first_read = asyncio.Event()
    read_calls = 0

    async def read_attributes(*args, **kwargs):
        nonlocal read_calls
        read_calls += 1
        if read_calls == 1:
            first_read_started.set()
            await release_first_read.wait()
        return {attribute.id: encode_protection_modify_array(device_state)}, {}

    async def write_attributes(attributes, **kwargs):
        nonlocal device_state
        device_state = decode_protection_state(attributes[attribute.id])
        return _success_write_result()

    with (
        mock.patch.object(cluster, "read_attributes", side_effect=read_attributes),
        mock.patch.object(cluster, "write_attributes", side_effect=write_attributes),
    ):
        first_write = asyncio.create_task(
            local_cluster.write_attributes(
                {local_cluster.AttributeDefs.protection_over_current.id: 15000}
            )
        )
        await first_read_started.wait()
        second_write = asyncio.create_task(
            local_cluster.write_attributes(
                {local_cluster.AttributeDefs.protection_under_voltage.id: 166000}
            )
        )
        await asyncio.sleep(0)
        assert read_calls == 1
        release_first_read.set()
        await asyncio.gather(first_write, second_write)

    assert read_calls == 4
    assert device_state == replace(
        REAL_PROTECTION_STATE,
        over_current_ma=15000,
        under_voltage_mv=166000,
    )


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

    metadata_by_model = {}
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
        entry = DEVICE_REGISTRY.match_entry(device)
        metadata_by_model[model] = {
            metadata.fallback_name: metadata
            for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
        }
        assert isinstance(
            device.endpoints[1].in_clusters[SonoffProtectionConfigCluster.cluster_id],
            SonoffProtectionConfigCluster,
        )

    gp_metadata = metadata_by_model["MINI-ZB1GP"]
    gsp_metadata = metadata_by_model["MINI-ZB1GSP"]

    for metadata_by_name in metadata_by_model.values():
        assert all(
            metadata.translation_key is not None and metadata.fallback_name is not None
            for metadata in metadata_by_name.values()
        )
        for name in (
            "Export energy today",
            "Export energy this month",
            "Total export energy",
            "Daily run time",
            "Total run time",
            "Voltage frequency",
        ):
            assert metadata_by_name[name].initially_disabled is True

        expected_numbers = {
            "Protection over-current threshold": ("A", 0.1, 16.0),
            "Protection overload threshold": ("W", 2.0, 3840.0),
            "Protection over-voltage threshold": ("V", 85.0, 277.0),
            "Protection under-voltage threshold": ("V", 85.0, 277.0),
        }
        for name, (unit, minimum, maximum) in expected_numbers.items():
            metadata = metadata_by_name[name]
            assert metadata.entity_platform.value == "number"
            assert metadata.entity_type.value == "config"
            assert metadata.cluster_id == SonoffProtectionConfigCluster.cluster_id
            assert metadata.unit == unit
            assert metadata.min == minimum
            assert metadata.max == maximum
            assert metadata.step == 0.001
            assert metadata.multiplier == 0.001
            assert metadata.initially_disabled is not True

        for name in (
            "Over-voltage protection enabled",
            "Under-voltage protection enabled",
        ):
            metadata = metadata_by_name[name]
            assert metadata.entity_platform.value == "switch"
            assert metadata.entity_type.value == "config"
            assert metadata.initially_disabled is not True

        notification = metadata_by_name["Protection notification"]
        assert notification.entity_platform.value == "binary_sensor"
        assert notification.entity_type.value == "diagnostic"
        assert notification.initially_disabled is True

        assert all(
            metadata.attribute_name != "protection_configuration"
            for metadata in metadata_by_name.values()
        )

    for name in (
        "Protection external switch restore",
        "Protection auto recover",
    ):
        assert gp_metadata[name].entity_platform.value == "binary_sensor"
        assert gp_metadata[name].entity_type.value == "diagnostic"
        assert gp_metadata[name].initially_disabled is True
        assert gsp_metadata[name].entity_platform.value == "switch"
        assert gsp_metadata[name].entity_type.value == "config"
        assert gsp_metadata[name].initially_disabled is not True

    assert (
        gp_metadata["Metering communication error"].resolved_unique_id_suffix
        == "metering_communication_error"
    )
    assert (
        gp_metadata["Overload protection error"].resolved_unique_id_suffix
        == "overload_protection"
    )
    assert (
        gp_metadata["Overheat protection error"].resolved_unique_id_suffix
        == "overheat_protection"
    )
    assert gp_metadata["Overheat protection error"].entity_type.value == "diagnostic"
