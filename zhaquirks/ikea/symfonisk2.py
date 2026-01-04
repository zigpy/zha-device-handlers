"""Device handler for IKEA of Sweden SYMFONISK sound remote gen2."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import PowerConfiguration

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    CLUSTER_ID,
    COMMAND,
    COMMAND_M_INITIAL_PRESS,
    COMMAND_M_LONG_PRESS,
    COMMAND_M_LONG_RELEASE,
    COMMAND_M_MULTI_PRESS_COMPLETE,
    COMMAND_M_SHORT_RELEASE,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_STEP,
    COMMAND_TOGGLE,
    DIM_DOWN,
    DIM_UP,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LEFT,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    PRESSED,
    RIGHT,
    SHORT_PRESS,
    TOGGLE,
)
from zhaquirks.ikea import (
    IKEA,
    WWAH_CLUSTER_ID,
    DoublingPowerConfig2AAACluster,
    PowerConfig2AAACluster,
    ShortcutV1Cluster,
    ShortcutV2Cluster,
)

COMMON_DEVICE_AUTOMATION_TRIGGERS = {
    (SHORT_PRESS, TOGGLE): {
        COMMAND: COMMAND_TOGGLE,
        CLUSTER_ID: 6,
        ENDPOINT_ID: 1,
    },
    (SHORT_PRESS, DIM_UP): {
        COMMAND: COMMAND_MOVE_ON_OFF,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        PARAMS: {"move_mode": 0},
    },
    (LONG_PRESS, DIM_UP): {
        COMMAND: COMMAND_MOVE,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        PARAMS: {"move_mode": 0},
    },
    (SHORT_PRESS, DIM_DOWN): {
        COMMAND: COMMAND_MOVE_ON_OFF,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        PARAMS: {"move_mode": 1},
    },
    (LONG_PRESS, DIM_DOWN): {
        COMMAND: COMMAND_MOVE,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        PARAMS: {"move_mode": 1},
    },
    (SHORT_PRESS, RIGHT): {
        COMMAND: COMMAND_STEP,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 0},
    },
    (SHORT_PRESS, LEFT): {
        COMMAND: COMMAND_STEP,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 1},
    },
}

(
    QuirkBuilder(IKEA, "SYMFONISK sound remote gen2")
    # TODO: differentiate between these devices without `filter`
    .filter(lambda dev: WWAH_CLUSTER_ID in dev.endpoints[1].in_clusters)
    .replaces(DoublingPowerConfig2AAACluster, endpoint_id=1)
    .replaces(ShortcutV1Cluster, cluster_type=ClusterType.Client, endpoint_id=1)
    .device_automation_triggers(
        {
            **COMMON_DEVICE_AUTOMATION_TRIGGERS,
            (SHORT_PRESS, BUTTON_1): {
                COMMAND: ShortcutV1Cluster.ServerCommandDefs.shortcut_v1_events.name,
                PARAMS: {"shortcut_button": 1, "shortcut_event": 1},
            },
            (DOUBLE_PRESS, BUTTON_1): {
                COMMAND: ShortcutV1Cluster.ServerCommandDefs.shortcut_v1_events.name,
                PARAMS: {"shortcut_button": 1, "shortcut_event": 2},
            },
            (LONG_PRESS, BUTTON_1): {
                COMMAND: ShortcutV1Cluster.ServerCommandDefs.shortcut_v1_events.name,
                PARAMS: {"shortcut_button": 1, "shortcut_event": 3},
            },
            (SHORT_PRESS, BUTTON_2): {
                COMMAND: ShortcutV1Cluster.ServerCommandDefs.shortcut_v1_events.name,
                PARAMS: {"shortcut_button": 2, "shortcut_event": 1},
            },
            (DOUBLE_PRESS, BUTTON_2): {
                COMMAND: ShortcutV1Cluster.ServerCommandDefs.shortcut_v1_events.name,
                PARAMS: {"shortcut_button": 2, "shortcut_event": 2},
            },
            (LONG_PRESS, BUTTON_2): {
                COMMAND: ShortcutV1Cluster.ServerCommandDefs.shortcut_v1_events.name,
                PARAMS: {"shortcut_button": 2, "shortcut_event": 3},
            },
        }
    )
    .add_to_registry()
)

(
    QuirkBuilder(IKEA, "SYMFONISK sound remote gen2")
    # TODO: differentiate between these devices without `filter`
    .filter(lambda dev: WWAH_CLUSTER_ID not in dev.endpoints[1].in_clusters)
    .replaces(
        PowerConfig2AAACluster, cluster_id=PowerConfiguration.cluster_id, endpoint_id=1
    )
    .replaces(ShortcutV2Cluster, cluster_type=ClusterType.Server, endpoint_id=2)
    .replaces(ShortcutV2Cluster, cluster_type=ClusterType.Client, endpoint_id=2)
    .replaces(ShortcutV2Cluster, cluster_type=ClusterType.Server, endpoint_id=3)
    .replaces(ShortcutV2Cluster, cluster_type=ClusterType.Client, endpoint_id=3)
    .device_automation_triggers(
        {
            **COMMON_DEVICE_AUTOMATION_TRIGGERS,
            (PRESSED, BUTTON_1): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_INITIAL_PRESS},
            (SHORT_PRESS, BUTTON_1): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_SHORT_RELEASE},
            (DOUBLE_PRESS, BUTTON_1): {
                ENDPOINT_ID: 2,
                COMMAND: COMMAND_M_MULTI_PRESS_COMPLETE,
            },
            (LONG_PRESS, BUTTON_1): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_LONG_PRESS},
            (LONG_RELEASE, BUTTON_1): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_LONG_RELEASE},
            (PRESSED, BUTTON_2): {ENDPOINT_ID: 3, COMMAND: COMMAND_M_INITIAL_PRESS},
            (SHORT_PRESS, BUTTON_2): {ENDPOINT_ID: 3, COMMAND: COMMAND_M_SHORT_RELEASE},
            (DOUBLE_PRESS, BUTTON_2): {
                ENDPOINT_ID: 3,
                COMMAND: COMMAND_M_MULTI_PRESS_COMPLETE,
            },
            (LONG_PRESS, BUTTON_2): {ENDPOINT_ID: 3, COMMAND: COMMAND_M_LONG_PRESS},
            (LONG_RELEASE, BUTTON_2): {ENDPOINT_ID: 3, COMMAND: COMMAND_M_LONG_RELEASE},
        }
    )
    .add_to_registry()
)
