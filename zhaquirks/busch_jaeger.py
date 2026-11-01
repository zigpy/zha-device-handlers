"""Quirks for Busch-Jaeger ZigBee Light Link wall transmitters.

Covers two 4-gang rocker controllers whose rows do not expose named actions to
ZHA out of the box:

* 6737    -> model "RM01", mains-powered 4-gang control element with a built-in
             dimmer load on endpoint 0x12.
* 6737/01 -> model "RB01", battery-powered wall transmitter, no load.

Each rocker row is its own ZLL controller endpoint (0x0a-0x0d) with OnOff and
LevelControl output clusters. Per rocker half a short tap sends OnOff on/off and
a hold sends LevelControl step/stop. This quirk maps those to
``device_automation_triggers`` so the rows show up as named actions in the
automation editor.

Note: like other pure ZLL controllers, a rocker only transmits once its output
clusters are bound to a target (e.g. the coordinator). That binding is a manual
step the quirk cannot perform; until a row is bound it stays silent.
"""

from zhaquirks.builder import QuirkBuilder
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP,
    COMMAND_STEP_ON_OFF,
    COMMAND_STOP,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
)

ONOFF_CLUSTER_ID = 0x0006
LEVEL_CLUSTER_ID = 0x0008

ROW_ENDPOINTS = {1: 0x0A, 2: 0x0B, 3: 0x0C, 4: 0x0D}


def _row_triggers(row: int, endpoint: int) -> dict:
    """Return the device automation triggers for a single rocker row."""
    return {
        (SHORT_PRESS, f"on_row_{row}"): {
            ENDPOINT_ID: endpoint,
            CLUSTER_ID: ONOFF_CLUSTER_ID,
            COMMAND: COMMAND_ON,
        },
        (SHORT_PRESS, f"off_row_{row}"): {
            ENDPOINT_ID: endpoint,
            CLUSTER_ID: ONOFF_CLUSTER_ID,
            COMMAND: COMMAND_OFF,
        },
        (LONG_PRESS, f"up_row_{row}"): {
            ENDPOINT_ID: endpoint,
            CLUSTER_ID: LEVEL_CLUSTER_ID,
            COMMAND: COMMAND_STEP_ON_OFF,
        },
        (LONG_PRESS, f"down_row_{row}"): {
            ENDPOINT_ID: endpoint,
            CLUSTER_ID: LEVEL_CLUSTER_ID,
            COMMAND: COMMAND_STEP,
        },
        (LONG_RELEASE, f"stop_row_{row}"): {
            ENDPOINT_ID: endpoint,
            CLUSTER_ID: LEVEL_CLUSTER_ID,
            COMMAND: COMMAND_STOP,
        },
    }


_TRIGGERS: dict = {}
for _row, _ep in ROW_ENDPOINTS.items():
    _TRIGGERS.update(_row_triggers(_row, _ep))


(
    QuirkBuilder("Busch-Jaeger", "RM01")
    .device_automation_triggers(_TRIGGERS)
    .add_to_registry()
)

(
    QuirkBuilder("Busch-Jaeger", "RB01")
    .device_automation_triggers(_TRIGGERS)
    .add_to_registry()
)
