"""Tests for xiaomi."""
import asyncio
from unittest import mock

import pytest
import zigpy.device
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.clusters.security import IasZone

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
from zhaquirks.xiaomi.aqara.feeder_acn001 import (
    FEEDER_ATTR,
    ZCL_CHILD_LOCK,
    ZCL_DISABLE_LED_INDICATOR,
    ZCL_ERROR_DETECTED,
    ZCL_FEEDING,
    ZCL_FEEDING_MODE,
    ZCL_LAST_FEEDING_SIZE,
    ZCL_LAST_FEEDING_SOURCE,
    ZCL_PORTION_WEIGHT,
    ZCL_PORTIONS_DISPENSED,
    ZCL_SERVING_SIZE,
    ZCL_WEIGHT_DISPENSED,
    AqaraFeederAcn001,
    OppleCluster,
)
import zhaquirks.xiaomi.aqara.motion_aq2
import zhaquirks.xiaomi.aqara.motion_aq2b
import zhaquirks.xiaomi.aqara.plug_eu
import zhaquirks.xiaomi.aqara.smoke
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
async def test_xiaomi_motion(zigpy_device_from_quirk, quirk):
    """Test Xiaomi motion sensor."""

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


@pytest.mark.parametrize(
    "attribute, value, expected_bytes",
    [
        ("disable_led_indicator", 1, b"\x00\x02\x01\x04\x17\x00U\x01\x01"),
        ("disable_led_indicator", 0, b"\x00\x02\x01\x04\x17\x00U\x01\x00"),
        ("child_lock", 1, b"\x00\x02\x01\x04\x16\x00U\x01\x01"),
        ("child_lock", 0, b"\x00\x02\x01\x04\x16\x00U\x01\x00"),
        (
            "feeding_mode",
            OppleCluster.FeedingMode.Manual,
            b"\x00\x02\x01\x04\x18\x00U\x01\x00",
        ),
        (
            "feeding_mode",
            OppleCluster.FeedingMode.Schedule,
            b"\x00\x02\x01\x04\x18\x00U\x01\x01",
        ),
        ("serving_size", 3, b"\x00\x02\x01\x0e\\\x00U\x04\x00\x00\x00\x03"),
        ("portion_weight", 8, b"\x00\x02\x01\x0e_\x00U\x04\x00\x00\x00\x08"),
    ],
)
async def test_aqara_feeder_write_attrs(
    zigpy_device_from_quirk, attribute, value, expected_bytes
):
    """Test Aqara C1 pet feeder attr writing."""

    device = zigpy_device_from_quirk(AqaraFeederAcn001)
    opple_cluster = device.endpoints[1].opple_cluster
    opple_cluster._write_attributes = mock.AsyncMock()

    expected_attr_def = opple_cluster.find_attribute(0xFFF1)
    expected = foundation.Attribute(0xFFF1, foundation.TypeValue())
    expected.value.type = foundation.DATA_TYPES.pytype_to_datatype_id(
        expected_attr_def.type
    )
    expected.value.value = expected_attr_def.type(expected_bytes)

    await opple_cluster.write_attributes({attribute: value}, manufacturer=0x115F)

    opple_cluster._write_attributes.assert_awaited_with(
        [expected],
        manufacturer=0x115F,
    )


@pytest.mark.parametrize(
    "bytes_received, call_count, calls",
    [
        (
            b"\x1c_\x11f\n\xf1\xffA\t\x00\x05\x01\x04\x15\x00U\x01\x01",
            2,
            [
                mock.call(ZCL_FEEDING, True),
                mock.call(FEEDER_ATTR, b"\x00\x05\x01\x04\x15\x00U\x01\x01"),
            ],
        ),
        (
            b"\x1c_\x11l\n\xf1\xffA\x0c\x00\x05\xd0\x04\x15\x02\xbc\x040203",
            3,
            [
                mock.call(ZCL_LAST_FEEDING_SIZE, 3),
                mock.call(ZCL_LAST_FEEDING_SOURCE, OppleCluster.FeedingSource.Remote),
                mock.call(FEEDER_ATTR, b"\x00\x05\xd0\x04\x15\x02\xbc\x040203"),
            ],
        ),
        (
            b"\x1c_\x11m\n\xf1\xffA\n\x00\x05\xd1\rh\x00U\x02\x00!",
            2,
            [
                mock.call(ZCL_PORTIONS_DISPENSED, 33),
                mock.call(FEEDER_ATTR, b"\x00\x05\xd1\rh\x00U\x02\x00!"),
            ],
        ),
        (
            b"\x1c_\x11n\n\xf1\xffA\x0c\x00\x05\xd2\ri\x00U\x04\x00\x00\x01\x08",
            2,
            [
                mock.call(ZCL_WEIGHT_DISPENSED, 264),
                mock.call(FEEDER_ATTR, b"\x00\x05\xd2\ri\x00U\x04\x00\x00\x01\x08"),
            ],
        ),
        (
            b"\x1c_\x11o\n\xf1\xffA\t\x00\x05\xd3\r\x0b\x00U\x01\x00",
            2,
            [
                mock.call(ZCL_ERROR_DETECTED, False),
                mock.call(FEEDER_ATTR, b"\x00\x05\xd3\r\x0b\x00U\x01\x00"),
            ],
        ),
        (
            b"\x1c_\x11p\n\xf1\xffA\t\x00\x05\x05\x04\x16\x00U\x01\x01",
            2,
            [
                mock.call(ZCL_CHILD_LOCK, True),
                mock.call(FEEDER_ATTR, b"\x00\x05\x05\x04\x16\x00U\x01\x01"),
            ],
        ),
        (
            b"\x1c_\x11r\n\xf1\xffA\t\x00\x05\t\x04\x17\x00U\x01\x01",
            2,
            [
                mock.call(ZCL_DISABLE_LED_INDICATOR, True),
                mock.call(FEEDER_ATTR, b"\x00\x05\t\x04\x17\x00U\x01\x01"),
            ],
        ),
        (
            b"\x1c_\x11s\n\xf1\xffA\t\x00\x05\x0b\x04\x18\x00U\x01\x01",
            2,
            [
                mock.call(ZCL_FEEDING_MODE, OppleCluster.FeedingMode.Schedule),
                mock.call(FEEDER_ATTR, b"\x00\x05\x0b\x04\x18\x00U\x01\x01"),
            ],
        ),
        (
            b"\x1c_\x11u\n\xf1\xffA\t\x00\x05\x0f\x0e_\x00U\x01\x06",
            2,
            [
                mock.call(ZCL_PORTION_WEIGHT, 6),
                mock.call(FEEDER_ATTR, b"\x00\x05\x0f\x0e_\x00U\x01\x06"),
            ],
        ),
        (
            b"\x1c_\x11v\n\xf1\xffA\t\x00\x05\x11\x0e\\\x00U\x01\x02",
            2,
            [
                mock.call(ZCL_SERVING_SIZE, 2),
                mock.call(FEEDER_ATTR, b"\x00\x05\x11\x0e\\\x00U\x01\x02"),
            ],
        ),
        (
            b"\x1c_\x11{\n\xf7\x00A\x0e\x05!\x0e\x00\r#!%\x00\x00\t!\x02\x03",
            1,
            [
                mock.call(0x00F7, b"\x05!\x0e\x00\r#!%\x00\x00\t!\x02\x03"),
            ],
        ),
        (
            b"\x1c_\x11}\n\xf1\xffA(\x00\x05\x15\x08\x00\x08\xc8 7F09000100,7F0D000100,7F13000100",
            1,
            [
                mock.call(
                    FEEDER_ATTR,
                    b"\x00\x05\x15\x08\x00\x08\xc8 7F09000100,7F0D000100,7F13000100",
                ),
            ],
        ),
    ],
)
async def test_aqara_feeder_attr_reports(
    zigpy_device_from_quirk, bytes_received, call_count, calls
):
    """Test Aqara C1 pet feeder attr writing."""

    class Listener:

        attribute_updated = mock.MagicMock()

    device = zigpy_device_from_quirk(AqaraFeederAcn001)
    opple_cluster = device.endpoints[1].opple_cluster
    cluster_listener = Listener()
    opple_cluster.add_listener(cluster_listener)

    device.handle_message(
        260,
        opple_cluster.cluster_id,
        opple_cluster.endpoint.endpoint_id,
        opple_cluster.endpoint.endpoint_id,
        bytes_received,
    )

    assert cluster_listener.attribute_updated.call_count == call_count
    for call in calls:
        assert call in cluster_listener.attribute_updated.mock_calls


@pytest.mark.parametrize("quirk", (zhaquirks.xiaomi.aqara.smoke.LumiSensorSmokeAcn03,))
async def test_aqara_smoke_sensor_attribute_update(zigpy_device_from_quirk, quirk):
    """Test update_attribute on Aqara smoke sensor."""

    device = zigpy_device_from_quirk(quirk)

    opple_cluster = device.endpoints[1].opple_cluster
    opple_listener = ClusterListener(opple_cluster)

    ias_cluster = device.endpoints[1].ias_zone
    ias_listener = ClusterListener(ias_cluster)

    zone_status_id = IasZone.attributes_by_name["zone_status"].id

    # check that updating Xiaomi smoke attribute also updates zone status on the Ias Zone cluster

    # turn on smoke alarm
    opple_cluster._update_attribute(0x013A, 1)
    assert len(opple_listener.attribute_updates) == 1
    assert len(ias_listener.attribute_updates) == 1
    assert ias_listener.attribute_updates[0][0] == zone_status_id
    assert ias_listener.attribute_updates[0][1] == IasZone.ZoneStatus.Alarm_1

    # turn off smoke alarm
    opple_cluster._update_attribute(0x013A, 0)
    assert len(opple_listener.attribute_updates) == 2
    assert len(ias_listener.attribute_updates) == 2
    assert ias_listener.attribute_updates[1][0] == zone_status_id
    assert ias_listener.attribute_updates[1][1] == 0

    # check if fake dB/m smoke density attribute is also updated
    opple_cluster._update_attribute(0x013B, 10)
    assert len(opple_listener.attribute_updates) == 4
    assert opple_listener.attribute_updates[2][0] == 0x013B
    assert opple_listener.attribute_updates[2][1] == 10
    assert opple_listener.attribute_updates[3][0] == 0x1403  # fake attribute
    assert opple_listener.attribute_updates[3][1] == 0.125


@pytest.mark.parametrize(
    "raw_report, expected_zone_status",
    (
        (
            "1C5F11E10AF700413E0121360C0328190421A81305211E0006240200000000082111010A21"
            "00000C20016620036720016821A800A0210000A12000A22000A32000A42000A52000",
            0,
        ),
    ),
)
async def test_aqara_smoke_sensor_xiaomi_attribute_report(
    zigpy_device_from_quirk, raw_report, expected_zone_status
):
    """Test that a Xiaomi attribute report changes the IAS zone status on Aqara smoke sensor."""
    raw_report = bytes.fromhex(raw_report)

    device = zigpy_device_from_quirk(zhaquirks.xiaomi.aqara.smoke.LumiSensorSmokeAcn03)

    opple_cluster = device.endpoints[1].opple_cluster
    opple_listener = ClusterListener(opple_cluster)

    ias_cluster = device.endpoints[1].ias_zone
    ias_listener = ClusterListener(ias_cluster)

    device.handle_message(
        260,
        opple_cluster.cluster_id,
        opple_cluster.endpoint.endpoint_id,
        opple_cluster.endpoint.endpoint_id,
        raw_report,
    )

    # check that Xiaomi attribute report also updates attribute cache
    assert len(opple_listener.attribute_updates) == 1
    assert opple_listener.attribute_updates[0][0] == 0x00F7

    # check that Xiaomi attribute report resets smoke zone status
    assert len(ias_listener.attribute_updates) == 1
    assert (
        ias_listener.attribute_updates[0][0]
        == IasZone.attributes_by_name["zone_status"].id
    )
    assert ias_listener.attribute_updates[0][1] == expected_zone_status


@pytest.mark.parametrize(
    "attr_redirect, attr_no_redirect",
    [
        ("system_mode", "unoccupied_heating_setpoint"),
        (
            Thermostat.attributes_by_name["system_mode"].id,
            Thermostat.attributes_by_name["unoccupied_heating_setpoint"].id,
        ),
    ],
)
async def test_xiaomi_e1_thermostat_rw_redirection(
    zigpy_device_from_quirk,
    attr_redirect,
    attr_no_redirect,
):
    """Test system_mode rw redirection to OppleCluster on Xiaomi E1 thermostat with id and named reads/writes."""

    device = zigpy_device_from_quirk(zhaquirks.xiaomi.aqara.thermostat_agl001.AGL001)

    opple_cluster = device.endpoints[1].opple_cluster
    opple_listener = ClusterListener(opple_cluster)

    thermostat_cluster = device.endpoints[1].thermostat
    thermostat_listener = ClusterListener(thermostat_cluster)

    # fake read response for attributes: return 1 for all attributes
    def mock_read(attributes, manufacturer=None):
        records = [
            foundation.ReadAttributeRecord(
                attr, foundation.Status.SUCCESS, foundation.TypeValue(None, 1)
            )
            for attr in attributes
        ]
        return (records,)

    # patch read commands
    patch_opple_read = mock.patch.object(
        opple_cluster, "_read_attributes", mock.AsyncMock(side_effect=mock_read)
    )
    patch_thermostat_read = mock.patch.object(
        thermostat_cluster, "_read_attributes", mock.AsyncMock(side_effect=mock_read)
    )

    # patch write commands
    patch_opple_write = mock.patch.object(
        opple_cluster,
        "_write_attributes",
        mock.AsyncMock(
            return_value=(
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],
            )
        ),
    )
    patch_thermostat_write = mock.patch.object(
        thermostat_cluster,
        "_write_attributes",
        mock.AsyncMock(
            return_value=(
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],
            )
        ),
    )

    with patch_opple_read, patch_thermostat_read, patch_opple_write, patch_thermostat_write:
        # test reads:

        # read system_mode attribute from thermostat cluster
        await thermostat_cluster.read_attributes([attr_redirect])

        # check that system_mode reads were directed to the Opple cluster
        assert len(thermostat_cluster._read_attributes.mock_calls) == 0
        assert len(opple_cluster._read_attributes.mock_calls) == 1
        assert opple_cluster._read_attributes.mock_calls[0][1][0] == [
            0x0271
        ]  # Opple system_mode attribute
        assert thermostat_listener.attribute_updates[0] == (
            Thermostat.attributes_by_name["system_mode"].id,
            Thermostat.SystemMode.Heat,
        )  # check that attributes are correctly mapped and updated on ZCL thermostat cluster

        thermostat_cluster._read_attributes.reset_mock()
        opple_cluster._read_attributes.reset_mock()

        # check that other attribute reads are not redirected
        await thermostat_cluster.read_attributes([attr_no_redirect])

        assert len(thermostat_cluster._read_attributes.mock_calls) == 1
        assert len(opple_cluster._read_attributes.mock_calls) == 0

        thermostat_cluster._read_attributes.reset_mock()
        opple_cluster._read_attributes.reset_mock()

        # test writes:

        # write system_mode attribute to thermostat cluster
        await thermostat_cluster.write_attributes(
            {attr_redirect: Thermostat.SystemMode.Heat}
        )

        # check that system_mode writes were directed to the Opple cluster
        assert len(thermostat_cluster._write_attributes.mock_calls) == 0
        assert len(opple_cluster._write_attributes.mock_calls) == 1
        assert opple_listener.attribute_updates[1] == (0x0271, 1)  # Opple system_mode

        assert thermostat_listener.attribute_updates[2] == (
            Thermostat.attributes_by_name["system_mode"].id,
            Thermostat.SystemMode.Heat,
        )  # check ZCL attribute is in correct mode

        thermostat_cluster._write_attributes.reset_mock()
        opple_cluster._write_attributes.reset_mock()

        # check that other attribute writes are not redirected
        await thermostat_cluster.write_attributes({attr_no_redirect: 2000})

        assert len(thermostat_cluster._write_attributes.mock_calls) == 1
        assert len(opple_cluster._write_attributes.mock_calls) == 0


@pytest.mark.parametrize("quirk", (zhaquirks.xiaomi.aqara.thermostat_agl001.AGL001,))
async def test_xiaomi_e1_thermostat_attribute_update(zigpy_device_from_quirk, quirk):
    """Test update_attribute on Xiaomi E1 thermostat."""

    device = zigpy_device_from_quirk(quirk)

    opple_cluster = device.endpoints[1].opple_cluster
    opple_listener = ClusterListener(opple_cluster)

    thermostat_cluster = device.endpoints[1].thermostat
    thermostat_listener = ClusterListener(thermostat_cluster)

    power_config_cluster = device.endpoints[1].power
    power_config_listener = ClusterListener(power_config_cluster)

    zcl_system_mode_id = Thermostat.attributes_by_name["system_mode"].id
    zcl_battery_percentage_id = PowerConfiguration.attributes_by_name[
        "battery_percentage_remaining"
    ].id

    # check that updating Xiaomi system_mode also updates an attribute on the Thermostat cluster

    # turn off heating
    opple_cluster._update_attribute(0x0271, 0)
    assert len(opple_listener.attribute_updates) == 1
    assert len(thermostat_listener.attribute_updates) == 1
    assert thermostat_listener.attribute_updates[0][0] == zcl_system_mode_id
    assert thermostat_listener.attribute_updates[0][1] == Thermostat.SystemMode.Off

    # turn on heating
    opple_cluster._update_attribute(0x0271, 1)
    assert len(opple_listener.attribute_updates) == 2
    assert len(thermostat_listener.attribute_updates) == 2
    assert thermostat_listener.attribute_updates[1][0] == zcl_system_mode_id
    assert thermostat_listener.attribute_updates[1][1] == Thermostat.SystemMode.Heat

    # check that updating battery_percentage on the OppleCluster also updates the PowerConfiguration cluster
    opple_cluster._update_attribute(0x040A, 50)  # 50% battery
    assert len(opple_listener.attribute_updates) == 3
    assert len(power_config_listener.attribute_updates) == 1
    assert power_config_listener.attribute_updates[0][0] == zcl_battery_percentage_id
    assert power_config_listener.attribute_updates[0][1] == 100  # ZCL is doubled
