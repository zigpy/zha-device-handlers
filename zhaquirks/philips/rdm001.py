"""Signify RDM001 device."""
import logging
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
    Ota,
    PowerConfiguration,
)

from zhaquirks.const import (
    ARGS,
    BUTTON,
    COMMAND,
    COMMAND_ID,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    QUADRUPLE_PRESS,
    QUINTUPLE_PRESS,
    SHORT_PRESS,
    SHORT_RELEASE,
    TRIPLE_PRESS,
    TURN_ON,
    ZHA_SEND_EVENT,
)
from zhaquirks.philips import PHILIPS, SIGNIFY

DEVICE_SPECIFIC_UNKNOWN = 64512
_LOGGER = logging.getLogger(__name__)


class PhilipsBasicCluster(CustomCluster, Basic):
    """Philips Basic cluster."""

    attributes = Basic.attributes.copy()
    attributes.update(
        {
            0x0031: ("philips", t.bitmap16, True),
            0x0034: ("mode", t.enum8, True),
        }
    )

    attr_config = {0x0031: 0x000B, 0x0034: 0x02}

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        await self.write_attributes(self.attr_config, manufacturer=0x100B)
        return result


class PhilipsRemoteCluster(CustomCluster):
    """Philips remote cluster."""

    cluster_id = 64512
    name = "PhilipsRemoteCluster"
    ep_attribute = "philips_remote_cluster"
    client_commands = {
        0x00: foundation.ZCLCommandDef(
            "notification",
            {
                "param1": t.uint8_t,
                "param2": t.uint24_t,
                "param3": t.uint8_t,
                "param4": t.uint8_t,
                "param5": t.uint8_t,
                "param6": t.uint8_t,
            },
            is_manufacturer_specific=True,
            is_reply=False,
        )
    }
    BUTTONS = {
        1: "left",
        2: "right",
    }
    PRESS_TYPES = {0: "press", 1: "hold", 2: "press_release", 3: "hold_release"}

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle the cluster command."""
        _LOGGER.debug(
            "PhilipsRemoteCluster - handle_cluster_request tsn: [%s] command id: %s - args: [%s]",
            hdr.tsn,
            hdr.command_id,
            args,
        )

        button = self.BUTTONS.get(args[0], args[0])
        press_type = self.PRESS_TYPES.get(args[2], args[2])

        event_args = {
            BUTTON: button,
            PRESS_TYPE: press_type,
            COMMAND_ID: hdr.command_id,
            ARGS: args,
        }

        action = f"{button}_{press_type}"
        self.listener_event(ZHA_SEND_EVENT, action, event_args)


class PhilipsROM001(CustomDevice):
    """Philips ROM001 device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=2080
        #  device_version=1
        #  input_clusters=[0, 1, 3, 64512]
        #  output_clusters=[3, 4, 6, 8, 25]>
        MODELS_INFO: [(PHILIPS, "RDM001"), (SIGNIFY, "RDM001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    DEVICE_SPECIFIC_UNKNOWN,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    PhilipsBasicCluster,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PhilipsRemoteCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {COMMAND: "left_press"},
        (LONG_PRESS, TURN_ON): {COMMAND: "left_hold"},
        (DOUBLE_PRESS, TURN_ON): {COMMAND: "left_double_press"},
        (TRIPLE_PRESS, TURN_ON): {COMMAND: "left_triple_press"},
        (QUADRUPLE_PRESS, TURN_ON): {COMMAND: "left_quadruple_press"},
        (QUINTUPLE_PRESS, TURN_ON): {COMMAND: "left_quintuple_press"},
        (SHORT_RELEASE, TURN_ON): {COMMAND: "left_short_release"},
        (LONG_RELEASE, TURN_ON): {COMMAND: "left_long_release"},
    }
