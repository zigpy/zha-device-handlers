"""Test units for new Tuya cluster framework."""

from unittest import mock

import pytest
import zigpy.types as t
import zigpy.zcl.foundation as zcl_f

from zhaquirks.tuya import (
    TUYA_ACTIVE_STATUS_RPT,
    TUYA_GET_DATA,
    TUYA_SET_DATA_RESPONSE,
    TUYA_SET_TIME,
    TuyaCommand,
    TuyaData,
    TuyaDatapointData,
    TuyaNewManufCluster,
)


@pytest.fixture(name="TuyaCluster")
def tuya_cluster(zigpy_device_mock):
    """Mock of the new Tuya manufacturer cluster."""
    device = zigpy_device_mock()
    endpoint = device.add_endpoint(1)
    cluster = TuyaNewManufCluster(endpoint)
    return cluster


def test_tuya_data_raw():
    """Test tuya "Raw" datatype."""

    class Test(t.Struct):
        test_bool: t.Bool
        test_uint16_t_be: t.uint16_t_be

    data = b"\x00\x00\x03\x01\x02\x46"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 0
    assert r.raw == b"\x01\x02\x46"
    assert Test.deserialize(r.payload)[0] == Test(True, 582)

    r.payload = Test(False, 314)
    assert r.raw == b"\x00\x01\x3a"


def test_tuya_data_value():
    """Test tuya "Value" datatype."""

    data = b"\x02\x00\x04\x00\x00\x02\xdb"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 2
    assert r.raw == b"\x00\x00\x02\xdb"
    assert r.payload == 731

    r.payload = 582
    assert r.raw == b"\x00\x00\x02\x46"


def test_tuya_negative_value():
    """Test tuya negative "Value" datatype."""

    data = b"\x02\x00\x04\xff\xff\xff\xf8"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 2
    assert r.raw == b"\xff\xff\xff\xf8"
    assert r.payload == -8


def test_tuya_data_bool():
    """Test tuya Bool datatype."""

    data = b"\x01\x00\x01\x00"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 1
    assert r.raw == b"\x00"
    assert not r.payload

    r.payload = True
    assert r.raw == b"\x01"

    data = b"\x01\x00\x01\x01"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 1
    assert r.raw == b"\x01"
    assert r.payload

    r.payload = False
    assert r.raw == b"\x00"


def test_tuya_data_enum():
    """Test tuya Enum datatype."""

    data = b"\x04\x00\x01\x40"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 4
    assert r.raw == b"\x40"
    assert r.payload == 0x40

    r.payload = 0x42
    assert r.raw == b"\x42"


def test_tuya_data_string():
    """Test tuya String datatype."""

    data = b"\x03\x00\x04Tuya"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 3
    assert r.raw == b"Tuya"
    assert r.payload == "Tuya"

    r.payload = "Data"
    assert r.raw == b"Data"


def test_tuya_data_bitmap():
    """Test tuya Bitmap datatype."""

    data = b"\x05\x00\x01\x40"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 5
    assert r.raw == b"\x40"
    assert r.payload == 0x40

    r.payload = 0x82
    assert r.raw == b"\x82"

    data = b"\x05\x00\x02\x40\x02"
    r, _ = TuyaData.deserialize(data)
    assert r.payload == 0x0240

    r.payload = t.bitmap16(0x2004)
    assert r.raw == b"\x20\x04"

    data = b"\x05\x00\x04\x40\x02\x80\x01"
    r, _ = TuyaData.deserialize(data)
    assert r.payload == 0x1800240

    r.payload = t.bitmap32(0x10082004)
    assert r.raw == b"\x10\x08\x20\x04"


def test_tuya_data_bitmap_invalid():
    """Test tuya Bitmap datatype."""

    data = b"\x05\x00\x03\x4012"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    with pytest.raises(ValueError):
        r.payload


def test_tuya_data_unknown():
    """Test tuya unknown datatype."""

    data = b"\x06\x00\x04\x03\x02\x01\x00"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 6
    assert r.raw == b"\x03\x02\x01\x00"

    with pytest.raises(ValueError):
        r.payload

    with pytest.raises(ValueError):
        r.payload = 0


@pytest.mark.parametrize(
    "cmd_id, handler_name, args",
    (
        (
            TUYA_GET_DATA,
            "handle_get_data",
            (
                TuyaCommand(
                    status=0,
                    tsn=2,
                    datapoints=[TuyaDatapointData(2, TuyaData(1, 0, b"\x01\x01"))],
                ),
            ),
        ),
        (
            TUYA_SET_DATA_RESPONSE,
            "handle_set_data_response",
            (
                TuyaCommand(
                    status=0,
                    tsn=2,
                    datapoints=[TuyaDatapointData(2, TuyaData(1, 0, b"\x01\x01"))],
                ),
            ),
        ),
        (
            TUYA_ACTIVE_STATUS_RPT,
            "handle_active_status_report",
            (
                TuyaCommand(
                    status=0,
                    tsn=2,
                    datapoints=[TuyaDatapointData(2, TuyaData(1, 0, b"\x01\x01"))],
                ),
            ),
        ),
        (TUYA_SET_TIME, "handle_set_time_request", (0x1234,)),
    ),
)
@mock.patch("zhaquirks.tuya.TuyaNewManufCluster.send_default_rsp")
def test_tuya_cluster_request(
    default_rsp_mock, cmd_id, handler_name, args, TuyaCluster
):
    """Test cluster specific request."""

    hdr = zcl_f.ZCLHeader.general(1, cmd_id, direction=zcl_f.Direction.Server_to_Client)
    hdr.frame_control.disable_default_response = False

    with mock.patch.object(TuyaCluster, handler_name) as handler:
        handler.return_value = mock.sentinel.status
        TuyaCluster.handle_cluster_request(hdr, args)
        assert handler.call_count == 1
        assert default_rsp_mock.call_count == 1
        assert default_rsp_mock.call_args[1]["status"] is mock.sentinel.status


@mock.patch("zhaquirks.tuya.TuyaNewManufCluster.send_default_rsp")
def test_tuya_cluster_request_unk_command(default_rsp_mock, TuyaCluster):
    """Test cluster specific request handler -- no handler."""

    hdr = zcl_f.ZCLHeader.general(1, 0xFE, direction=zcl_f.Direction.Server_to_Client)
    hdr.frame_control.disable_default_response = False

    TuyaCluster.handle_cluster_request(hdr, (mock.sentinel.args,))
    assert default_rsp_mock.call_count == 1
    assert default_rsp_mock.call_args[1]["status"] == zcl_f.Status.UNSUP_CLUSTER_COMMAND


@mock.patch("zhaquirks.tuya.TuyaNewManufCluster.send_default_rsp")
def test_tuya_cluster_request_no_handler(default_rsp_mock, TuyaCluster):
    """Test cluster specific request handler -- no handler."""

    hdr = zcl_f.ZCLHeader.general(1, 0xFE, direction=zcl_f.Direction.Server_to_Client)
    hdr.frame_control.disable_default_response = False

    new_client_commands = TuyaCluster.client_commands.copy()
    new_client_commands[0xFE] = zcl_f.ZCLCommandDef(
        "no_such_handler", {}, is_manufacturer_specific=True
    )

    with mock.patch.object(TuyaCluster, "client_commands", new_client_commands):
        TuyaCluster.handle_cluster_request(hdr, (mock.sentinel.args,))

    assert default_rsp_mock.call_count == 1
    assert default_rsp_mock.call_args[1]["status"] == zcl_f.Status.UNSUP_CLUSTER_COMMAND
