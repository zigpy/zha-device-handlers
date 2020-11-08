"""Tests for xiaomi."""
from unittest import mock

from zhaquirks.xiaomi.aqara.ctrl_neutral import CtrlNeutral

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
