"""Exercise the real pinned quirk loader and Tuya wire codec, without a radio."""

import asyncio
import importlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
import zigpy.device
from zigpy.profiles import zgp, zha
import zigpy.types as t
from zigpy.zcl import foundation

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.builder.discovery import discover_quirks_v2_entities

SAMPLE_IEEE = "00:11:22:33:44:55:66:77"


@pytest.fixture
def smartpad():
    """Create the real quirk on a synthetic-address device with the measured signature."""
    zhaquirks.setup()
    module = importlib.import_module("zhaquirks.tuya.ts0601_smartpad")
    app = MagicMock()
    app.get_sequence.return_value = 42
    app.request = AsyncMock(return_value=(foundation.Status.SUCCESS, ""))
    device = zigpy.device.Device(app, t.EUI64.convert(SAMPLE_IEEE), 0x1234)
    device.manufacturer = "_TZE28C1000000_zpvusbtv"
    device.model = "TS0601"
    endpoint = device.add_endpoint(1)
    endpoint.profile_id = zha.PROFILE_ID
    endpoint.device_type = zha.DeviceType.SMART_PLUG
    for cluster_id in (0, 3, 4, 5, 0xE000, 0xEB00, 0xED00, 0xEF00):
        endpoint.add_input_cluster(cluster_id)
    gp = device.add_endpoint(242)
    gp.profile_id = zgp.PROFILE_ID
    gp.device_type = zgp.DeviceType.PROXY_BASIC
    gp.add_output_cluster(0x21)
    resolved = DEVICE_REGISTRY.resolve(device)
    assert resolved is not device
    return module, device, resolved.endpoints[1].tuya_manufacturer


def test_exact_signature_without_ieee_filter(smartpad):
    """Match the same confirmed signature independently of its IEEE."""
    _, bare, cluster = smartpad
    assert 242 in cluster.endpoint.device.endpoints
    assert set(cluster.endpoint.in_clusters) == set(bare.endpoints[1].in_clusters)

    other = zigpy.device.Device(
        bare.application, t.EUI64.convert("00:11:22:33:44:55:66:78"), 0x5678
    )
    other.manufacturer, other.model = bare.manufacturer, bare.model
    other_ep = other.add_endpoint(1)
    other_ep.profile_id = zha.PROFILE_ID
    other_ep.device_type = zha.DeviceType.SMART_PLUG
    for cluster_id in bare.endpoints[1].in_clusters:
        other_ep.add_input_cluster(cluster_id)
    gp = other.add_endpoint(242)
    gp.profile_id = zgp.PROFILE_ID
    gp.device_type = zgp.DeviceType.PROXY_BASIC
    gp.add_output_cluster(0x21)
    assert DEVICE_REGISTRY.resolve(other) is not other

    # Different manufacturer: no accidental match for related OEM models.
    bare.manufacturer = "_TZE284_zpvusbtv"
    assert DEVICE_REGISTRY.resolve(bare) is bare

    # Same manufacturer and model without EF00: no match.
    no_ef00 = zigpy.device.Device(
        other.application, t.EUI64.convert("00:11:22:33:44:55:66:79"), 0x5679
    )
    no_ef00.manufacturer, no_ef00.model = other.manufacturer, other.model
    no_ef00.add_endpoint(1).add_input_cluster(0x0000)
    assert DEVICE_REGISTRY.resolve(no_ef00) is no_ef00


@pytest.mark.parametrize(
    "manufacturer,model,endpoint_id,input_clusters,output_clusters",
    [
        ("_TZE284_zpvusbtv", "TS0601", 1, [0xEF00], []),
        ("_TZE28C1000000_zpvusbtv", "TS0602", 1, [0xEF00], []),
        ("_TZE28C1000000_zpvusbtv", "TS0601", 2, [0xEF00], []),
        ("_TZE28C1000000_zpvusbtv", "TS0601", 1, [0], [0xEF00]),
        ("_TZE28C1000000_zpvusbtv", "TS0601", 1, [0], []),
    ],
)
def test_reject_incompatible_signatures(
    smartpad, manufacturer, model, endpoint_id, input_clusters, output_clusters
):
    """Reject a wrong OEM/model or an MCU on the wrong endpoint/direction."""
    _, bare, _ = smartpad
    device = zigpy.device.Device(
        bare.application, t.EUI64.convert("00:11:22:33:44:55:66:80"), 0x5680
    )
    device.manufacturer, device.model = manufacturer, model
    endpoint = device.add_endpoint(endpoint_id)
    endpoint.profile_id = zha.PROFILE_ID
    for cluster_id in input_clusters:
        endpoint.add_input_cluster(cluster_id)
    for cluster_id in output_clusters:
        endpoint.add_output_cluster(cluster_id)
    assert DEVICE_REGISTRY.resolve(device) is device


def test_real_entity_unique_ids_survive_neutral_naming(smartpad):
    """Exercise ZHA entity construction, not just builder metadata."""
    _, bare, cluster = smartpad
    entry = DEVICE_REGISTRY.match_entry(bare)
    facade = entry.zha_device_factory(cluster.endpoint.device, MagicMock())
    entities = list(discover_quirks_v2_entities(facade))
    expected = {
        ("switch", "relay_1"),
        ("switch", "relay_2"),
        ("switch", "dp16_raw"),
        ("number", "dp102_raw"),
        ("select", "led_on_color"),
        ("select", "led_off_color"),
        ("sensor", "dp15_raw"),
        ("button", "query_data"),
    }
    assert {(entity.PLATFORM.value, entity.unique_id) for entity in entities} == {
        (platform, f"{SAMPLE_IEEE}-1-{suffix}") for platform, suffix in expected
    }
    assert len(entities) == 8
    # Merely loading/discovering entities must not write values to the device.
    bare.application.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_reports_are_isolated_between_matching_devices(smartpad):
    """Different matching units must never share a relay state/cache."""
    _, bare, first = smartpad
    second_bare = zigpy.device.Device(
        bare.application, t.EUI64.convert("00:11:22:33:44:55:66:81"), 0x5681
    )
    second_bare.manufacturer, second_bare.model = bare.manufacturer, bare.model
    for ep_id, original in bare.endpoints.items():
        if ep_id == 0:
            continue
        endpoint = second_bare.add_endpoint(ep_id)
        endpoint.profile_id, endpoint.device_type = (
            original.profile_id,
            original.device_type,
        )
        for cluster_id in original.in_clusters:
            endpoint.add_input_cluster(cluster_id)
        for cluster_id in original.out_clusters:
            endpoint.add_output_cluster(cluster_id)
    second = DEVICE_REGISTRY.resolve(second_bare).endpoints[1].tuya_manufacturer
    for cluster, frame in [
        (first, "09 96 02 00 d4 01 01 00 01 01"),
        (second, "09 98 02 00 da 02 01 00 01 01"),
    ]:
        header, args = cluster.deserialize(bytes.fromhex(frame))
        cluster.handle_message(header, args)
    assert (first.get("relay_1"), first.get("relay_2")) == (1, None)
    assert (second.get("relay_1"), second.get("relay_2")) == (None, 1)
    await asyncio.sleep(0)


def test_original_attribute_ids_and_types(smartpad):
    """Keep the released DP schema and IDs even when display names change."""
    module, _, cluster = smartpad
    expected = {
        "relay_1": (0xEF01, t.Bool),
        "relay_2": (0xEF02, t.Bool),
        "dp102_raw": (0xEF66, t.uint32_t),
        "dp15_raw": (0xEF0F, t.uint8_t),
        "dp16_raw": (0xEF10, t.Bool),
        "led_on_color": (0xEF67, module.LedColor),
        "led_off_color": (0xEF68, module.LedColor),
    }
    assert {
        name: (
            cluster.attributes_by_name[name].id,
            cluster.attributes_by_name[name].type,
        )
        for name in expected
    } == expected
    assert not (
        cluster.attributes_by_name["dp15_raw"].access
        & foundation.ZCLAttributeAccess.Write
    )


@pytest.mark.parametrize(
    "frame,attribute,value",
    [
        ("09 96 02 00 d4 01 01 00 01 01", "relay_1", 1),
        ("09 97 02 00 d7 01 01 00 01 00", "relay_1", 0),
        ("09 98 02 00 da 02 01 00 01 01", "relay_2", 1),
        ("09 99 02 00 dd 02 01 00 01 00", "relay_2", 0),
        ("09 88 02 00 49 66 02 00 04 00 00 00 1e", "dp102_raw", 30),
        ("09 8c 02 00 4f 67 04 00 01 01", "led_on_color", 1),
        ("09 8d 02 00 50 68 04 00 01 03", "led_off_color", 3),
        ("09 89 02 00 4c 0f 04 00 01 01", "dp15_raw", 1),
        ("09 8a 02 00 4d 10 01 00 01 01", "dp16_raw", 1),
    ],
)
@pytest.mark.asyncio
async def test_real_reports(smartpad, frame, attribute, value):
    """Decode measured Tuya report frames into the corresponding attributes."""
    _, _, cluster = smartpad
    header, args = cluster.deserialize(bytes.fromhex(frame))
    cluster.handle_message(header, args)
    assert cluster.get(attribute) == value
    if attribute == "relay_1":
        assert cluster.get("relay_2") is None
    if attribute == "relay_2":
        assert cluster.get("relay_1") is None
    await asyncio.sleep(0)


@pytest.mark.parametrize(
    "attribute,value,dp,wire_type",
    [
        ("relay_1", 1, 1, 1),
        ("relay_1", 0, 1, 1),
        ("relay_2", 1, 2, 1),
        ("relay_2", 0, 2, 1),
        ("led_on_color", 2, 103, 4),
        ("led_off_color", 8, 104, 4),
        ("dp102_raw", 0, 102, 2),
        ("dp102_raw", 30, 102, 2),
        ("dp102_raw", 100, 102, 2),
        ("dp16_raw", 0, 16, 1),
        ("dp16_raw", 1, 16, 1),
    ],
)
@pytest.mark.asyncio
async def test_outbound_dp_codec(smartpad, attribute, value, dp, wire_type):
    """Serialize each writable datapoint with its original Tuya wire type."""
    _, _, cluster = smartpad
    cluster.endpoint.request = AsyncMock(return_value=foundation.Status.SUCCESS)
    result = await cluster.write_attributes({attribute: value})
    assert result[0][0].status == foundation.Status.SUCCESS
    await asyncio.sleep(0)
    request = cluster.endpoint.request.call_args.kwargs
    # Endpoint request receives a serialized ZCL frame: set_data, status, tsn, DP.
    data = request["data"]
    header, payload = foundation.ZCLHeader.deserialize(data)
    assert header.command_id == 0
    length = 4 if wire_type == 2 else 1
    assert payload == bytes([0, 42, dp, wire_type, 0, length]) + value.to_bytes(
        length, "big"
    )


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("dp102_raw", 101),
        ("dp102_raw", 255),
        ("dp15_raw", 0),
        ("dp16_raw", 2),
        ("led_on_color", 9),
        ("led_off_color", 255),
    ],
)
@pytest.mark.asyncio
async def test_unverified_or_invalid_writes_blocked(smartpad, attribute, value):
    """Reject diagnostic or out-of-range writes without sending a command."""
    _, _, cluster = smartpad
    cluster.command = AsyncMock()
    result = await cluster.write_attributes({attribute: value})
    assert result[0][0].status == foundation.Status.INVALID_VALUE
    await asyncio.sleep(0)
    cluster.command.assert_not_awaited()


def test_entity_contract(smartpad):
    """Preserve the released entity schema and neutral channel display names."""
    _, bare, _ = smartpad
    definition = DEVICE_REGISTRY.match_entry(bare).zha_device_factory.quirk_definition
    metadata = definition.entity_metadata
    switches = [m for m in metadata if m.entity_platform.value == "switch"]
    assert {m.attribute_name for m in switches} == {"relay_1", "relay_2", "dp16_raw"}
    relay_names = {
        m.attribute_name: m.fallback_name
        for m in switches
        if m.attribute_name in ("relay_1", "relay_2")
    }
    assert relay_names == {"relay_1": "Channel 1", "relay_2": "Channel 2"}
    assert all(
        "kitchen" not in name.lower() and "porch" not in name.lower()
        for name in relay_names.values()
    )
    led_switch = next(m for m in switches if m.attribute_name == "dp16_raw")
    assert led_switch.entity_type.value == "config"
    assert led_switch.fallback_name == "LED on/off"
    selects = [m for m in metadata if m.entity_platform.value == "select"]
    assert {m.attribute_name for m in selects} == {"led_on_color", "led_off_color"}
    numbers = [m for m in metadata if m.entity_platform.value == "number"]
    assert len(numbers) == 1
    assert numbers[0].resolved_unique_id_suffix == "dp102_raw"
    assert (
        numbers[0].attribute_name,
        numbers[0].min,
        numbers[0].max,
        numbers[0].step,
        numbers[0].mode,
    ) == ("dp102_raw", 0, 100, 1, "slider")
    sensors = [m for m in metadata if m.entity_platform.value == "sensor"]
    assert {m.attribute_name for m in sensors} == {"dp15_raw"}
    assert sensors[0].entity_type.value == "diagnostic"
    assert sensors[0].fallback_name == "LED mode"
    assert not any(m.entity_platform.value == "binary_sensor" for m in metadata)
    assert len(metadata) == 8
    assert definition.skip_configuration


@pytest.mark.asyncio
async def test_refresh_is_query_without_dp_writes(smartpad):
    """Query datapoints without sending any set-data payload."""
    _, _, cluster = smartpad
    cluster.endpoint.request = AsyncMock(return_value=foundation.Status.SUCCESS)
    await cluster.query_data()
    data = cluster.endpoint.request.call_args.kwargs["data"]
    header, payload = foundation.ZCLHeader.deserialize(data)
    assert header.command_id == 3
    assert payload == b""


@pytest.mark.asyncio
async def test_mixed_write_rejected_before_any_dp_is_sent(smartpad):
    """Reject a mixed request atomically before changing a valid relay."""
    _, _, cluster = smartpad
    cluster.command = AsyncMock()
    result = await cluster.write_attributes({"relay_1": 1, "dp15_raw": 0})
    assert result[0][0].status == foundation.Status.INVALID_VALUE
    await asyncio.sleep(0)
    cluster.command.assert_not_awaited()
    assert cluster.get("relay_1") is None


@pytest.mark.asyncio
async def test_numeric_attribute_ids_do_not_bypass_write_guard(smartpad):
    """Enforce brightness bounds when an attribute is addressed numerically."""
    _, _, cluster = smartpad
    cluster.command = AsyncMock()
    result = await cluster.write_attributes({0xEF66: 101})
    assert result[0][0].status == foundation.Status.INVALID_VALUE
    await asyncio.sleep(0)
    cluster.command.assert_not_awaited()


async def test_diagnostics_create_all_smartpad_entities():
    """Join the measured, explicitly anonymized device through a fake ZHA gateway."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "smartpad-ts0601-0x00000063.json", DEVICE_REGISTRY
        )
        expected = {
            (Platform.SWITCH, "relay_1"),
            (Platform.SWITCH, "relay_2"),
            (Platform.SWITCH, "dp16_raw"),
            (Platform.NUMBER, "dp102_raw"),
            (Platform.SELECT, "led_on_color"),
            (Platform.SELECT, "led_off_color"),
            (Platform.SENSOR, "dp15_raw"),
            (Platform.BUTTON, "query_data"),
        }
        assert {
            (platform, f"{SAMPLE_IEEE}-1-{suffix}") for platform, suffix in expected
        }.issubset(device.platform_entities)
        # Replay measured device reports after joining; a diagnostic cache is
        # not evidence of a fresh report from hardware.
        cluster = device.device.endpoints[1].tuya_manufacturer
        for frame in (
            "09 88 02 00 49 66 02 00 04 00 00 00 1e",
            "09 8a 02 00 4d 10 01 00 01 01",
        ):
            header, args = cluster.deserialize(bytes.fromhex(frame))
            cluster.handle_message(header, args)
        await gateway.async_block_till_done()
        assert (
            device.get_platform_entity(
                Platform.NUMBER, unique_id=f"{SAMPLE_IEEE}-1-dp102_raw"
            ).native_value
            == 30
        )
        assert device.get_platform_entity(
            Platform.SWITCH, unique_id=f"{SAMPLE_IEEE}-1-dp16_raw"
        ).is_on
