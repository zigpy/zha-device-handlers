"""Smart button."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff

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
    .add_to_registry()
)
