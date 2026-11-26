"""Tests for Shelly quirks."""

import asyncio

import pytest
from zha.quirks import DEVICE_REGISTRY
import zigpy.device
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    LevelControl,
    OnOff,
    OnOffConfiguration,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.foundation import ZCLAttributeAccess

from tests.common import ButtonEventRecorder
import zhaquirks
from zhaquirks.const import (
    BUTTON_2,
    BUTTON_3,
    CLUSTER_ID,
    COMMAND,
    COMMAND_RECALL,
    COMMAND_TOGGLE,
    ENDPOINT_ID,
    LONG_PRESS,
    PARAMS,
    SHORT_PRESS,
)
from zhaquirks.shelly import SHELLY_MANUFACTURER_CODE
from zhaquirks.shelly.wifi import (
    SHELLY_WIFI_SETUP_CLUSTER_ID,
    SHELLY_WIFI_SETUP_ENDPOINT_ID,
    SHELLY_WIFI_SETUP_PROFILE_ID,
    ShellyCustomProfileDevice,
    ShellyWiFiSetupCluster,
)

zhaquirks.setup()


def _attribute_report_data(
    attribute: foundation.ZCLAttributeDef, value: object
) -> bytes:
    """Build a typed ZCL attribute report payload for Shelly WiFi attributes."""

    header = foundation.ZCLHeader.general(
        tsn=1,
        command_id=foundation.GeneralCommand.Report_Attributes,
        manufacturer=SHELLY_MANUFACTURER_CODE,
        direction=foundation.Direction.Server_to_Client,
    ).serialize()
    response = foundation.Attribute(
        attrid=attribute.id,
        value=foundation.TypeValue(type=attribute.zcl_type, value=value),
    )
    command = (
        foundation.GENERAL_COMMANDS[foundation.GeneralCommand.Report_Attributes]
        .schema([response])
        .serialize()
    )
    return t.SerializableBytes(header + command).serialize()


@pytest.mark.parametrize("model", ["1PM", "2PM"])
def test_shelly_wifi_setup_cluster_replaced(zigpy_device_from_v2_quirk, model) -> None:
    """Ensure Shelly relay devices expose a typed WiFi setup cluster."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        model,
        endpoint_ids=[1, SHELLY_WIFI_SETUP_ENDPOINT_ID],
        cluster_ids={
            SHELLY_WIFI_SETUP_ENDPOINT_ID: {
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )

    cluster = quirked.endpoints[SHELLY_WIFI_SETUP_ENDPOINT_ID].in_clusters[
        SHELLY_WIFI_SETUP_CLUSTER_ID
    ]

    assert isinstance(quirked, ShellyCustomProfileDevice)
    assert isinstance(cluster, ShellyWiFiSetupCluster)
    assert cluster.ep_attribute == "shelly_wifi_setup"
    assert cluster.find_attribute("status") == cluster.AttributeDefs.status
    assert cluster.find_attribute("ssid") == cluster.AttributeDefs.ssid
    assert cluster.AttributeDefs.status.manufacturer_code == SHELLY_MANUFACTURER_CODE
    assert cluster.AttributeDefs.dhcp.access == ZCLAttributeAccess.Read
    assert cluster.AttributeDefs.enable.access == (
        ZCLAttributeAccess.Read | ZCLAttributeAccess.Write
    )
    assert cluster.AttributeDefs.action.access == ZCLAttributeAccess.Write
    assert cluster.AttributeDefs.action.type is t.uint8_t


@pytest.mark.parametrize("model", ["1PM", "2PM"])
def test_shelly_wifi_custom_profile_packet_processed(
    zigpy_device_from_v2_quirk, model
) -> None:
    """Ensure Shelly custom profile packets are processed as ZCL for WiFi reads."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        model,
        endpoint_ids=[1, SHELLY_WIFI_SETUP_ENDPOINT_ID],
        cluster_ids={
            SHELLY_WIFI_SETUP_ENDPOINT_ID: {
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )

    cluster = quirked.endpoints[SHELLY_WIFI_SETUP_ENDPOINT_ID].in_clusters[
        SHELLY_WIFI_SETUP_CLUSTER_ID
    ]

    async def deliver_packet() -> None:
        quirked.packet_received(
            t.ZigbeePacket(
                profile_id=SHELLY_WIFI_SETUP_PROFILE_ID,
                cluster_id=SHELLY_WIFI_SETUP_CLUSTER_ID,
                src_ep=SHELLY_WIFI_SETUP_ENDPOINT_ID,
                dst_ep=SHELLY_WIFI_SETUP_ENDPOINT_ID,
                data=t.SerializableBytes(
                    _attribute_report_data(
                        cluster.AttributeDefs.status,
                        t.CharacterString("got ip"),
                    )
                ),
            )
        )

    asyncio.run(deliver_packet())

    assert cluster.get("status") == "got ip"


@pytest.mark.parametrize("model", ["1PM", "2PM"])
def test_shelly_wifi_standard_profile_packet_delegated(
    zigpy_device_from_v2_quirk, model
) -> None:
    """Ensure standard ZHA profile packets fall through to normal zigpy parsing."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        model,
        endpoint_ids=[1, SHELLY_WIFI_SETUP_ENDPOINT_ID],
        cluster_ids={
            SHELLY_WIFI_SETUP_ENDPOINT_ID: {
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )

    # Standard ZHA profile packet should delegate to super()
    zha_packet = t.ZigbeePacket(
        profile_id=zha.PROFILE_ID,
        cluster_id=Basic.cluster_id,
        src_ep=1,
        dst_ep=1,
        data=t.SerializableBytes(
            _attribute_report_data(
                Basic.AttributeDefs.model,
                t.CharacterString("1PM"),
            )
        ),
    )

    hdr, rsp_key = quirked._parse_packet_header(zha_packet)

    assert hdr is not None
    assert rsp_key is not None
    assert rsp_key.endpoint_id == 1
    assert rsp_key.cluster_id == Basic.cluster_id


@pytest.fixture
def button4(MockAppController):
    """Create a BLU RC Button 4 ZB with the endpoints from Shelly's API docs."""
    device = zigpy.device.Device(
        MockAppController, t.EUI64.convert("01:02:03:04:05:06:07:08"), 0x1234
    )
    device.manufacturer = "Shelly"
    device.model = "BLU RC Button 4 ZB"

    for endpoint_id in range(1, 5):
        endpoint = device.add_endpoint(endpoint_id)
        endpoint.profile_id = zha.PROFILE_ID
        endpoint.device_type = zha.DeviceType.ON_OFF_SWITCH
        endpoint.add_input_cluster(Basic.cluster_id)
        endpoint.add_input_cluster(Identify.cluster_id)
        endpoint.add_output_cluster(Scenes.cluster_id)
        endpoint.add_output_cluster(OnOff.cluster_id)

    endpoint = device.endpoints[1]
    endpoint.add_input_cluster(PowerConfiguration.cluster_id)
    endpoint.add_output_cluster(OnOffConfiguration.cluster_id)
    endpoint.add_output_cluster(LevelControl.cluster_id)

    return DEVICE_REGISTRY.resolve(device)


def _send(device, endpoint_id: int, cluster_id: int, payload: bytes) -> None:
    """Receive a ZCL frame from an endpoint of the remote."""
    device.packet_received(
        t.ZigbeePacket(
            src_ep=endpoint_id,
            dst_ep=1,
            tsn=payload[1],
            profile_id=zha.PROFILE_ID,
            cluster_id=cluster_id,
            data=t.SerializableBytes(payload),
        )
    )


def _recall(scene_id: int, button: int) -> bytes:
    """Return a cluster specific Scenes recall frame for group 0."""
    return bytes([0x01, button, 0x05, 0x00, 0x00, scene_id])


async def test_shelly_button4_event_types(button4) -> None:
    """Each button gets an event entity with the gestures the remote resolves."""
    recorder = await ButtonEventRecorder.create(button4)

    expected = ["single_press", "multi_press", "long_press_start"]
    assert recorder.event_types() == {
        f"button_{button}": expected for button in range(1, 5)
    }
    for button in range(1, 5):
        entity = recorder.entities[f"button_{button}"]
        assert entity.endpoint.id == button


async def test_shelly_button4_toggle_mode(button4) -> None:
    """Toggle mode sends toggle from the button's own endpoint."""
    recorder = await ButtonEventRecorder.create(button4)
    device = recorder.zha_device.device

    for button in range(1, 5):
        _send(device, button, OnOff.cluster_id, bytes([0x01, button, 0x02]))

    assert recorder.pop() == [
        (f"button_{button}", "single_press") for button in range(1, 5)
    ]


async def test_shelly_button4_on_off_mode(button4) -> None:
    """On/Off mode sends on/off from endpoint 1 (buttons 1/2) and 2 (buttons 3/4)."""
    recorder = await ButtonEventRecorder.create(button4)
    device = recorder.zha_device.device

    _send(device, 1, OnOff.cluster_id, b"\x01\x01\x01")  # on
    _send(device, 1, OnOff.cluster_id, b"\x01\x02\x00")  # off
    _send(device, 2, OnOff.cluster_id, b"\x01\x03\x01")  # on
    _send(device, 2, OnOff.cluster_id, b"\x01\x04\x00")  # off

    assert recorder.pop() == [
        ("button_1", "single_press"),
        ("button_2", "single_press"),
        ("button_3", "single_press"),
        ("button_4", "single_press"),
    ]


async def test_shelly_button4_scene_gestures(button4) -> None:
    """Multi and long clicks recall a scene from the button's endpoint."""
    recorder = await ButtonEventRecorder.create(button4)
    device = recorder.zha_device.device

    _send(device, 1, Scenes.cluster_id, _recall(1, 1))
    _send(device, 2, Scenes.cluster_id, _recall(2, 2))
    _send(device, 3, Scenes.cluster_id, _recall(11, 3))

    assert recorder.pop() == [
        ("button_1", "multi_press", {"press_count": 2}),
        ("button_2", "multi_press", {"press_count": 3}),
        ("button_3", "long_press_start"),
    ]

    # Double and triple long clicks and level steps have no standard event type
    _send(device, 4, Scenes.cluster_id, _recall(12, 4))
    _send(device, 4, Scenes.cluster_id, _recall(13, 5))
    _send(device, 1, LevelControl.cluster_id, b"\x01\x06\x02\x00\x20\x00\x00")

    assert recorder.pop() == []


def test_shelly_button4_device_automation_triggers(button4):
    """The remote's gestures are also available as device automation triggers."""
    triggers = button4.device_automation_triggers

    assert len(triggers) == 16
    assert triggers[(SHORT_PRESS, BUTTON_3)] == {
        ENDPOINT_ID: 3,
        CLUSTER_ID: OnOff.cluster_id,
        COMMAND: COMMAND_TOGGLE,
    }
    assert triggers[(LONG_PRESS, BUTTON_2)] == {
        ENDPOINT_ID: 2,
        CLUSTER_ID: Scenes.cluster_id,
        COMMAND: COMMAND_RECALL,
        PARAMS: {"scene_id": 11},
    }
