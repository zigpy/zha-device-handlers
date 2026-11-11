"""Aqara Roller Shade Controller (lumi.curtain.aq2) device."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from zha.application.platforms.cover import Cover
from zigpy import types as t
from zigpy.exceptions import ZigbeeException
from zigpy.zcl import AttributeReadEvent, AttributeReportedEvent, foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import AnalogOutput

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.xiaomi import LUMI, BasicCluster

LIFT_ATTR = WindowCovering.AttributeDefs.current_position_lift_percentage


def _to_lift_percentage(present_value: float) -> t.uint8_t:
    """Convert a present_value position (0 closed, 100 open) to a ZCL lift percentage."""
    return t.uint8_t(round(100 - min(max(present_value, 0), 100)))


class CurtainAq2Cover(Cover):
    """Cover that trusts the device's position reports instead of inferring motion.

    The device reports `present_value` sparsely: an echo shortly after a command and
    the final position once it arrives (or ~1 s after a stop). ZHA's cover state
    machine makes two assumptions that do not hold for that pattern:

    - A position report with no commanded target is read as the cover moving towards
      the open or closed end. Here, it is the cover having stopped.
    - A position report during a transition limits the transition timer to
      DEFAULT_MOVEMENT_TIMEOUT (5 s), much shorter than this device's travel time,
      so the entity would flip to open/closed before the shade arrives.

    So while a commanded transition is running, the cover is moving until it reaches
    the target, a stop is sent or the full-travel timer expires. Reports only move
    the position.

    The device sends nothing between the echo and the arrival, so a report that comes
    well after the command, and is not the target, means the shade was stopped or
    moved by something else (a physical button). That ends the transition. Reads
    triggered by ZHA itself (a refresh mid-movement) are not such a report.
    """

    # Seconds after a command in which a report is its echo
    _ECHO_WINDOW = 5

    _command_time: float | None = None
    _refreshing: bool = False

    async def _commanded(self, command) -> None:
        """Run a movement command, the echo window starts once it has returned.

        A report that arrives while the command is still in flight is not late.
        """
        self._command_time = float("inf")
        try:
            await command
        finally:
            self._command_time = asyncio.get_running_loop().time()

    async def async_open_cover(self) -> None:
        """Open the cover."""
        await self._commanded(super().async_open_cover())

    async def async_close_cover(self) -> None:
        """Close the cover."""
        await self._commanded(super().async_close_cover())

    async def async_set_cover_position(self, position: int) -> None:
        """Move the cover to a specific position."""
        await self._commanded(super().async_set_cover_position(position))

    async def async_update(self) -> None:
        """Refresh the position, which is not a report from the device."""
        self._refreshing = True
        try:
            await super().async_update()
        finally:
            self._refreshing = False

    def handle_attribute_updated(self, event) -> None:
        """End a commanded transition on a late report that is not the target."""
        super().handle_attribute_updated(event)

        if (
            event.attribute_id == LIFT_ATTR.id
            and not self._refreshing
            and self._target_lift_position is not None
            and self.current_cover_position != self._target_lift_position
            and self._command_time is not None
            and asyncio.get_running_loop().time() - self._command_time
            > self._ECHO_WINDOW
        ):
            self._clear_lift_transition(determine_state=True)

    @staticmethod
    def _determine_state(
        current: int | None,
        target: int | None,
        previous: int | None,
        is_position_update: bool = False,
        is_transition: bool = False,
    ):
        """Never infer a direction from a position report alone."""
        return Cover._determine_state(current, target, previous, False, is_transition)

    def _start_lift_transition(self, is_position_update: bool = False) -> None:
        """Keep the full-travel timer when a position report arrives."""
        super()._start_lift_transition(is_position_update=False)


class AnalogOutputCurtainAq2(CustomCluster, AnalogOutput):
    """AnalogOutput cluster reporting current position and used for writing target position.

    `present_value` is the position in percent, 0 closed and 100 open, so the
    WindowCovering lift percentage (0 open, 100 closed) is `100 - present_value`.
    """

    _CONSTANT_ATTRIBUTES = {
        AnalogOutput.AttributeDefs.description.id: "Current position",
        AnalogOutput.AttributeDefs.max_present_value.id: 100.0,
        AnalogOutput.AttributeDefs.min_present_value.id: 0.0,
        AnalogOutput.AttributeDefs.out_of_service.id: 0,
        AnalogOutput.AttributeDefs.resolution.id: 1.0,
        AnalogOutput.AttributeDefs.status_flags.id: 0x00,
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.on_event(AttributeReadEvent.event_type, self._update_lift_position)
        self.on_event(AttributeReportedEvent.event_type, self._update_lift_position)

    def _update_lift_position(
        self, event: AttributeReadEvent | AttributeReportedEvent
    ) -> None:
        """Mirror present_value reads and reports to the WindowCovering position."""
        if event.attribute_id == self.AttributeDefs.present_value.id:
            self.endpoint.window_covering.update_attribute(
                LIFT_ATTR.id, _to_lift_percentage(event.value)
            )


class WindowCoveringCurtainAq2(CustomCluster, WindowCovering):
    """Window covering cluster translating motor commands to AnalogOutput writes."""

    _CONSTANT_ATTRIBUTES = {
        WindowCovering.AttributeDefs.window_covering_type.id: WindowCovering.WindowCoveringType.Rollershade,
    }

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Route movement commands to AnalogOutput writes; stop uses standard ZCL stop."""
        if command_id == WindowCovering.ServerCommandDefs.up_open.id:
            target = 100.0
        elif command_id == WindowCovering.ServerCommandDefs.down_close.id:
            target = 0.0
        elif command_id == WindowCovering.ServerCommandDefs.go_to_lift_percentage.id:
            percentage = args[0] if args else kwargs["percentage_lift_value"]
            target = float(100 - percentage)
        elif command_id == WindowCovering.ServerCommandDefs.stop.id:
            result = await super().command(command_id, *args, **kwargs)
            if getattr(result, "status", None) == foundation.Status.SUCCESS:
                # The device does not necessarily report the position after a stop
                # (a failed read must not turn the successful stop into an error)
                with contextlib.suppress(ZigbeeException, TimeoutError):
                    await self.endpoint.analog_output.read_attributes(
                        [AnalogOutput.AttributeDefs.present_value], allow_cache=False
                    )
            return result
        else:
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(
                command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND
            )

        (res,) = await self.endpoint.analog_output.write_attributes(
            {AnalogOutput.AttributeDefs.present_value.name: target}
        )
        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=res[0].status)

    def handle_cluster_general_request(self, hdr, args, *, dst_addressing=None):
        """Ignore the device's own lift reports: the position comes from AnalogOutput."""
        if hdr.command_id == foundation.GeneralCommand.Report_Attributes:
            args.attribute_reports = [
                attr for attr in args.attribute_reports if attr.attrid != LIFT_ATTR.id
            ]
            if not args.attribute_reports:
                return

        super().handle_cluster_general_request(hdr, args, dst_addressing=dst_addressing)

    async def read_attributes(
        self,
        attributes: list[int | str | foundation.ZCLAttributeDef],
        **kwargs,
    ) -> Any:
        """Redirect current_position_lift_percentage reads to AnalogOutput."""
        if kwargs.get("allow_cache") or kwargs.get("only_cache"):
            # The AnalogOutput cache holds the last written target, not the position
            return await super().read_attributes(attributes, **kwargs)

        pos_attr_key = next(
            (attr for attr in attributes if self.find_attribute(attr) == LIFT_ATTR),
            None,
        )

        if pos_attr_key is None:
            return await super().read_attributes(attributes, **kwargs)

        success = {}
        failure = {}

        present_value = AnalogOutput.AttributeDefs.present_value
        ao_success, ao_failure = await self.endpoint.analog_output.read_attributes(
            [present_value], **kwargs
        )
        if present_value in ao_success:
            success[pos_attr_key] = _to_lift_percentage(ao_success[present_value])
        if present_value in ao_failure:
            failure[pos_attr_key] = ao_failure[present_value]

        remaining = [a for a in attributes if a != pos_attr_key]
        if remaining:
            other_success, other_failure = await super().read_attributes(
                remaining, **kwargs
            )
            success.update(other_success)
            failure.update(other_failure)

        return success, failure


(
    QuirkBuilder(LUMI, "lumi.curtain.aq2")
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=AnalogOutput.cluster_id)
    .replaces(AnalogOutputCurtainAq2, endpoint_id=1)
    .replaces(BasicCluster, endpoint_id=1)
    .replaces(WindowCoveringCurtainAq2, endpoint_id=1)
    .replaces_entity(
        Cover,
        CurtainAq2Cover,
        endpoint_id=1,
        cluster_id=WindowCovering.cluster_id,
    )
    .add_to_registry()
)
