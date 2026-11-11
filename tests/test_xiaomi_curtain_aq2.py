"""Tests for the Aqara Roller Shade Controller (lumi.curtain.aq2) quirk."""

import asyncio
import itertools
from unittest import mock

import pytest
from zha.application import Platform
from zha.application.platforms.cover import Cover
from zha.quirks import DEVICE_REGISTRY
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import AnalogOutput

from tests.common import ClusterListener
from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.xiaomi.aqara.curtain_aq2 import CurtainAq2Cover

zhaquirks.setup()

DIAGNOSTICS = "lumi-lumi-curtain-aq2.json"
COVER_UNIQUE_ID = "ab:cd:ef:12:28:b9:4c:7c-1-258"
PRESENT_VALUE = AnalogOutput.AttributeDefs.present_value


_tsn = itertools.count(1)


def report_position(zigpy_device, value: float) -> None:
    """Deliver an AnalogOutput present_value report from the device."""
    analog = zigpy_device.endpoints[1].analog_output
    hdr = foundation.ZCLHeader.general(
        next(_tsn) % 256,
        foundation.GeneralCommand.Report_Attributes,
        direction=foundation.Direction.Server_to_Client,
    ).serialize()
    cmd = (
        foundation.GENERAL_COMMANDS[foundation.GeneralCommand.Report_Attributes]
        .schema(
            [
                foundation.Attribute(
                    attrid=PRESENT_VALUE.id,
                    value=foundation.TypeValue(0x39, t.Single(value)),
                )
            ]
        )
        .serialize()
    )
    zigpy_device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=analog.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(hdr + cmd),
        )
    )


def patch_write(zigpy_device, status=foundation.Status.SUCCESS):
    """Patch the AnalogOutput write the cover commands end up in."""
    return mock.patch.object(
        zigpy_device.endpoints[1].analog_output,
        "_write_attributes",
        mock.AsyncMock(
            return_value=(
                [
                    foundation.WriteAttributesStatusRecord(
                        status=status, attrid=PRESENT_VALUE.id
                    )
                ],
            )
        ),
    )


async def make_cover(gateway, position: float):
    """Join the device, with the shade at `position` (0 closed, 100 open)."""
    device = await join_device_from_diagnostics(gateway, DIAGNOSTICS, DEVICE_REGISTRY)
    cover = device.get_platform_entity(Platform.COVER, unique_id=COVER_UNIQUE_ID)
    report_position(device.device, position)
    return device.device, cover


async def test_cover_entity_replaced():
    """The default cover entity is replaced with the one for this device."""
    async with zha_gateway() as gateway:
        _, cover = await make_cover(gateway, 100)

        assert type(cover) is CurtainAq2Cover
        assert isinstance(cover, Cover)
        assert cover.current_cover_position == 100
        assert cover.is_closed is False
        assert cover.is_opening is False
        assert cover.is_closing is False


async def test_unsolicited_report_does_not_infer_direction():
    """A report without a command (button press, stop) settles on open/closed."""
    async with zha_gateway() as gateway:
        zigpy_device, cover = await make_cover(gateway, 100)

        report_position(zigpy_device, 40)
        assert cover.current_cover_position == 40
        assert not cover.is_opening
        assert not cover.is_closing
        assert cover.is_closed is False

        report_position(zigpy_device, 0)
        assert cover.current_cover_position == 0
        assert not cover.is_opening
        assert not cover.is_closing
        assert cover.state.is_closed is True

        report_position(zigpy_device, 70)
        assert cover.current_cover_position == 70
        assert not cover.is_opening
        assert not cover.is_closing


async def test_close_with_echo_and_arrival():
    """Echo, then arrival report: stay closing the whole way, then closed."""
    async with zha_gateway() as gateway:
        zigpy_device, cover = await make_cover(gateway, 100)
        with patch_write(zigpy_device) as write:
            await cover.async_close_cover()

        assert write.call_args[0][0][0].value.value == 0.0
        assert cover.is_closing

        # Echo with the shade barely moved
        report_position(zigpy_device, 97)
        assert cover.current_cover_position == 97
        assert cover.is_closing

        # The transition timer covers the travel time, not 5 seconds
        timer = cover._lift_transition_timer
        assert timer is not None
        assert timer.when() - asyncio.get_running_loop().time() > 100

        # Arrival
        report_position(zigpy_device, 0)
        assert cover.current_cover_position == 0
        assert cover.is_closed is True
        assert not cover.is_closing
        assert cover._lift_transition_timer is None


async def test_close_with_lost_echo():
    """The arrival report is applied as the arrival even if no echo came first."""
    async with zha_gateway() as gateway:
        zigpy_device, cover = await make_cover(gateway, 100)

        with patch_write(zigpy_device):
            await cover.async_close_cover()
        assert cover.is_closing

        report_position(zigpy_device, 0)
        assert cover.current_cover_position == 0
        assert cover.is_closed is True
        assert not cover.is_closing


async def test_command_that_does_not_move_the_shade():
    """A command to the current position leaves nothing pending for later reports."""
    async with zha_gateway() as gateway:
        zigpy_device, cover = await make_cover(gateway, 100)

        with patch_write(zigpy_device):
            await cover.async_open_cover()
        assert not cover.is_opening
        assert not cover.is_closing

        # ZHA's short timer for a command that has nothing to move ends the
        # transition, and a later physical movement is applied as such
        timer = cover._lift_transition_timer
        assert timer is not None
        assert timer.when() - asyncio.get_running_loop().time() <= 5
        cover._clear_lift_transition(determine_state=True)

        report_position(zigpy_device, 50)
        assert cover.current_cover_position == 50
        assert not cover.is_opening
        assert not cover.is_closing


async def test_position_read_mid_movement_keeps_state():
    """An explicit refresh while the shade moves does not end the transition."""
    async with zha_gateway() as gateway:
        zigpy_device, cover = await make_cover(gateway, 100)
        analog = zigpy_device.endpoints[1].analog_output

        with patch_write(zigpy_device):
            await cover.async_close_cover()
        report_position(zigpy_device, 97)

        with mock.patch.object(
            analog,
            "read_attributes_raw",
            mock.AsyncMock(
                return_value=(
                    [
                        foundation.ReadAttributeRecord(
                            PRESENT_VALUE.id,
                            foundation.Status.SUCCESS,
                            foundation.TypeValue(None, t.Single(60.0)),
                        )
                    ],
                )
            ),
        ):
            await cover.async_update()

        assert cover.current_cover_position == 60
        assert cover.is_closing
        timer = cover._lift_transition_timer
        assert timer is not None
        assert timer.when() - asyncio.get_running_loop().time() > 50


async def test_set_position_and_stop():
    """Set position writes the target, stop ends the transition."""
    async with zha_gateway() as gateway:
        zigpy_device, cover = await make_cover(gateway, 100)
        with patch_write(zigpy_device) as write:
            await cover.async_set_cover_position(30)
        assert write.call_args[0][0][0].value.value == 30.0
        assert cover.is_closing

        report_position(zigpy_device, 80)
        assert cover.is_closing

        with mock.patch.object(
            zigpy_device.endpoints[1].window_covering,
            "request",
            mock.AsyncMock(
                return_value=foundation.GENERAL_COMMANDS[
                    foundation.GeneralCommand.Default_Response
                ].schema(
                    command_id=WindowCovering.ServerCommandDefs.stop.id,
                    status=foundation.Status.SUCCESS,
                )
            ),
        ):
            await cover.async_stop_cover()

        assert not cover.is_closing
        assert not cover.is_opening
        assert cover._lift_transition_timer is None

        # The natural report after the stop
        report_position(zigpy_device, 62)
        assert cover.current_cover_position == 62
        assert not cover.is_closing
        assert not cover.is_opening
        assert cover.is_closed is False


@pytest.mark.parametrize(
    ("command_id", "args", "expected"),
    [
        (WindowCovering.ServerCommandDefs.up_open.id, (), 100.0),
        (WindowCovering.ServerCommandDefs.down_close.id, (), 0.0),
        (WindowCovering.ServerCommandDefs.go_to_lift_percentage.id, (60,), 40.0),
    ],
)
async def test_commands_write_analog_output(command_id, args, expected):
    """Movement commands become AnalogOutput writes, a failure is reported."""
    async with zha_gateway() as gateway:
        zigpy_device, _ = await make_cover(gateway, 50)
        wc = zigpy_device.endpoints[1].window_covering
        with patch_write(zigpy_device) as write:
            res = await wc.command(command_id, *args)
        assert res.status == foundation.Status.SUCCESS
        assert write.call_args[0][0][0].value.value == expected

        with patch_write(zigpy_device, foundation.Status.FAILURE):
            res = await wc.command(command_id, *args)
        assert res.status == foundation.Status.FAILURE

        res = await wc.go_to_tilt_percentage(0)
        assert res.status == foundation.Status.UNSUP_CLUSTER_COMMAND


async def test_position_read_redirects_to_analog_output():
    """Lift reads are answered from AnalogOutput, other attributes pass through."""
    async with zha_gateway() as gateway:
        zigpy_device, _ = await make_cover(gateway, 50)
        wc = zigpy_device.endpoints[1].window_covering
        listener = ClusterListener(wc)
        lift = WindowCovering.AttributeDefs.current_position_lift_percentage

        def mock_read(value):
            def read(attributes, manufacturer=None):
                return (
                    [
                        foundation.ReadAttributeRecord(
                            attr,
                            foundation.Status.SUCCESS,
                            foundation.TypeValue(None, value),
                        )
                        for attr in attributes
                    ],
                )

            return read

        with (
            mock.patch.object(
                wc, "read_attributes_raw", mock.AsyncMock(side_effect=mock_read(1))
            ),
            mock.patch.object(
                zigpy_device.endpoints[1].analog_output,
                "read_attributes_raw",
                mock.AsyncMock(side_effect=mock_read(t.Single(25.0))),
            ) as ao_read,
        ):
            success, failure = await wc.read_attributes([lift.name])
            assert success == {lift.name: 75}
            assert failure == {}
            assert ao_read.call_args[0][0] == [PRESENT_VALUE.id]
            assert wc.read_attributes_raw.call_count == 0

            # Mixed read: the rest goes to the WindowCovering cluster
            status = WindowCovering.AttributeDefs.config_status
            success, _ = await wc.read_attributes([lift.id, status.id])
            assert success[lift.id] == 75
            assert wc.read_attributes_raw.call_args[0][0] == [status.id]

        assert (lift.id, 75) in listener.attribute_updates

        # A failed AnalogOutput read is reported as a failed lift read
        with mock.patch.object(
            zigpy_device.endpoints[1].analog_output,
            "read_attributes_raw",
            mock.AsyncMock(
                return_value=(
                    [
                        foundation.ReadAttributeRecord(
                            PRESENT_VALUE.id, foundation.Status.FAILURE
                        )
                    ],
                )
            ),
        ):
            success, failure = await wc.read_attributes([lift.name])
        assert success == {}
        assert failure == {lift.name: foundation.Status.FAILURE}


async def start_close_and_echo(zigpy_device, cover):
    """Close from open and deliver the echo."""
    with patch_write(zigpy_device):
        await cover.async_close_cover()
    report_position(zigpy_device, 97)
    assert cover.is_closing


@pytest.mark.parametrize(("position", "closed"), [(60, False), (100, False)])
async def test_physical_stop_or_reversal_during_movement(position, closed):
    """A late report that is not the target ends the commanded transition."""
    async with zha_gateway() as gateway:
        zigpy_device, cover = await make_cover(gateway, 100)
        await start_close_and_echo(zigpy_device, cover)

        # Well after the echo
        cover._command_time -= 30
        report_position(zigpy_device, position)

        assert cover.current_cover_position == position
        assert not cover.is_closing
        assert not cover.is_opening
        assert cover.state.is_closed is closed
        assert cover._lift_transition_timer is None


async def test_refresh_is_not_a_late_report():
    """A refresh long after the command does not end the transition."""
    async with zha_gateway() as gateway:
        zigpy_device, cover = await make_cover(gateway, 100)
        await start_close_and_echo(zigpy_device, cover)
        cover._command_time -= 30

        with mock.patch.object(
            zigpy_device.endpoints[1].analog_output,
            "read_attributes_raw",
            mock.AsyncMock(
                return_value=(
                    [
                        foundation.ReadAttributeRecord(
                            PRESENT_VALUE.id,
                            foundation.Status.SUCCESS,
                            foundation.TypeValue(None, t.Single(60.0)),
                        )
                    ],
                )
            ),
        ):
            await cover.async_update()

        assert cover.current_cover_position == 60
        assert cover.is_closing


async def test_device_lift_reports_are_ignored():
    """The position comes from AnalogOutput, not from the WindowCovering cluster."""
    async with zha_gateway() as gateway:
        zigpy_device, cover = await make_cover(gateway, 0)
        wc = zigpy_device.endpoints[1].window_covering
        assert cover.state.is_closed is True

        hdr = foundation.ZCLHeader.general(
            200,
            foundation.GeneralCommand.Report_Attributes,
            direction=foundation.Direction.Server_to_Client,
        ).serialize()
        cmd = (
            foundation.GENERAL_COMMANDS[foundation.GeneralCommand.Report_Attributes]
            .schema(
                [
                    foundation.Attribute(
                        attrid=WindowCovering.AttributeDefs.current_position_lift_percentage.id,
                        value=foundation.TypeValue(0x20, t.uint8_t(0)),
                    )
                ]
            )
            .serialize()
        )
        zigpy_device.packet_received(
            t.ZigbeePacket(
                profile_id=260,
                cluster_id=wc.cluster_id,
                src_ep=1,
                dst_ep=1,
                data=t.SerializableBytes(hdr + cmd),
            )
        )

        assert cover.current_cover_position == 0
        assert cover.state.is_closed is True


async def test_stop_reads_position():
    """The position is read after a successful stop."""
    async with zha_gateway() as gateway:
        zigpy_device, cover = await make_cover(gateway, 100)
        wc = zigpy_device.endpoints[1].window_covering
        analog = zigpy_device.endpoints[1].analog_output

        with (
            mock.patch.object(
                wc,
                "request",
                mock.AsyncMock(
                    return_value=foundation.GENERAL_COMMANDS[
                        foundation.GeneralCommand.Default_Response
                    ].schema(
                        command_id=WindowCovering.ServerCommandDefs.stop.id,
                        status=foundation.Status.SUCCESS,
                    )
                ),
            ),
            mock.patch.object(
                analog,
                "read_attributes_raw",
                mock.AsyncMock(
                    return_value=(
                        [
                            foundation.ReadAttributeRecord(
                                PRESENT_VALUE.id,
                                foundation.Status.SUCCESS,
                                foundation.TypeValue(None, t.Single(35.0)),
                            )
                        ],
                    )
                ),
            ) as read,
        ):
            await wc.stop()

        assert read.call_args[0][0] == [PRESENT_VALUE.id]
        assert cover.current_cover_position == 35


async def test_position_is_clamped_and_cache_reads_use_the_cluster():
    """Out of range values stay in range, cache reads do not touch AnalogOutput."""
    async with zha_gateway() as gateway:
        zigpy_device, cover = await make_cover(gateway, 100)
        wc = zigpy_device.endpoints[1].window_covering
        lift = WindowCovering.AttributeDefs.current_position_lift_percentage

        report_position(zigpy_device, 101)
        assert cover.current_cover_position == 100
        report_position(zigpy_device, -1)
        assert cover.current_cover_position == 0

        with mock.patch.object(
            zigpy_device.endpoints[1].analog_output,
            "read_attributes_raw",
            mock.AsyncMock(),
        ) as ao_read:
            success, _ = await wc.read_attributes([lift.name], only_cache=True)
        assert ao_read.call_count == 0
        assert success == {lift.name: 100}

        with patch_write(zigpy_device) as write:
            await wc.go_to_lift_percentage(percentage_lift_value=40)
        assert write.call_args[0][0][0].value.value == 60.0


async def test_stop_succeeds_when_the_position_read_fails():
    """A failing position read after a stop does not fail the stop."""
    async with zha_gateway() as gateway:
        zigpy_device, _ = await make_cover(gateway, 100)
        wc = zigpy_device.endpoints[1].window_covering

        with (
            mock.patch.object(
                wc,
                "request",
                mock.AsyncMock(
                    return_value=foundation.GENERAL_COMMANDS[
                        foundation.GeneralCommand.Default_Response
                    ].schema(
                        command_id=WindowCovering.ServerCommandDefs.stop.id,
                        status=foundation.Status.SUCCESS,
                    )
                ),
            ),
            mock.patch.object(
                zigpy_device.endpoints[1].analog_output,
                "read_attributes_raw",
                mock.AsyncMock(side_effect=TimeoutError),
            ),
        ):
            res = await wc.stop()

        assert res.status == foundation.Status.SUCCESS


async def test_echo_during_a_slow_write_is_not_late():
    """The echo window starts when the command returns, not when it is sent."""
    async with zha_gateway() as gateway:
        zigpy_device, cover = await make_cover(gateway, 100)
        analog = zigpy_device.endpoints[1].analog_output
        loop = asyncio.get_running_loop()

        async def slow_write(*args, **kwargs):
            # The echo comes in before the write has returned, a lot later than
            # the echo window after the command was started
            cover._command_time -= 30
            report_position(zigpy_device, 97)
            return (
                [
                    foundation.WriteAttributesStatusRecord(
                        status=foundation.Status.SUCCESS, attrid=PRESENT_VALUE.id
                    )
                ],
            )

        with mock.patch.object(analog, "_write_attributes", slow_write):
            await cover.async_close_cover()

        assert cover.current_cover_position == 97
        assert cover.is_closing
        assert cover._target_lift_position == 0
        assert loop.time() - cover._command_time < 5
