"""Module for the Legrand / BTicino wireless master remote (Home / Away)."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import BinaryInput, PowerConfiguration, Scenes

from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_RECALL,
    ENDPOINT_ID,
    PARAMS,
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


def _button(number: int, group_id: int) -> dict:
    """Return the button event entity of the button recalling the given group."""
    return {
        # The remote sends a single recall as soon as a button goes down, and
        # nothing while it is held or when it is released
        "events": [
            ButtonEvent(
                event_type=ButtonEventType.PRESS_START,
                event_data={
                    COMMAND: COMMAND_RECALL,
                    CLUSTER_ID: Scenes.cluster_id,
                    ENDPOINT_ID: 1,
                    PARAMS: {"group_id": group_id},
                },
            ),
        ],
        "cluster_id": Scenes.cluster_id,
        "cluster_type": ClusterType.Client,
        "unique_id_suffix": f"button_{number}",
        "translation_key": "button_numbered",
        "translation_placeholders": {"number": str(number)},
        "fallback_name": f"Button {number}",
    }


(
    QuirkBuilder(f" {LEGRAND}", " Master remote SW Home / Away")
    .replaces(MasterRemotePowerConfiguration)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=BinaryInput.cluster_id)
    .button_event(**_button(1, HOME_GROUP_ID))
    .button_event(**_button(2, AWAY_GROUP_ID))
    .add_to_registry()
)
