"""Zemismart ZM24TQ / _TZE200_fzo2pocs motor configuration and positioning.

Protocol references:
https://github.com/Koenkk/zigbee-herdsman-converters/pull/11625
https://github.com/Koenkk/zigbee2mqtt/issues/22451

Match the Zigbee identity, not the retail name: other TS0601 motors use
different datapoints. No calibration or direction writes happen on startup.
"""

from typing import Any, Final

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering

from zhaquirks.tuya import TUYA_CLUSTER_ID, TUYA_MCU_COMMAND
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaClusterData, TuyaWindowCovering


class MotorDirection(t.enum8):
    """Direction stored by the motor, independent of percentage conversion."""

    Normal = 0
    Reversed = 1


class ZemismartWindowCovering(TuyaWindowCovering):
    """Keep the requested target separate from the measured position."""

    class AttributeDefs(TuyaWindowCovering.AttributeDefs):
        """Local target used to route writes exclusively to datapoint 2."""

        target_position: Final = foundation.ZCLAttributeDef(
            id=0xEF02, type=t.uint8_t, manufacturer_code=None
        )

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args: Any,
        **kwargs: Any,
    ) -> foundation.CommandSchema:
        """Send target changes without claiming the motor has reached them."""
        if command_id != WindowCovering.ServerCommandDefs.go_to_lift_percentage.id:
            return await super().command(command_id, *args, **kwargs)

        position = args[0] if args else kwargs.get("percentage_lift_value")
        status = foundation.Status.INVALID_VALUE
        if (
            isinstance(position, int)
            and not isinstance(position, bool)
            and 0 <= position <= 100
        ):
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                TuyaClusterData(
                    endpoint_id=self.endpoint.endpoint_id,
                    cluster_name=self.ep_attribute,
                    cluster_attr=self.AttributeDefs.target_position.name,
                    attr_value=position,
                    expect_reply=kwargs.get("expect_reply", True),
                    manufacturer=kwargs.get("manufacturer"),
                ),
            )
            status = foundation.Status.SUCCESS

        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=status)


builder = (
    TuyaQuirkBuilder("_TZE200_fzo2pocs", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=ZemismartWindowCovering.ep_attribute,
        attribute_name=ZemismartWindowCovering.AttributeDefs.tuya_cover_command.name,
    )
    .tuya_dp(
        dp_id=2,
        ep_attribute=ZemismartWindowCovering.ep_attribute,
        attribute_name=ZemismartWindowCovering.AttributeDefs.target_position.name,
        converter=lambda value: 100 - value,
        dp_converter=lambda value: 100 - value,
    )
    .tuya_dp(
        dp_id=3,
        ep_attribute=ZemismartWindowCovering.ep_attribute,
        attribute_name=WindowCovering.AttributeDefs.current_position_lift_percentage.name,
        converter=lambda value: 100 - value,
    )
    .adds(ZemismartWindowCovering)
    .replaces_endpoint(1, device_type=zha.DeviceType.WINDOW_COVERING_DEVICE)
    .tuya_enum(
        dp_id=5,
        attribute_name="motor_direction",
        enum_class=MotorDirection,
        translation_key="motor_direction",
        fallback_name="Motor direction",
    )
)

# Bool, not enum: SET=true / RESET=false. Buttons are repeatable commands;
# a switch would incorrectly imply we can always read the stored limit state.
for dp_id, label in ((103, "upper"), (104, "middle"), (105, "lower")):
    attribute_name = f"{label}_limit"
    builder.tuya_dp_attribute(
        dp_id=dp_id,
        attribute_name=attribute_name,
        type=t.Bool,
        access=foundation.ZCLAttributeAccess.Write,
    )
    for action, value in (("set", t.Bool.true), ("delete", t.Bool.false)):
        builder.write_attr_button(
            attribute_name=attribute_name,
            attribute_value=value,
            cluster_id=TUYA_CLUSTER_ID,
            unique_id_suffix=f"{action}_{label}_limit",
            translation_key=f"{action}_{label}_limit",
            fallback_name=f"{action.capitalize()} {label} limit",
        )

QUIRK = builder.skip_configuration().add_to_registry()
