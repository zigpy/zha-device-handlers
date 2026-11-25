"""Tests for Tuya TS0049 (_TZ3000_kz1anoi8) water valve quirk."""

from unittest import mock

import pytest
from zigpy.zcl import foundation

from tests.common import wait_for_zigpy_tasks
import zhaquirks
import zhaquirks.tuya.ts0049_kz1anoi8

zhaquirks.setup()

MANUFACTURER = "_TZ3000_kz1anoi8"
MODEL = "TS0049"
CLUSTER_E001 = 0xE001


@pytest.fixture
def water_valve(zigpy_device_from_v2_quirk):
    """Return quirked TS0049 water valve device."""
    return zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)


async def test_irrigation_time_sends_e001_frame(water_valve):
    """Test write irrigation_time (seconds) sends correct 0xE001 frame."""
    tuya_cluster = water_valve.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint.device, "request", return_value=None
    ) as m:
        await tuya_cluster.write_attributes({"irrigation_time": 300})
        await wait_for_zigpy_tasks()

    assert m.called
    call_kwargs = m.call_args.kwargs
    assert call_kwargs["cluster"] == CLUSTER_E001
    assert call_kwargs["expect_reply"] is False
    # ZCL frame: [0x11, tsn, 0xFE, DP=11, 0x00, 0x00, 0x01, 0x2C]
    data = call_kwargs["data"]
    assert data[0] == 0x11
    assert data[2] == 0xFE
    assert data[3] == 11
    assert int.from_bytes(data[4:8], "big") == 300

    # irrigation_time stored in seconds
    attr_id = tuya_cluster.attributes_by_name["irrigation_time"].id
    assert tuya_cluster.get(attr_id) == 300


async def test_irrigation_time_zero_disables_autooff(water_valve):
    """Test that value 0 disables auto-off by sending 0 seconds."""
    tuya_cluster = water_valve.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint.device, "request", return_value=None
    ) as m:
        await tuya_cluster.write_attributes({"irrigation_time": 0})
        await wait_for_zigpy_tasks()

    data = m.call_args.kwargs["data"]
    assert int.from_bytes(data[4:8], "big") == 0


async def test_irrigation_time_clamped(water_valve):
    """Test that values are clamped to 86400 seconds."""
    tuya_cluster = water_valve.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint.device, "request", return_value=None
    ) as m:
        await tuya_cluster.write_attributes({"irrigation_time": 99999})
        await wait_for_zigpy_tasks()

    data = m.call_args.kwargs["data"]
    assert int.from_bytes(data[4:8], "big") == 86400


async def test_irrigation_time_int_key(water_valve):
    """Test write_attributes with integer attribute ID key."""
    tuya_cluster = water_valve.endpoints[1].tuya_manufacturer
    attr_id = tuya_cluster.attributes_by_name["irrigation_time"].id

    with mock.patch.object(
        tuya_cluster.endpoint.device, "request", return_value=None
    ) as m:
        await tuya_cluster.write_attributes({attr_id: 60})
        await wait_for_zigpy_tasks()

    data = m.call_args.kwargs["data"]
    assert int.from_bytes(data[4:8], "big") == 60


async def test_irrigation_time_zcl_attr_def_key(water_valve):
    """Test write_attributes with ZCLAttributeDef key."""
    tuya_cluster = water_valve.endpoints[1].tuya_manufacturer
    attr_def = tuya_cluster.attributes_by_name["irrigation_time"]

    with mock.patch.object(
        tuya_cluster.endpoint.device, "request", return_value=None
    ) as m:
        await tuya_cluster.write_attributes({attr_def: 120})
        await wait_for_zigpy_tasks()

    data = m.call_args.kwargs["data"]
    assert int.from_bytes(data[4:8], "big") == 120


async def test_non_timer_attr_uses_super(water_valve):
    """Test that non-timer attributes are forwarded to the base class."""
    tuya_cluster = water_valve.endpoints[1].tuya_manufacturer
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    with (
        mock.patch.object(tuya_cluster.endpoint.device, "request", return_value=None),
        mock.patch(
            "zhaquirks.tuya.mcu.TuyaMCUCluster.write_attributes",
            return_value=success,
        ) as super_mock,
    ):
        # 0x0000 is not the irrigation_time attr id, so it goes to other_attrs
        await tuya_cluster.write_attributes({0x0000: 1})
        await wait_for_zigpy_tasks()

    assert super_mock.called
