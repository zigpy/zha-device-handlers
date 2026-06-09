"""Device handler for Aurora dimmer switch, battery powered."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color

from zhaquirks import EventableCluster, PowerConfigurationCluster
from zhaquirks.const import (
    ARGS,
    CLUSTER_ID,
    COMMAND,
    COMMAND_STEP,
    COMMAND_STEP_COLOR_TEMP,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    LEFT,
    PARAMS,
    RIGHT,
    SHORT_PRESS,
)

COLOR_UP = "color_up"
COLOR_DOWN = "color_down"
CURRENT_LEVEL = "current_level"


class WallSwitchOnOffCluster(EventableCluster, OnOff):
    """WallSwitchOnOffCluster: fire events corresponding to press type."""

    # prevent creation of junk entities
    ep_attribute = "not_on_off"

    # as the device is battery powered, whether or not it thinks it is
    # on or off is irrelevant
    def _update_attribute(self, attrid, value):
        return


class WallSwitchLevelControlCluster(EventableCluster, LevelControl):
    """WallSwitchLevelControlCluster: fire events corresponding to level changes."""

    # the value reported by the device is always 254, so we may as well
    # throw away this report
    def _update_attribute(self, attrid, value):
        if attrid == CURRENT_LEVEL:
            return
        else:
            super()._update_attribute(attrid, value)


class WallSwitchColorCluster(EventableCluster, Color):
    """WallSwitchColorCluster: fire events corresponding to color changes."""


(
    QuirkBuilder("Aurora", "2GBatteryDimmer50AU")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .replaces(WallSwitchOnOffCluster, endpoint_id=1)
    .replaces(WallSwitchLevelControlCluster, endpoint_id=1)
    .replaces(WallSwitchColorCluster, endpoint_id=1)
    .replaces(WallSwitchOnOffCluster, endpoint_id=2)
    .replaces(WallSwitchLevelControlCluster, endpoint_id=2)
    .replaces(WallSwitchColorCluster, endpoint_id=2)
    .device_automation_triggers(
        {
            (DIM_UP, RIGHT): {
                COMMAND: COMMAND_STEP,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 0},
            },
            (DIM_DOWN, RIGHT): {
                COMMAND: COMMAND_STEP,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 1},
            },
            (COLOR_UP, RIGHT): {
                COMMAND: COMMAND_STEP_COLOR_TEMP,
                CLUSTER_ID: 768,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 3},
            },
            (COLOR_DOWN, RIGHT): {
                COMMAND: COMMAND_STEP_COLOR_TEMP,
                CLUSTER_ID: 768,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 1},
            },
            (DIM_UP, LEFT): {
                COMMAND: COMMAND_STEP,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"step_mode": 0},
            },
            (DIM_DOWN, LEFT): {
                COMMAND: COMMAND_STEP,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"step_mode": 1},
            },
            (COLOR_UP, LEFT): {
                COMMAND: COMMAND_STEP_COLOR_TEMP,
                CLUSTER_ID: 768,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 3},
            },
            (COLOR_DOWN, LEFT): {
                COMMAND: COMMAND_STEP_COLOR_TEMP,
                CLUSTER_ID: 768,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 1},
            },
            (SHORT_PRESS, RIGHT): {
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
                ARGS: [],
            },
            (SHORT_PRESS, LEFT): {
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
                ARGS: [],
            },
        }
    )
    .add_to_registry()
)
