"""Tests for xiaomi."""
import asyncio
from unittest import mock

import pytest
import zigpy.device
import zigpy.types as t
from zigpy.zcl import foundation

import zhaquirks
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
    CONSUMPTION_REPORTED,
    LUMI,
    POWER_REPORTED,
    VOLTAGE_REPORTED,
    XIAOMI_NODE_DESC,
    BasicCluster,
    XiaomiCustomDevice,
    XiaomiQuickInitDevice,
    handle_quick_init,
)
import zhaquirks.xiaomi.aqara.motion_aq2
import zhaquirks.xiaomi.aqara.motion_aq2b
import zhaquirks.xiaomi.aqara.plug_eu
import zhaquirks.xiaomi.mija.motion

from tests.common import ZCL_OCC_ATTR_RPT_OCC, ClusterListener

zhaquirks.setup()


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


@pytest.mark.parametrize(
    "raw_report",
    (
        # https://community.hubitat.com/t/xiaomi-aqara-devices-pairing-keeping-them-connected/623?page=34
        "02FF4C0600100121BA0B21A813240100000000215D062058",
        "02FF4C0600100021EC0B21A8012400000000002182002063",
        "01FF421F0121110D0328130421A8430521F60006240600030000082108140A21E51F",
        "01FF421A0121C70B03281C0421A84305212B01062403000300000A2120CB",
        "01FF421F0121C70B0328190421A8430521100106240400040000082109140A2120CB",
        "01FF421F0121C70B0328180421A8430521100106240600050000082109140A213C50",
        "01FF421A0121BD0B03281D0421A84305212F01062407000300000A2120CB",
        # https://community.hubitat.com/t/xiaomi-aqara-zigbee-device-drivers-possibly-may-no-longer-be-maintained/631/print
        "01FF42090421A8130A212759",
        (
            "01FF42296410006510016E20006F20010121E40C03281E05210500082116260A2100009923"
            "000000009B210000"
        ),
        "01FF42220121D10B0328190421A81305212D0006240200000000082104020A21A4B4641000",
        "01FF42220121D10B03281C0421A81305213A0006240000000000082104020A210367641001",
        (
            "01FF42280121B70C0328200421A81305211E00062402000000000A21E18C08210410642000"
            "962300000000"
        ),
        (
            "01FF42270328240521170007270000000000000000082117010921000A0A2130C064200065"
            "20336621FA00"
        ),
        "02FF4C0600100121B30B21A8012400000000002195002056",
        "02FF4C0600100121B30B21A8012400000000002195002057",
        # puddly's logs
        "01FF421A0121DB0B03280C0421A84305215401062401000000000A2178E0",
        "01FF421D0121BD0B03280A0421A8330521E801062401000000000A214444641000",
        "01FF421F0121E50B0328170421A8130521500006240100000000082105140A214761",
        "01FF42210121950B0328130421A81305214400062401000000000A217CBE6410000B210400",
        (
            "01FF42250121630B0421A81305217D2F06240100000000642905006521631D662B4D7F0100"
            "0A2157DE"
        ),
        "02FF4C06001001213C0C21A81324010000000021D1052061",
        (
            "050042166C756D692E73656E736F725F6D6F74696F6E2E61713201FF42210121950B032816"
            "0421A83105214400062401000000000A217CBE6410000B210900"
        ),
        # GH Issue #811
        (
            "01FF424403282305212E0008212E12092100106410006510006E20006F200094200295390A"
            "078C41963999EB0C4597390030683B983980BB873C9B2100009C20010A2100000C280000"
        ),
        # https://github.com/dresden-elektronik/deconz-rest-plugin/issues/1491#issuecomment-489032272
        (
            "01FF422E0121BD0B03281A0421A8430521470106240100010000082108030A216535982128"
            "00992125009A252900FFFFDC04"
        ),
        # https://github.com/dresden-elektronik/deconz-rest-plugin/issues/1411#issuecomment-485724957
        (
            "01FF424403280005210F000727000000000000000008212312092100086410006510006E20"
            "006F20009420089539000000009639B22E1645973988E5C83B9839C013063E9B210000"
        ),
        # https://github.com/dresden-elektronik/deconz-rest-plugin/issues/1588
        (
            "01FF422E0121770B0328230421A8010521250006240100000000082108030A2161F3982128"
            "00992100009A25AFFE5B016904"
        ),
        # https://github.com/dresden-elektronik/deconz-rest-plugin/issues/1069
        "02FF4C0600100121D10B21A801240000000000216E002050",
        "01FF421D0121D10B0328150421A8130521A200062403000000000A210000641000",
        "01FF421D0121DB0B0328140421A84305219A00062401000000000A21C841641000",
        "01FF421D0121BD0B0328150421A83305213B00062401000000000A219FF8641000",
        "01FF421D0121C70B0328130421A81305219200062401000000000A21C96B641000",
    ),
)
def test_attribute_parsing(raw_report):
    """Test the parsing of various Xiaomi 0xFF01 attribute reports."""
    raw_report = bytes.fromhex(raw_report)

    hdr = foundation.ZCLHeader.general(
        manufacturer=4447,
        tsn=127,
        command_id=foundation.GeneralCommand.Report_Attributes,
    )
    cluster = BasicCluster(mock.MagicMock())

    hdr, reports = cluster.deserialize(hdr.serialize() + raw_report)

    # Keep track of all the data encoded in the attribute report
    parsed_chunks = []

    for report in reports[0]:
        # This shouldn't throw an error
        cluster._update_attribute(report.attrid, report.value.value)

        parsed_chunks.append(report.attrid.serialize())
        parsed_chunks.append(report.value.value.serialize()[1:])

    # Remove every parsed chunk from the original report bytes
    for chunk in parsed_chunks:
        raw_report = raw_report.replace(chunk, b"", 1)

    # The only remaining data should be the data type and the length.
    # Everything else is passed through unmodified.
    assert len(raw_report) == 2 * len(reports[0])


@mock.patch("zigpy.zcl.Cluster.bind", mock.AsyncMock())
@pytest.mark.parametrize("quirk", (zhaquirks.xiaomi.aqara.plug_eu.PlugMAEU01,))
async def test_xiaomi_eu_plug_binding(zigpy_device_from_quirk, quirk):
    """Test binding Xiaomi EU plug sets OppleMode to True and removes the plug from group 0."""

    device = zigpy_device_from_quirk(quirk)
    opple_cluster = device.endpoints[1].opple_cluster

    p1 = mock.patch.object(opple_cluster, "create_catching_task")
    p2 = mock.patch.object(opple_cluster.endpoint, "request", mock.AsyncMock())

    with p1 as mock_task, p2 as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        await opple_cluster.bind()

        # Only removed the plug from group 0 so far
        assert len(request_mock.mock_calls) == 1
        assert mock_task.call_count == 1

        assert request_mock.mock_calls[0][1] == (
            4,
            1,
            b"\x01\x01\x03\x00\x00",
        )

        # Await call writing OppleMode attribute
        await mock_task.call_args[0][0]

        assert len(request_mock.mock_calls) == 2
        assert request_mock.mock_calls[1][1] == (
            64704,
            2,
            b"\x04_\x11\x02\x02\t\x00 \x01",
        )


@pytest.mark.parametrize("quirk", (zhaquirks.xiaomi.aqara.plug_eu.PlugMAEU01,))
async def test_xiaomi_eu_plug_power(zigpy_device_from_quirk, quirk):
    """Test current power consumption, total power consumption, and current voltage on Xiaomi EU plug."""

    device = zigpy_device_from_quirk(quirk)

    em_cluster = device.endpoints[1].electrical_measurement
    em_listener = ClusterListener(em_cluster)

    # Test voltage on ElectricalMeasurement cluster
    em_cluster.endpoint.device.voltage_bus.listener_event(VOLTAGE_REPORTED, 230)
    assert len(em_listener.attribute_updates) == 1
    assert em_listener.attribute_updates[0][0] == 1285
    assert em_listener.attribute_updates[0][1] == 230

    # Test current power consumption on ElectricalMeasurement cluster
    em_cluster.endpoint.device.power_bus.listener_event(POWER_REPORTED, 15)
    assert len(em_listener.attribute_updates) == 2
    assert em_listener.attribute_updates[1][0] == 1291
    assert em_listener.attribute_updates[1][1] == 150  # multiplied by 10

    # Test total power consumption on ElectricalMeasurement cluster
    em_cluster.endpoint.device.consumption_bus.listener_event(
        CONSUMPTION_REPORTED, 0.001
    )
    assert len(em_listener.attribute_updates) == 3
    assert em_listener.attribute_updates[2][0] == 772
    assert em_listener.attribute_updates[2][1] == 1  # multiplied by 1000

    # Test total power consumption on SmartEnergy cluster
    se_cluster = device.endpoints[1].smartenergy_metering
    se_listener = ClusterListener(se_cluster)

    se_cluster.endpoint.device.consumption_bus.listener_event(
        CONSUMPTION_REPORTED, 0.001
    )
    assert len(se_listener.attribute_updates) == 1
    assert se_listener.attribute_updates[0][0] == 0
    assert se_listener.attribute_updates[0][1] == 1  # multiplied by 1000
