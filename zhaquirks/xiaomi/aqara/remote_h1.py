"""Aqara H1-series wireless remote."""

from zigpy import types
from zigpy.quirks.v2 import ClusterType, QuirkBuilder
from zigpy.zcl.clusters.general import Identify, OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    ALT_DOUBLE_PRESS,
    ALT_SHORT_PRESS,
    ARGS,
    BUTTON,
    COMMAND,
    COMMAND_OFF,
    COMMAND_TOGGLE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LEFT,
    LONG_PRESS,
    RIGHT,
    SHORT_PRESS,
    TRIPLE_PRESS,
)
from zhaquirks.xiaomi import LUMI, XiaomiAqaraE1Cluster
from zhaquirks.xiaomi.aqara.opple_remote import (
    COMMAND_1_DOUBLE,
    COMMAND_1_HOLD,
    COMMAND_1_SINGLE,
    COMMAND_1_TRIPLE,
    COMMAND_2_DOUBLE,
    COMMAND_2_HOLD,
    COMMAND_2_SINGLE,
    COMMAND_2_TRIPLE,
    COMMAND_3_DOUBLE,
    COMMAND_3_HOLD,
    COMMAND_3_SINGLE,
    COMMAND_3_TRIPLE,
    MultistateInputCluster,
)

BOTH_BUTTONS = "both_buttons"


class AqaraSwitchClickMode(types.enum8):
    """Aqara switch click mode attribute values."""

    Single = 0x01  # Low latency (50ms) but only sends single click events.
    Multiple = 0x02  # (default) Slightly higher latency but supports single/double/triple click and long press.


class AqaraSwitchOperationMode(types.enum8):
    """Aqara switch operation mode attribute values."""

    Command = 0x00
    Event = 0x01


class AqaraRemoteManuSpecificCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer cluster for the presence sensor FP1E."""

    class AttributeDefs(BaseAttributeDefs):
        """Manufacturer specific attributes."""

        # To get/set these attributes, you might need to click the button 5 times quickly.

        operation_mode = ZCLAttributeDef(
            id=0x0009,
            type=AqaraSwitchOperationMode,
            zcl_type=DataTypeId.uint8,
            access="rw",
            is_manufacturer_specific=True,
        )

        click_mode = ZCLAttributeDef(
            id=0x0125,
            type=AqaraSwitchClickMode,
            zcl_type=DataTypeId.uint8,
            access="rw",
            is_manufacturer_specific=True,
        )


class PowerConfigurationClusterH1Remote(PowerConfigurationCluster):
    """Reports battery level."""

    # Aqara H1 wireless remote uses one CR2450 battery.
    # Values are copied from zigbee-herdsman-converters.
    MIN_VOLTS = 2.5
    MAX_VOLTS = 3.0


(
    QuirkBuilder(LUMI, "lumi.remote.b18ac1")
    # temporarily commented out due to potentially breaking existing blueprints
    # .friendly_name(
    #     manufacturer="Aqara", model="Wireless Remote Switch H1 (Single Rocker)"
    # )
    .replaces(AqaraRemoteManuSpecificCluster)
    .replaces(MultistateInputCluster)
    .replaces(PowerConfigurationClusterH1Remote)
    .enum(
        AqaraRemoteManuSpecificCluster.AttributeDefs.click_mode.name,
        AqaraSwitchClickMode,
        AqaraRemoteManuSpecificCluster.cluster_id,
        translation_key="click_mode",
        fallback_name="Click mode",
    )
    .enum(
        AqaraRemoteManuSpecificCluster.AttributeDefs.operation_mode.name,
        AqaraSwitchOperationMode,
        AqaraRemoteManuSpecificCluster.cluster_id,
        translation_key="operation_mode",
        fallback_name="Operation mode",
    )
    .device_automation_triggers(
        {
            # triggers when operation_mode == event
            # the button doesn't send an release event after hold
            (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_1_SINGLE},
            (DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_1_DOUBLE},
            (TRIPLE_PRESS, BUTTON): {COMMAND: COMMAND_1_TRIPLE},
            (LONG_PRESS, BUTTON): {COMMAND: COMMAND_1_HOLD},
            # triggers when operation_mode == command
            (ALT_SHORT_PRESS, BUTTON): {
                COMMAND: COMMAND_TOGGLE,
                ENDPOINT_ID: 1,
                ARGS: [],
            },
            (ALT_DOUBLE_PRESS, BUTTON): {
                COMMAND: COMMAND_OFF,
                ENDPOINT_ID: 1,
                ARGS: [],
            },
        }
    )
    .add_to_registry()
)


(
    QuirkBuilder(LUMI, "lumi.remote.b28ac1")
    # temporarily commented out due to potentially breaking existing blueprints
    # .friendly_name(
    #     manufacturer="Aqara", model="Wireless Remote Switch H1 (Double Rocker)"
    # )
    .replaces(AqaraRemoteManuSpecificCluster)
    .adds(Identify)
    .replaces(MultistateInputCluster)
    .replaces(MultistateInputCluster, endpoint_id=2)
    .replaces(MultistateInputCluster, endpoint_id=3)
    .adds(OnOff, cluster_type=ClusterType.Client)
    .adds(OnOff, endpoint_id=2, cluster_type=ClusterType.Client)
    .adds(OnOff, endpoint_id=3, cluster_type=ClusterType.Client)
    .replaces(PowerConfigurationClusterH1Remote)
    .enum(
        AqaraRemoteManuSpecificCluster.AttributeDefs.click_mode.name,
        AqaraSwitchClickMode,
        AqaraRemoteManuSpecificCluster.cluster_id,
        translation_key="click_mode",
        fallback_name="Click mode",
    )
    .enum(
        AqaraRemoteManuSpecificCluster.AttributeDefs.operation_mode.name,
        AqaraSwitchOperationMode,
        AqaraRemoteManuSpecificCluster.cluster_id,
        translation_key="operation_mode",
        fallback_name="Operation mode",
    )
    .device_automation_triggers(
        {
            # triggers when operation_mode == event
            # the button doesn't send a release event after hold
            (SHORT_PRESS, LEFT): {COMMAND: COMMAND_1_SINGLE},
            (DOUBLE_PRESS, LEFT): {COMMAND: COMMAND_1_DOUBLE},
            (TRIPLE_PRESS, LEFT): {COMMAND: COMMAND_1_TRIPLE},
            (LONG_PRESS, LEFT): {COMMAND: COMMAND_1_HOLD},
            (SHORT_PRESS, RIGHT): {COMMAND: COMMAND_2_SINGLE},
            (DOUBLE_PRESS, RIGHT): {COMMAND: COMMAND_2_DOUBLE},
            (TRIPLE_PRESS, RIGHT): {COMMAND: COMMAND_2_TRIPLE},
            (LONG_PRESS, RIGHT): {COMMAND: COMMAND_2_HOLD},
            (SHORT_PRESS, BOTH_BUTTONS): {COMMAND: COMMAND_3_SINGLE},
            (DOUBLE_PRESS, BOTH_BUTTONS): {COMMAND: COMMAND_3_DOUBLE},
            (TRIPLE_PRESS, BOTH_BUTTONS): {COMMAND: COMMAND_3_TRIPLE},
            (LONG_PRESS, BOTH_BUTTONS): {COMMAND: COMMAND_3_HOLD},
            # triggers when operation_mode == command
            # known issue: it seems impossible to know which button being pressed
            # when operation_mode == command
            (ALT_SHORT_PRESS, BUTTON): {
                COMMAND: COMMAND_TOGGLE,
                ENDPOINT_ID: 1,
                ARGS: [],
            },
        }
    )
    .add_to_registry()
)
