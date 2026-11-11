"""Tests for the Tuya TS0601 pilot wire (fil pilote) heating controller."""

from unittest import mock

import pytest
from zigpy.zcl import foundation

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.ts0601_pilot_wire import ModeSwitching, OperatingMode, PilotWireMode

zhaquirks.setup()


@pytest.mark.parametrize(
    "msg,attr_name,value",
    [
        (
            b"\x09\x10\x02\x00\x10\x02\x04\x00\x01\x02",  # DP 2: holiday
            "operating_mode",
            OperatingMode.Holiday,
        ),
        (
            b"\x09\x11\x02\x00\x11\x7f\x04\x00\x01\x03",  # DP 127: eco
            "pilot_wire_mode",
            PilotWireMode.Eco,
        ),
        (
            b"\x09\x12\x02\x00\x12\x7e\x04\x00\x01\x02",  # DP 126: comfort -2
            "auto_pilot_wire_mode",
            PilotWireMode.ComfortMinus2,
        ),
        (
            b"\x09\x13\x02\x00\x13\x0b\x02\x00\x04\x00\x00\x00\x81",  # DP 11: 129 kWh
            "energy_consumed",
            129,
        ),
        (
            b"\x09\x14\x02\x00\x14\x65\x02\x00\x04\xff\xff\xff\xf6",  # DP 101: -1.0 °C
            "local_temperature_calibration",
            -10,
        ),
        (
            b"\x09\x15\x02\x00\x15\x8c\x02\x00\x04\x00\x00\x00\x1e",  # DP 140: 30 min
            "window_opening_mode_duration",
            30,
        ),
        (
            # DP 142: 1500 W, frame captured from a real device
            b"\x19\xe5\x01\x00\x04\x8e\x02\x00\x04\x00\x00\x05\xdc",
            "power_rating",
            1500,
        ),
        (
            b"\x09\x16\x02\x00\x16\x90\x04\x00\x01\x01",  # DP 144: six modes
            "mode_switching",
            ModeSwitching.SixModes,
        ),
        (
            b"\x09\x17\x02\x00\x17\x27\x01\x00\x01\x01",  # DP 39: child lock on
            "child_lock",
            True,
        ),
    ],
)
async def test_pilot_wire_handle_get_data(
    zigpy_device_from_v2_quirk, msg, attr_name, value
):
    """Test that data points are decoded into the Tuya cluster attributes."""

    quirked = zigpy_device_from_v2_quirk("_TZE204_3q3maeoo", "TS0601")
    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    cluster_listener = ClusterListener(ep.tuya_manufacturer)

    hdr, data = ep.tuya_manufacturer.deserialize(msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert len(cluster_listener.attribute_updates) == 1
    attr_id = ep.tuya_manufacturer.attributes_by_name[attr_name].id
    assert cluster_listener.attribute_updates[0][0] == attr_id
    assert cluster_listener.attribute_updates[0][1] == value
    assert ep.tuya_manufacturer.get(attr_id) == value


@pytest.mark.parametrize(
    "msg,cluster_name,value",
    [
        (
            b"\x09\x20\x02\x00\x20\x10\x02\x00\x04\x00\x00\x00\xd1",  # DP 16: 20.9 °C
            "temperature",
            2090,
        ),
        (
            b"\x09\x21\x02\x00\x21\x08\x02\x00\x04\x00\x00\x00\x29",  # DP 8: 41 %
            "humidity",
            4100,
        ),
    ],
)
async def test_pilot_wire_measurements(
    zigpy_device_from_v2_quirk, msg, cluster_name, value
):
    """Test that temperature and humidity are forwarded to the ZCL clusters."""

    quirked = zigpy_device_from_v2_quirk("_TZE204_3q3maeoo", "TS0601")
    ep = quirked.endpoints[1]

    hdr, data = ep.tuya_manufacturer.deserialize(msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert getattr(ep, cluster_name).get("measured_value") == value


async def test_pilot_wire_write_attributes(zigpy_device_from_v2_quirk):
    """Test that writing attributes sends the expected Tuya data points."""

    quirked = zigpy_device_from_v2_quirk("_TZE204_3q3maeoo", "TS0601")
    tuya_cluster = quirked.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        (status,) = await tuya_cluster.write_attributes(
            {"pilot_wire_mode": PilotWireMode.Eco}
        )
        await wait_for_zigpy_tasks()
        assert m1.call_args.kwargs["cluster"] == 0xEF00
        assert m1.call_args.kwargs["data"].endswith(b"\x7f\x04\x00\x01\x03")
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await tuya_cluster.write_attributes({"power_rating": 1500})
        await wait_for_zigpy_tasks()
        assert m1.call_args.kwargs["data"].endswith(b"\x8e\x02\x00\x04\x00\x00\x05\xdc")
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await tuya_cluster.write_attributes(
            {"reset_energy_consumption": True}
        )
        await wait_for_zigpy_tasks()
        assert m1.call_args.kwargs["data"].endswith(b"\x8d\x01\x00\x01\x01")
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]
