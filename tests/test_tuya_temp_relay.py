"""Tests for the Tuya TS000F relay with temperature probe."""

from unittest import mock

from zigpy.zcl import foundation

from tests.common import wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya import TUYA_SEND_DATA, TuyaDPType

zhaquirks.setup()


async def test_ts000f_7fiyo3kv(zigpy_device_from_v2_quirk):
    """Test probe temperature, calibration and child lock datapoints."""
    quirked = zigpy_device_from_v2_quirk("_TZ3218_7fiyo3kv", "TS000F")
    ep = quirked.endpoints[1]
    mcu = ep.tuya_manufacturer

    message = (
        b"\x09\xe0\x02\x0b\x33"
        + bytes([102, TuyaDPType.VALUE, 0, 4])
        + (-55).to_bytes(4, "big", signed=True)
        + bytes([108, TuyaDPType.VALUE, 0, 4])
        + (-15).to_bytes(4, "big", signed=True)
        + bytes([111, TuyaDPType.BOOL, 0, 1, 1])
    )
    hdr, data = mcu.deserialize(message)
    assert mcu.handle_get_data(data.data) == foundation.Status.SUCCESS

    assert ep.temperature.get("measured_value") == -550
    assert mcu.get("temperature_calibration") == -15
    assert mcu.get("child_lock") == 1

    with mock.patch.object(
        mcu.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        await mcu.write_attributes({"child_lock": False})
        await wait_for_zigpy_tasks()

    assert request.call_args.kwargs["command_id"] == TUYA_SEND_DATA
    assert request.call_args.kwargs["data"].endswith(
        bytes([111, TuyaDPType.BOOL, 0, 1, 0])
    )
