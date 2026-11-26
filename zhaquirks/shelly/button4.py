"""Shelly BLU RC Button 4 ZB (SBBT-104CUS) four button remote.

The remote sends plain Zigbee commands from its client clusters (Shelly API docs,
BLU RC Button 4 ZB):

* Toggle mode: a single click on button k sends OnOff toggle from endpoint k.
* On/Off mode (default): buttons 1 and 2 send OnOff on and off from endpoint 1,
  buttons 3 and 4 send them from endpoint 2.
* Both modes: a double, triple or long click on button k sends Scenes recall from
  endpoint k, with the gesture as the scene ID.

The remote resolves its multi-clicks itself, so its single click is a concluded
single press. Double and triple long clicks (scenes 12 and 13) and the Level Control
steps sent while a button is held in On/Off mode have no standard button event type
and are not exposed.
"""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff, Scenes

from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    CLUSTER_ID,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_RECALL,
    COMMAND_TOGGLE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    PARAMS,
    SHORT_PRESS,
    TRIPLE_PRESS,
)

BUTTONS = {1: BUTTON_1, 2: BUTTON_2, 3: BUTTON_3, 4: BUTTON_4}

# Scenes recall scene ID of each gesture
SCENE_DOUBLE_CLICK = 1
SCENE_TRIPLE_CLICK = 2
SCENE_LONG_CLICK = 11


def _scene_recall(endpoint_id: int, scene_id: int) -> dict:
    """Return the `zha_event` data of a Scenes recall from an endpoint."""
    return {
        ENDPOINT_ID: endpoint_id,
        CLUSTER_ID: Scenes.cluster_id,
        COMMAND: COMMAND_RECALL,
        PARAMS: {"scene_id": scene_id},
    }


def _on_off_mode_press(button: int) -> dict:
    """Return the `zha_event` data of a single click in On/Off mode."""
    return {
        ENDPOINT_ID: 1 if button <= 2 else 2,
        CLUSTER_ID: OnOff.cluster_id,
        COMMAND: COMMAND_ON if button % 2 else COMMAND_OFF,
    }


TRIGGERS = {}
for _button, _subtype in BUTTONS.items():
    TRIGGERS[(SHORT_PRESS, _subtype)] = {
        ENDPOINT_ID: _button,
        CLUSTER_ID: OnOff.cluster_id,
        COMMAND: COMMAND_TOGGLE,
    }
    TRIGGERS[(DOUBLE_PRESS, _subtype)] = _scene_recall(_button, SCENE_DOUBLE_CLICK)
    TRIGGERS[(TRIPLE_PRESS, _subtype)] = _scene_recall(_button, SCENE_TRIPLE_CLICK)
    TRIGGERS[(LONG_PRESS, _subtype)] = _scene_recall(_button, SCENE_LONG_CLICK)


builder = (
    QuirkBuilder("Shelly", "BLU RC Button 4 ZB")
    .friendly_name(manufacturer="Shelly", model="BLU RC Button 4 ZB")
    .device_automation_triggers(TRIGGERS)
)

for _button, _subtype in BUTTONS.items():
    builder = builder.button_event(
        events=[
            # Toggle mode
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS,
                trigger=(SHORT_PRESS, _subtype),
            ),
            # On/Off mode
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS,
                event_data=_on_off_mode_press(_button),
            ),
            ButtonEvent(
                event_type=ButtonEventType.MULTI_PRESS,
                trigger=(DOUBLE_PRESS, _subtype),
                press_count=2,
            ),
            ButtonEvent(
                event_type=ButtonEventType.MULTI_PRESS,
                trigger=(TRIPLE_PRESS, _subtype),
                press_count=3,
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, _subtype),
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=_button,
        unique_id_suffix=f"button_{_button}",
        translation_key="button_numbered",
        translation_placeholders={"number": str(_button)},
        fallback_name=f"Button {_button}",
    )

builder.add_to_registry()
