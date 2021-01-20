"""Tests for xiaomi."""
import asyncio
from unittest import mock

import pytest
import zigpy.device
import zigpy.types as t

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MANUFACTURER,
    MODEL,
    NODE_DESCRIPTOR,
    OFF,
    ON,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZONE_STATE,
)
from zhaquirks.xiaomi import (
    LUMI,
    XIAOMI_NODE_DESC,
    BasicCluster,
    XiaomiCustomDevice,
    XiaomiQuickInitDevice,
    handle_quick_init,
)
import zhaquirks.xiaomi.aqara.motion_aq2
import zhaquirks.xiaomi.aqara.motion_aq2b
import zhaquirks.xiaomi.mija.motion

from tests.common import ZCL_OCC_ATTR_RPT_OCC, ClusterListener


def test_basic_cluster_deserialize_wrong_len():
    """Test attr report with model and xiaomi attr."""
    cluster = BasicCluster(mock.MagicMock())

    data = b"\x1c_\x11\x12\n"
    data += b'\x05\x00B\x15lumi.sensor_wleak.aq1\x01\xffB"\x01!\xb3\x0b\x03('
    data += b"\x17\x04!\xa8C\x05!\xa7\x00\x06$\x00\x00\x00\x00\x00\x08!\x04"
    data += b"\x02\n!\x00\x00d\x10\x01"

    deserialized = cluster.deserialize(data)
    assert deserialized[1]


def test_basic_cluster_deserialize_wrong_len_2():
    """Test attr report with xiaomi attr."""
    cluster = BasicCluster(mock.MagicMock())

    data = b"\x1c_\x11\x12\n"
    data += b'\x01\xffB"\x01!\xb3\x0b\x03(\x17\x04!\xa8C\x05!\xa7\x00\x06$\x15'
    data += b"\x00\x14\x00\x00\x08!\x04\x02\n!\x00\x00d\x10\x01"

    deserialized = cluster.deserialize(data)
    assert deserialized[1]


@pytest.mark.parametrize(
    "quirk",
    (
        zhaquirks.xiaomi.aqara.motion_aq2.MotionAQ2,
        zhaquirks.xiaomi.aqara.motion_aq2b.MotionAQ2,
        zhaquirks.xiaomi.mija.motion.Motion,
    ),
)
async def test_konke_motion(zigpy_device_from_quirk, quirk):
    """Test Orvibo motion sensor."""

    motion_dev = zigpy_device_from_quirk(quirk)

    motion_cluster = motion_dev.endpoints[1].ias_zone
    motion_listener = ClusterListener(motion_cluster)

    occupancy_cluster = motion_dev.endpoints[1].occupancy
    occupancy_listener = ClusterListener(occupancy_cluster)

    p1 = mock.patch.object(motion_cluster, "reset_s", 0)
    p2 = mock.patch.object(occupancy_cluster, "reset_s", 0)
    # send motion on IAS zone command
    hdr, args = occupancy_cluster.deserialize(ZCL_OCC_ATTR_RPT_OCC)
    with p1, p2:
        occupancy_cluster.handle_message(hdr, args)

    assert len(motion_listener.cluster_commands) == 1
    assert len(motion_listener.attribute_updates) == 1
    assert motion_listener.cluster_commands[0][1] == ZONE_STATE
    assert motion_listener.cluster_commands[0][2][0] == ON

    assert len(occupancy_listener.cluster_commands) == 0
    assert len(occupancy_listener.attribute_updates) == 1
    assert occupancy_listener.attribute_updates[0][0] == 0x0000
    assert occupancy_listener.attribute_updates[0][1] == 1

    await asyncio.sleep(0.1)

    assert len(motion_listener.cluster_commands) == 2
    assert motion_listener.cluster_commands[1][1] == ZONE_STATE
    assert motion_listener.cluster_commands[1][2][0] == OFF

    assert len(occupancy_listener.cluster_commands) == 0
    assert len(occupancy_listener.attribute_updates) == 2
    assert occupancy_listener.attribute_updates[1][0] == 0x0000
    assert occupancy_listener.attribute_updates[1][1] == 0


@pytest.fixture
def raw_device():
    """Raw device fixture."""

    ieee = t.EUI64.convert("11:22:33:44:55:66:77:88")
    device = zigpy.device.Device(mock.MagicMock(), ieee, 0x1234)
    with mock.patch.object(device, "cancel_initialization"):
        yield device


@pytest.mark.parametrize(
    "ep_id, cluster, message",
    (
        (0, 0, b"\x18\x00\n\x05\x00B\x11lumi.sensor_sm0ke\x01\x00 \x01"),
        (0, 1, b"\x18\x00\n\x05\x00B\x11lumi.sensor_sm0ke\x01\x00 \x01"),
    ),
)
def test_xiaomi_quick_init_wrong_ep(raw_device, ep_id, cluster, message):
    """Test quick init when message is received on wrong endpoint."""

    with mock.patch("zigpy.zcl.foundation.ZCLHeader.deserialize") as hdr_deserialize:
        assert (
            handle_quick_init(raw_device, 0x0260, cluster, ep_id, ep_id, message)
            is None
        )
        assert hdr_deserialize.call_count == 0
        assert raw_device.cancel_initialization.call_count == 0
        assert raw_device.application.device_initialized.call_count == 0


@pytest.mark.parametrize(
    "cluster, message",
    (
        (
            0,
            b"\x19\x00\n\x05\x00B\x11lumi.sensor_sm0ke\x01\x00 \x01",
        ),  # cluster command
        (1, b"\x18\x00\n\x05\x00B\x11lumi.sensor_sm0ke\x01\x00 \x01"),  # wrong cluster
        (
            0,
            b"\x18\x00\x01\x05\x00B\x11lumi.sensor_sm0ke\x01\x00 \x01",
        ),  # wrong command
        (
            0,
            b"\x18\x00\xFF\x05\x00B\x11lumi.sensor_sm0ke\x01\x00 \x01",
        ),  # unknown command
        (0, b"\x18\x00\n\x04\x00B\x11lumi.sensor_sm0ke\x01\x00 \x01"),  # wrong attr id
        (0, b"\x18\x00\n\x05\x00B\x11lumi.sensor_sm0ke\x01\x00 "),  # data under run
        (0, b"\x18\x00\n\x05\x00B\x00\x01\x00 \x01"),  # no model
        (0, b"\x18\x00\n\x05\x00B\x11lumi.sensor_sm0ke\x01\x00 \x01"),  # no quirk
    ),
)
def test_xiaomi_quick_init_wrong_cluster_or_message(raw_device, cluster, message):
    """Test quick init when message is received on wrong cluster or wrong endpoint."""

    assert handle_quick_init(raw_device, 0x0260, cluster, 1, 1, message) is None
    assert raw_device.cancel_initialization.call_count == 0
    assert raw_device.application.device_initialized.call_count == 0


def test_xiaomi_quick_init_wrong_quirk_type(raw_device):
    """Test quick init for existing quirk which is not enabled for quick joining."""

    class WrongDevice(XiaomiCustomDevice):
        signature = {
            MANUFACTURER: LUMI,
            MODEL: "lumi.sensor_smoke_2",
        }

    assert (
        handle_quick_init(
            raw_device,
            0x0260,
            0,
            1,
            1,
            b"\x18\x00\n\x05\x00B\x13lumi.sensor_smoke_2\x01\x00 \x01",
        )
        is None
    )
    assert raw_device.cancel_initialization.call_count == 0
    assert raw_device.application.device_initialized.call_count == 0


def test_xiaomi_quick_init_wrong_signature(raw_device):
    """Test quick init for existing quirk with wrong signature for quick joining."""

    class WrongSignature(XiaomiQuickInitDevice):
        signature = {
            MODEL: "lumi.sensor_sm0ke",
        }

    assert (
        handle_quick_init(
            raw_device,
            0x0260,
            0,
            1,
            1,
            b"\x18\x00\n\x05\x00B\x11lumi.sensor_sm0ke\x01\x00 \x01",
        )
        is None
    )
    assert raw_device.cancel_initialization.call_count == 0
    assert raw_device.application.device_initialized.call_count == 0


def test_xiaomi_quick_init(raw_device):
    """Test quick init."""

    class XiaomiQuirk(XiaomiQuickInitDevice):
        signature = {
            NODE_DESCRIPTOR: XIAOMI_NODE_DESC,
            ENDPOINTS: {
                1: {
                    PROFILE_ID: 0x0260,
                    DEVICE_TYPE: 0x0000,
                    INPUT_CLUSTERS: [],
                    OUTPUT_CLUSTERS: [],
                }
            },
            MANUFACTURER: LUMI,
            MODEL: "lumi.sensor_sm0ke",
        }

    assert (
        handle_quick_init(
            raw_device,
            0x0260,
            0,
            1,
            1,
            b"\x18\x00\n\x05\x00B\x11lumi.sensor_sm0ke\x01\x00 \x01",
        )
        is True
    )
    assert raw_device.cancel_initialization.call_count == 1
    assert raw_device.application.device_initialized.call_count == 1


@pytest.mark.parametrize(
    "voltage, bpr",
    (
        (3240, 200),
        (3200, 200),
        (3000, 129),
        (2985, 118),
        (2860, 29),
        (2845, 18),
        (2830, 7),
        (2600, 0),
    ),
)
async def test_xiaomi_battery(zigpy_device_from_quirk, voltage, bpr):
    """Test xiaomi batter voltage to % battery left."""
    data_1 = b'\x1c_\x11I\n\x01\xffB"\x01!'
    data_2 = (
        b"\x03(\r\x04!\xa8\x13\x05!\xcb\x00\x06$\x01\x00\x00\x00\x00\x08!\x04\x02\n!"
        b"\x00\x00d\x10\x00"
    )

    device = zigpy_device_from_quirk(zhaquirks.xiaomi.aqara.vibration_aq1.VibrationAQ1)
    device.handle_message(
        0x260, 0x0000, 1, 1, data_1 + t.uint16_t(voltage).serialize() + data_2
    )
    power_cluster = device.endpoints[1].power
    assert power_cluster["battery_percentage_remaining"] == bpr


@pytest.mark.parametrize(
    "voltage, bpr",
    (
        (3240, 200),
        (3200, 200),
        (3000, 129),
        (2985, 118),
        (2860, 29),
        (2845, 18),
        (2830, 7),
        (2600, 0),
    ),
)
async def test_mija_battery(zigpy_device_from_quirk, voltage, bpr):
    """Test xiaomi batter voltage to % battery left."""
    data_1 = b"\x1c4\x12\x02\n\x02\xffL\x06\x00\x10\x01!"
    data_2 = b"!\xa8\x01$\x00\x00\x00\x00\x00!n\x00 P"

    device = zigpy_device_from_quirk(zhaquirks.xiaomi.mija.motion.Motion)
    device.handle_message(
        0x260, 0x0000, 1, 1, data_1 + t.uint16_t(voltage).serialize() + data_2
    )
    power_cluster = device.endpoints[1].power
    assert power_cluster["battery_percentage_remaining"] == bpr


@pytest.mark.parametrize(
    "quirk, batt_size",
    (
        (zhaquirks.xiaomi.aqara.vibration_aq1.VibrationAQ1, 0x0A),
        (zhaquirks.xiaomi.mija.motion.Motion, 0x09),
        (zhaquirks.xiaomi.mija.sensor_switch.MijaButton, 0x0A),
        (zhaquirks.xiaomi.mija.sensor_magnet.Magnet, 0x0B),
    ),
)
async def test_xiaomi_batt_size(zigpy_device_from_quirk, quirk, batt_size):
    """Test xiaomi battery size overrides."""

    device = zigpy_device_from_quirk(quirk)
    cluster = device.endpoints[1].power
    succ, fail = await cluster.read_attributes(("battery_size", "battery_quantity"))
    assert succ["battery_quantity"] == 1
    assert succ["battery_size"] == batt_size
