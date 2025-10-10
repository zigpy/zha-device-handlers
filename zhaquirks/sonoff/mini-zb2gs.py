"""Sonoff MINI-ZB2GS - Zigbee Switch."""

from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.typing import AddressingMode, EndpointType
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class SonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11
    manufacturer_id_override = foundation.ZCLHeader.NO_MANUFACTURER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""
        external_trigger_mode = ZCLAttributeDef(
            id=0x0016,
            type=t.uint8_t,
        )
        detach_relay = ZCLAttributeDef(
            id=0x0019,
            type=t.bitmap8,
        )
        # 添加turbo模式属性
        turbo_mode = ZCLAttributeDef(
            id=0x0012,
            type=t.int16s,
        )
        # 添加network_led属性
        network_led = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
        )

class SonoffExternalSwitchTriggerType(types.enum8):
    """extern switch trigger type."""
    Edge_trigger = 0x00
    Pulse_trigger = 0x01
    Normally_off_follow_trigger = 0x02
    Normally_on_follow_trigger = 0x82

class SonoffDetachRelayType(types.enum8):
    """detach relay type."""
    ALL_CH_DETACH_RELAY_CLOSE = 0x00
    JUST_CH1_ENABLE_DETACH_RELAY = 0x01
    JUST_CH2_ENABLE_DETACH_RELAY = 0x02
    CH1_AND_CH2_ENABLE_DETACH_RELAY = 0x03

# 定义turbo模式的枚举类型
class SonoffTurboModeType(types.enum16):
    """turbo mode type."""
    NORMAL_MODE = 0x0009  # 9
    TURBO_MODE = 0x0014   # 20

(
    QuirkBuilder("SONOFF", "MINI-ZB2GS")
    .replaces(SonoffCluster, endpoint_id = 1)
    .replaces(SonoffCluster, endpoint_id = 2)
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalSwitchTriggerType,
        SonoffCluster.cluster_id,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
        endpoint_id=1,
    )
    .enum(
        SonoffCluster.AttributeDefs.detach_relay.name,
        SonoffDetachRelayType,
        SonoffCluster.cluster_id,
        translation_key="detach_relay",
        fallback_name="Detach relay",
        endpoint_id=1,
    )
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalSwitchTriggerType,
        SonoffCluster.cluster_id,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
        endpoint_id=2,
    )
    # 添加turbo模式实体
    .enum(
        SonoffCluster.AttributeDefs.turbo_mode.name,
        SonoffTurboModeType,
        SonoffCluster.cluster_id,
        translation_key="turbo_mode",
        fallback_name="Turbo mode",
        endpoint_id=1,
    )
    # 添加network_led实体
    .switch(
        SonoffCluster.AttributeDefs.network_led.name,
        SonoffCluster.cluster_id,
        translation_key="network_led",
        fallback_name="Network LED",
        endpoint_id=1,
    )
    .add_to_registry()
)