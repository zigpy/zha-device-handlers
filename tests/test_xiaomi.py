"""Tests for xiaomi."""

import asyncio
import logging
import math
from unittest import mock

import pytest
import zigpy.device
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    AnalogInput,
    AnalogOutput,
    DeviceTemperature,
    MultistateInput,
    MultistateOutput,
    OnOff,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    PressureMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ZCL_OCC_ATTR_RPT_OCC, ClusterListener
import zhaquirks
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
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
    ZONE_STATUS_CHANGE_COMMAND,
)
from zhaquirks.xiaomi import (
    LUMI,
    XIAOMI_AQARA_ATTRIBUTE,
    XIAOMI_AQARA_ATTRIBUTE_E1,
    XIAOMI_NODE_DESC,
    BasicCluster,
    XiaomiCustomDevice,
    XiaomiQuickInitDevice,
    handle_quick_init,
)
import zhaquirks.xiaomi.aqara.driver_curtain_e1
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
import zhaquirks.xiaomi.aqara.magnet_agl02
import zhaquirks.xiaomi.aqara.motion_ac02
import zhaquirks.xiaomi.aqara.motion_agl02
import zhaquirks.xiaomi.aqara.motion_aq2
import zhaquirks.xiaomi.aqara.motion_aq2b
import zhaquirks.xiaomi.aqara.plug
import zhaquirks.xiaomi.aqara.plug_eu
import zhaquirks.xiaomi.aqara.roller_curtain_e1
import zhaquirks.xiaomi.aqara.sensor_ht_agl02
import zhaquirks.xiaomi.aqara.smoke
import zhaquirks.xiaomi.aqara.switch_t1
from zhaquirks.xiaomi.aqara.thermostat_agl001 import ScheduleEvent, ScheduleSettings
import zhaquirks.xiaomi.aqara.weather
import zhaquirks.xiaomi.mija.motion

zhaquirks.setup()


def create_aqara_attr_report(attributes):
    """Create a special Aqara attribute report with t.Single as a type for all values."""
    serialized_data = b""
    for key, value in attributes.items():
        tv = foundation.TypeValue(0x39, t.Single(value))  # mostly used
        serialized_data += bytes([key]) + tv.serialize()
    return serialized_data


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
    assert motion_listener.cluster_commands[0][1] == ZONE_STATUS_CHANGE_COMMAND
    assert motion_listener.cluster_commands[0][2][0] == ON

    assert len(occupancy_listener.cluster_commands) == 0
    assert len(occupancy_listener.attribute_updates) == 1
    assert occupancy_listener.attribute_updates[0][0] == 0x0000
    assert occupancy_listener.attribute_updates[0][1] == 1

    await asyncio.sleep(0.1)

    assert len(motion_listener.cluster_commands) == 2
    assert motion_listener.cluster_commands[1][1] == ZONE_STATUS_CHANGE_COMMAND
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
            b"\x18\x00\xff\x05\x00B\x11lumi.sensor_sm0ke\x01\x00 \x01",
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

        assert request_mock.mock_calls[0]
        assert request_mock.mock_calls[0].kwargs["cluster"] == 4
        assert request_mock.mock_calls[0].kwargs["sequence"] == 1
        assert request_mock.mock_calls[0].kwargs["data"] == b"\x01\x01\x03\x00\x00"

        # Await call writing OppleMode attribute
        await mock_task.call_args[0][0]

        assert len(request_mock.mock_calls) == 2
        assert request_mock.mock_calls[1].kwargs["cluster"] == 64704
        assert request_mock.mock_calls[1].kwargs["sequence"] == 2
        assert (
            request_mock.mock_calls[1].kwargs["data"] == b"\x04_\x11\x02\x02\t\x00 \x01"
        )


@pytest.mark.parametrize(
    "quirk",
    (
        zhaquirks.xiaomi.aqara.plug_eu.PlugMAEU01,
        zhaquirks.xiaomi.aqara.switch_t1.SwitchT1,
    ),
)
async def test_xiaomi_plug_power(zigpy_device_from_quirk, quirk):
    """Test current power consumption, total power consumption, and current voltage on Xiaomi EU plug and T1 relay."""

    device = zigpy_device_from_quirk(quirk)
    basic_cluster = device.endpoints[1].basic

    em_cluster = device.endpoints[1].electrical_measurement
    em_listener = ClusterListener(em_cluster)

    # Test voltage on ElectricalMeasurement cluster
    zcl_em_voltage = ElectricalMeasurement.AttributeDefs.rms_voltage.id
    basic_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE, create_aqara_attr_report({150: 2300})
    )
    assert len(em_listener.attribute_updates) == 1
    assert em_listener.attribute_updates[0][0] == zcl_em_voltage
    assert em_listener.attribute_updates[0][1] == 230

    # Test current power consumption on ElectricalMeasurement cluster
    zcl_em_current_power = ElectricalMeasurement.AttributeDefs.active_power.id
    basic_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE, create_aqara_attr_report({152: 15})
    )
    assert len(em_listener.attribute_updates) == 2
    assert em_listener.attribute_updates[1][0] == zcl_em_current_power
    assert em_listener.attribute_updates[1][1] == 150  # multiplied by 10

    # Test total power consumption on ElectricalMeasurement cluster and SmartEnergy cluster
    zcl_em_total_power = ElectricalMeasurement.AttributeDefs.total_active_power.id
    zcl_se_total_power = Metering.AttributeDefs.current_summ_delivered.id
    se_cluster = device.endpoints[1].smartenergy_metering
    se_listener = ClusterListener(se_cluster)

    basic_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE, create_aqara_attr_report({149: 0.001})
    )
    # electrical measurement cluster
    assert len(em_listener.attribute_updates) == 3
    assert em_listener.attribute_updates[2][0] == zcl_em_total_power
    assert em_listener.attribute_updates[2][1] == 1  # multiplied by 1000

    # smart energy cluster
    assert len(se_listener.attribute_updates) == 1
    assert se_listener.attribute_updates[0][0] == zcl_se_total_power
    assert se_listener.attribute_updates[0][1] == 1  # multiplied by 1000

    # test current power consumption attribute report on AnalogInput is forwarded to ElectricalMeasurement
    analog_input_cluster = device.endpoints[21].analog_input
    analog_input_listener = ClusterListener(analog_input_cluster)
    zcl_analog_input_value = AnalogInput.AttributeDefs.present_value.id

    analog_input_cluster.update_attribute(zcl_analog_input_value, 40)
    assert len(analog_input_listener.attribute_updates) == 1
    assert analog_input_listener.attribute_updates[0][0] == zcl_analog_input_value
    assert analog_input_listener.attribute_updates[0][1] == 40

    assert em_listener.attribute_updates[3][0] == zcl_em_current_power
    assert em_listener.attribute_updates[3][1] == 400  # multiplied by 10


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
    expected.value.type = foundation.DataType.from_python_type(
        expected_attr_def.type
    ).type_id
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
                mock.call(ZCL_FEEDING, True, mock.ANY),
                mock.call(FEEDER_ATTR, b"\x00\x05\x01\x04\x15\x00U\x01\x01", mock.ANY),
            ],
        ),
        (
            b"\x1c_\x11l\n\xf1\xffA\x0c\x00\x05\xd0\x04\x15\x02\xbc\x040203",
            3,
            [
                mock.call(ZCL_LAST_FEEDING_SIZE, 3, mock.ANY),
                mock.call(
                    ZCL_LAST_FEEDING_SOURCE, OppleCluster.FeedingSource.Remote, mock.ANY
                ),
                mock.call(
                    FEEDER_ATTR, b"\x00\x05\xd0\x04\x15\x02\xbc\x040203", mock.ANY
                ),
            ],
        ),
        (
            b"\x1c_\x11m\n\xf1\xffA\n\x00\x05\xd1\rh\x00U\x02\x00!",
            2,
            [
                mock.call(ZCL_PORTIONS_DISPENSED, 33, mock.ANY),
                mock.call(FEEDER_ATTR, b"\x00\x05\xd1\rh\x00U\x02\x00!", mock.ANY),
            ],
        ),
        (
            b"\x1c_\x11n\n\xf1\xffA\x0c\x00\x05\xd2\ri\x00U\x04\x00\x00\x01\x08",
            2,
            [
                mock.call(ZCL_WEIGHT_DISPENSED, 264, mock.ANY),
                mock.call(
                    FEEDER_ATTR, b"\x00\x05\xd2\ri\x00U\x04\x00\x00\x01\x08", mock.ANY
                ),
            ],
        ),
        (
            b"\x1c_\x11o\n\xf1\xffA\t\x00\x05\xd3\r\x0b\x00U\x01\x00",
            2,
            [
                mock.call(ZCL_ERROR_DETECTED, False, mock.ANY),
                mock.call(FEEDER_ATTR, b"\x00\x05\xd3\r\x0b\x00U\x01\x00", mock.ANY),
            ],
        ),
        (
            b"\x1c_\x11p\n\xf1\xffA\t\x00\x05\x05\x04\x16\x00U\x01\x01",
            2,
            [
                mock.call(ZCL_CHILD_LOCK, True, mock.ANY),
                mock.call(FEEDER_ATTR, b"\x00\x05\x05\x04\x16\x00U\x01\x01", mock.ANY),
            ],
        ),
        (
            b"\x1c_\x11r\n\xf1\xffA\t\x00\x05\t\x04\x17\x00U\x01\x01",
            2,
            [
                mock.call(ZCL_DISABLE_LED_INDICATOR, True, mock.ANY),
                mock.call(FEEDER_ATTR, b"\x00\x05\t\x04\x17\x00U\x01\x01", mock.ANY),
            ],
        ),
        (
            b"\x1c_\x11s\n\xf1\xffA\t\x00\x05\x0b\x04\x18\x00U\x01\x01",
            2,
            [
                mock.call(
                    ZCL_FEEDING_MODE, OppleCluster.FeedingMode.Schedule, mock.ANY
                ),
                mock.call(FEEDER_ATTR, b"\x00\x05\x0b\x04\x18\x00U\x01\x01", mock.ANY),
            ],
        ),
        (
            b"\x1c_\x11u\n\xf1\xffA\t\x00\x05\x0f\x0e_\x00U\x01\x06",
            2,
            [
                mock.call(ZCL_PORTION_WEIGHT, 6, mock.ANY),
                mock.call(FEEDER_ATTR, b"\x00\x05\x0f\x0e_\x00U\x01\x06", mock.ANY),
            ],
        ),
        (
            b"\x1c_\x11v\n\xf1\xffA\t\x00\x05\x11\x0e\\\x00U\x01\x02",
            2,
            [
                mock.call(ZCL_SERVING_SIZE, 2, mock.ANY),
                mock.call(FEEDER_ATTR, b"\x00\x05\x11\x0e\\\x00U\x01\x02", mock.ANY),
            ],
        ),
        (
            b"\x1c_\x11{\n\xf7\x00A\x0e\x05!\x0e\x00\r#!%\x00\x00\t!\x02\x03",
            1,
            [
                mock.call(0x00F7, b"\x05!\x0e\x00\r#!%\x00\x00\t!\x02\x03", mock.ANY),
            ],
        ),
        (
            b"\x1c_\x11}\n\xf1\xffA(\x00\x05\x15\x08\x00\x08\xc8 7F09000100,7F0D000100,7F13000100",
            1,
            [
                mock.call(
                    FEEDER_ATTR,
                    b"\x00\x05\x15\x08\x00\x08\xc8 7F09000100,7F0D000100,7F13000100",
                    mock.ANY,
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

    zone_status_id = IasZone.AttributeDefs.zone_status.id

    # check that updating Xiaomi smoke attribute also updates zone status on the Ias Zone cluster

    # turn on smoke alarm
    opple_cluster.update_attribute(0x013A, 1)
    assert len(opple_listener.attribute_updates) == 1
    assert len(ias_listener.attribute_updates) == 1
    assert ias_listener.attribute_updates[0][0] == zone_status_id
    assert ias_listener.attribute_updates[0][1] == IasZone.ZoneStatus.Alarm_1

    # turn off smoke alarm
    opple_cluster.update_attribute(0x013A, 0)
    assert len(opple_listener.attribute_updates) == 2
    assert len(ias_listener.attribute_updates) == 2
    assert ias_listener.attribute_updates[1][0] == zone_status_id
    assert ias_listener.attribute_updates[1][1] == 0

    # check if fake dB/m smoke density attribute is also updated
    opple_cluster.update_attribute(0x013B, 10)
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
    assert ias_listener.attribute_updates[0][0] == IasZone.AttributeDefs.zone_status.id
    assert ias_listener.attribute_updates[0][1] == expected_zone_status


@pytest.mark.parametrize(
    "attr_redirect, attr_no_redirect",
    [
        ("system_mode", "unoccupied_heating_setpoint"),
        (
            Thermostat.AttributeDefs.system_mode.id,
            Thermostat.AttributeDefs.unoccupied_heating_setpoint.id,
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

    with (
        patch_opple_read,
        patch_thermostat_read,
        patch_opple_write,
        patch_thermostat_write,
    ):
        # test reads:

        # read system_mode attribute from thermostat cluster
        await thermostat_cluster.read_attributes([attr_redirect])

        # check that system_mode reads were directed to the Opple cluster
        assert len(thermostat_cluster._read_attributes.mock_calls) == 0
        assert len(opple_cluster._read_attributes.mock_calls) == 1
        assert opple_cluster._read_attributes.mock_calls[0][1][0] == [
            0x0271
        ]  # Opple system_mode attribute
        assert (
            thermostat_listener.attribute_updates[0]
            == (
                Thermostat.AttributeDefs.system_mode.id,
                Thermostat.SystemMode.Heat,
            )
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
            Thermostat.AttributeDefs.system_mode.id,
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

    zcl_system_mode_id = Thermostat.AttributeDefs.system_mode.id
    zcl_battery_percentage_id = (
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
    )

    # check that updating Xiaomi system_mode also updates an attribute on the Thermostat cluster

    # turn off heating
    opple_cluster.update_attribute(0x0271, 0)
    assert len(opple_listener.attribute_updates) == 1
    assert len(thermostat_listener.attribute_updates) == 1
    assert thermostat_listener.attribute_updates[0][0] == zcl_system_mode_id
    assert thermostat_listener.attribute_updates[0][1] == Thermostat.SystemMode.Off

    # turn on heating
    opple_cluster.update_attribute(0x0271, 1)
    assert len(opple_listener.attribute_updates) == 2
    assert len(thermostat_listener.attribute_updates) == 2
    assert thermostat_listener.attribute_updates[1][0] == zcl_system_mode_id
    assert thermostat_listener.attribute_updates[1][1] == Thermostat.SystemMode.Heat

    # check that updating battery_percentage on the OppleCluster also updates the PowerConfiguration cluster
    opple_cluster.update_attribute(0x040A, 50)  # 50% battery
    assert len(opple_listener.attribute_updates) == 3
    assert len(power_config_listener.attribute_updates) == 1
    assert power_config_listener.attribute_updates[0][0] == zcl_battery_percentage_id
    assert power_config_listener.attribute_updates[0][1] == 100  # ZCL is doubled


@pytest.mark.parametrize(
    "schedule_settings",
    [
        "mon,tue,wed,thu,fri|8:00,24.0|18:00,17.0|23:00,22.0|8:00,22.0",
        "mon,tue,wed,thu,fri,sat,sun|8:00,24.0|18:00,17.0|23:00,22.0|8:00,22.0",
        "mon|8:00,21.5|18:30,17.5|23:00,22.0|8:00,22.5",
    ],
)
async def test_xiaomi_e1_thermostat_schedule_settings_string_representation(
    schedule_settings,
):
    """Test creation of ScheduleSettings from str and converting back to same str."""

    s = ScheduleSettings(schedule_settings)
    assert str(s) == schedule_settings


@pytest.mark.parametrize(
    "schedule_settings",
    [
        "invalid|8:00,24.0|18:00,17.0|23:00,22.0|8:00,22.0",
        "mon,tue,wed,thu,fri|8:00,24.0|18:00,17.0|23:00,22.0",
        "mon,tue,wed,thu,fri|8:00,24.0|18:00,17.0|23:00,22.0|8:00,22.0|9:00,25.0",
        "mon,tue,wed,thu,fri,sat,sun,some_day|8:00,24.0|18:00,17.0|23:00,22.0|8:00,22.0",
        "mon|some_time,21.5|18:30,17.5|23:00,22.0|8:00,22.5",
        "mon|8:00,some_temp|18:30,17.5|23:00,22.0|8:00,22.5",
        "mon,tue,wed,thu,fri|8:00,24.0|8:30,17.0|23:00,22.0|8:00,22.0",
        "mon,tue,wed,thu,fri|8:00,24.0|18:00,17.0|23:00,22.0|9:00,22.0",
        "mon,tue,wed,thu,fri|8:00.24.0|18:00,17.0|23:00,22.0|9:00,22.0",
        "mon,tue,wed,thu,fri|-8:00,24.0|18:00,17.0|23:00,22.0|9:00,22.0",
        "mon,tue,wed,thu,fri|8:00,24.0|18:00,17.0|23:00,22.0|25:00,22.0",
        "mon,tue,wed,thu,fri|8:00,03.0|18:00,17.0|23:00,22.0|9:00,22.0",
        "mon,tue,wed,thu,fri|8:00,31.0|18:00,17.0|23:00,22.0|9:00,22.0",
        "mon,mon|8:00,24.0|18:00,17.0|23:00,22.0|8:00,22.0",
        "mon,tue,wed,thu,fri|8:00,24.1|18:00,17.0|23:00,22.0|9:00,22.0",
        b"\x04>\x01\xe0\x00\x00\t`\x048\x00\x00\x06\xa4\x05d\x00\x00\x08\x98\x81\xe0\x00\x00\x08\x98\x00",
        b"\x00>\x01\xe0\x00\x00\t`\x048\x00\x00\x06\xa4\x05d\x00\x00\x08\x98\x81\xe0\x00\x00\x08\x98",
        b"\x04\x01\x01\xe0\x00\x00\t`\x048\x00\x00\x06\xa4\x05d\x00\x00\x08\x98\x81\xe0\x00\x00\x08\x98",
        None,
    ],
)
async def test_xiaomi_e1_thermostat_schedule_settings_data_validation(
    schedule_settings,
):
    """Test data validation of ScheduleSettings class."""

    with pytest.raises(Exception):
        ScheduleSettings(schedule_settings)


@pytest.mark.parametrize(
    "schedule_event",
    [
        b"\x01\xe0\x00\x00",
        None,
    ],
)
async def test_xiaomi_e1_thermostat_schedule_event_data_validation(schedule_event):
    """Test data validation of ScheduleEvent class."""

    with pytest.raises(Exception):
        ScheduleEvent(schedule_event)


@pytest.mark.parametrize(
    "schedule_settings, expected_bytes",
    [
        (
            "mon,tue,wed,thu,fri|8:00,24.0|18:00,17.0|23:00,22.0|8:00,22.0",
            b"\x1a\x04>\x01\xe0\x00\x00\t`\x048\x00\x00\x06\xa4\x05d\x00\x00\x08\x98\x81\xe0\x00\x00\x08\x98",
        )
    ],
)
async def test_xiaomi_e1_thermostat_schedule_settings_serialization(
    schedule_settings, expected_bytes
):
    """Test that serialization works correctly."""

    s = ScheduleSettings(schedule_settings)
    assert s.serialize() == expected_bytes


@pytest.mark.parametrize(
    "schedule_settings, expected_string",
    [
        (
            b"\x04>\x01\xe0\x00\x00\t`\x048\x00\x00\x06\xa4\x05d\x00\x00\x08\x98\x81\xe0\x00\x00\x08\x98",
            "mon,tue,wed,thu,fri|8:00,24.0|18:00,17.0|23:00,22.0|8:00,22.0",
        )
    ],
)
async def test_xiaomi_e1_thermostat_schedule_settings_deserialization(
    schedule_settings, expected_string
):
    """Test that deserialization works correctly."""

    s = ScheduleSettings(schedule_settings)
    assert str(s) == expected_string


@pytest.mark.parametrize(
    "quirk, invalid_iilluminance_report",
    (
        (zhaquirks.xiaomi.aqara.motion_ac02.LumiMotionAC02, 0),
        (zhaquirks.xiaomi.aqara.motion_agl02.MotionT1, -1),
        (zhaquirks.xiaomi.aqara.motion_acn001.MotionE1, -1),
    ),
)
async def test_xiaomi_p1_t1_motion_sensor(
    zigpy_device_from_quirk, quirk, invalid_iilluminance_report
):
    """Test Aqara P1, T1, and E1 motion sensors."""

    device = zigpy_device_from_quirk(quirk)

    opple_cluster = device.endpoints[1].opple_cluster
    opple_listener = ClusterListener(opple_cluster)

    ias_cluster = device.endpoints[1].ias_zone
    ias_listener = ClusterListener(ias_cluster)

    occupancy_cluster = device.endpoints[1].occupancy
    occupancy_listener = ClusterListener(occupancy_cluster)

    illuminance_cluster = device.endpoints[1].illuminance
    illuminance_listener = ClusterListener(illuminance_cluster)

    zcl_zone_status_change_cmd_id = (
        IasZone.ClientCommandDefs.status_change_notification.id
    )
    zcl_occupancy_id = OccupancySensing.AttributeDefs.occupancy.id
    zcl_iilluminance_id = IlluminanceMeasurement.AttributeDefs.measured_value.id

    # send motion and illuminance report 10
    opple_cluster.update_attribute(274, 10 + 65536)

    # confirm manufacturer specific attribute report
    assert len(opple_listener.attribute_updates) == 1
    assert opple_listener.attribute_updates[0][0] == 274
    assert opple_listener.attribute_updates[0][1] == 10 + 65536

    # confirm zone status change notification command
    assert len(ias_listener.cluster_commands) == 1
    assert ias_listener.cluster_commands[0][1] == zcl_zone_status_change_cmd_id
    assert ias_listener.cluster_commands[0][2][0] == IasZone.ZoneStatus.Alarm_1

    # confirm occupancy report
    assert len(occupancy_listener.attribute_updates) == 1
    assert occupancy_listener.attribute_updates[0][0] == zcl_occupancy_id
    assert (
        occupancy_listener.attribute_updates[0][1]
        == OccupancySensing.Occupancy.Occupied
    )

    # confirm illuminance report (with conversion)
    assert len(illuminance_listener.attribute_updates) == 1
    assert illuminance_listener.attribute_updates[0][0] == zcl_iilluminance_id
    assert illuminance_listener.attribute_updates[0][1] == 10000 * math.log10(10) + 1

    # send invalid illuminance report 0xFFFF (and motion)
    opple_cluster.update_attribute(274, 0xFFFF)

    # confirm invalid illuminance report is interpreted as 0 for P1 sensor,
    # and -1 for the T1/E1 sensors, as they don't seem to send invalid illuminance reports
    assert len(illuminance_listener.attribute_updates) == 2
    assert illuminance_listener.attribute_updates[1][0] == zcl_iilluminance_id
    assert illuminance_listener.attribute_updates[1][1] == invalid_iilluminance_report

    # send illuminance report only, parsed via Xiaomi cluster implementation
    opple_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE_E1, create_aqara_attr_report({101: 20})
    )
    assert len(illuminance_listener.attribute_updates) == 3
    assert illuminance_listener.attribute_updates[2][0] == zcl_iilluminance_id
    assert illuminance_listener.attribute_updates[2][1] == 10000 * math.log10(20) + 1


@pytest.mark.parametrize(
    "quirk, cluster_name, raw_report, expected_results",
    (
        (
            zhaquirks.xiaomi.aqara.weather.Weather2,
            "basic",
            "18200A01FF412501214F0B0421A84305214E020624010000000064299B096521BE1B662B138D01000A21900D",
            [
                2459,  # temperature
                7102,  # humidity
                1016.51,  # pressure
                28.9,  # battery voltage
                54,  # battery percent * 2
            ],
        ),
        (
            zhaquirks.xiaomi.aqara.sensor_ht_agl02.LumiSensorHtAgl02,
            "opple_cluster",
            "1C5F11860AF700412D0121B60B0328170421A81305210B000624060000000008211D010A210"
            "0000C200164292D09652904186629E903",
            [
                2349,  # temperature
                6148,  # humidity
                1001,  # pressure
                30.0,  # battery voltage
                127,  # battery percent * 2
            ],
        ),
    ),
)
async def test_xiaomi_weather(
    zigpy_device_from_quirk, quirk, cluster_name, raw_report, expected_results
):
    """Test Aqara weather sensors."""
    raw_report = bytes.fromhex(raw_report)
    device = zigpy_device_from_quirk(quirk)
    xiaomi_attr_cluster = getattr(device.endpoints[1], cluster_name)

    temperature_cluster = device.endpoints[1].temperature
    temperature_listener = ClusterListener(temperature_cluster)

    humidity_cluster = device.endpoints[1].humidity
    humidity_listener = ClusterListener(humidity_cluster)

    pressure_cluster = device.endpoints[1].pressure
    pressure_listener = ClusterListener(pressure_cluster)

    power_cluster = device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)

    zcl_temperature_id = TemperatureMeasurement.AttributeDefs.measured_value.id
    zcl_humidity_id = RelativeHumidity.AttributeDefs.measured_value.id
    zcl_pressure_id = PressureMeasurement.AttributeDefs.measured_value.id
    zcl_power_voltage_id = PowerConfiguration.AttributeDefs.battery_voltage.id
    zcl_power_percent_id = (
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
    )

    device.handle_message(
        260,
        xiaomi_attr_cluster.cluster_id,
        xiaomi_attr_cluster.endpoint.endpoint_id,
        xiaomi_attr_cluster.endpoint.endpoint_id,
        raw_report,
    )

    assert len(temperature_listener.attribute_updates) == 1
    assert temperature_listener.attribute_updates[0][0] == zcl_temperature_id
    assert temperature_listener.attribute_updates[0][1] == expected_results[0]

    assert len(humidity_listener.attribute_updates) == 1
    assert humidity_listener.attribute_updates[0][0] == zcl_humidity_id
    assert humidity_listener.attribute_updates[0][1] == expected_results[1]

    assert len(pressure_listener.attribute_updates) == 1
    assert pressure_listener.attribute_updates[0][0] == zcl_pressure_id
    assert pressure_listener.attribute_updates[0][1] == expected_results[2]

    assert len(power_listener.attribute_updates) == 2
    assert power_listener.attribute_updates[0][0] == zcl_power_voltage_id
    assert power_listener.attribute_updates[0][1] == expected_results[3]
    assert power_listener.attribute_updates[1][0] == zcl_power_percent_id
    assert power_listener.attribute_updates[1][1] == expected_results[4]


@pytest.mark.parametrize(
    "raw_report, expected_results",
    (
        [
            "1C5F11C10A01FF41210121DB0B03281F0421A8430521B60006240B000000000A21CA356410000B210800",
            [
                3100,  # temperature
                9031.899869919436,  # illuminance
                30.4,  # battery voltage
                154,  # battery percent * 2
            ],
        ],
    ),
)
async def test_xiaomi_motion_sensor_misc(
    zigpy_device_from_quirk, raw_report, expected_results
):
    """Test device temperature, illuminance, and power from old Aqara motion sensor models."""
    raw_report = bytes.fromhex(raw_report)

    device = zigpy_device_from_quirk(zhaquirks.xiaomi.aqara.motion_aq2.MotionAQ2)

    basic_cluster = device.endpoints[1].basic

    device_temperature_cluster = device.endpoints[1].device_temperature
    device_temperature_listener = ClusterListener(device_temperature_cluster)

    illuminance_cluster = device.endpoints[1].illuminance
    illuminance_listener = ClusterListener(illuminance_cluster)

    power_cluster = device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)

    zcl_device_temperature_id = DeviceTemperature.AttributeDefs.current_temperature.id
    zcl_illuminance_id = IlluminanceMeasurement.AttributeDefs.measured_value.id
    zcl_power_voltage_id = PowerConfiguration.AttributeDefs.battery_voltage.id
    zcl_power_percent_id = (
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
    )

    device.handle_message(
        260,
        basic_cluster.cluster_id,
        basic_cluster.endpoint.endpoint_id,
        basic_cluster.endpoint.endpoint_id,
        raw_report,
    )

    assert len(device_temperature_listener.attribute_updates) == 1
    assert (
        device_temperature_listener.attribute_updates[0][0] == zcl_device_temperature_id
    )
    assert device_temperature_listener.attribute_updates[0][1] == expected_results[0]

    assert len(illuminance_listener.attribute_updates) == 1
    assert illuminance_listener.attribute_updates[0][0] == zcl_illuminance_id
    assert illuminance_listener.attribute_updates[0][1] == expected_results[1]

    assert len(power_listener.attribute_updates) == 2
    assert power_listener.attribute_updates[0][0] == zcl_power_voltage_id
    assert power_listener.attribute_updates[0][1] == expected_results[2]
    assert power_listener.attribute_updates[1][0] == zcl_power_percent_id
    assert power_listener.attribute_updates[1][1] == expected_results[3]


@pytest.mark.parametrize("quirk", (zhaquirks.xiaomi.aqara.plug.Plug,))
async def test_xiaomi_power_cluster_not_used(zigpy_device_from_quirk, caplog, quirk):
    """Test log is printed which warns when a device reports battery mV readout.

    ... even though XiaomiPowerConfigurationCluster is not used. This explicitly uses the Plug quirk
    which will always report this message, as this shouldn't have a battery readout.
    Other battery-powered devices might implement the XiaomiPowerConfigurationCluster in the future,
    so they would no longer report this message.
    """
    caplog.set_level(logging.DEBUG)  # relevant message is currently DEBUG level

    device = zigpy_device_from_quirk(quirk)
    basic_cluster = device.endpoints[1].basic

    power_cluster = device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)

    # fake a battery voltage attribute report
    basic_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE, create_aqara_attr_report({1: 2300})
    )

    # confirm that no battery voltage attribute was updated
    assert len(power_listener.attribute_updates) == 0

    # confirm that a debug message was logged
    assert (
        "Xiaomi battery voltage attribute received but XiaomiPowerConfiguration not used"
        in caplog.text
    )


@pytest.mark.parametrize(
    "quirk", (zhaquirks.xiaomi.aqara.roller_curtain_e1.RollerE1AQ,)
)
async def test_xiaomi_e1_roller_curtain_battery(zigpy_device_from_quirk, quirk):
    """Test Aqara E1 roller curtain battery reporting."""
    # Ideally, get a real Xiaomi "heartbeat" message to test.
    # For now, fake the heartbeat message and check if battery parsing works.

    device = zigpy_device_from_quirk(quirk)

    basic_cluster = device.endpoints[1].basic
    ClusterListener(basic_cluster)

    power_cluster = device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)

    zcl_power_voltage_id = PowerConfiguration.AttributeDefs.battery_voltage.id
    zcl_power_percent_id = (
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
    )

    # battery voltage: 2895 mV
    # battery percentage: 80%
    basic_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE, create_aqara_attr_report({1: 2895, 101: 60})
    )

    # confirm that battery voltage attribute and percentage were each updated just once,
    # so we verify the percent value sent was used,
    # and the voltage value sent was only used for the voltage and not also for the percentage
    assert len(power_listener.attribute_updates) == 2

    # verify voltage and percentage values match the values sent
    assert power_listener.attribute_updates[0][0] == zcl_power_voltage_id
    assert power_listener.attribute_updates[0][1] == 28.9
    assert power_listener.attribute_updates[1][0] == zcl_power_percent_id
    assert power_listener.attribute_updates[1][1] == 120


@pytest.mark.parametrize(
    "raw_report, expected_results",
    (
        [
            "1C5F11670AF700412E0121B00C0328190421A8130521090006240D0000000008211E010A2100000C20016410016620036720016821A800",
            [
                32.5,  # battery voltage
                200,  # battery percent * 2
            ],
        ],
    ),
)
async def test_xiaomi_t1_door_sensor(
    zigpy_device_from_quirk, raw_report, expected_results
):
    """Test Aqara T1 door sensor."""
    raw_report = bytes.fromhex(raw_report)

    device = zigpy_device_from_quirk(zhaquirks.xiaomi.aqara.magnet_agl02.MagnetT1)

    on_off_cluster = device.endpoints[1].out_clusters[OnOff.cluster_id]
    on_off_listener = ClusterListener(on_off_cluster)

    # check open state
    device.handle_message(
        260,
        on_off_cluster.cluster_id,
        on_off_cluster.endpoint.endpoint_id,
        on_off_cluster.endpoint.endpoint_id,
        bytes.fromhex("185D0A00001001"),
    )

    assert len(on_off_listener.attribute_updates) == 1
    assert on_off_listener.attribute_updates[0][0] == OnOff.AttributeDefs.on_off.id
    assert on_off_listener.attribute_updates[0][1] == t.Bool.true

    # check closed state
    device.handle_message(
        260,
        on_off_cluster.cluster_id,
        on_off_cluster.endpoint.endpoint_id,
        on_off_cluster.endpoint.endpoint_id,
        bytes.fromhex("18640A00001000"),
    )

    assert len(on_off_listener.attribute_updates) == 2
    assert on_off_listener.attribute_updates[1][0] == OnOff.AttributeDefs.on_off.id
    assert on_off_listener.attribute_updates[1][1] == t.Bool.false

    opple_cluster = device.endpoints[1].opple_cluster
    ClusterListener(opple_cluster)

    power_cluster = device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)

    zcl_power_voltage_id = PowerConfiguration.AttributeDefs.battery_voltage.id
    zcl_power_percent_id = (
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
    )

    # check Xiaomi attribute report
    device.handle_message(
        260,
        opple_cluster.cluster_id,
        opple_cluster.endpoint.endpoint_id,
        opple_cluster.endpoint.endpoint_id,
        raw_report,
    )

    assert len(power_listener.attribute_updates) == 2
    assert power_listener.attribute_updates[0][0] == zcl_power_voltage_id
    assert power_listener.attribute_updates[0][1] == expected_results[0]
    assert power_listener.attribute_updates[1][0] == zcl_power_percent_id
    assert power_listener.attribute_updates[1][1] == expected_results[1]


@pytest.mark.parametrize(
    "command, command_id, value",
    [
        (
            WindowCovering.ServerCommandDefs.up_open.id,
            WindowCovering.ServerCommandDefs.go_to_lift_percentage.id,
            0,
        ),
        (
            WindowCovering.ServerCommandDefs.down_close.id,
            WindowCovering.ServerCommandDefs.go_to_lift_percentage.id,
            100,
        ),
        (
            WindowCovering.ServerCommandDefs.stop.id,
            WindowCovering.ServerCommandDefs.stop.id,
            None,
        ),
    ],
)
async def test_xiaomi_e1_driver_commands(
    zigpy_device_from_quirk, command, command_id, value
):
    """Test Aqara E1 driver commands for basic movement functions using WindowCovering cluster."""
    device = zigpy_device_from_quirk(zhaquirks.xiaomi.aqara.driver_curtain_e1.DriverE1)

    window_covering_cluster = device.endpoints[1].window_covering
    p = mock.patch.object(window_covering_cluster, "request", mock.AsyncMock())

    with p as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        # test command
        await window_covering_cluster.command(command)
        assert request_mock.call_count == 1
        assert request_mock.call_args[0][1] == command_id
        if value is not None:
            assert request_mock.call_args[0][3] == value


@pytest.mark.parametrize(
    "device_level, converted_level",
    [
        (0, 0),
        (1, 50),
        (2, 100),
    ],
)
async def test_xiaomi_e1_driver_light_level(
    zigpy_device_from_quirk, device_level, converted_level
):
    """Test Aqara E1 driver light level cluster conversion."""
    device = zigpy_device_from_quirk(zhaquirks.xiaomi.aqara.driver_curtain_e1.DriverE1)

    opple_cluster = device.endpoints[1].opple_cluster
    opple_listener = ClusterListener(opple_cluster)
    opple_zcl_iilluminance_id = 0x0429

    illuminance_cluster = device.endpoints[1].illuminance
    illuminance_listener = ClusterListener(illuminance_cluster)
    zcl_iilluminance_id = IlluminanceMeasurement.AttributeDefs.measured_value.id

    # send motion and illuminance report 10
    opple_cluster.update_attribute(opple_zcl_iilluminance_id, device_level)

    # confirm manufacturer specific attribute report
    assert len(opple_listener.attribute_updates) == 1
    assert opple_listener.attribute_updates[0][0] == opple_zcl_iilluminance_id
    assert opple_listener.attribute_updates[0][1] == device_level

    # confirm illuminance report (with conversion)
    assert len(illuminance_listener.attribute_updates) == 1
    assert illuminance_listener.attribute_updates[0][0] == zcl_iilluminance_id

    assert (
        device_level == 0
        and converted_level == 0
        or (
            illuminance_listener.attribute_updates[0][1]
            == 10000 * math.log10(converted_level) + 1
        )
    )


@pytest.mark.parametrize(
    "command, value",
    [
        (WindowCovering.ServerCommandDefs.up_open.id, 1),
        (WindowCovering.ServerCommandDefs.down_close.id, 0),
        (WindowCovering.ServerCommandDefs.stop.id, 2),
    ],
)
async def test_xiaomi_e1_roller_commands_1(zigpy_device_from_quirk, command, value):
    """Test Aqara E1 roller commands for basic movement functions using MultistateOutput Cluster."""
    device = zigpy_device_from_quirk(
        zhaquirks.xiaomi.aqara.roller_curtain_e1.RollerE1AQ
    )

    window_covering_cluster = device.endpoints[1].window_covering
    multistate_cluster = device.endpoints[1].multistate_output
    multistate_cluster._write_attributes = mock.AsyncMock(
        return_value=(
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],
        )
    )
    attr_id = MultistateOutput.AttributeDefs.present_value.id

    # test command
    await window_covering_cluster.command(command)
    assert multistate_cluster._write_attributes.call_count == 1
    assert multistate_cluster._write_attributes.call_args[0][0][0].attrid == attr_id
    assert multistate_cluster._write_attributes.call_args[0][0][0].value.value == value


@pytest.mark.parametrize(
    "command, value",
    [
        (WindowCovering.ServerCommandDefs.go_to_lift_percentage.id, 60),
    ],
)
async def test_xiaomi_e1_roller_commands_2(zigpy_device_from_quirk, command, value):
    """Test Aqara E1 roller commands for go to lift percentage using AnalogOutput cluster."""
    device = zigpy_device_from_quirk(
        zhaquirks.xiaomi.aqara.roller_curtain_e1.RollerE1AQ
    )

    window_covering_cluster = device.endpoints[1].window_covering
    analog_cluster = device.endpoints[1].analog_output
    analog_cluster._write_attributes = mock.AsyncMock(
        return_value=(
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],
        )
    )
    attr_id = AnalogOutput.AttributeDefs.present_value.id

    # test go to lift percentage command
    await window_covering_cluster.go_to_lift_percentage(value)
    assert analog_cluster._write_attributes.call_count == 1
    assert analog_cluster._write_attributes.call_args[0][0][0].attrid == attr_id
    assert (
        analog_cluster._write_attributes.call_args[0][0][0].value.value == 100 - value
    )


@pytest.mark.parametrize("endpoint", [(1), (2)])
async def test_aqara_t2_relay(zigpy_device_from_quirk, endpoint):
    """Test Aqara T2 relay."""

    device = zigpy_device_from_quirk(zhaquirks.xiaomi.aqara.switch_acn047.AqaraT2Relay)
    mi_cluster = device.endpoints[endpoint].multistate_input
    mi_listener = ClusterListener(mi_cluster)

    buttons = {1: BUTTON_1, 2: BUTTON_2}

    mi_cluster.update_attribute(MultistateInput.AttributeDefs.present_value.id, 1)
    assert len(mi_listener.attribute_updates) == 1
    assert mi_listener.attribute_updates[0][0] == 0
    assert mi_listener.attribute_updates[0][1] == buttons[endpoint]

    mi_cluster.update_attribute(MultistateInput.AttributeDefs.state_text.id, "foo")
    assert len(mi_listener.attribute_updates) == 2
    assert (
        mi_listener.attribute_updates[1][0]
        == MultistateInput.AttributeDefs.state_text.id
    )
    assert mi_listener.attribute_updates[1][1] == "foo"


def test_aqara_acn003_signature_match(assert_signature_matches_quirk):
    """Test signature."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.FullFunctionDevice|MainsPowered|RxOnWhenIdle|AllocateAddress: 142>, manufacturer_code=4447, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 0x0104,
                "device_type": "0x0102",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x0300",
                    "0xfcc0",
                ],
                "out_clusters": ["0x000a", "0x0019"],
            }
        },
        "manufacturer": "Aqara",
        "model": "lumi.light.acn003",
        "class": "aqara_light.LumiLightAcn003",
    }

    assert_signature_matches_quirk(
        zhaquirks.xiaomi.aqara.light_acn.LumiLightAcn003, signature
    )


def test_aqara_acn014_signature_match(assert_signature_matches_quirk):
    """Test signature."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.FullFunctionDevice|MainsPowered|RxOnWhenIdle|AllocateAddress: 142>, manufacturer_code=4447, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 0x0104,
                "device_type": "0x010c",
                "in_clusters": [
                    "0x0000",
                    "0x0002",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x0009",
                    "0x000c",
                    "0x000f",
                    "0x0012",
                    "0x0300",
                    "0x0702",
                    "0x0b04",
                    "0xfcc0",
                ],
                "out_clusters": ["0x000a", "0x0019"],
            },
            "21": {
                "profile_id": 0x0104,
                "device_type": "0x010c",
                "in_clusters": ["0x000c"],
                "out_clusters": [],
            },
            "31": {
                "profile_id": 0x0104,
                "device_type": "0x010c",
                "in_clusters": ["0x000c"],
                "out_clusters": [],
            },
            "242": {
                "profile_id": 0xA1E0,
                "device_type": "0x0061",
                "in_clusters": [],
                "out_clusters": ["0x0021"],
            },
        },
        "manufacturer": "LUMI",
        "model": "lumi.light.acn014",
        "class": "zigpy.device.Device",
    }

    assert_signature_matches_quirk(
        zhaquirks.xiaomi.aqara.light_acn.LumiLightAcn014, signature
    )


@pytest.mark.parametrize(
    "occupancy_value, expected_occ_status, motion_value, expected_motion_status",
    [
        (0, OccupancySensing.Occupancy.Unoccupied, 2, 0),
        (1, OccupancySensing.Occupancy.Occupied, 3, IasZone.ZoneStatus.Alarm_1),
        (1, OccupancySensing.Occupancy.Occupied, 4, 0),
    ],
)
async def test_aqara_fp1e_sensor(
    zigpy_device_from_v2_quirk,
    occupancy_value,
    expected_occ_status,
    motion_value,
    expected_motion_status,
):
    """Test Aqara FP1E sensor."""
    quirk = zigpy_device_from_v2_quirk("aqara", "lumi.sensor_occupy.agl1")

    opple_cluster = quirk.endpoints[1].opple_cluster
    ias_cluster = quirk.endpoints[1].ias_zone
    occupancy_cluster = quirk.endpoints[1].occupancy

    opple_listener = ClusterListener(opple_cluster)
    ias_listener = ClusterListener(ias_cluster)
    occupancy_listener = ClusterListener(occupancy_cluster)

    # update custom occupancy attribute id
    opple_cluster.update_attribute(0x0142, occupancy_value)
    assert len(opple_listener.attribute_updates) == 1

    # confirm occupancy cluster is updated
    assert len(occupancy_listener.attribute_updates) == 1
    assert (
        occupancy_listener.attribute_updates[0][0]
        == OccupancySensing.AttributeDefs.occupancy.id
    )
    assert occupancy_listener.attribute_updates[0][1] == expected_occ_status

    # update custom motion attribute id
    opple_cluster.update_attribute(0x0160, motion_value)
    assert len(opple_listener.attribute_updates) == 2

    # confirm ias cluster is updated
    assert len(ias_listener.attribute_updates) == 1
    assert ias_listener.attribute_updates[0][0] == IasZone.AttributeDefs.zone_status.id
    assert ias_listener.attribute_updates[0][1] == expected_motion_status
