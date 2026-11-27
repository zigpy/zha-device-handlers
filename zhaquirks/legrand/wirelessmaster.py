"""Module for the Legrand / BTicino wireless master remote (Home / Away)."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import BinaryInput, PowerConfiguration, Scenes

from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    CLUSTER_ID,
    COMMAND,
    COMMAND_RECALL,
    ENDPOINT_ID,
    PARAMS,
    SHORT_PRESS,
    BatterySize,
)
from zhaquirks.legrand import LEGRAND, LegrandPowerConfigurationCluster

# Each button recalls scene 1 of its own group
HOME_GROUP_ID = 0xFFF7
AWAY_GROUP_ID = 0xFFF6


class MasterRemotePowerConfiguration(LegrandPowerConfigurationCluster):
    """Legrand voltage to percentage conversion, powered by one CR2032 coin cell."""

    _CONSTANT_ATTRIBUTES = {
        PowerConfiguration.AttributeDefs.battery_size.id: BatterySize.CR2032,
        PowerConfiguration.AttributeDefs.battery_quantity.id: 1,
    }


(
    QuirkBuilder(f" {LEGRAND}", " Master remote SW Home / Away")
    .replaces(MasterRemotePowerConfiguration)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=BinaryInput.cluster_id)
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {
                COMMAND: COMMAND_RECALL,
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {"group_id": HOME_GROUP_ID},
            },
            (SHORT_PRESS, BUTTON_2): {
                COMMAND: COMMAND_RECALL,
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {"group_id": AWAY_GROUP_ID},
            },
        }
    )
    # The remote sends a single recall as soon as a button goes down, and nothing
    # while it is held or when it is released
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_START,
                trigger=(SHORT_PRESS, BUTTON_1),
            ),
        ],
        cluster_id=Scenes.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button_1",
        translation_key="button_numbered",
        translation_placeholders={"number": "1"},
        fallback_name="Button 1",
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_START,
                trigger=(SHORT_PRESS, BUTTON_2),
            ),
        ],
        cluster_id=Scenes.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button_2",
        translation_key="button_numbered",
        translation_placeholders={"number": "2"},
        fallback_name="Button 2",
    )
    .add_to_registry()
)
