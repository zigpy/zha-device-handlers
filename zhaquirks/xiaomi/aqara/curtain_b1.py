"""Aqara Curtain Driver B1 (ZNCLDJ11LM) device."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from zigpy import types as t
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import AttributeReadEvent, AttributeReportedEvent, Cluster, foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import AnalogOutput, MultistateOutput, OnOff
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import CustomCluster
from zhaquirks.xiaomi import LUMI


class AnalogOutputCurtainB1(CustomCluster, AnalogOutput):
    """AnalogOutput cluster used as source of truth for curtain position.

    present_value semantics: 0 = fully closed, 100 = fully open.
    """

    _CONSTANT_ATTRIBUTES = {
        AnalogOutput.AttributeDefs.max_present_value.id: 100.0,
        AnalogOutput.AttributeDefs.min_present_value.id: 0.0,
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        super().__init__(*args, **kwargs)
        self.on_event(
            AttributeReadEvent.event_type, self._handle_attribute_read_or_reported
        )
        self.on_event(
            AttributeReportedEvent.event_type, self._handle_attribute_read_or_reported
        )

    def _handle_attribute_read_or_reported(
        self, event: AttributeReadEvent | AttributeReportedEvent
    ) -> None:
        """Propagate present_value to WindowCovering current_position_lift_percentage."""
        if event.attribute_id == self.AttributeDefs.present_value.id:
            wc = self.endpoint.window_covering
            wc._from_analog = True  # pylint: disable=protected-access
            try:
                wc.update_attribute(
                    WindowCovering.AttributeDefs.current_position_lift_percentage.id,
                    t.uint8_t(100 - event.value),
                )
            finally:
                wc._from_analog = False  # pylint: disable=protected-access


class WindowCoveringCurtainB1(CustomCluster, WindowCovering):
    """WindowCovering cluster backed by AnalogOutput.present_value.

    The device reports current_position_lift_percentage in a non-standard
    scale (0 = closed, 100 = open, same as present_value) rather than the
    Zigbee standard (0 = open, 100 = closed). Reads are redirected to
    AnalogOutput.present_value, autonomous reports are inverted on receipt,
    and motor commands are translated to AnalogOutput writes.
    """

    _CONSTANT_ATTRIBUTES = {
        WindowCovering.AttributeDefs.window_covering_type.id: WindowCovering.WindowCoveringType.Drapery,
    }

    # Redirect reads of current_position_lift_percentage to AnalogOutput.present_value.
    _REDIRECT_ATTRIBUTES: dict[
        ZCLAttributeDef, tuple[ZCLAttributeDef, type[Cluster], Callable]
    ] = {
        WindowCovering.AttributeDefs.current_position_lift_percentage: (
            AnalogOutput.AttributeDefs.present_value,
            AnalogOutput,
            lambda x: t.uint8_t(100 - x),
        ),
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        super().__init__(*args, **kwargs)
        self._from_analog = False

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Invert device-sourced lift_percentage to standard Zigbee scale."""
        lift_id = self.AttributeDefs.current_position_lift_percentage.id
        if attrid == lift_id and not self._from_analog:
            value = t.uint8_t(100 - value)
        super()._update_attribute(attrid, value)

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args: Any,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ) -> Any:
        """Translate motor commands to AnalogOutput writes.

        The B1 expects target positions written to AnalogOutput.present_value
        (100 = open, 0 = closed) rather than via native WindowCovering commands.
        Each command is followed by a read so HA's position state stays in sync.
        """
        if command_id == WindowCovering.ServerCommandDefs.up_open.id:
            (res,) = await self.endpoint.analog_output.write_attributes(
                {AnalogOutput.AttributeDefs.present_value.name: 100}
            )
            await self.read_attributes(
                [self.AttributeDefs.current_position_lift_percentage.id]
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)

        if command_id == WindowCovering.ServerCommandDefs.down_close.id:
            (res,) = await self.endpoint.analog_output.write_attributes(
                {AnalogOutput.AttributeDefs.present_value.name: 0}
            )
            await self.read_attributes(
                [self.AttributeDefs.current_position_lift_percentage.id]
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)

        if command_id == WindowCovering.ServerCommandDefs.go_to_lift_percentage.id:
            (res,) = await self.endpoint.analog_output.write_attributes(
                {AnalogOutput.AttributeDefs.present_value.name: (100 - args[0])}
            )
            await self.read_attributes(
                [self.AttributeDefs.current_position_lift_percentage.id]
            )
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
            await self.read_attributes(
                [self.AttributeDefs.current_position_lift_percentage.id]
            )
            return result

        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND)

    async def read_attributes(
        self,
        attributes: list[int | str | foundation.ZCLAttributeDef],
        **kwargs,
    ) -> Any:
        """Redirect attribute reads to another cluster per _REDIRECT_ATTRIBUTES."""
        success = {}
        failure = {}

        attr_defs = {self.find_attribute(attr): attr for attr in attributes}

        for redirected_attr_def, (
            target_attr,
            target_cluster,
            format_func,
        ) in self._REDIRECT_ATTRIBUTES.items():
            if redirected_attr_def not in attr_defs:
                continue

            other_cluster = getattr(self.endpoint, target_cluster.ep_attribute)
            other_success, other_failure = await other_cluster.read_attributes(
                [target_attr], **kwargs
            )

            attr_key = attr_defs.pop(redirected_attr_def)
            attributes.remove(attr_key)

            if target_attr in other_success:
                success[attr_key] = format_func(other_success[target_attr])

            if target_attr in other_failure:
                failure[attr_key] = other_failure[target_attr]

        other_success, other_failure = await super().read_attributes(
            attributes, **kwargs
        )
        success.update(other_success)
        failure.update(other_failure)

        return success, failure


(
    QuirkBuilder(LUMI, "lumi.curtain")
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=AnalogOutput.cluster_id)
    .prevent_default_entity_creation(
        endpoint_id=1, cluster_id=MultistateOutput.cluster_id
    )
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=OnOff.cluster_id)
    .prevent_default_entity_creation(
        endpoint_id=1, cluster_id=OccupancySensing.cluster_id
    )
    .replaces(AnalogOutputCurtainB1, endpoint_id=1)
    .replaces(WindowCoveringCurtainB1, endpoint_id=1)
    .add_to_registry()
)
