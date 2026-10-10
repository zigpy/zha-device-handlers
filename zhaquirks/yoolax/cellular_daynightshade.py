"""Yoolax dual-rail day/night shades."""

from typing import Any

from zhaquirks.builder import QuirkBuilder
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
import zigpy.types as t

from zhaquirks.clusters import CustomCluster
from zhaquirks.tuya import TUYA_MCU_COMMAND
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import (
    TuyaClusterData,
    TuyaCoverControl,
    TuyaWindowCovering,
)


class YoolaxNewWindowCovering(TuyaWindowCovering):
    """Custom TuyaWindowCovering for Yoolax command order changes."""

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args: Any,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ) -> Any:
        """Override the default Cluster command."""

        # up_open
        if command_id == WindowCovering.ServerCommandDefs.up_open.id:
            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_name=self.ep_attribute,
                cluster_attr=(
                    WindowCovering.AttributeDefs.current_position_lift_percentage.name
                ),
                attr_value=0,
                expect_reply=expect_reply,
                manufacturer=manufacturer,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

        # down_close
        if command_id == WindowCovering.ServerCommandDefs.down_close.id:
            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_name=self.ep_attribute,
                cluster_attr=(
                    WindowCovering.AttributeDefs.current_position_lift_percentage.name
                ),
                attr_value=100,
                expect_reply=expect_reply,
                manufacturer=manufacturer,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

        # Close and stop commands are swapped on this device. We need to send a Close
        # command when the user sends a Stop command.
        if command_id == WindowCovering.ServerCommandDefs.stop.id:
            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_name=self.ep_attribute,
                cluster_attr=self.AttributeDefs.tuya_cover_command.name,
                attr_value=TuyaCoverControl.Close,
                expect_reply=expect_reply,
                manufacturer=manufacturer,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

        # Handle all other commands normally
        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )


class InvertedWindowCoveringCluster(CustomCluster, WindowCovering):
    """WindowCovering cluster implementation.

    This implementation inverts reported cover percentages for non-standard devices
    that do not follow the reporting spec and replaces open/close commands with
    go-to-lift-percentage commands.
    """

    cluster_id = WindowCovering.cluster_id

    def _update_attribute(self, attrid, value):
        if attrid == WindowCovering.AttributeDefs.current_position_lift_percentage.id:
            value = 100 - value
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
        """Translate open/close commands to inverted lift-percentage values."""
        if command_id == WindowCovering.ServerCommandDefs.up_open.id:
            command_id = WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
            args = (0,)
        elif command_id == WindowCovering.ServerCommandDefs.down_close.id:
            command_id = WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
            args = (100,)

        if (
            command_id == WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
            and args
        ):
            args = (100 - args[0],)

        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )


# Newer shades fully support Tuya commands, so we can use the TuyaWindowCovering
# cluster instead of manual inversion.
(
    TuyaQuirkBuilder("_TZE210_yqwse3h5", "TS0301")
    .tuya_cover(
        control_dp=125,
        position_state_dp=123,
        position_control_dp=124,
        cover_cfg=YoolaxNewWindowCovering,
    )
    .tuya_battery(dp_id=13)
    .skip_configuration()
    .add_to_registry()
)

# Older shades do not report state back on Tuya DPIDs, so we use plain
# WindowCovering cluster with inverted position reporting and command overrides.
(
    QuirkBuilder("_TZE200_eatmkx5j", "TS0301")
    .replaces(InvertedWindowCoveringCluster)
    .add_to_registry()
)
