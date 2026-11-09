"""Quirk for Tuya TS130F cover."""

import asyncio
from typing import Final

import zigpy.types as t
from zigpy.zcl import AttributeReportedEvent
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class MotorMode(t.enum8):
    """Motor mode enum."""

    Strong = 0x00
    Weak = 0x01


class MotorState(t.enum8):
    """Motor moving state."""

    Opening = 0x00
    Idle = 0x01
    Closing = 0x02


CURRENT_LIFT_PERC_ATTR_ID = (
    WindowCovering.AttributeDefs.current_position_lift_percentage.id
)
WRITE_DELAY_S = 3


class TuyaCoveringCluster(CustomCluster, WindowCovering):
    """Custom covering cluster that addresses device quirks.

    Covering cluster that manually writes the
    `current_position_lift_percentage` back to the device.
    While for home assistant 0=open and 100=closed, for the device 0=closed and
    100=open; therefore the percentage value is inverted when reading/writing
    it from/to the device, and when sending the go_to_lift_percentage command.
    """

    class AttributeDefs(WindowCovering.AttributeDefs):
        """Attribute definitions."""

        tuya_motor_mode: Final = ZCLAttributeDef(
            id=0x8000,
            type=MotorMode,
        )
        tuya_motor_state: Final = ZCLAttributeDef(
            id=0xF000,
            type=MotorState,
        )
        tuya_calibrated: Final = ZCLAttributeDef(
            id=0xF001,
            type=t.enum8,
        )
        tuya_motor_reversal: Final = ZCLAttributeDef(
            id=0xF002,
            type=t.enum8,
        )
        tuya_calibration_time: Final = ZCLAttributeDef(
            id=0xF003,
            type=t.uint16_t,
        )

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.on_event(
            AttributeReportedEvent.event_type,
            self._handle_on_report_event,
        )

    def _handle_on_report_event(self, event: AttributeReportedEvent) -> None:
        """Handle writeback of `current_lift_percentage`.

        When the device report `tuya_motor_state` as `IDLE`, it means it has
        completed its movement; we write the lift percentage back to the device

        NOTE: if the percentage is desynced, a up_open / down_close command
        could cause the device to continuously report a percentage change
        regardless of its real position.
        If the device is fully open, it will continuously report a percentage
        of 99%; after the configured `tuya_calibration_time` has passed, it
        will report 100% and `tuya_motor_state` as `IDLE`; if a `stop` command
        is issued before the `tuya_calibration_time` has passed, the device
        won't report percentage as 100%. Same applies when the cover is fully
        closed.
        """
        if (
            event.attribute_id == self.AttributeDefs.tuya_motor_state.id
            and event.value == MotorState.Idle
        ):
            self.create_catching_task(self._write_lift_percentage())

    async def _write_lift_percentage(self):
        # HACK: immediately reading cached percentage could skip the last round
        # of percentage report.
        await asyncio.sleep(WRITE_DELAY_S)
        cached_value = self._attr_cache.get(CURRENT_LIFT_PERC_ATTR_ID)
        if cached_value is not None:
            await self.write_attributes(
                attributes={"current_position_lift_percentage": 100 - cached_value},
                update_cache=False,
            )

    def _update_attribute(self, attrid, value):
        """Invert read/reported current_position_lift_percentage value."""
        if attrid == CURRENT_LIFT_PERC_ATTR_ID:
            value = 100 - value
        super()._update_attribute(attrid, value)

    async def command(
        self,
        command_id,
        *args,
        manufacturer=None,
        expect_reply=True,
        tsn=None,
    ):
        """Invert up_open, down_close and go_to_lift_percentage command."""
        if command_id in (
            WindowCovering.ServerCommandDefs.up_open.id,
            WindowCovering.ServerCommandDefs.down_close.id,
        ):
            success, _ = await self.read_attributes(
                [self.AttributeDefs.tuya_motor_reversal.id],
                manufacturer=manufacturer,
            )
            try:
                is_reversed = success[self.AttributeDefs.tuya_motor_reversal.id]
                if is_reversed:
                    if command_id == WindowCovering.ServerCommandDefs.up_open.id:
                        command_id = WindowCovering.ServerCommandDefs.down_close.id
                    else:
                        command_id = WindowCovering.ServerCommandDefs.up_open.id
            except KeyError:
                self.error("Error when reading tuya_motor_reversal")
        # TODO: check if `is_reversed`?
        if command_id == WindowCovering.ServerCommandDefs.go_to_lift_percentage.id:
            # TODO: possible issue but unable to reproduce https://github.com/zigpy/zha-device-handlers/issues/2676#issuecomment-5284034085
            v = (100 - args[0],)
            return await super().command(
                command_id,
                *v,
                manufacturer=manufacturer,
                expect_reply=expect_reply,
                tsn=tsn,
            )
        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
        )


(
    QuirkBuilder("_TZ3210_dwytrmda", "TS130F")
    # .applies_to("_TZ3000_eg7awg6a", "TS130F")
    .replaces(TuyaCoveringCluster)
    .number(
        attribute_name=TuyaCoveringCluster.AttributeDefs.tuya_calibration_time.name,
        cluster_id=TuyaCoveringCluster.cluster_id,
        min_value=1,
        max_value=1500,  # A sensible max?
        step=0.1,
        multiplier=0.1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="calibration_vertical_run_time_up",
        fallback_name="Calibration vertical run time up",
        # initially_disabled=True,
    )
    .switch(
        attribute_name=TuyaCoveringCluster.AttributeDefs.tuya_motor_reversal.name,
        cluster_id=TuyaCoveringCluster.cluster_id,
        translation_key="reverse",
        fallback_name="Reverse",
    )
    .switch(
        attribute_name=TuyaCoveringCluster.AttributeDefs.tuya_calibrated.name,
        cluster_id=TuyaCoveringCluster.cluster_id,
        translation_key="calibrated",
        fallback_name="Calibrated",
        # initially_disabled=True,
    )
    .enum(
        attribute_name=TuyaCoveringCluster.AttributeDefs.tuya_motor_state.name,
        cluster_id=TuyaCoveringCluster.cluster_id,
        enum_class=MotorState,
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="motor_state",
        fallback_name="Motor state",
    )
    .add_to_registry()
)
