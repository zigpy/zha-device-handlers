"""zigfred device handler."""

import logging
from typing import Any, Optional, Union

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseCommandDefs

from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    COMMAND,
    DOUBLE_PRESS,
    LONG_PRESS,
    LONG_RELEASE,
    PRESS_TYPE,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)

_LOGGER = logging.getLogger(__name__)

# Siglis zigfred specific clusters
SIGLIS_MANUFACTURER_CODE = 0x129C
ZIGFRED_CLUSTER_ID = 0xFC42
ZIGFRED_CLUSTER_BUTTONS_ATTRIBUTE_ID = 0x0008
ZIGFRED_CLUSTER_COMMAND_BUTTON_EVENT = 0x02


# Siglis zigfred cluster implementation
class ZigfredCluster(CustomCluster):
    """Siglis manufacturer specific cluster for zigfred."""

    name = "Siglis Manufacturer Specific"
    cluster_id = ZIGFRED_CLUSTER_ID
    buttons_attribute_id = ZIGFRED_CLUSTER_BUTTONS_ATTRIBUTE_ID

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        button_event = foundation.ZCLCommandDef(
            id=ZIGFRED_CLUSTER_COMMAND_BUTTON_EVENT,
            schema={"param1": t.uint32_t},
            is_manufacturer_specific=True,
        )

    def _process_button_event(self, value: t.uint32_t):
        button_lookup = {
            0: BUTTON_1,
            1: BUTTON_2,
            2: BUTTON_3,
            3: BUTTON_4,
        }

        press_type_lookup = {
            0: LONG_RELEASE,
            1: SHORT_PRESS,
            2: DOUBLE_PRESS,
            3: LONG_PRESS,
        }

        button = value & 0xFF
        press_type = (value >> 8) & 0xFF

        button = button_lookup[button]
        press_type = press_type_lookup[press_type]

        action = f"{button}_{press_type}"

        event_args = {
            BUTTON: button,
            PRESS_TYPE: press_type,
        }

        _LOGGER.info("Got button press on zigfred cluster: %s", action)

        if button and press_type:
            self.listener_event(ZHA_SEND_EVENT, action, event_args)

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ) -> None:
        """Handle cluster specific commands."""
        if hdr.command_id == ZIGFRED_CLUSTER_COMMAND_BUTTON_EVENT:
            self._process_button_event(args[0])


(
    QuirkBuilder("Siglis", "zigfred uno")
    .replaces(ZigfredCluster, endpoint_id=5)
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{SHORT_PRESS}"},
            (SHORT_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{SHORT_PRESS}"},
            (SHORT_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{SHORT_PRESS}"},
            (SHORT_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_{SHORT_PRESS}"},
            (DOUBLE_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{DOUBLE_PRESS}"},
            (DOUBLE_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{DOUBLE_PRESS}"},
            (DOUBLE_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{DOUBLE_PRESS}"},
            (DOUBLE_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_{DOUBLE_PRESS}"},
            (LONG_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{LONG_PRESS}"},
            (LONG_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{LONG_PRESS}"},
            (LONG_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{LONG_PRESS}"},
            (LONG_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_{LONG_PRESS}"},
            (LONG_RELEASE, BUTTON_1): {COMMAND: f"{BUTTON_1}_{LONG_RELEASE}"},
            (LONG_RELEASE, BUTTON_2): {COMMAND: f"{BUTTON_2}_{LONG_RELEASE}"},
            (LONG_RELEASE, BUTTON_3): {COMMAND: f"{BUTTON_3}_{LONG_RELEASE}"},
            (LONG_RELEASE, BUTTON_4): {COMMAND: f"{BUTTON_4}_{LONG_RELEASE}"},
        }
    )
    .add_to_registry()
)


(
    QuirkBuilder("Siglis", "zigfred plus")
    .replaces(ZigfredCluster, endpoint_id=5)
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{SHORT_PRESS}"},
            (SHORT_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{SHORT_PRESS}"},
            (SHORT_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{SHORT_PRESS}"},
            (SHORT_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_{SHORT_PRESS}"},
            (DOUBLE_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{DOUBLE_PRESS}"},
            (DOUBLE_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{DOUBLE_PRESS}"},
            (DOUBLE_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{DOUBLE_PRESS}"},
            (DOUBLE_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_{DOUBLE_PRESS}"},
            (LONG_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_{LONG_PRESS}"},
            (LONG_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_{LONG_PRESS}"},
            (LONG_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_{LONG_PRESS}"},
            (LONG_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_{LONG_PRESS}"},
            (LONG_RELEASE, BUTTON_1): {COMMAND: f"{BUTTON_1}_{LONG_RELEASE}"},
            (LONG_RELEASE, BUTTON_2): {COMMAND: f"{BUTTON_2}_{LONG_RELEASE}"},
            (LONG_RELEASE, BUTTON_3): {COMMAND: f"{BUTTON_3}_{LONG_RELEASE}"},
            (LONG_RELEASE, BUTTON_4): {COMMAND: f"{BUTTON_4}_{LONG_RELEASE}"},
        }
    )
    .add_to_registry()
)
