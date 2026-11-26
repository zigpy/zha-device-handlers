"""Tests for the MOES ZM6LT1 energy meter."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation

from tests.common import wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya import TUYA_CLUSTER_ID
import zhaquirks.tuya.ts0601_moes_meter as moes_meter
from zhaquirks.tuya.ts1201 import ir_msg_part_crc

zhaquirks.setup()

SEGMENTED_CLUSTER_ID = 0xED00

# DP6: 219.3 V, 8.269 A, 1789 W, no reactive or apparent power, power factor 98 %.
PHASE = bytes.fromhex("020f089100204d0006fd0000000000006200")
# DP17: over-current alarm (id 1) on at 32 A, over-voltage alarm (id 3) off at 250 V.
ALARM_SETTINGS = bytes.fromhex("01010020030000fa")


def datapoint(dp, dp_type, data):
    """Encode a datapoint as the meter puts it into a segmented report."""
    return bytes([dp, dp_type]) + len(data).to_bytes(2, "big") + data


# A report as the meter sends it: a sequence number, then its datapoints.
REPORT = (
    b"\x07\x00"
    + datapoint(1, 0x02, (1884).to_bytes(4, "big"))  # energy 18.84 kWh
    + datapoint(2, 0x02, (12).to_bytes(4, "big"))  # reverse energy 0.12 kWh
    + datapoint(10, 0x05, (0).to_bytes(4, "big"))  # no fault
    + datapoint(6, 0x00, PHASE)
    + datapoint(17, 0x00, ALARM_SETTINGS)
    + datapoint(49, 0x02, (5000).to_bytes(4, "big"))  # 50.00 Hz
)


@pytest.fixture
def meter(zigpy_device_from_v2_quirk):
    """Return a quirked meter whose endpoint requests always succeed."""
    device = zigpy_device_from_v2_quirk(
        "_TZE28C1000000_2fnssffc",
        "TS0601",
        cluster_ids={
            1: {
                TUYA_CLUSTER_ID: ClusterType.Server,
                SEGMENTED_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    with mock.patch.object(
        device.endpoints[1], "request", return_value=foundation.Status.SUCCESS
    ) as request:
        device.request_mock = request
        yield device


def device_frame(cluster, command_name, **kwargs):
    """Build a frame as the meter sends it on the segmented report cluster."""
    command = getattr(cluster.ServerCommandDefs, command_name)
    data = bytes([0x11, 0x42, command.id]) + command.schema(**kwargs).serialize()
    return cluster.deserialize(data)


def sent_frames(meter):
    """Return the frames sent to the meter on the segmented report cluster."""
    cluster = meter.endpoints[1].zosung_irtransmit
    frames = []
    for call in meter.request_mock.mock_calls:
        if call.kwargs["cluster"] != SEGMENTED_CLUSTER_ID:
            continue
        command = cluster.server_commands[call.kwargs["command_id"]]
        args, _ = command.schema.deserialize(call.kwargs["data"][3:])
        frames.append((command.id, args))
    return frames


def announce(cluster, length, seq=7, clusterid=TUYA_CLUSTER_ID, cmd=2):
    """Frame 0x00: the meter announces a report."""
    cluster.handle_message(
        *device_frame(
            cluster,
            "receive_ir_frame_00",
            seq=seq,
            length=length,
            unk1=0,
            clusterid=clusterid,
            unk2=0,
            cmd=cmd,
            unk3=0,
        )
    )


def send_part(cluster, position, part, seq=7, crc=None):
    """Frame 0x03: the meter sends a part of a report."""
    cluster.handle_message(
        *device_frame(
            cluster,
            "receive_ir_frame_03",
            zero=0,
            seq=seq,
            position=position,
            msgpart=part,
            msgpartcrc=ir_msg_part_crc(part) if crc is None else crc,
        )
    )


async def transfer(cluster, report, seq=7):
    """Hand a whole report over the way the meter does, part by part."""
    announce(cluster, len(report), seq=seq)
    for position in range(0, len(report), moes_meter.SEGMENT_PART_LENGTH):
        send_part(
            cluster,
            position,
            report[position : position + moes_meter.SEGMENT_PART_LENGTH],
            seq=seq,
        )
    await wait_for_zigpy_tasks()


@pytest.mark.parametrize(
    "raw,expected",
    [
        (PHASE, moes_meter.PhaseData(2193, 8269, 1789, 98)),
        # flags: negative current and power, e.g. solar export
        (PHASE[:-1] + b"\x03", moes_meter.PhaseData(2193, -8269, -1789, 98)),
        # short frame without power factor and flags
        (PHASE[:10], moes_meter.PhaseData(2193, 8269, 1789, None)),
        (PHASE[:9], None),
        (b"", None),
    ],
)
def test_decode_phase(raw, expected):
    """Test decoding voltage, current, power and power factor of DP6."""
    assert moes_meter.decode_phase(raw) == expected


def test_decode_alarm_settings():
    """Test reading the over-current threshold from DP17."""
    assert moes_meter.decode_alarm_settings(ALARM_SETTINGS) == ALARM_SETTINGS
    assert moes_meter.decode_over_current_threshold(ALARM_SETTINGS) == 32
    assert moes_meter.decode_over_current_threshold(ALARM_SETTINGS[4:]) is None
    assert moes_meter.decode_alarm_settings(ALARM_SETTINGS[:5]) is None
    assert moes_meter.decode_over_current_threshold(ALARM_SETTINGS[:5]) is None


def test_encode_over_current_threshold():
    """Test that a new threshold is sent with the other alarm records unchanged."""
    encoded = moes_meter.encode_over_current_threshold(ALARM_SETTINGS, 40)
    assert encoded.serialize() == bytes.fromhex("01010028030000fa")


@pytest.mark.parametrize(
    "alarm_settings,value,error",
    [
        (None, 40, "not reported"),
        (ALARM_SETTINGS[:5], 40, "not reported"),
        (ALARM_SETTINGS, 0, "must be"),
        (ALARM_SETTINGS, 121, "must be"),
        (ALARM_SETTINGS[4:], 40, "no single"),
        (ALARM_SETTINGS[:4] * 2, 40, "no single"),
    ],
)
def test_encode_over_current_threshold_refused(alarm_settings, value, error):
    """Test that a threshold change the meter cannot take is refused."""
    with pytest.raises(ValueError, match=error):
        moes_meter.encode_over_current_threshold(alarm_settings, value)


async def test_segmented_report(meter):
    """Test pulling a report part by part and decoding its datapoints."""
    segmented = meter.endpoints[1].zosung_irtransmit
    mcu = meter.endpoints[1].tuya_manufacturer
    part_length = moes_meter.SEGMENT_PART_LENGTH
    assert len(REPORT) > part_length

    await transfer(segmented, REPORT)

    frames = sent_frames(meter)
    assert [command_id for command_id, _ in frames] == [0x01, 0x02, 0x02, 0x04]
    assert frames[0][1].seq == 7
    assert frames[0][1].length == len(REPORT)
    assert frames[1][1].position == 0
    assert frames[1][1].maxlen == part_length
    assert frames[2][1].position == part_length
    assert frames[3][1].seq == 7
    assert not segmented.reports

    assert mcu.get("energy") == 1884
    assert mcu.get("reverse_energy") == 12
    assert mcu.get("fault") == 0
    assert mcu.get("voltage") == 2193
    assert mcu.get("current") == 8269
    assert mcu.get("power") == 1789
    assert mcu.get("power_factor") == 98
    assert mcu.get("alarm_settings") == ALARM_SETTINGS
    assert mcu.get("over_current_threshold") == 32
    assert mcu.get("ac_frequency") == 5000


@pytest.mark.parametrize(
    "position,crc",
    [
        (1, None),  # not where the report continues
        (0, 0x00),  # wrong checksum
    ],
)
async def test_segmented_report_bad_part(meter, position, crc):
    """Test that a report with a bad part is dropped."""
    segmented = meter.endpoints[1].zosung_irtransmit
    mcu = meter.endpoints[1].tuya_manufacturer

    announce(segmented, len(REPORT))
    send_part(segmented, position, REPORT[:20], crc=crc)
    await wait_for_zigpy_tasks()

    assert [command_id for command_id, _ in sent_frames(meter)] == [0x01, 0x02]
    assert not segmented.reports
    assert mcu.get("voltage") is None


async def test_segmented_report_too_long_part(meter):
    """Test that a part running past the announced length drops the report."""
    segmented = meter.endpoints[1].zosung_irtransmit

    announce(segmented, 10)
    send_part(segmented, 0, REPORT[:20])
    await wait_for_zigpy_tasks()

    assert not segmented.reports


@pytest.mark.parametrize(
    "length,clusterid,cmd",
    [
        (100, 0xE004, 2),  # not a Tuya report
        (100, TUYA_CLUSTER_ID, 1),  # not a data report
        (1, TUYA_CLUSTER_ID, 2),
        (moes_meter.SEGMENT_MAX_LENGTH + 1, TUYA_CLUSTER_ID, 2),
    ],
)
async def test_segmented_report_ignored_announcement(meter, length, clusterid, cmd):
    """Test that transfers that are no datapoint report are not pulled."""
    segmented = meter.endpoints[1].zosung_irtransmit

    announce(segmented, length, clusterid=clusterid, cmd=cmd)
    await wait_for_zigpy_tasks()

    assert sent_frames(meter) == []
    assert not segmented.reports


async def test_segmented_report_part_without_announcement(meter):
    """Test that a part of a report that was never announced is ignored."""
    segmented = meter.endpoints[1].zosung_irtransmit

    send_part(segmented, 0, REPORT[:20])
    await wait_for_zigpy_tasks()

    assert sent_frames(meter) == []


async def test_segmented_report_aborted(meter):
    """Test that frame 0x05 ends a transfer."""
    segmented = meter.endpoints[1].zosung_irtransmit

    announce(segmented, len(REPORT))
    segmented.handle_message(
        *device_frame(segmented, "receive_ir_frame_05", seq=7, zero=0)
    )

    assert not segmented.reports


async def test_segmented_report_keeps_few_transfers(meter):
    """Test that only the latest unfinished transfers are kept."""
    segmented = meter.endpoints[1].zosung_irtransmit

    for seq in range(moes_meter.SEGMENT_MAX_TRANSFERS + 2):
        announce(segmented, len(REPORT), seq=seq)
    await wait_for_zigpy_tasks()

    assert list(segmented.reports) == list(
        range(2, moes_meter.SEGMENT_MAX_TRANSFERS + 2)
    )


@pytest.mark.parametrize(
    "report",
    [
        REPORT[:-2],  # last datapoint cut short
        REPORT + b"\x01\x02",  # datapoint header cut short
        b"\x07\x00" + datapoint(1, 0x09, b"\x00"),  # unknown datapoint type
    ],
)
async def test_segmented_report_undecodable(meter, report, caplog):
    """Test that a report that cannot be decoded changes nothing."""
    segmented = meter.endpoints[1].zosung_irtransmit
    mcu = meter.endpoints[1].tuya_manufacturer

    await transfer(segmented, report)

    assert "Cannot decode segmented report" in caplog.text
    assert mcu.get("energy") is None


async def test_short_phase_frame_keeps_measurements(meter):
    """Test that a DP6 frame too short to decode keeps the last measurements."""
    segmented = meter.endpoints[1].zosung_irtransmit
    mcu = meter.endpoints[1].tuya_manufacturer

    await transfer(segmented, REPORT)
    await transfer(segmented, b"\x08\x00" + datapoint(6, 0x00, PHASE[:4]), seq=8)

    assert mcu.get("voltage") == 2193
    assert mcu.get("power") == 1789


async def test_write_over_current_threshold(meter):
    """Test that changing the threshold sends the whole alarm settings back."""
    segmented = meter.endpoints[1].zosung_irtransmit
    mcu = meter.endpoints[1].tuya_manufacturer
    await transfer(segmented, REPORT)
    meter.request_mock.reset_mock()

    await mcu.write_attributes({"over_current_threshold": 40})
    await wait_for_zigpy_tasks()

    (call,) = [
        call
        for call in meter.request_mock.mock_calls
        if call.kwargs["cluster"] == TUYA_CLUSTER_ID
    ]
    assert call.kwargs["data"].endswith(
        datapoint(17, 0x00, bytes.fromhex("01010028030000fa"))
    )


async def test_refresh_measurements(meter):
    """Test that the refresh button sends DP44."""
    mcu = meter.endpoints[1].tuya_manufacturer

    await mcu.write_attributes(
        {"refresh_measurements": moes_meter.RefreshMeasurements.Refresh}
    )
    await wait_for_zigpy_tasks()

    (call,) = [
        call
        for call in meter.request_mock.mock_calls
        if call.kwargs["cluster"] == TUYA_CLUSTER_ID
    ]
    assert call.kwargs["data"].endswith(datapoint(44, 0x04, b"\x01"))
