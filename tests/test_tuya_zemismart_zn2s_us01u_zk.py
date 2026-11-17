"""Exact-fingerprint, real Tuya serialization and entity metadata regression tests.

The anonymous signature and DP tuples below are transcribed from the company's
2026-09-28 rzdkn5rx-before.json and dp-reports-before.json diagnostics. A synthetic
IEEE replaces the live identifier. Only the outgoing radio boundary is mocked;
these tests do not establish live runtime selection or physical relay behaviour.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TypedDict
from unittest.mock import AsyncMock

import pytest
from zha.application import EntityPlatform, EntityType
from zha.application.platforms.number import NumberConfigurationEntity
from zha.application.platforms.select import ZCLEnumSelectEntity
from zha.application.platforms.switch import ConfigurableAttributeSwitch
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation

from tests.common import wait_for_zigpy_tasks
from zhaquirks.tuya import zemismart_zn2s_us01u_zk as quirk


class ObservedEndpoint(TypedDict):
    """Anonymous endpoint fields exported by the real HA diagnostics."""

    profile_id: int
    device_type: int
    input_clusters: list[int]
    output_clusters: list[int]


LIVE_ENDPOINTS: dict[int, ObservedEndpoint] = {
    1: {
        "profile_id": 0x0104,
        "device_type": 0x0051,
        "input_clusters": [0x0004, 0x0005, 0xEF00, 0x0000, 0xED00],
        "output_clusters": [0x0019, 0x000A],
    },
    242: {
        "profile_id": 0xA1E0,
        "device_type": 0x0061,
        "input_clusters": [],
        "output_clusters": [0x0021],
    },
}

# Each tuple is (DP, observed Tuya datatype, exact raw payload, local attribute,
# expected platform value). DP19 is STRING, not an enum despite related devices.
LIVE_REPORTS = [
    (1, 1, "00", "relay_state", False),
    (7, 2, "00000000", "countdown", 0),
    (15, 4, "01", "indicator_mode", quirk.IndicatorMode.on_off_status),
    (16, 1, "01", "backlight", True),
    (19, 3, "", "unknown_dp19", ""),
    (29, 4, "00", "power_on_behavior", quirk.PowerOnBehavior.power_off),
    (101, 1, "00", "child_lock", False),
    (102, 2, "0000001e", "backlight_brightness", 30),
    (103, 4, "01", "indicator_color_off", quirk.IndicatorColor.blue),
    (104, 4, "03", "indicator_color_on", quirk.IndicatorColor.white),
    (209, 0, "", "unknown_dp209", b""),
    (210, 0, "", "unknown_dp210", b""),
]


@pytest.fixture
def make_device(zigpy_device_mock):
    """Build the actual interview using the repository's raw-device fixture."""

    def _make(manufacturer=quirk.MANUFACTURER, model=quirk.MODEL):
        original = zigpy_device_mock()
        original.manufacturer = manufacturer
        original.model = model
        for endpoint_id, observed in LIVE_ENDPOINTS.items():
            endpoint = original.add_endpoint(endpoint_id)
            endpoint.profile_id = observed["profile_id"]
            endpoint.device_type = observed["device_type"]
            for cluster_id in observed["input_clusters"]:
                endpoint.add_input_cluster(cluster_id)
            for cluster_id in observed["output_clusters"]:
                endpoint.add_output_cluster(cluster_id)
        original.endpoints[1].basic._update_attribute(0x0001, 78)
        return original

    return _make


@pytest.fixture
def resolve(make_device):
    """Resolve the actual registry and stub only the radio transport."""

    def _resolve():
        original = make_device()
        assert DEVICE_REGISTRY.match_entry(original) is quirk.QUIRK
        device = DEVICE_REGISTRY.resolve(original)
        device.endpoints[1].request = AsyncMock(
            return_value=foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=0, status=foundation.Status.SUCCESS)
        )
        return device

    return _resolve


def replay_report(device, dp, datatype, payload_hex):
    """Deserialize and handle actual-format commandDataReport bytes."""
    cluster = device.endpoints[1].in_clusters[0xEF00]
    raw = bytes.fromhex(payload_hex)
    # ZCL cluster-specific server-to-client report, Tuya status/sequence,
    # then DP, datatype, function/length (the observed payloads are <256 bytes).
    frame = bytes([0x19, 0x23, 0x02, 0x00, 0x23, dp, datatype, 0, len(raw)]) + raw
    header, parsed = cluster.deserialize(frame)
    cluster.handle_cluster_request(header, parsed)
    return cluster


def native_entities(device):
    """Instantiate ZHA's real switch, select and number entity classes."""
    entities = {}
    for metadata in quirk.QUIRK.zha_device_factory.quirk_definition.entity_metadata:
        kwargs = {
            "endpoint": SimpleNamespace(id=metadata.endpoint_id),
            "device": SimpleNamespace(
                ieee=device.ieee, available=True, primary_entity=None
            ),
            "cluster": device.endpoints[metadata.endpoint_id].in_clusters[
                metadata.cluster_id
            ],
            "from_quirk": True,
            "attribute_name": metadata.attribute_name,
            "entity_type": metadata.entity_type,
            "fallback_name": metadata.fallback_name,
            "translation_key": metadata.translation_key,
            "unique_id_suffix": metadata.unique_id_suffix,
        }
        if metadata.entity_platform is EntityPlatform.SWITCH:
            entity = ConfigurableAttributeSwitch(
                **kwargs,
                force_inverted=metadata.force_inverted,
                off_value=metadata.off_value,
                on_value=metadata.on_value,
            )
        elif metadata.entity_platform is EntityPlatform.SELECT:
            entity = ZCLEnumSelectEntity(**kwargs, enum=metadata.enum)
        else:
            entity = NumberConfigurationEntity(
                **kwargs,
                min_value=metadata.min,
                max_value=metadata.max,
                step=metadata.step,
                unit=metadata.unit,
                multiplier=metadata.multiplier,
            )
        entities[metadata.attribute_name] = entity
    return entities


def test_live_reports_create_all_native_entities(resolve):
    """Generate nine supported native entities and verify their report state."""
    device = resolve()
    for dp, datatype, raw, _, _ in LIVE_REPORTS:
        replay_report(device, dp, datatype, raw)
    entities = native_entities(device)
    assert len(entities) == 9
    assert all(entity._is_supported() for entity in entities.values())
    assert entities["relay_state"].is_on is False
    assert entities["backlight"].is_on is True
    assert entities["child_lock"].is_on is False
    assert entities["countdown"].native_value == 0
    assert entities["backlight_brightness"].native_value == 30
    assert entities["indicator_mode"].current_option == "on off status"
    assert entities["power_on_behavior"].current_option == "power off"
    assert entities["indicator_color_off"].current_option == "blue"
    assert entities["indicator_color_on"].current_option == "white"
    assert not device.endpoints[1].request.called


def test_live_diagnostic_resolves_and_keeps_topology(resolve):
    """Resolve the captured interview and preserve its real endpoint layout."""
    device = resolve()
    assert set(device.endpoints) == {0, 1, 242}
    for endpoint_id, observed in LIVE_ENDPOINTS.items():
        endpoint = device.endpoints[endpoint_id]
        assert endpoint.profile_id == observed["profile_id"]
        assert endpoint.device_type == observed["device_type"]
        assert set(endpoint.in_clusters) == set(observed["input_clusters"])
        assert set(endpoint.out_clusters) == set(observed["output_clusters"])
    assert device.endpoints[1].basic.get(0x0001) == 78
    assert quirk.QUIRK.device_match.applies_to == ((quirk.MANUFACTURER, quirk.MODEL),)


@pytest.mark.parametrize(
    ("manufacturer", "model"),
    [
        ("_TZE28C1000000_rzdkn5rx", "TS0601"),
        ("_TZE284_lnyz4a6v", "TS0601"),
        ("_TZE284_1tnysxwl", "TS0601"),
        ("_TZE204_znvwzxkq", "TS0601"),
        ("_TZE284_rzdkn5rx", "TS0001"),
        (None, "TS0601"),
    ],
)
def test_unrelated_and_old_fingerprints_do_not_match(make_device, manufacturer, model):
    """Reject nearby model prefixes and previously supported screen switches."""
    original = make_device(manufacturer, model)
    assert not quirk.QUIRK.device_match.matches(original)
    assert DEVICE_REGISTRY.match_entry(original) is not quirk.QUIRK


@pytest.mark.parametrize("missing", ["endpoint", "tuya", "profile"])
def test_required_tuya_protocol_is_checked(make_device, missing):
    """Reject devices missing the Tuya protocol endpoint."""
    original = make_device()
    if missing == "endpoint":
        del original.endpoints[1]
    elif missing == "tuya":
        del original.endpoints[1].in_clusters[0xEF00]
    else:
        original.endpoints[1].profile_id = 0xA1E0
    assert not quirk.QUIRK.device_match.matches(original)


@pytest.mark.parametrize(
    ("dp", "datatype", "raw", "attribute", "expected"), LIVE_REPORTS
)
def test_live_report_replay(resolve, dp, datatype, raw, attribute, expected):
    """Replay independently captured report bytes through the real parser."""
    cluster = replay_report(resolve(), dp, datatype, raw)
    assert cluster.get(attribute) == expected


def test_entity_surface_and_unknown_datapoints(resolve):
    """Expose supported controls and keep unknown reports read-only."""
    device = resolve()
    cluster = device.endpoints[1].in_clusters[0xEF00]
    definition = quirk.QUIRK.zha_device_factory.quirk_definition
    assert definition.friendly_name.manufacturer == "Zemismart"
    assert definition.friendly_name.model == "ZN2S-US01U-ZK"
    metadata = {item.attribute_name: item for item in definition.entity_metadata}
    assert set(metadata) == {
        "relay_state",
        "countdown",
        "indicator_mode",
        "backlight",
        "power_on_behavior",
        "child_lock",
        "backlight_brightness",
        "indicator_color_off",
        "indicator_color_on",
    }
    assert metadata["relay_state"].entity_platform is EntityPlatform.SWITCH
    assert metadata["relay_state"].entity_type is EntityType.STANDARD
    assert metadata["countdown"].min == 0
    assert metadata["countdown"].max == 43200
    assert metadata["backlight_brightness"].min == 0
    assert metadata["backlight_brightness"].max == 100
    for dp in (19, 209, 210):
        attribute = cluster.attributes_by_name[f"unknown_dp{dp}"]
        assert not attribute.access & foundation.ZCLAttributeAccess.Write
    assert {14, 105, 111}.isdisjoint(cluster.dp_to_attribute)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("attribute", "value", "dp", "datatype", "payload_hex"),
    [
        ("relay_state", True, 1, 1, "01"),
        ("relay_state", False, 1, 1, "00"),
        ("countdown", 60, 7, 2, "0000003c"),
        ("indicator_mode", quirk.IndicatorMode.switch_position, 15, 4, "02"),
        ("backlight", False, 16, 1, "00"),
        ("power_on_behavior", quirk.PowerOnBehavior.restart_memory, 29, 4, "02"),
        ("child_lock", True, 101, 1, "01"),
        ("backlight_brightness", 50, 102, 2, "00000032"),
        ("indicator_color_off", quirk.IndicatorColor.green, 103, 4, "02"),
        ("indicator_color_on", quirk.IndicatorColor.red, 104, 4, "00"),
    ],
)
async def test_writes_serialize_exact_dp_and_datatype(
    resolve, attribute, value, dp, datatype, payload_hex
):
    """Use native entity actions and serialize the exact Tuya DP and datatype."""
    device = resolve()
    cluster = device.endpoints[1].in_clusters[0xEF00]
    entity = native_entities(device)[attribute]
    if isinstance(entity, ConfigurableAttributeSwitch):
        if value:
            await entity.async_turn_on()
        else:
            await entity.async_turn_off()
    elif isinstance(entity, ZCLEnumSelectEntity):
        await entity.async_select_option(value.name.replace("_", " "))
    else:
        await entity.async_set_native_value(value)
    await wait_for_zigpy_tasks()
    [call] = device.endpoints[1].request.call_args_list
    assert call.kwargs["cluster"] == 0xEF00
    header, payload = foundation.ZCLHeader.deserialize(call.kwargs["data"])
    assert header.command_id == 0x00
    schema = cluster.server_commands[header.command_id].schema
    parsed, remaining = schema.deserialize(payload)
    assert not remaining
    [record] = parsed.data.datapoints
    assert record.dp == dp
    assert record.data.dp_type == datatype
    assert record.data.raw == bytes.fromhex(payload_hex)


def outgoing_datapoints(device):
    """Decode all Tuya values serialized to the mocked radio transport."""
    cluster = device.endpoints[1].in_clusters[0xEF00]
    result = []
    for call in device.endpoints[1].request.call_args_list:
        assert call.kwargs["cluster"] == 0xEF00
        header, payload = foundation.ZCLHeader.deserialize(call.kwargs["data"])
        assert header.command_id == 0
        parsed, remaining = cluster.server_commands[
            header.command_id
        ].schema.deserialize(payload)
        assert not remaining
        result.extend(
            (record.dp, int(record.data.dp_type), bytes(record.data.raw))
            for record in parsed.data.datapoints
        )
    return result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("dp", "datatype", "attribute", "expected"),
    [
        (19, 3, "unknown_dp19", ""),
        (209, 0, "unknown_dp209", b""),
        (210, 0, "unknown_dp210", b""),
    ],
)
@pytest.mark.parametrize("key_kind", ["name", "id", "definition"])
async def test_unknown_dp_writes_are_read_only_without_cache_or_radio_changes(
    resolve, dp, datatype, attribute, expected, key_kind
):
    """Reject advanced writes to unknown STRING/RAW DPs through every key form."""
    device = resolve()
    cluster = replay_report(device, dp, datatype, "")
    definition = cluster.attributes_by_name[attribute]
    key = {"name": attribute, "id": definition.id, "definition": definition}[key_kind]
    # A numeric advanced write previously escaped access=Read and could send a
    # VALUE frame despite the captured STRING/RAW datatype. It must be rejected.
    result = await cluster.write_attributes({key: 7})
    await wait_for_zigpy_tasks()
    assert len(result[0]) == 1
    assert result[0][0].status == foundation.Status.READ_ONLY
    assert result[0][0].attrid == definition.id
    assert cluster.get(attribute) == expected
    assert outgoing_datapoints(device) == []


@pytest.mark.asyncio
async def test_mixed_write_rejects_unknown_dps_and_preserves_supported_writes(resolve):
    """Reject unknown entries while preserving native BOOL and VALUE writes."""
    device = resolve()
    cluster = device.endpoints[1].in_clusters[0xEF00]
    for dp, datatype, raw, _, _ in LIVE_REPORTS:
        replay_report(device, dp, datatype, raw)
    result = await cluster.write_attributes(
        {
            "unknown_dp19": 7,
            "relay_state": True,
            cluster.attributes_by_name["unknown_dp209"].id: 8,
            "backlight_brightness": 35,
            cluster.attributes_by_name["unknown_dp210"]: 9,
        }
    )
    await wait_for_zigpy_tasks()
    assert len(result[0]) == 3
    assert all(record.status == foundation.Status.READ_ONLY for record in result[0])
    assert {record.attrid for record in result[0]} == {0xEF13, 0xEFD1, 0xEFD2}
    assert cluster.get("unknown_dp19") == ""
    assert cluster.get("unknown_dp209") == b""
    assert cluster.get("unknown_dp210") == b""
    assert bool(cluster.get("relay_state")) is True
    assert cluster.get("backlight_brightness") == 35
    assert outgoing_datapoints(device) == [
        (1, 1, b"\x01"),
        (102, 2, b"\x00\x00\x00\x23"),
    ]
