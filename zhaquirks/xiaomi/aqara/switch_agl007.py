"""Quirk for Aqara Dimmer Switch H2 US (lumi.switch.agl007).

Three buttons on separate endpoints: 1 = paddle, 2 = brightness up,
3 = brightness down. Endpoint 1 pairs as a bare on/off switch without this
quirk, so brightness, the button events and per-button decoupling are all
unavailable.

Attribute ids are taken from zigbee-herdsman-converters' `lumi.switch.agl007`
definition and lib/lumi.ts. Press types are `PRESS_TYPES` in
zhaquirks.xiaomi.aqara.opple_remote ({0: hold, 1: single, 2: double,
3: triple, 255: release}), which agrees with Z2M's `lumiAction` lookup for this
model.

Buttons report as `zha_event` with `command` set to "<endpoint>_<press type>",
e.g. "2_single", whatever the operation mode is: decoupling stops the relay,
not the report. Decoupling endpoint 1 (the paddle) disables the up and down
buttons entirely, which is why only endpoints 2 and 3 are meant to be
decoupled in practice.

Tested on hardware, firmware sw 1.0.6.0, 2026-08-23.
"""

from zigpy import types
from zigpy.profiles import zha
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.xiaomi import XiaomiAqaraE1Cluster
from zhaquirks.xiaomi.aqara.opple_remote import MultistateInputCluster

LUMI_MFG_CODE = 0x115F


class OperationMode(types.enum8):
    """Whether a button drives the load or only reports the press."""

    Decoupled = 0x00
    Relay = 0x01


class ModeSwitch(types.enum16):
    """Quick mode responds faster; anti-flicker fixes blinking dimmed LEDs."""

    Quick = 0x01
    Anti_Flicker = 0x04


class Phase(types.enum8):
    """Dimming phase: trailing edge suits most LED loads."""

    Leading = 0x00
    Trailing = 0x01


class PowerOnState(types.enum8):
    """What the load does when mains power comes back."""

    On = 0x00
    Previous = 0x01
    Off = 0x02
    Inverted = 0x03


class MultiClick(types.enum8):
    """Multi-click costs response time: the device waits for a second press."""

    Single = 0x01
    Multi = 0x02


class DimmerH2USCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer-specific cluster, as this dimmer implements it."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # 0x0009 = 0 -> the buttons send zigbee COMMANDS (for binding),
        #          1 -> they send EVENTS, which is what Home Assistant wants.
        # Written on bind below; without it the buttons stay silent.
        mode = ZCLAttributeDef(
            id=0x0009, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        mode_switch = ZCLAttributeDef(
            id=0x0004, type=types.uint16_t, access="rw", is_manufacturer_specific=True
        )
        flip_indicator_light = ZCLAttributeDef(
            id=0x00F0, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        operation_mode = ZCLAttributeDef(
            id=0x0200, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        led_indicator = ZCLAttributeDef(
            id=0x0203, type=types.Bool, access="rw", is_manufacturer_specific=True
        )
        multi_click = ZCLAttributeDef(
            id=0x0286, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        phase = ZCLAttributeDef(
            id=0x030A, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        min_brightness = ZCLAttributeDef(
            id=0x0515, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        max_brightness = ZCLAttributeDef(
            id=0x0516, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        power_on_behavior = ZCLAttributeDef(
            id=0x0517, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )

    async def bind(self):
        """Bind, then put the device into event mode so the buttons report."""
        result = await super().bind()
        await self.write_attributes({"mode": 1}, manufacturer=LUMI_MFG_CODE)
        return result


(
    QuirkBuilder("Aqara", "lumi.switch.agl007")
    # Endpoint 1 pairs as a bare ON_OFF_SWITCH without this, i.e. no brightness.
    .replaces_endpoint(1, device_type=zha.DeviceType.DIMMABLE_LIGHT)
    # The event-emitting MultistateInput, one per button.
    .replaces(MultistateInputCluster, endpoint_id=1)
    .replaces(MultistateInputCluster, endpoint_id=2)
    .replaces(MultistateInputCluster, endpoint_id=3)
    .adds(DimmerH2USCluster, endpoint_id=1)
    .adds(DimmerH2USCluster, endpoint_id=2)
    .adds(DimmerH2USCluster, endpoint_id=3)
    # One operation mode per button. The paddle's is exposed for completeness,
    # but decoupling it disables the up and down buttons entirely.
    .enum(
        DimmerH2USCluster.AttributeDefs.operation_mode.name,
        OperationMode,
        DimmerH2USCluster.cluster_id,
        endpoint_id=1,
        unique_id_suffix="operation_mode_paddle",
        translation_key="operation_mode_paddle",
        fallback_name="Operation mode (paddle)",
    )
    .enum(
        DimmerH2USCluster.AttributeDefs.operation_mode.name,
        OperationMode,
        DimmerH2USCluster.cluster_id,
        endpoint_id=2,
        unique_id_suffix="operation_mode_up",
        translation_key="operation_mode_up",
        fallback_name="Operation mode (up button)",
    )
    .enum(
        DimmerH2USCluster.AttributeDefs.operation_mode.name,
        OperationMode,
        DimmerH2USCluster.cluster_id,
        endpoint_id=3,
        unique_id_suffix="operation_mode_down",
        translation_key="operation_mode_down",
        fallback_name="Operation mode (down button)",
    )
    .enum(
        DimmerH2USCluster.AttributeDefs.mode_switch.name,
        ModeSwitch,
        DimmerH2USCluster.cluster_id,
        translation_key="mode_switch",
        fallback_name="Mode switch",
    )
    .enum(
        DimmerH2USCluster.AttributeDefs.phase.name,
        Phase,
        DimmerH2USCluster.cluster_id,
        translation_key="phase",
        fallback_name="Phase",
    )
    .enum(
        DimmerH2USCluster.AttributeDefs.power_on_behavior.name,
        PowerOnState,
        DimmerH2USCluster.cluster_id,
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .number(
        DimmerH2USCluster.AttributeDefs.min_brightness.name,
        DimmerH2USCluster.cluster_id,
        min_value=0,
        max_value=99,
        step=1,
        translation_key="min_brightness",
        fallback_name="Minimum brightness",
    )
    .number(
        DimmerH2USCluster.AttributeDefs.max_brightness.name,
        DimmerH2USCluster.cluster_id,
        min_value=1,
        max_value=100,
        step=1,
        translation_key="max_brightness",
        fallback_name="Maximum brightness",
    )
    .switch(
        DimmerH2USCluster.AttributeDefs.led_indicator.name,
        DimmerH2USCluster.cluster_id,
        translation_key="led_indicator",
        fallback_name="LED indicator",
    )
    .switch(
        DimmerH2USCluster.AttributeDefs.flip_indicator_light.name,
        DimmerH2USCluster.cluster_id,
        translation_key="flip_indicator_light",
        fallback_name="Flip indicator light",
    )
    .device_automation_triggers(
        {
            ("single", "paddle"): {"command": "1_single"},
            ("double", "paddle"): {"command": "1_double"},
            ("hold", "paddle"): {"command": "1_hold"},
            ("release", "paddle"): {"command": "1_release"},
            ("single", "up"): {"command": "2_single"},
            ("double", "up"): {"command": "2_double"},
            ("hold", "up"): {"command": "2_hold"},
            ("release", "up"): {"command": "2_release"},
            ("single", "down"): {"command": "3_single"},
            ("double", "down"): {"command": "3_double"},
            ("hold", "down"): {"command": "3_hold"},
            ("release", "down"): {"command": "3_release"},
        }
    )
    .add_to_registry()
)
