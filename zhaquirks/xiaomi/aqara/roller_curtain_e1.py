"""Aqara Roller Shade Driver E1 device."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final

from zigpy import types as t
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.zcl import AttributeReadEvent, Cluster, foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import AnalogOutput, MultistateOutput, OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks import CustomCluster
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    XiaomiAqaraE1Cluster,
    XiaomiPowerConfigurationPercent,
)


class AqaraRollerDriverCharging(t.enum8):
    """Aqara roller driver charging status attribute values."""

    Charging = 0x01
    NotCharging = 0x02


class AqaraRollerDriverSpeed(t.enum8):
    """Aqara roller driver speed attribute values."""

    Low = 0x00
    Medium = 0x01
    High = 0x02


class AqaraRollerControl(t.enum8):
    """Aqara roller control attribute values."""

    Close = 0x00
    Open = 0x01
    Stop = 0x02


class XiaomiAqaraRollerE1(XiaomiAqaraE1Cluster):
    """Aqara manufacturer cluster for the Roller Driver E1."""

    class AttributeDefs(BaseAttributeDefs):
        """Manufacturer specific attributes."""

        reverse_direction = ZCLAttributeDef(
            id=0x0400,
            type=t.Bool,
            access="rwp",
            is_manufacturer_specific=True,
        )

        positions_stored = ZCLAttributeDef(
            id=0x0402,
            type=t.Bool,
            access="rwp",
            is_manufacturer_specific=True,
        )

        store_position = ZCLAttributeDef(
            id=0x0407,
            type=t.uint8_t,
            access="rwp",
            is_manufacturer_specific=True,
        )

        speed = ZCLAttributeDef(
            id=0x0408,
            type=AqaraRollerDriverSpeed,
            zcl_type=DataTypeId.uint8,
            access="rwp",
            is_manufacturer_specific=True,
        )

        charging = ZCLAttributeDef(
            id=0x0409,
            type=AqaraRollerDriverCharging,
            zcl_type=DataTypeId.uint8,
            access="rp",
            is_manufacturer_specific=True,
        )

        aqara_attributes = ZCLAttributeDef(
            id=0x00F7,
            type=t.LVBytes,
            is_manufacturer_specific=True,
        )


class AnalogOutputRollerE1(CustomCluster, AnalogOutput):
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

    def _handle_attribute_read(self, event: AttributeReadEvent) -> None:
        """Handle attribute read event."""
        if event.attribute_id == self.AttributeDefs.present_value.id:
            self.endpoint.window_covering.update_attribute(
                WindowCovering.AttributeDefs.current_position_lift_percentage.id,
                t.uint8_t(100 - event.value),
            )


class WindowCoveringRollerE1(CustomCluster, WindowCovering):
    """Window covering cluster for handling motor commands."""

    _CONSTANT_ATTRIBUTES = {
        WindowCovering.AttributeDefs.window_covering_type.id: WindowCovering.WindowCoveringType.Rollershade,
    }

    # This is used to redirect 'current_position_lift_percentage' reads to AnalogOutput 'present_value'
    _REDIRECT_ATTRIBUTES: dict[
        ZCLAttributeDef, tuple[ZCLAttributeDef, type[Cluster], Callable]
    ] = {
        WindowCovering.AttributeDefs.current_position_lift_percentage: (
            AnalogOutput.AttributeDefs.present_value,
            AnalogOutput,
            lambda x: t.uint8_t(100 - x),
        ),
    }

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args: Any,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ) -> Any:
        """Overwrite the commands to make it work for both firmware 1425 and 1427.

        Write to AnalogOutput current_value for go go_to_lift_percentage.
        Write to MultistateOutput current_value for up_open/down_close/stop.

        The current_position_lift_percentage is read prior to returning the command response
        to ensure that ZHA has the correct position during changes in direction/stopping.
        """
        if command_id == WindowCovering.ServerCommandDefs.up_open.id:
            (res,) = await self.endpoint.multistate_output.write_attributes(
                {
                    MultistateOutput.AttributeDefs.present_value.name: AqaraRollerControl.Open
                }
            )
            await self.read_attributes(
                [self.AttributeDefs.current_position_lift_percentage.id]
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)

        if command_id == WindowCovering.ServerCommandDefs.down_close.id:
            (res,) = await self.endpoint.multistate_output.write_attributes(
                {
                    MultistateOutput.AttributeDefs.present_value.name: AqaraRollerControl.Close
                }
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
            (res,) = await self.endpoint.multistate_output.write_attributes(
                {
                    MultistateOutput.AttributeDefs.present_value.name: AqaraRollerControl.Stop
                }
            )
            await self.read_attributes(
                [self.AttributeDefs.current_position_lift_percentage.id]
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)

        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND)

    async def read_attributes(
        self,
        attributes: list[int | str | foundation.ZCLAttributeDef],
        **kwargs,
    ) -> Any:
        """Redirect attribute reads to another cluster."""
        success = {}
        failure = {}

        # Attribute reads reply with the attribute format as provided during the read
        attr_defs = {self.find_attribute(attr): attr for attr in attributes}

        for redirected_attr_def, (
            target_attr,
            target_cluster,
            format_func,
        ) in self._REDIRECT_ATTRIBUTES.items():
            if redirected_attr_def not in attr_defs:
                continue

            # Skip this attribute and read it from the other cluster
            other_cluster = getattr(self.endpoint, target_cluster.ep_attribute)
            other_success, other_failure = await other_cluster.read_attributes(
                [target_attr], **kwargs
            )

            # Remove it from the remaining attributes
            attr_key = attr_defs.pop(redirected_attr_def)
            attributes.remove(attr_key)

            if target_attr in other_success:
                success[attr_key] = format_func(other_success[target_attr])

            if target_attr in other_failure:
                failure[attr_key] = other_failure[target_attr]

        # Read the remaining ones directly
        other_success, other_failure = await super().read_attributes(
            attributes, **kwargs
        )
        success.update(other_success)
        failure.update(other_failure)

        return success, failure


class MultistateOutputRollerE1(CustomCluster, MultistateOutput):
    """MultistateOutput cluster used for writing commands (up_open, down_close, stop).

    This requires a change to the present_value attribute type because the device responds
    with an error when using the standard t.Single type.
    """

    class AttributeDefs(MultistateOutput.AttributeDefs):
        """Aqara attribute definition overrides."""

        present_value: Final = ZCLAttributeDef(
            id=0x0055,
            type=t.Single,
            zcl_type=DataTypeId.uint16,
            access="r*w",
            mandatory=True,
        )


(
    QuirkBuilder(LUMI, "lumi.curtain.acn002")
    # temporarily commented out due to potentially breaking existing blueprints
    #    .friendly_name(
    #        manufacturer="Aqara", model="Roller Shade Driver E1"
    #    )
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=AnalogOutput.cluster_id)
    .prevent_default_entity_creation(
        endpoint_id=1, cluster_id=MultistateOutput.cluster_id
    )
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=OnOff.cluster_id)
    .replaces(AnalogOutputRollerE1, endpoint_id=1)
    .replaces(BasicCluster, endpoint_id=1)
    .replaces(MultistateOutputRollerE1, endpoint_id=1)
    .replaces(XiaomiPowerConfigurationPercent, endpoint_id=1)
    .replaces(WindowCoveringRollerE1, endpoint_id=1)
    .replaces(XiaomiAqaraRollerE1, endpoint_id=1)
    .enum(
        XiaomiAqaraRollerE1.AttributeDefs.speed.name,
        AqaraRollerDriverSpeed,
        XiaomiAqaraRollerE1.cluster_id,
        translation_key="speed",
        fallback_name="Speed",
    )
    .binary_sensor(
        XiaomiAqaraRollerE1.AttributeDefs.charging.name,
        XiaomiAqaraRollerE1.cluster_id,
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        fallback_name="Charging",
        attribute_converter=lambda x: x == AqaraRollerDriverCharging.Charging,
    )
    .binary_sensor(
        XiaomiAqaraRollerE1.AttributeDefs.positions_stored.name,
        XiaomiAqaraRollerE1.cluster_id,
        translation_key="calibrated",
        fallback_name="Calibrated",
    )
    .add_to_registry()
)
