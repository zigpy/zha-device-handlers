"""Tests for xiaomi."""

from unittest import mock

import pytest
from zha.application import Platform
from zha.application.const import ZHA_EVENT
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.general import OnOff

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.const import (
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    COMMAND_ATTRIBUTE_UPDATED,
    VALUE,
)
from zhaquirks.xiaomi.aqara.ctrl_neutral import CtrlNeutral, CtrlNeutral_2G

zhaquirks.setup()

# zigbee-herdsman:controller:endpoint Command 0x00158d00024be541/2 genOnOff.on({},
#   {"timeout":6000,"manufacturerCode":null,"disableDefaultResponse":false})
# zigbee-herdsman:adapter:zStack:znp:SREQ --> AF - dataRequest -
#   {"dstaddr":65311,"destendpoint":2,"srcendpoint":1,"clusterid":6,"transid":17,"options":0,"radius":30,"len":3,
#       "data":{"type":"Buffer","data":[1,8,1]}}
# zigbee-herdsman:adapter:zStack:unpi:writer -->frame [254,13,36,1,31,255,2,1,6,0,17,0,30,3,1,8,1,201]


# zigbee-herdsman:controller:endpoint Command 0x00158d00024be541/2 genOnOff.off({},
#   {"timeout":6000,"manufacturerCode":null,"disableDefaultResponse":false})
# zigbee-herdsman:adapter:zStack:znp:SREQ --> AF - dataRequest -
#   {"dstaddr":65311,"destendpoint":2,"srcendpoint":1,"clusterid":6,"transid":16,"options":0,"radius":30,"len":3,
#       "data":{"type":"Buffer","data":[1,7,0]}}
# zigbee-herdsman:adapter:zStack:unpi:writer --> frame [254,13,36,1,31,255,2,1,6,0,16,0,30,3,1,7,0,198]


def test_ctrl_neutral(zigpy_device_from_quirk):
    """Test ctrl neutral 1 sends correct request."""
    data = b"\x01\x01\x01"
    cluster = 6
    src_ep = 1
    dst_ep = 2

    dev = zigpy_device_from_quirk(CtrlNeutral)
    dev.request = mock.MagicMock()

    dev[2].in_clusters[cluster].command(1)

    assert dev.request.call_args[0][0] == 260
    assert dev.request.call_args[0][1] == cluster
    assert dev.request.call_args[0][2] == src_ep
    assert dev.request.call_args[0][3] == dst_ep
    assert dev.request.call_args[0][5] == data


@pytest.mark.parametrize(
    ("quirk", "button_endpoints"),
    [(CtrlNeutral, (4,)), (CtrlNeutral_2G, (4, 5))],
)
def test_ctrl_neutral_button_endpoints(
    zigpy_device_from_quirk, quirk, button_endpoints
):
    """Button endpoints fire events but are not exposed as plain OnOff switches."""
    dev = zigpy_device_from_quirk(quirk)

    for ep_id in (2, 3) if quirk is CtrlNeutral_2G else (2,):
        assert dev.endpoints[ep_id].in_clusters[OnOff.cluster_id].ep_attribute == (
            OnOff.ep_attribute
        )

    for ep_id in button_endpoints:
        cluster = dev.endpoints[ep_id].in_clusters[OnOff.cluster_id]
        # ZHA skips its default Switch entity for clusters with a renamed ep_attribute
        assert cluster.ep_attribute != OnOff.ep_attribute

        listener = mock.MagicMock()
        cluster.add_listener(listener)

        # Report_Attributes(on_off=False), then (on_off=True): a press and release
        for value, frame in ((0, "18010a00001000"), (1, "18020a00001001")):
            listener.reset_mock()
            hdr, args = cluster.deserialize(bytes.fromhex(frame))
            cluster.handle_message(hdr, args)
            listener.zha_send_event.assert_called_once_with(
                COMMAND_ATTRIBUTE_UPDATED,
                {
                    ATTRIBUTE_ID: OnOff.AttributeDefs.on_off.id,
                    ATTRIBUTE_NAME: OnOff.AttributeDefs.on_off.name,
                    VALUE: value,
                },
            )


async def test_ctrl_neutral2_zha_entities_and_events():
    """ZHA exposes only the two relays as switches; button presses become zha_events."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "lumi-lumi-ctrl-neutral2-0x00000016.json", DEVICE_REGISTRY
        )
        assert isinstance(device.device, CtrlNeutral_2G)

        switch_endpoints = sorted(
            entity.endpoint.id
            for (platform, _), entity in device.platform_entities.items()
            if platform == Platform.SWITCH
        )
        assert switch_endpoints == [2, 3]

        events = []
        device.on_event(ZHA_EVENT, events.append)

        # Physical press and release of the right key, as reported by the device
        cluster = device.device.endpoints[5].in_clusters[OnOff.cluster_id]
        for frame in ("18010a00001000", "18020a00001001"):
            hdr, args = cluster.deserialize(bytes.fromhex(frame))
            cluster.handle_message(hdr, args)
        await gateway.async_block_till_done()

        assert [
            (e.data["endpoint_id"], e.data["command"], e.data["args"]) for e in events
        ] == [
            (
                5,
                COMMAND_ATTRIBUTE_UPDATED,
                {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: "on_off", VALUE: 0},
            ),
            (
                5,
                COMMAND_ATTRIBUTE_UPDATED,
                {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: "on_off", VALUE: 1},
            ),
        ]
