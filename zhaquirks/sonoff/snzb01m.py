"""SONOFF SNZB-01M 4-button wireless switch quirk."""

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import CustomCluster, CustomDevice
from zhaquirks.const import (
    COMMAND,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    TRIPLE_PRESS,
    ZHA_SEND_EVENT,
)

SONOFF_CLUSTER_ID_FC12 = 0xFC12


class SonoffButtonCluster(CustomCluster):
    """Sonoff button cluster for handling button events."""

    cluster_id = SONOFF_CLUSTER_ID_FC12
    ep_attribute = "sonoff_button_cluster"

    manufacturer_id_override = foundation.ZCLHeader.NO_MANUFACTURER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for the Sonoff button cluster."""
        key_action_event = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,  # 用标准uint8类型
            is_manufacturer_specific=True,
        )

    def _update_attribute(self, attrid, value):
        import logging

        _LOGGER = logging.getLogger(__name__)
        _LOGGER.warning(
            "SonoffButtonCluster收到属性上报:endpoint=%s, attrid=%s, value=%s",
            self.endpoint.endpoint_id,
            attrid,
            value,
        )
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.key_action_event.id:
            event = button_event_from_report(self.endpoint.endpoint_id, value)
            if event:
                try:
                    self.listener_event(ZHA_SEND_EVENT, event["event"], event)
                    _LOGGER.warning("派发zha_event成功: %s", event)
                except Exception as e:
                    _LOGGER.error("派发zha_event失败: %s", e)
            else:
                _LOGGER.warning(
                    "无法解析的按钮事件: endpoint=%s, value=%s",
                    self.endpoint.endpoint_id,
                    value,
                )
        else:
            _LOGGER.warning(
                "未知属性上报: attrid=%s, value=%s, endpoint=%s",
                attrid,
                value,
                self.endpoint.endpoint_id,
            )


# 直接用整数做key
ACTION_MAP = {
    1: SHORT_PRESS,  # 0x01
    2: DOUBLE_PRESS,  # 0x02
    3: LONG_PRESS,  # 0x03
    4: TRIPLE_PRESS,  # 0x04
}


def button_event_from_report(endpoint_id, value):
    """Convert button report value to event dictionary."""
    action = ACTION_MAP.get(value)
    if action:
        return {
            "endpoint_id": endpoint_id,
            "event": action,
            "button": f"button{endpoint_id}",
        }
    return None


class SNZB01M(CustomDevice):
    """SONOFF SNZB-01M 4-button wireless switch device."""

    signature = {
        MODELS_INFO: [("SONOFF", "SNZB-01M")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    0x0001,  # Power Configuration
                    0x0003,  # Identify
                    0x0020,  # Poll Control
                    0xFC12,  # Sonoff FC12
                ],
                OUTPUT_CLUSTERS: [
                    0x0003,  # Identify
                    0x0004,  # Groups
                    0x0005,  # Scenes
                    0x0006,  # On/Off
                    0x0008,  # Level Control
                    0x0019,  # OTA
                    0x1000,  # Touchlink Commissioning
                ],
            },
            2: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    0xFC12,  # Sonoff FC12
                ],
                OUTPUT_CLUSTERS: [
                    0x0008,  # Level Control
                ],
            },
            3: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    0xFC12,  # Sonoff FC12
                ],
                OUTPUT_CLUSTERS: [
                    0x0008,  # Level Control
                ],
            },
            4: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    0xFC12,  # Sonoff FC12
                ],
                OUTPUT_CLUSTERS: [
                    0x0008,  # Level Control
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    0x0001,  # Power Configuration
                    0x0003,  # Identify
                    0x0020,  # Poll Control
                    SonoffButtonCluster,  # 自定义 cluster
                ],
                OUTPUT_CLUSTERS: [
                    0x0003,  # Identify
                    0x0004,  # Groups
                    0x0005,  # Scenes
                    0x0006,  # On/Off
                    0x0008,  # Level Control
                    0x0019,  # OTA
                    0x1000,  # Touchlink Commissioning
                ],
            },
            2: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    SonoffButtonCluster,
                ],
                OUTPUT_CLUSTERS: [
                    0x0008,  # Level Control
                ],
            },
            3: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    SonoffButtonCluster,
                ],
                OUTPUT_CLUSTERS: [
                    0x0008,  # Level Control
                ],
            },
            4: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0001,
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    SonoffButtonCluster,
                ],
                OUTPUT_CLUSTERS: [
                    0x0008,  # Level Control
                ],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, f"button{ep}"): {COMMAND: SHORT_PRESS, "endpoint_id": ep}
        for ep in range(1, 5)
    }
    device_automation_triggers.update(
        {
            (DOUBLE_PRESS, f"button{ep}"): {COMMAND: DOUBLE_PRESS, "endpoint_id": ep}
            for ep in range(1, 5)
        }
    )
    device_automation_triggers.update(
        {
            (LONG_PRESS, f"button{ep}"): {COMMAND: LONG_PRESS, "endpoint_id": ep}
            for ep in range(1, 5)
        }
    )
    device_automation_triggers.update(
        {
            (TRIPLE_PRESS, f"button{ep}"): {COMMAND: TRIPLE_PRESS, "endpoint_id": ep}
            for ep in range(1, 5)
        }
    )
