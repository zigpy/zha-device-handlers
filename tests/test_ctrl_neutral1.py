"""Tests for the Aqara wall switches without neutral (lumi.ctrl_neutral*)."""

import json
from pathlib import Path
from unittest import mock

import pytest
from zha.application import Platform
from zha.application.const import ZHA_EVENT
from zha.quirks import DEVICE_REGISTRY
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.const import (
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    COMMAND_ATTRIBUTE_UPDATED,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    VALUE,
)
from zhaquirks.xiaomi import OnOffCluster
from zhaquirks.xiaomi.aqara.ctrl_neutral import WallSwitchOnOffCluster

zhaquirks.setup()

DIAGNOSTICS = "lumi-lumi-ctrl-neutral2-0x00000016.json"

# Endpoints and server clusters both models report (from the device signature)
SIGNATURE = {
    1: [0x0000, 0x0001, 0x0002, 0x0003, 0x000A, 0x0019],
    2: [0x0004, 0x0005, 0x0006, 0x0010],
    3: [0x0004, 0x0005, 0x0006, 0x0010],
    4: [0x0006, 0x0012],
    5: [0x0006, 0x0012],
    6: [0x0006, 0x0012],
    8: [0x000C],
}

# Report_Attributes(on_off=False), then (on_off=True): a press and its release
PRESS = bytes.fromhex("18010a00001000")
RELEASE = bytes.fromhex("18020a00001001")

MODELS = [
    ("lumi.ctrl_neutral1", (2,), (4,)),
    ("lumi.switch.b1lacn02", (2,), (4,)),
    ("lumi.ctrl_neutral2", (2, 3), (4, 5)),
    ("lumi.switch.b2lacn02", (2, 3), (4, 5)),
]


@pytest.fixture
def ctrl_neutral(zigpy_device_from_v2_quirk):
    """Return a quirked switch built from the real device signature."""

    def _dev(model):
        return zigpy_device_from_v2_quirk(
            "LUMI",
            model,
            cluster_ids={
                ep: dict.fromkeys(clusters, ClusterType.Server)
                for ep, clusters in SIGNATURE.items()
            },
        )

    return _dev


def _packet(endpoint_id: int, data: bytes) -> t.ZigbeePacket:
    return t.ZigbeePacket(
        profile_id=zha.PROFILE_ID,
        cluster_id=OnOff.cluster_id,
        src_ep=endpoint_id,
        dst_ep=1,
        data=t.SerializableBytes(data),
    )


def _event(value: int) -> mock._Call:
    return mock.call(
        COMMAND_ATTRIBUTE_UPDATED,
        {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: "on_off", VALUE: value},
    )


@pytest.mark.parametrize(("model", "relays", "buttons"), MODELS)
async def test_ctrl_neutral_endpoints(ctrl_neutral, model, relays, buttons):
    """Relays become switch endpoints, buttons fire events, unused endpoints go."""
    dev = ctrl_neutral(model)

    assert {ep.endpoint_id for ep in dev.non_zdo_endpoints} == {1, *relays, *buttons}

    for ep_id in relays:
        assert dev.endpoints[ep_id].device_type == zha.DeviceType.ON_OFF_SWITCH
        assert isinstance(dev.endpoints[ep_id].on_off, OnOffCluster)

    for ep_id in buttons:
        cluster = dev.endpoints[ep_id].on_off
        assert isinstance(cluster, WallSwitchOnOffCluster)

        listener = mock.MagicMock()
        cluster.add_listener(listener)
        dev.packet_received(_packet(ep_id, PRESS))
        dev.packet_received(_packet(ep_id, RELEASE))
        assert listener.zha_send_event.mock_calls == [_event(0), _event(1)]


@pytest.mark.parametrize(("model", "relays", "buttons"), MODELS)
async def test_ctrl_neutral_relay_command(ctrl_neutral, model, relays, buttons):
    """Relay commands are sent from endpoint 1 to the relay endpoint."""
    dev = ctrl_neutral(model)
    dev.request = mock.MagicMock()

    for ep_id in relays:
        dev.endpoints[ep_id].on_off.command(OnOff.ServerCommandDefs.on.id)

        assert dev.request.call_args[0][:4] == (260, OnOff.cluster_id, 1, ep_id)
        assert dev.request.call_args[0][5][2] == OnOff.ServerCommandDefs.on.id


@pytest.mark.parametrize(
    ("model", "triggers"),
    [
        ("lumi.ctrl_neutral1", {BUTTON: 4}),
        ("lumi.ctrl_neutral2", {BUTTON_1: 4, BUTTON_2: 5}),
    ],
)
def test_ctrl_neutral_device_triggers(ctrl_neutral, model, triggers):
    """Every key keeps its hold, release and double press triggers."""
    dev = ctrl_neutral(model)

    assert dev.device_automation_triggers == {
        (command, button): {
            "endpoint_id": ep_id,
            "cluster_id": OnOff.cluster_id,
            "command": COMMAND_ATTRIBUTE_UPDATED,
            "args": {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: "on_off", VALUE: value},
        }
        for button, ep_id in triggers.items()
        for command, value in (
            (COMMAND_HOLD, 0),
            (COMMAND_RELEASE, 1),
            (COMMAND_DOUBLE, 2),
        )
    }


async def test_ctrl_neutral2_zha_entities_and_events():
    """ZHA creates the device's entities minus the button switches; presses fire."""
    diagnostics = json.loads(
        (Path(__file__).parent / "data" / "devices" / DIAGNOSTICS).read_text()
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, DIAGNOSTICS, DEVICE_REGISTRY
        )

        # The diagnostics were taken with the button switches already hidden. Its
        # older ZHA had no virtual entities yet.
        assert {
            (platform, unique_id)
            for platform, unique_id in device.platform_entities
            if platform != Platform.VIRTUAL
        } == {
            (Platform(platform), entity["unique_id"])
            for platform, entities in diagnostics["zha_lib_entities"].items()
            for entity in entities
        }
        assert sorted(
            entity.endpoint.id
            for (platform, _), entity in device.platform_entities.items()
            if platform == Platform.SWITCH
        ) == [2, 3]

        events = []
        device.on_event(ZHA_EVENT, events.append)
        device.device.packet_received(_packet(5, PRESS))
        device.device.packet_received(_packet(5, RELEASE))
        await gateway.async_block_till_done()

        assert [
            (e.data["endpoint_id"], e.data["command"], e.data["args"]) for e in events
        ] == [(5, COMMAND_ATTRIBUTE_UPDATED, _event(value).args[1]) for value in (0, 1)]
