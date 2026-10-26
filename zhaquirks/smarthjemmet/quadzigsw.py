"""Device handler for smarthjemmet.dk QUAD-ZIG-SW."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import MultistateInput

from zhaquirks import PowerConfigurationCluster
from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.clusters import CustomCluster
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

SMARTHJEMMET = "smarthjemmet.dk"

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

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if (
            attrid == MultistateInput.AttributeDefs.present_value.id
            and (action := ACTION_TYPE.get(value)) is not None
        ):
            event_args = {VALUE: value}
            self.listener_event(ZHA_SEND_EVENT, action, event_args)


quad_zig_sw_quirk = (
    QuirkBuilder(SMARTHJEMMET, "QUAD-ZIG-SW")
    .applies_to(SMARTHJEMMET, "MULTI-ZIG-SW")
    .skip_configuration()
    .replaces(CR2032PowerConfigurationCluster)
    .removes(MultistateInput.cluster_id, cluster_type=ClusterType.Client, endpoint_id=2)
    .removes(MultistateInput.cluster_id, cluster_type=ClusterType.Client, endpoint_id=3)
    .removes(MultistateInput.cluster_id, cluster_type=ClusterType.Client, endpoint_id=4)
    .removes(MultistateInput.cluster_id, cluster_type=ClusterType.Client, endpoint_id=5)
    .adds(CustomMultistateInputCluster, endpoint_id=2)
    .adds(CustomMultistateInputCluster, endpoint_id=3)
    .adds(CustomMultistateInputCluster, endpoint_id=4)
    .adds(CustomMultistateInputCluster, endpoint_id=5)
    .device_automation_triggers(
        {
            (press_type, f"button_{i}"): {
                COMMAND: command,
                ENDPOINT_ID: i + 1,
            }
            for i in range(1, 5)
            for press_type, command in {
                (SHORT_PRESS, COMMAND_SINGLE),
                (DOUBLE_PRESS, COMMAND_DOUBLE),
                (TRIPLE_PRESS, COMMAND_TRIPLE),
                (LONG_PRESS, COMMAND_HOLD),
                (LONG_RELEASE, COMMAND_RELEASE),
            }
        }
    )
)

# The multi-click mode resolves the press count, so the single press is a resolved
# one. The release is classified by the hold, as it is not known whether the switch
# also sends it after a short press.
for i in range(1, 5):
    quad_zig_sw_quirk.button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS,
                trigger=(SHORT_PRESS, f"button_{i}"),
            ),
            ButtonEvent(
                event_type=ButtonEventType.MULTI_PRESS,
                trigger=(DOUBLE_PRESS, f"button_{i}"),
                press_count=2,
            ),
            ButtonEvent(
                event_type=ButtonEventType.MULTI_PRESS,
                trigger=(TRIPLE_PRESS, f"button_{i}"),
                press_count=3,
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, f"button_{i}"),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, f"button_{i}"),
                while_held=True,
            ),
        ],
        cluster_id=MultistateInput.cluster_id,
        cluster_type=ClusterType.Server,
        endpoint_id=i + 1,
        unique_id_suffix=f"button_{i}",
        translation_key="numbered_button",
        translation_placeholders={"button_number": str(i)},
        fallback_name=f"Button {i}",
    )

quad_zig_sw_quirk.add_to_registry()
