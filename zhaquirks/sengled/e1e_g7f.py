"""Sengled E1E-G7F device."""
from typing import Any, List, Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    PollControl,
    PowerConfiguration,
)

from zhaquirks import Bus
from zhaquirks.const import (
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PARAMS,
    PROFILE_ID,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
    ZHA_SEND_EVENT,
)


class SengledE1EG7FOnOffCluster(CustomCluster, OnOff):
    """Sengled E1E-G7F OnOff cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""

        super().__init__(*args, **kwargs)

        self.endpoint.device.on_off_bus.add_listener(self)


class SengledE1EG7FLevelControlCluster(CustomCluster, LevelControl):
    """Sengled E1E-G7F LevelControl cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""

        super().__init__(*args, **kwargs)

        self.endpoint.device.level_control_bus.add_listener(self)


class SengledE1EG7FManufacturerSpecificCluster(CustomCluster):
    """Sengled E1E-G7F manufacturer-specific cluster."""

    cluster_id = 0xFC10
    name = "Sengled Manufacturer Specific"
    ep_attribute = "sengled_manufacturer_specific"

    server_commands = {
        0x0000: foundation.ZCLCommandDef(
            name="command",
            schema={
                "param1": t.uint8_t,
                "param2": t.uint8_t,
                "param3": t.uint8_t,
                "param4": t.uint8_t,
            },
            is_reply=False,
            is_manufacturer_specific=True,
        )
    }

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle cluster request."""

        if args[0] == 1:
            self.endpoint.device.on_off_bus.listener_event(
                "listener_event", ZHA_SEND_EVENT, COMMAND_ON, []
            )
        elif args[0] == 2:
            if args[2] == 2:
                self.endpoint.device.level_control_bus.listener_event(
                    "listener_event", ZHA_SEND_EVENT, COMMAND_STEP, [0, 2, 0]
                )
            else:
                self.endpoint.device.level_control_bus.listener_event(
                    "listener_event", ZHA_SEND_EVENT, COMMAND_STEP, [0, 1, 0]
                )
        elif args[0] == 3:
            if args[2] == 2:
                self.endpoint.device.level_control_bus.listener_event(
                    "listener_event", ZHA_SEND_EVENT, COMMAND_STEP, [1, 2, 0]
                )
            else:
                self.endpoint.device.level_control_bus.listener_event(
                    "listener_event", ZHA_SEND_EVENT, COMMAND_STEP, [1, 1, 0]
                )
        elif args[0] == 4:
            self.endpoint.device.on_off_bus.listener_event(
                "listener_event", ZHA_SEND_EVENT, COMMAND_OFF, []
            )
        elif args[0] == 5:
            self.endpoint.device.on_off_bus.listener_event(
                "listener_event", ZHA_SEND_EVENT, "on_double", []
            )
        elif args[0] == 6:
            self.endpoint.device.on_off_bus.listener_event(
                "listener_event", ZHA_SEND_EVENT, "on_long", []
            )
        elif args[0] == 7:
            self.endpoint.device.on_off_bus.listener_event(
                "listener_event", ZHA_SEND_EVENT, "off_double", []
            )
        elif args[0] == 8:
            self.endpoint.device.on_off_bus.listener_event(
                "listener_event", ZHA_SEND_EVENT, "off_long", []
            )


class SengledE1EG7F(CustomDevice):
    """Sengled E1E-G7F device."""

    def __init__(self, *args, **kwargs):
        """Init."""

        self.on_off_bus = Bus()
        self.level_control_bus = Bus()

        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [("sengled", "E1E-G7F")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=260
            # device_version=0
            # input_clusters=[0, 1, 3, 32, 64529]
            # output_clusters=[3, 4, 6, 8, 64528]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    0xFC11,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    SengledE1EG7FManufacturerSpecificCluster.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    0xFC11,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    SengledE1EG7FOnOffCluster,
                    SengledE1EG7FLevelControlCluster,
                    SengledE1EG7FManufacturerSpecificCluster,
                ],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON},
        (LONG_PRESS, TURN_ON): {COMMAND: "on_long"},
        (DOUBLE_PRESS, TURN_ON): {COMMAND: "on_double"},
        (SHORT_PRESS, DIM_UP): {
            COMMAND: COMMAND_STEP,
            PARAMS: {"step_mode": 0},
        },
        (SHORT_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_STEP,
            PARAMS: {"step_mode": 1},
        },
        (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF},
        (LONG_PRESS, TURN_OFF): {COMMAND: "off_long"},
        (DOUBLE_PRESS, TURN_OFF): {COMMAND: "off_double"},
    }
