"""Namron 8-button wireless remote (4512772 white / 4512773 black)."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff, Ota, PowerConfiguration

from zhaquirks.builder import QuirkBuilder
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
    BUTTON_7,
    BUTTON_8,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP_ON_OFF,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    SHORT_PRESS,
)

# (endpoint_id, "on"-side button, "off"-side button) - 4 rocker channels,
# each its own endpoint with a standard OnOff + LevelControl pair.
# Endpoint 1 is physically the rightmost channel, endpoint 4 the leftmost.
CHANNELS = (
    (4, BUTTON_1, BUTTON_2),
    (3, BUTTON_3, BUTTON_4),
    (2, BUTTON_5, BUTTON_6),
    (1, BUTTON_7, BUTTON_8),
)

_TRIGGERS = {}
for endpoint_id, on_button, off_button in CHANNELS:
    _TRIGGERS.update(
        {
            (SHORT_PRESS, on_button): {
                COMMAND: COMMAND_ON,
                ENDPOINT_ID: endpoint_id,
                CLUSTER_ID: OnOff.cluster_id,
            },
            (SHORT_PRESS, off_button): {
                COMMAND: COMMAND_OFF,
                ENDPOINT_ID: endpoint_id,
                CLUSTER_ID: OnOff.cluster_id,
            },
            (LONG_PRESS, on_button): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                ENDPOINT_ID: endpoint_id,
                CLUSTER_ID: LevelControl.cluster_id,
                PARAMS: {"move_mode": LevelControl.MoveMode.Up},
            },
            (LONG_PRESS, off_button): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                ENDPOINT_ID: endpoint_id,
                CLUSTER_ID: LevelControl.cluster_id,
                PARAMS: {"move_mode": LevelControl.MoveMode.Down},
            },
            # Stop carries no direction, so only one release trigger per
            # channel is possible here, not one per button.
            (LONG_RELEASE, on_button): {
                COMMAND: COMMAND_STOP_ON_OFF,
                ENDPOINT_ID: endpoint_id,
                CLUSTER_ID: LevelControl.cluster_id,
            },
        }
    )


_builder = (
    QuirkBuilder("NAMRON AS", "4512772")
    .applies_to("NAMRON AS", "4512773")
    .device_automation_triggers(_TRIGGERS)
)

# Endpoints 2-4 mirror endpoint 1's battery/firmware exactly (same one
# physical battery and firmware image), so only keep the entities on 1.
for endpoint_id in (2, 3, 4):
    _builder.prevent_default_entity_creation(
        endpoint_id=endpoint_id, cluster_id=PowerConfiguration.cluster_id
    )
    _builder.prevent_default_entity_creation(
        endpoint_id=endpoint_id,
        cluster_id=Ota.cluster_id,
        cluster_type=ClusterType.Client,
    )

_builder.add_to_registry()
