"""Aqara H1 Smart Knob (wireless)."""

import math
from typing import Any

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef
from zigpy.zdo.types import LogicalType, NodeDescriptor

from zhaquirks.const import (
    ALT_DOUBLE_PRESS,
    ALT_LONG_PRESS,
    ARGS,
    BUTTON,
    COMMAND,
    COMMAND_OFF,
    COMMAND_TOGGLE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    ROTATED,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import LUMI, XiaomiAqaraE1Cluster, XiaomiPowerConfiguration
from zhaquirks.xiaomi.aqara.opple_remote import (
    COMMAND_1_DOUBLE,
    COMMAND_1_HOLD,
    COMMAND_1_RELEASE,
    COMMAND_1_SINGLE,
    MultistateInputCluster,
)
from zhaquirks.xiaomi.aqara.remote_h1 import (
    AqaraRemoteManuSpecificCluster,
    AqaraSwitchOperationMode,
)

# Device advertises MainsPowered in its MAC capability flags; clear it so ZHA
# treats it as a battery-powered end device.
H1_KNOB_NODE_DESCRIPTOR = NodeDescriptor(
    logical_type=LogicalType.EndDevice,
    complex_descriptor_available=0,
    user_descriptor_available=0,
    reserved=0,
    aps_flags=0,
    frequency_band=NodeDescriptor.FrequencyBand.Freq2400MHz,
    mac_capability_flags=NodeDescriptor.MACCapabilityFlags.AllocateAddress,
    manufacturer_code=0x115F,
    maximum_buffer_size=127,
    maximum_incoming_transfer_size=100,
    server_mask=11264,
    maximum_outgoing_transfer_size=100,
    descriptor_capability_field=NodeDescriptor.DescriptorCapability.NONE,
)

ROTATION_DIRECTION = "rotation_direction"

ROTATE_LEFT = "rotate_left"
ROTATE_RIGHT = "rotate_right"
HOLD_ROTATE_LEFT = "hold_rotate_left"
HOLD_ROTATE_RIGHT = "hold_rotate_right"

STOP_ROTATION = "stop_rotation"
HOLD_STOP_ROTATION = "hold_stop_rotation"


class KnobAction(t.enum8):
    """Aqara H1 knob rotation action."""

    off = 0x00
    start_rotation = 0x01
    rotation = 0x02
    stop_rotation = 0x03
    hold_start_rotation = 0x81
    hold_rotation = 0x82
    hold_stop_rotation = 0x83


class KnobManuSpecificCluster(XiaomiAqaraE1Cluster):
    """Aqara H1 knob cluster that reports rotation events on endpoints 71/72."""

    class AttributeDefs(BaseAttributeDefs):
        """Rotation reporting attributes."""

        rotation_time_delta = ZCLAttributeDef(
            id=0x022C,
            type=t.uint16_t,
            zcl_type=DataTypeId.uint16,
            access="rp",
            manufacturer_code=0x115F,
        )
        rotation_angle = ZCLAttributeDef(
            id=0x022E,
            type=t.Single,
            zcl_type=DataTypeId.single,
            access="rp",
            manufacturer_code=0x115F,
        )
        rotation_angle_delta = ZCLAttributeDef(
            id=0x0230,
            type=t.Single,
            zcl_type=DataTypeId.single,
            access="rp",
            manufacturer_code=0x115F,
        )
        rotation_time = ZCLAttributeDef(
            id=0x0231,
            type=t.uint32_t,
            zcl_type=DataTypeId.uint32,
            access="rp",
            manufacturer_code=0x115F,
        )
        rotation_percent_delta = ZCLAttributeDef(
            id=0x0232,
            type=t.Single,
            zcl_type=DataTypeId.single,
            access="rp",
            manufacturer_code=0x115F,
        )
        rotation_percent = ZCLAttributeDef(
            id=0x0233,
            type=t.Single,
            zcl_type=DataTypeId.single,
            access="rp",
            manufacturer_code=0x115F,
        )
        action = ZCLAttributeDef(
            id=0x023A,
            type=KnobAction,
            zcl_type=DataTypeId.uint8,
            access="rp",
            manufacturer_code=0x115F,
        )

    def handle_cluster_general_request(
        self,
        header: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing=None,
    ) -> None:
        """Emit a zha_event carrying rotation details when an action is reported."""
        super().handle_cluster_general_request(
            header, args, dst_addressing=dst_addressing
        )

        if header.command_id != foundation.GeneralCommand.Report_Attributes:
            return

        event_args: dict[str, Any] = {}
        for attr in args.attribute_reports:
            if attr.attrid not in self.attributes:
                continue
            attr_def = self.attributes[attr.attrid]
            try:
                value = attr_def.type(attr.value.value)
            except ValueError:
                value = attr.value.value
            event_args[attr_def.name] = value

        action = event_args.get(KnobManuSpecificCluster.AttributeDefs.action.name)
        if action is None:
            return

        # Delta attributes are stale on stop events; drop them and derive direction
        # from the (signed) final rotation_angle instead.
        if action in (KnobAction.stop_rotation, KnobAction.hold_stop_rotation):
            for key in list(event_args):
                if key.endswith("_delta"):
                    del event_args[key]
            event_args[ROTATION_DIRECTION] = math.copysign(
                1,
                event_args.get(
                    KnobManuSpecificCluster.AttributeDefs.rotation_angle.name, 0
                ),
            )

        self.listener_event(ZHA_SEND_EVENT, action.name, event_args)


(
    QuirkBuilder(LUMI, "lumi.remote.rkba01")
    .friendly_name(manufacturer="Aqara", model="Smart Knob H1 (wireless)")
    .node_descriptor(H1_KNOB_NODE_DESCRIPTOR)
    .replaces(XiaomiPowerConfiguration)
    .adds(MultistateInputCluster)
    .replaces(AqaraRemoteManuSpecificCluster)
    .adds_endpoint(71, device_type=zha.DeviceType.DIMMER_SWITCH)
    .adds(KnobManuSpecificCluster, endpoint_id=71)
    .adds_endpoint(72, device_type=zha.DeviceType.SHADE_CONTROLLER)
    .adds(KnobManuSpecificCluster, endpoint_id=72)
    .enum(
        attribute_name=AqaraRemoteManuSpecificCluster.AttributeDefs.operation_mode.name,
        enum_class=AqaraSwitchOperationMode,
        cluster_id=AqaraRemoteManuSpecificCluster.cluster_id,
        translation_key="operation_mode",
        fallback_name="Operation mode",
    )
    .device_automation_triggers(
        {
            # operation_mode == event
            (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_1_SINGLE},
            (DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_1_DOUBLE},
            (LONG_PRESS, BUTTON): {COMMAND: COMMAND_1_HOLD},
            (LONG_RELEASE, BUTTON): {COMMAND: COMMAND_1_RELEASE},
            (ROTATED, BUTTON): {COMMAND: STOP_ROTATION},
            (ROTATE_LEFT, BUTTON): {
                COMMAND: STOP_ROTATION,
                ARGS: {ROTATION_DIRECTION: -1},
            },
            (ROTATE_RIGHT, BUTTON): {
                COMMAND: STOP_ROTATION,
                ARGS: {ROTATION_DIRECTION: 1},
            },
            (HOLD_ROTATE_LEFT, BUTTON): {
                COMMAND: HOLD_STOP_ROTATION,
                ARGS: {ROTATION_DIRECTION: -1},
            },
            (HOLD_ROTATE_RIGHT, BUTTON): {
                COMMAND: HOLD_STOP_ROTATION,
                ARGS: {ROTATION_DIRECTION: 1},
            },
            # operation_mode == command (single press does not emit an event)
            (ALT_DOUBLE_PRESS, BUTTON): {
                COMMAND: COMMAND_TOGGLE,
                ENDPOINT_ID: 1,
                ARGS: [],
            },
            (ALT_LONG_PRESS, BUTTON): {
                COMMAND: COMMAND_OFF,
                ENDPOINT_ID: 1,
                ARGS: [],
            },
        }
    )
    .add_to_registry()
)
