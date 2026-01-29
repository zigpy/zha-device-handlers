"""Device handler for IKEA of Sweden SOMRIG shortcut button."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import PowerConfiguration

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    COMMAND,
    COMMAND_M_INITIAL_PRESS,
    COMMAND_M_LONG_PRESS,
    COMMAND_M_LONG_RELEASE,
    COMMAND_M_MULTI_PRESS_COMPLETE,
    COMMAND_M_SHORT_RELEASE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    PRESSED,
    SHORT_PRESS,
)
from zhaquirks.ikea import IKEA, PowerConfig1AAACluster, ShortcutV2Cluster

(
    QuirkBuilder(IKEA, "SOMRIG shortcut button")
    .replaces(PowerConfig1AAACluster, PowerConfiguration.cluster_id, endpoint_id=1)
    .replaces(ShortcutV2Cluster, endpoint_id=1)
    .replaces(ShortcutV2Cluster, endpoint_id=1, cluster_type=ClusterType.Client)
    .replaces(ShortcutV2Cluster, endpoint_id=2)
    .replaces(ShortcutV2Cluster, endpoint_id=2, cluster_type=ClusterType.Client)
    .device_automation_triggers(
        {
            (PRESSED, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: COMMAND_M_INITIAL_PRESS},
            (SHORT_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: COMMAND_M_SHORT_RELEASE},
            (DOUBLE_PRESS, BUTTON_1): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_M_MULTI_PRESS_COMPLETE,
            },
            (LONG_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: COMMAND_M_LONG_PRESS},
            (LONG_RELEASE, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: COMMAND_M_LONG_RELEASE},
            (PRESSED, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_INITIAL_PRESS},
            (SHORT_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_SHORT_RELEASE},
            (DOUBLE_PRESS, BUTTON_2): {
                ENDPOINT_ID: 2,
                COMMAND: COMMAND_M_MULTI_PRESS_COMPLETE,
            },
            (LONG_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_LONG_PRESS},
            (LONG_RELEASE, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_LONG_RELEASE},
        }
    )
    .add_to_registry()
)
