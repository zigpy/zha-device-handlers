"""Quirk for Aqara Smart Wall Switch E1 (no neutral, single rocker) QBKG38LM."""

from zigpy import types
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.xiaomi import LUMI, XiaomiAqaraE1Cluster


class ModeSwitch(types.enum16):
    """Enum for switch mode."""

    Quick = 0x01
    Anti_Flicker = 0x04


class OperationMode(types.enum8):
    """Enum for switch operation mode."""

    Decoupled = 0x00
    Relay = 0x01


class OppleCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer-specific cluster for the E1 wall switch."""

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        mode_switch = ZCLAttributeDef(
            id=0x0004, type=types.uint16_t, access="rw", manufacturer_code=0x115F
        )
        flip_indicator_light = ZCLAttributeDef(
            id=0x00F0, type=types.uint8_t, access="rw", manufacturer_code=0x115F
        )
        operation_mode = ZCLAttributeDef(
            id=0x0200, type=types.uint8_t, access="rw", manufacturer_code=0x115F
        )
        power_outage_memory = ZCLAttributeDef(
            id=0x0201, type=types.Bool, access="rw", manufacturer_code=0x115F
        )


(
    QuirkBuilder(LUMI, "lumi.switch.b1lc04")
    .replaces(OppleCluster)
    .switch(
        OppleCluster.AttributeDefs.flip_indicator_light.name,
        OppleCluster.cluster_id,
        translation_key="flip_indicator_light",
        fallback_name="Flip indicator light",
    )
    .switch(
        OppleCluster.AttributeDefs.power_outage_memory.name,
        OppleCluster.cluster_id,
        translation_key="power_outage_memory",
        fallback_name="Power outage memory",
    )
    .enum(
        OppleCluster.AttributeDefs.operation_mode.name,
        OperationMode,
        OppleCluster.cluster_id,
        translation_key="operation_mode",
        fallback_name="Operation mode",
    )
    .enum(
        OppleCluster.AttributeDefs.mode_switch.name,
        ModeSwitch,
        OppleCluster.cluster_id,
        translation_key="mode_switch",
        fallback_name="Mode switch",
    )
    .add_to_registry()
)
