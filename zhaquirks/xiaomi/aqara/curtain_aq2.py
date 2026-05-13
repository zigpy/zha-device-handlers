"""Aqara Roller Shade Controller (lumi.curtain.aq2) device."""

from __future__ import annotations

from typing import Any

from zigpy import types as t
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import AttributeReadEvent, AttributeReportedEvent, foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import AnalogOutput

from zhaquirks import CustomCluster
from zhaquirks.xiaomi import LUMI, BasicCluster


class AnalogOutputCurtainAq2(CustomCluster, AnalogOutput):
    """AnalogOutput cluster reporting current position and used for writing target position."""

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
        self.on_event(AttributeReadEvent.event_type, self._handle_attribute_read)
        self.on_event(
            AttributeReportedEvent.event_type, self._handle_attribute_reported
        )

    def _handle_attribute_read(self, event: AttributeReadEvent) -> None:
        """Handle attribute read events — update WindowCovering position."""
        if event.attribute_id == self.AttributeDefs.present_value.id:
            self.endpoint.window_covering.update_attribute(
                WindowCovering.AttributeDefs.current_position_lift_percentage.id,
                t.uint8_t(100 - event.value),
            )

    def _handle_attribute_reported(self, event: AttributeReportedEvent) -> None:
        """Handle present_value reports.

        Device reporting protocol:
          - Commanded movement: an echo (~30 ms after the write ACK, with the
            position slightly advanced from the start) and a final-position
            report on arrival.
          - Stop or physical movement: a single natural report ~1 s later.
        """
        if event.attribute_id == self.AttributeDefs.present_value.id:
            wc = self.endpoint.window_covering
            was_moving = wc._is_moving
            wc._is_moving = False
            if was_moving:
                # Discard the echo: feeding a position update to ZHA mid-movement
                # caps its transition timer at DEFAULT_MOVEMENT_TIMEOUT (5 s) via
                # _start_lift_transition(is_position_update=True), shorter than
                # this device's travel time — the entity would flip to OPEN/
                # CLOSED before the curtain arrives.
                return
            wc_attr = WindowCovering.AttributeDefs.current_position_lift_percentage.id
            wc_pos = t.uint8_t(100 - event.value)
            # Update twice to defeat ZHA's direction inference.  When
            # _target_lift_position is None (post-stop or unsolicited reports),
            # _determine_state otherwise marks the cover CLOSING/OPENING from
            # the previous→current change.  Identical updates leave
            # _lift_position_history=[v, v] so the inference branch — which
            # requires previous != current — is skipped.
            wc.update_attribute(wc_attr, wc_pos)
            wc.update_attribute(wc_attr, wc_pos)


class WindowCoveringCurtainAq2(CustomCluster, WindowCovering):
    """Window covering cluster for handling motor commands."""

    _CONSTANT_ATTRIBUTES = {
        WindowCovering.AttributeDefs.window_covering_type.id: WindowCovering.WindowCoveringType.Rollershade,
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        # True between a movement command and the echo report (or a successful
        # stop).  Read by AO._handle_attribute_reported to identify the echo
        # and by read_attributes to suppress the post-command poll.
        self._is_moving = False

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args: Any,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ) -> Any:
        """Route movement commands to AnalogOutput writes; stop uses standard ZCL stop.

        No explicit position read is issued after a command — position updates
        come from device reports (see AO._handle_attribute_reported).  A read
        here would propagate a mid-movement position update to ZHA and cap its
        transition timer at 5 s (see read_attributes).
        """
        if command_id == WindowCovering.ServerCommandDefs.up_open.id:
            (res,) = await self.endpoint.analog_output.write_attributes(
                {AnalogOutput.AttributeDefs.present_value.name: 100.0}
            )
            if res[0].status == foundation.Status.SUCCESS:
                self._is_moving = True
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)

        if command_id == WindowCovering.ServerCommandDefs.down_close.id:
            (res,) = await self.endpoint.analog_output.write_attributes(
                {AnalogOutput.AttributeDefs.present_value.name: 0.0}
            )
            if res[0].status == foundation.Status.SUCCESS:
                self._is_moving = True
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)

        if command_id == WindowCovering.ServerCommandDefs.go_to_lift_percentage.id:
            (res,) = await self.endpoint.analog_output.write_attributes(
                {AnalogOutput.AttributeDefs.present_value.name: float(100 - args[0])}
            )
            if res[0].status == foundation.Status.SUCCESS:
                self._is_moving = True
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)

        if command_id == WindowCovering.ServerCommandDefs.stop.id:
            result = await super().command(
                command_id,
                *args,
                manufacturer=manufacturer,
                expect_reply=expect_reply,
                tsn=tsn,
                **kwargs,
            )
            # Only clear when the stop actually succeeded: a NACK'd or failed
            # stop leaves the curtain moving and reads should stay suppressed.
            if getattr(result, "status", None) == foundation.Status.SUCCESS:
                self._is_moving = False
            return result

        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND)

    async def read_attributes(
        self,
        attributes: list[int | str | foundation.ZCLAttributeDef],
        **kwargs,
    ) -> Any:
        """Redirect current_position_lift_percentage reads to AnalogOutput.

        While _is_moving is True the redirect is suppressed: a mid-movement
        read would feed a position update to ZHA via
        _start_lift_transition(is_position_update=True), capping its
        transition timer at DEFAULT_MOVEMENT_TIMEOUT (5 s) — shorter than this
        device's travel time, causing a premature OPEN/CLOSED transition.
        The cached position is returned instead so the caller always gets a
        defined response.
        """
        success = {}
        failure = {}

        pos_attr_def = WindowCovering.AttributeDefs.current_position_lift_percentage
        pos_attr_key = next(
            (attr for attr in attributes if self.find_attribute(attr) == pos_attr_def),
            None,
        )

        if pos_attr_key is not None:
            remaining = [a for a in attributes if a != pos_attr_key]
            if not self._is_moving:
                pv = AnalogOutput.AttributeDefs.present_value
                (
                    ao_success,
                    ao_failure,
                ) = await self.endpoint.analog_output.read_attributes([pv], **kwargs)
                if pv in ao_success:
                    success[pos_attr_key] = t.uint8_t(100 - ao_success[pv])
                if pv in ao_failure:
                    failure[pos_attr_key] = ao_failure[pv]
            else:
                # No cache yet → surface a defined failure rather than
                # silently dropping the attribute from the response.
                cached = self._attr_cache.get(pos_attr_def.id)
                if cached is not None:
                    success[pos_attr_key] = cached
                else:
                    failure[pos_attr_key] = foundation.Status.FAILURE
        else:
            remaining = attributes

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
    .add_to_registry()
)
