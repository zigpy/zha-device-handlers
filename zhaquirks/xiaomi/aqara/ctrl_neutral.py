"""Aqara wall switches without neutral (single and double key)."""

from typing import Final

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import EventableCluster
from zhaquirks.builder import QuirkBuilder
from zhaquirks.const import (
    ARGS,
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    CLUSTER_ID,
    COMMAND,
    COMMAND_ATTRIBUTE_UPDATED,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    ENDPOINT_ID,
    VALUE,
)
from zhaquirks.xiaomi import LUMI, BasicCluster, OnOffCluster, XiaomiPowerConfiguration

ATTRIBUTE_ON_OFF = "on_off"


class BasicClusterDecoupled(BasicCluster):
    """Adds attributes for decoupled mode."""

    # Known Options for 'decoupled_mode_<button>':
    # * 254 (decoupled)
    # * 18 (relay controlled)
    class AttributeDefs(BasicCluster.AttributeDefs):
        """Attribute definitions."""

        decoupled_mode_left: Final = ZCLAttributeDef(
            id=0xFF22, type=t.uint8_t, is_manufacturer_specific=True
        )
        decoupled_mode_right: Final = ZCLAttributeDef(
            id=0xFF23, type=t.uint8_t, is_manufacturer_specific=True
        )


class WallSwitchOnOffCluster(EventableCluster, OnOff):
    """Button endpoint: `on_off` is the press type (0 hold, 1 release, 2 double)."""


def _button_triggers(button: str, endpoint_id: int) -> dict:
    """Return the hold, release and double press triggers of one key."""
    return {
        (command, button): {
            ENDPOINT_ID: endpoint_id,
            CLUSTER_ID: OnOff.cluster_id,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: ATTRIBUTE_ON_OFF, VALUE: value},
        }
        for command, value in (
            (COMMAND_HOLD, 0),
            (COMMAND_RELEASE, 1),
            (COMMAND_DOUBLE, 2),
        )
    }


def _ctrl_neutral(
    models: tuple[str, ...], relays: tuple[int, ...], buttons: tuple[int, ...]
) -> QuirkBuilder:
    """Build the common part of both switches.

    Both models report the same endpoints: relays on 2 and 3, button events on 4
    and 5, plus the unused 3/5 (single key), 6 and 8.
    """
    builder = QuirkBuilder(LUMI, models[0])
    for model in models[1:]:
        builder.applies_to(LUMI, model)

    builder.replaces(BasicClusterDecoupled).replaces(
        XiaomiPowerConfiguration
    ).skip_configuration()

    for endpoint_id in relays:
        builder.replaces_endpoint(
            endpoint_id, device_type=zha.DeviceType.ON_OFF_SWITCH
        ).replaces(OnOffCluster, endpoint_id=endpoint_id)

    for endpoint_id in buttons:
        builder.replaces(
            WallSwitchOnOffCluster, endpoint_id=endpoint_id
        ).prevent_default_entity_creation(
            endpoint_id=endpoint_id, cluster_id=OnOff.cluster_id
        )

    for endpoint_id in {3, 5, 6, 8} - set(relays) - set(buttons):
        builder.removes_endpoint(endpoint_id)

    return builder


(
    _ctrl_neutral(("lumi.ctrl_neutral1", "lumi.switch.b1lacn02"), (2,), (4,))
    .device_automation_triggers(_button_triggers(BUTTON, 4))
    .add_to_registry()
)

(
    _ctrl_neutral(("lumi.ctrl_neutral2", "lumi.switch.b2lacn02"), (2, 3), (4, 5))
    .device_automation_triggers(
        _button_triggers(BUTTON_1, 4) | _button_triggers(BUTTON_2, 5)
    )
    .add_to_registry()
)
