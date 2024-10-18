"""Device handler for smarthjemmet.dk QUAD-ZIG-SW."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import MultistateInput
import zigpy.zcl.foundation

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_SINGLE,
    COMMAND_TRIPLE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
    TRIPLE_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
)

MANUFACTURER = "smarthjemmet.dk"
MODEL_ID = "QUAD-ZIG-SW"

ACTION_TYPE = {
    0: COMMAND_RELEASE,
    1: COMMAND_SINGLE,
    2: COMMAND_DOUBLE,
    3: COMMAND_TRIPLE,
    4: COMMAND_HOLD,
}


class CR2032PowerConfigurationCluster(PowerConfigurationCluster):
    """CR2032 Power Configuration Cluster."""

    MIN_VOLTS = 2.2
    MAX_VOLTS = 3.0


class CustomMultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster."""

    async def bind(self):
        """Prevent bind."""
        return zigpy.zcl.foundation.Status.SUCCESS

    async def unbind(self):
        """Prevent unbind."""
        return zigpy.zcl.foundation.Status.SUCCESS

    async def _configure_reporting(self, *args, **kwargs):
        """Prevent remote configure reporting."""
        return (
            zigpy.zcl.foundation.ConfigureReportingResponse.deserialize(b"\x00")[0],
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == 0x0055:
            if action := ACTION_TYPE.get(value) is not None:
                event_args = {VALUE: value}
                self.listener_event(ZHA_SEND_EVENT, action, event_args)

            super()._update_attribute(0, action)


(
    QuirkBuilder(MANUFACTURER, MODEL_ID)
    .skip_configuration()
    .replaces(CR2032PowerConfigurationCluster)
    .replace_cluster_occurrences(CustomMultistateInputCluster)
    .device_automation_triggers(
        {
            (press_type, f"button_{i}"): {
                COMMAND: command,
                ENDPOINT_ID: i + 1,
            }
            for i in range(1, 6)
            for press_type, command in {
                (SHORT_PRESS, COMMAND_SINGLE),
                (DOUBLE_PRESS, COMMAND_DOUBLE),
                (TRIPLE_PRESS, COMMAND_TRIPLE),
                (LONG_PRESS, COMMAND_HOLD),
                (LONG_RELEASE, COMMAND_RELEASE),
            }
        }
    )
    .add_to_registry()
)
