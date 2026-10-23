"""Tests for the SONOFF SNZB-06P24 presence sensor."""

import asyncio
from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.sonoff.snzb06p24 import (
    SonoffSNZB06P24FC11Cluster,
    SonoffSNZB06P24LocalCluster,
    SpatialLearningSubCommand,
    SpatialLearningUiState,
)

zhaquirks.setup()

FC11 = SonoffSNZB06P24FC11Cluster
LOCAL = SonoffSNZB06P24LocalCluster
ZONE_MASK = FC11.AttributeDefs.zone_enable
UI_STATE = LOCAL.AttributeDefs.spatial_learning_ui_state
COUNTDOWN = LOCAL.AttributeDefs.spatial_learning_countdown

ZONES = (
    LOCAL.AttributeDefs.zone_0_enable,
    LOCAL.AttributeDefs.zone_2_enable,
    LOCAL.AttributeDefs.zone_3_enable,
    LOCAL.AttributeDefs.zone_4_enable,
    LOCAL.AttributeDefs.zone_5_enable,
    LOCAL.AttributeDefs.zone_6_enable,
    LOCAL.AttributeDefs.zone_7_enable,
)

SEQUENCE = 1_700_000_000_000


@pytest.fixture
def snzb06p24(zigpy_device_from_v2_quirk):
    """SNZB-06P24 device with the quirk applied."""
    return zigpy_device_from_v2_quirk(
        "SONOFF", "SNZB-06P24", cluster_ids={1: {FC11.cluster_id: ClusterType.Server}}
    )


def write_response(status=foundation.Status.SUCCESS):
    """Build a raw write attributes response for the zone mask."""
    if status == foundation.Status.SUCCESS:
        return [[foundation.WriteAttributesStatusRecord(status=status)]]
    return [
        [foundation.WriteAttributesStatusRecord(status=status, attrid=ZONE_MASK.id)]
    ]


def read_response(value):
    """Build a raw read attributes response for the zone mask."""
    return [
        [
            foundation.ReadAttributeRecord(
                attrid=ZONE_MASK.id,
                status=foundation.Status.SUCCESS,
                value=foundation.TypeValue(type=ZONE_MASK.zcl_type, value=value),
            )
        ]
    ]


def test_snzb06p24_clusters(snzb06p24):
    """Test the quirk replaces FC11 and adds the local cluster."""
    assert isinstance(snzb06p24.endpoints[1].sonoff_manufacturer, FC11)
    assert isinstance(snzb06p24.endpoints[1].sonoff_presence_local, LOCAL)


@pytest.mark.parametrize(
    ("mask", "expected"),
    [
        (0x00FF, (True,) * 7),
        (0x0000, (False,) * 7),
        # Either band of zone 1 is enough for it to be on
        (0x0001, (True,) + (False,) * 6),
        (0x0002, (True,) + (False,) * 6),
        (0x0014, (False, True, False, True, False, False, False)),
    ],
)
def test_snzb06p24_zone_mask_to_switches(snzb06p24, mask, expected):
    """Test zone mask updates set the zone switches."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer
    local = snzb06p24.endpoints[1].sonoff_presence_local

    fc11.update_attribute(ZONE_MASK.id, mask)

    assert tuple(local.get(zone.id) for zone in ZONES) == expected


async def test_snzb06p24_zone_switches_read_locally(snzb06p24):
    """Test zone switches are answered locally and keyed as requested."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer
    local = snzb06p24.endpoints[1].sonoff_presence_local
    fc11.update_attribute(ZONE_MASK.id, 0x00FB)

    with mock.patch.object(fc11, "read_attributes_raw") as fc11_read:
        success, failure = await local.read_attributes(
            [ZONES[0].name, ZONES[1].id, UI_STATE.name]
        )

    assert fc11_read.call_count == 0
    assert success == {
        ZONES[0].name: True,
        ZONES[1].id: False,
        UI_STATE.name: SpatialLearningUiState.Idle,
    }
    assert failure == {}


async def test_snzb06p24_mask_read_on_configuration(snzb06p24):
    """Test the zone mask is read when the device is configured."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer
    local = snzb06p24.endpoints[1].sonoff_presence_local

    with mock.patch.object(
        fc11, "_read_attributes", mock.AsyncMock(return_value=read_response(0x00F3))
    ) as fc11_read:
        await snzb06p24.apply_custom_configuration()

    assert fc11_read.call_args[0][0] == [ZONE_MASK.id]
    assert fc11_read.call_args.kwargs["manufacturer"] is None
    assert tuple(local.get(zone.id) for zone in ZONES) == (
        (True, False, False) + (True,) * 4
    )


@pytest.mark.parametrize(
    ("zone", "value", "mask", "expected_mask"),
    [
        (ZONES[0], False, 0x01FF, 0x01FC),
        (ZONES[0], True, 0x01F0, 0x01F3),
        (ZONES[2], False, 0x01FF, 0x01F7),
        (ZONES[6], True, 0x0000, 0x0080),
    ],
)
async def test_snzb06p24_zone_write(snzb06p24, zone, value, mask, expected_mask):
    """Test a zone switch write changes only its bits in the device mask."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer
    local = snzb06p24.endpoints[1].sonoff_presence_local
    fc11.update_attribute(ZONE_MASK.id, mask)

    with mock.patch.object(
        fc11, "write_attributes_raw", mock.AsyncMock(return_value=write_response())
    ) as fc11_write:
        # ZHA passes the manufacturer code through
        result = await local.write_attributes(
            {zone.name: value}, manufacturer=foundation.UNDEFINED
        )

    assert result == [
        [
            foundation.WriteAttributesStatusRecord(
                foundation.Status.SUCCESS, ZONE_MASK.id
            )
        ]
    ]
    written = fc11_write.call_args[0][0]
    assert fc11_write.call_args.kwargs["manufacturer_code"] is None
    assert len(written) == 1
    assert written[0].attrid == ZONE_MASK.id
    assert written[0].value.value == expected_mask
    assert fc11.get(ZONE_MASK.id) == expected_mask
    assert local.get(zone.id) == value


async def test_snzb06p24_failed_zone_write(snzb06p24):
    """Test a rejected mask write leaves the zone switches untouched."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer
    local = snzb06p24.endpoints[1].sonoff_presence_local
    fc11.update_attribute(ZONE_MASK.id, 0x00FF)
    listener = ClusterListener(local)

    with mock.patch.object(
        fc11,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response(foundation.Status.FAILURE)),
    ):
        result = await local.write_attributes({ZONES[1].name: False})

    assert result == [
        [
            foundation.WriteAttributesStatusRecord(
                foundation.Status.FAILURE, ZONE_MASK.id
            )
        ]
    ]
    assert listener.attribute_updates == []
    assert local.get(ZONES[1].id) is True
    assert fc11.get(ZONE_MASK.id) == 0x00FF


async def test_snzb06p24_zone_write_reads_unknown_mask(snzb06p24):
    """Test the mask is read from the device before a write if not cached."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer

    with (
        mock.patch.object(
            fc11,
            "_read_attributes",
            mock.AsyncMock(return_value=read_response(0x00F0)),
        ),
        mock.patch.object(
            fc11, "write_attributes_raw", mock.AsyncMock(return_value=write_response())
        ) as fc11_write,
    ):
        await fc11.endpoint.sonoff_presence_local.write_attributes(
            {ZONES[0].name: True}
        )

    assert fc11_write.call_args[0][0][0].value.value == 0x00F3


async def test_snzb06p24_zone_write_unreadable_mask(snzb06p24):
    """Test nothing is written when the current mask cannot be read."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer
    local = snzb06p24.endpoints[1].sonoff_presence_local

    with (
        mock.patch.object(
            fc11,
            "_read_attributes",
            mock.AsyncMock(return_value=[foundation.Status.UNSUP_GENERAL_COMMAND]),
        ),
        mock.patch.object(fc11, "write_attributes_raw") as fc11_write,
    ):
        result = await local.write_attributes({ZONES[0].name: True})

    assert fc11_write.call_count == 0
    assert result == [
        [
            foundation.WriteAttributesStatusRecord(
                foundation.Status.UNSUP_GENERAL_COMMAND, ZONE_MASK.id
            )
        ]
    ]


async def test_snzb06p24_start_learning(snzb06p24):
    """Test the button sends a spatial learning start with the time as sequence."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer
    local = snzb06p24.endpoints[1].sonoff_presence_local

    with (
        mock.patch.object(fc11.endpoint, "request", mock.AsyncMock()) as request,
        mock.patch("time.time", return_value=SEQUENCE / 1000),
    ):
        await fc11.start_learning_now()

    assert local.get(UI_STATE.id) == SpatialLearningUiState.Start
    hdr, data = foundation.ZCLHeader.deserialize(request.call_args.kwargs["data"])
    assert hdr.command_id == FC11.ServerCommandDefs.spatial_learning.id
    assert hdr.frame_control.is_cluster
    assert hdr.manufacturer == snzb06p24.manufacturer_id
    assert data == bytes([SpatialLearningSubCommand.Start]) + SEQUENCE.to_bytes(
        8, "little"
    )

    # The device never answers
    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
        await local._timeout_task

    assert local.get(UI_STATE.id) == SpatialLearningUiState.Idle


# Replies of a SNZB-06P24 to a start request: learning started and takes
# 35 s, then learning succeeded
STARTED_FRAME = bytes.fromhex("117c040152ee4b68a10100000a774c68a1010000")
RESULT_FRAME = bytes.fromhex("11a0040252ee4b68a10100000000")


def send_frame(cluster, frame):
    """Feed a frame from the device to the cluster."""
    cluster.handle_message(*cluster.deserialize(frame))


async def test_snzb06p24_learning_countdown(snzb06p24):
    """Test the countdown follows the duration announced by the device."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer
    local = snzb06p24.endpoints[1].sonoff_presence_local
    listener = ClusterListener(local)

    with mock.patch.object(fc11, "send_default_rsp") as default_rsp:
        send_frame(fc11, STARTED_FRAME)

    assert default_rsp.call_count == 0
    assert local.get(UI_STATE.id) == SpatialLearningUiState.Countdown

    local._timeout_task.cancel()
    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
        await local._countdown_task

    countdown = [
        value for attr, value in listener.attribute_updates if attr == COUNTDOWN.id
    ]
    assert countdown == list(range(35, -1, -1))


async def test_snzb06p24_learning_result(snzb06p24):
    """Test a result from the device ends learning and stops the timers."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer
    local = snzb06p24.endpoints[1].sonoff_presence_local

    with mock.patch.object(fc11, "send_default_rsp"):
        send_frame(fc11, STARTED_FRAME)
        send_frame(fc11, RESULT_FRAME)

    assert local.get(UI_STATE.id) == SpatialLearningUiState.Idle
    assert local.get(COUNTDOWN.id) == 0

    listener = ClusterListener(local)
    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
        await asyncio.gather(
            local._countdown_task, local._timeout_task, return_exceptions=True
        )

    assert local._countdown_task.cancelled()
    assert local._timeout_task.cancelled()
    assert listener.attribute_updates == []


async def test_snzb06p24_learning_timeout(snzb06p24):
    """Test learning gives up when the device never reports a result."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer
    local = snzb06p24.endpoints[1].sonoff_presence_local
    listener = ClusterListener(local)

    with mock.patch.object(fc11, "send_default_rsp"):
        send_frame(fc11, STARTED_FRAME)
    local._countdown_task.cancel()

    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
        await local._timeout_task

    states = [
        value for attr, value in listener.attribute_updates if attr == UI_STATE.id
    ]
    assert states[-2:] == [SpatialLearningUiState.Timeout, SpatialLearningUiState.Idle]
    assert local.get(COUNTDOWN.id) == 0


async def test_snzb06p24_other_commands_untouched(snzb06p24):
    """Test commands other than start_learning_now are sent as is."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer
    local = snzb06p24.endpoints[1].sonoff_presence_local

    with mock.patch.object(fc11.endpoint, "request", mock.AsyncMock()) as request:
        await fc11.command(
            FC11.ServerCommandDefs.spatial_learning.id,
            SpatialLearningSubCommand.Start,
            1,
        )

    _, data = foundation.ZCLHeader.deserialize(request.call_args.kwargs["data"])
    assert data == bytes([SpatialLearningSubCommand.Start]) + (1).to_bytes(8, "little")
    assert local.get(UI_STATE.id) == SpatialLearningUiState.Idle


@pytest.mark.parametrize(
    "frame",
    [
        bytes.fromhex("0101050000"),
        # A spatial learning frame in the other direction
        bytes.fromhex("0901040152ee4b68a10100000a774c68a1010000"),
    ],
    ids=["other_command", "other_direction"],
)
def test_snzb06p24_other_requests_untouched(snzb06p24, frame):
    """Test other cluster requests get the default handling."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer
    local = snzb06p24.endpoints[1].sonoff_presence_local

    with mock.patch.object(fc11, "send_default_rsp") as default_rsp:
        send_frame(fc11, frame)

    assert default_rsp.call_count == 1
    assert local.get(UI_STATE.id) == SpatialLearningUiState.Idle


async def test_snzb06p24_learning_default_response(snzb06p24):
    """Test a default response is sent when the device asks for one."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer
    frame = bytes([STARTED_FRAME[0] & ~0x10]) + STARTED_FRAME[1:]

    with mock.patch.object(fc11, "send_default_rsp") as default_rsp:
        send_frame(fc11, frame)

    assert default_rsp.call_count == 1
    fc11.endpoint.sonoff_presence_local._cancel_tasks()


async def test_snzb06p24_local_write_stays_local(snzb06p24):
    """Test writes to attributes other than the zones never reach the device."""
    fc11 = snzb06p24.endpoints[1].sonoff_manufacturer
    local = snzb06p24.endpoints[1].sonoff_presence_local

    with mock.patch.object(fc11, "write_attributes_raw") as fc11_write:
        result = await local.write_attributes({COUNTDOWN.name: 5})

    assert fc11_write.call_count == 0
    assert result == [
        [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    ]
    assert local.get(COUNTDOWN.id) == 5
