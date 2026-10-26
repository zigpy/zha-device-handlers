"""Smart button."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import Basic, OnOff

from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.const import BUTTON, CLUSTER_ID, COMMAND, COMMAND_CLICK, ENDPOINT_ID

(
    QuirkBuilder("frient A/S", "SBTZB-110")
    .prevent_default_entity_creation(
        endpoint_id=32,
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
    )
    .device_automation_triggers(
        {
            (COMMAND_CLICK, BUTTON): {
                ENDPOINT_ID: 32,
                CLUSTER_ID: int(OnOff.cluster_id),
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
        }
    )
    # The button only reports a click, as a toggle command. The entity is attached
    # to the Basic cluster, as the OnOff client cluster entities are removed above.
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS,
                trigger=(COMMAND_CLICK, BUTTON),
            ),
        ],
        cluster_id=Basic.cluster_id,
        cluster_type=ClusterType.Server,
        endpoint_id=32,
        unique_id_suffix="button",
        translation_key="button",
        fallback_name="Button",
    )
    .add_to_registry()
)
