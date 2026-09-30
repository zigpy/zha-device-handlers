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
    """Motor direction values."""

    Forward = 0x00
    Back = 0x01


class ZemismartWindowCovering(TuyaWindowCovering):
    """Keep the requested target separate from the measured position."""

    class AttributeDefs(TuyaWindowCovering.AttributeDefs):
        """Local target used to route writes exclusively to datapoint 2."""

        target_position: Final = foundation.ZCLAttributeDef(
            id=0xEF02, type=t.uint8_t, is_manufacturer_specific=True
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


# Limit datapoints are bool, not enum: SET=true / RESET=false. Buttons are
# repeatable commands; a switch would incorrectly imply the stored limit state
# can always be read back.
(
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
    .tuya_dp_attribute(
        dp_id=103,
        attribute_name="upper_limit",
        type=t.Bool,
        access=foundation.ZCLAttributeAccess.Write,
    )
    .write_attr_button(
        attribute_name="upper_limit",
        attribute_value=t.Bool.true,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="set_upper_limit",
        translation_key="set_upper_limit",
        fallback_name="Set upper limit",
    )
    .write_attr_button(
        attribute_name="upper_limit",
        attribute_value=t.Bool.false,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="delete_upper_limit",
        translation_key="delete_upper_limit",
        fallback_name="Delete upper limit",
    )
    .tuya_dp_attribute(
        dp_id=104,
        attribute_name="middle_limit",
        type=t.Bool,
        access=foundation.ZCLAttributeAccess.Write,
    )
    .write_attr_button(
        attribute_name="middle_limit",
        attribute_value=t.Bool.true,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="set_middle_limit",
        translation_key="set_middle_limit",
        fallback_name="Set middle limit",
    )
    .write_attr_button(
        attribute_name="middle_limit",
        attribute_value=t.Bool.false,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="delete_middle_limit",
        translation_key="delete_middle_limit",
        fallback_name="Delete middle limit",
    )
    .tuya_dp_attribute(
        dp_id=105,
        attribute_name="lower_limit",
        type=t.Bool,
        access=foundation.ZCLAttributeAccess.Write,
    )
    .write_attr_button(
        attribute_name="lower_limit",
        attribute_value=t.Bool.true,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="set_lower_limit",
        translation_key="set_lower_limit",
        fallback_name="Set lower limit",
    )
    .write_attr_button(
        attribute_name="lower_limit",
        attribute_value=t.Bool.false,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="delete_lower_limit",
        translation_key="delete_lower_limit",
        fallback_name="Delete lower limit",
    )
    .skip_configuration()
    .add_to_registry()
)
