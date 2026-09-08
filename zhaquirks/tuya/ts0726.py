"""Device handler for Tuya/BSEED TS0726 scene switches."""

from __future__ import annotations

from typing import Any, Final

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import EventableCluster
from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    COMMAND,
    ENDPOINT_ID,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)
from zhaquirks.tuya import (
    TUYA_CLUSTER_E001_ID,
    TuyaZBE000Cluster,
    TuyaZBExternalSwitchTypeCluster,
)


class BseedBacklightMode(t.enum8):
    """Backlight mode enum."""

    Off = 0x00
    On = 0x01


class BseedIndicatorMode(t.enum8):
    """Indicator mode enum."""

    None_ = 0x00
    Relay = 0x01
    Position = 0x02


class BseedPowerOnBehavior(t.enum8):
    """Power-on behavior enum."""

    Off = 0x00
    On = 0x01
    Previous = 0x02


class BseedSwitchMode(t.enum8):
    """Switch mode enum."""

    Switch = 0x00
    Scene = 0x01


class BseedTS0726OnOffCluster(OnOff, EventableCluster):
    """OnOff cluster with BSEED TS0726 attributes and scene actions."""

    class AttributeDefs(OnOff.AttributeDefs):
        """Attribute definitions."""

        backlight_mode: Final = ZCLAttributeDef(id=0x5000, type=BseedBacklightMode)
        indicator_mode: Final = ZCLAttributeDef(id=0x8001, type=BseedIndicatorMode)

    class ServerCommandDefs(OnOff.ServerCommandDefs):
        """Server command definitions."""

        tuya_action_2: Final = foundation.ZCLCommandDef(
            id=0xFC,
            schema={"value": t.uint8_t},
            is_manufacturer_specific=True,
        )
        tuya_action: Final = foundation.ZCLCommandDef(
            id=0xFD,
            schema={"value": t.uint8_t},
            is_manufacturer_specific=True,
        )

    def __init__(self, *args, **kwargs):
        """Init."""

        self._last_action_tsn = None
        super().__init__(*args, **kwargs)

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing=None,
    ) -> None:
        """Emit ZHA events for TS0726 scene button presses."""

        if hdr.command_id not in (
            self.ServerCommandDefs.tuya_action_2.id,
            self.ServerCommandDefs.tuya_action.id,
        ):
            return super().handle_cluster_request(
                hdr, args, dst_addressing=dst_addressing
            )

        if not hdr.frame_control.disable_default_response:
            self.send_default_rsp(hdr, status=foundation.Status.SUCCESS)

        if self._last_action_tsn == hdr.tsn:
            return

        self._last_action_tsn = hdr.tsn
        self.listener_event(
            ZHA_SEND_EVENT,
            f"scene_{self.endpoint.endpoint_id}",
            [],
        )


class BseedTS0726OptionsCluster(CustomCluster):
    """Tuya cluster 0xE001 with TS0726 options."""

    name = "BSEED TS0726 options"
    cluster_id = TUYA_CLUSTER_E001_ID
    ep_attribute = "bseed_ts0726_options"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        power_on_behavior: Final = ZCLAttributeDef(id=0xD010, type=BseedPowerOnBehavior)
        switch_mode: Final = ZCLAttributeDef(id=0xD020, type=BseedSwitchMode)
        external_switch_type: Final = (
            TuyaZBExternalSwitchTypeCluster.AttributeDefs.external_switch_type
        )


(
    QuirkBuilder("_TZ3002_jn2x20tg", "TS0726")
    .friendly_name(model="EC-GL86ZPCS11", manufacturer="BSEED")
    .replaces(BseedTS0726OnOffCluster)
    .replaces(TuyaZBE000Cluster)
    .replaces(BseedTS0726OptionsCluster)
    .enum(
        BseedTS0726OnOffCluster.AttributeDefs.backlight_mode.name,
        BseedBacklightMode,
        BseedTS0726OnOffCluster.cluster_id,
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .enum(
        BseedTS0726OnOffCluster.AttributeDefs.indicator_mode.name,
        BseedIndicatorMode,
        BseedTS0726OnOffCluster.cluster_id,
        translation_key="indicator_mode",
        fallback_name="Indicator mode",
    )
    .enum(
        BseedTS0726OptionsCluster.AttributeDefs.power_on_behavior.name,
        BseedPowerOnBehavior,
        BseedTS0726OptionsCluster.cluster_id,
        translation_key="power_on_behavior",
        fallback_name="Power-on behavior",
    )
    .enum(
        BseedTS0726OptionsCluster.AttributeDefs.switch_mode.name,
        BseedSwitchMode,
        BseedTS0726OptionsCluster.cluster_id,
        translation_key="switch_mode",
        fallback_name="Switch mode",
    )
    .device_automation_triggers(
        {(SHORT_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: "scene_1"}}
    )
    .add_to_registry()
)

(
    QuirkBuilder("_TZ3002_zjuvw9zf", "TS0726")
    .friendly_name(model="EC-GL86ZPCS21", manufacturer="BSEED")
    .replaces(BseedTS0726OnOffCluster)
    .replaces(TuyaZBE000Cluster)
    .replaces(BseedTS0726OptionsCluster)
    .replaces(BseedTS0726OnOffCluster, endpoint_id=2)
    .replaces(BseedTS0726OptionsCluster, endpoint_id=2)
    .enum(
        BseedTS0726OnOffCluster.AttributeDefs.backlight_mode.name,
        BseedBacklightMode,
        BseedTS0726OnOffCluster.cluster_id,
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .enum(
        BseedTS0726OnOffCluster.AttributeDefs.indicator_mode.name,
        BseedIndicatorMode,
        BseedTS0726OnOffCluster.cluster_id,
        translation_key="indicator_mode",
        fallback_name="Indicator mode",
    )
    .enum(
        BseedTS0726OptionsCluster.AttributeDefs.power_on_behavior.name,
        BseedPowerOnBehavior,
        BseedTS0726OptionsCluster.cluster_id,
        endpoint_id=1,
        translation_key="power_on_behavior",
        fallback_name="Power-on behavior",
        unique_id_suffix="power_on_behavior_l1",
    )
    .enum(
        BseedTS0726OptionsCluster.AttributeDefs.power_on_behavior.name,
        BseedPowerOnBehavior,
        BseedTS0726OptionsCluster.cluster_id,
        endpoint_id=2,
        translation_key="power_on_behavior",
        fallback_name="Power-on behavior",
        unique_id_suffix="power_on_behavior_l2",
    )
    .enum(
        BseedTS0726OptionsCluster.AttributeDefs.switch_mode.name,
        BseedSwitchMode,
        BseedTS0726OptionsCluster.cluster_id,
        endpoint_id=1,
        translation_key="switch_mode",
        fallback_name="Switch mode",
        unique_id_suffix="switch_mode_l1",
    )
    .enum(
        BseedTS0726OptionsCluster.AttributeDefs.switch_mode.name,
        BseedSwitchMode,
        BseedTS0726OptionsCluster.cluster_id,
        endpoint_id=2,
        translation_key="switch_mode",
        fallback_name="Switch mode",
        unique_id_suffix="switch_mode_l2",
    )
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: "scene_1"},
            (SHORT_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: "scene_2"},
        }
    )
    .add_to_registry()
)
