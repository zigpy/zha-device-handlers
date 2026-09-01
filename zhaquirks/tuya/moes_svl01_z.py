"""MOES SVL01-Z - DP refresh after initialization/re-interview."""

import asyncio

from zha.application import EntityType
from zha.application.platforms.binary_sensor.device_class import BinarySensorDeviceClass
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster

# =========================================================
# TUYA MCU
# =========================================================

TUYA_QUERY_DATA = 0x03


# =========================================================
# ENUMS
# =========================================================


class PowerOnBehavior(t.enum8):
    """Power-on behavior."""

    off = 0x00
    on = 0x01
    restore = 0x02


class AutoOnMode(t.enum8):
    """Auto-on mode."""

    off = 0x00
    all = 0x01
    ch1 = 0x02
    ch2 = 0x03
    ch3 = 0x04
    ch1_and_ch2 = 0x05
    ch2_and_ch3 = 0x06
    ch1_and_ch3 = 0x07


class AutoOffMode(t.enum8):
    """Auto-off mode."""

    off = 0x00
    all = 0x01
    ch1 = 0x02
    ch2 = 0x03
    ch3 = 0x04
    ch1_and_ch2 = 0x05
    ch2_and_ch3 = 0x06
    ch1_and_ch3 = 0x07


# =========================================================
# TUYA MCU CLUSTER
# =========================================================


class PresenceSwitchCluster(TuyaMCUCluster):
    """MOES SVL01-Z Tuya MCU cluster."""

    def __init__(self, endpoint, is_server=True):
        """Initialize the cluster and schedule a delayed DP refresh."""
        super().__init__(endpoint, is_server=is_server)

        # Request the current DP values after a short delay.
        # The delay gives the Tuya MCU time to complete initialization
        # before the refresh is sent.
        self.endpoint.device.create_task(
            self._delayed_query_data(),
            name="moes_tuya_query_data",
        )

    async def _delayed_query_data(self):
        """Request the current DP values from the Tuya MCU."""
        await asyncio.sleep(2)

        try:
            await self.command(TUYA_QUERY_DATA)

            self.debug("MOES SVL01-Z: Tuya query_data (0x03) sent successfully")

        except Exception:
            self.debug(
                "MOES SVL01-Z: query_data (0x03) failed",
                exc_info=True,
            )

    class AttributeDefs(TuyaMCUCluster.AttributeDefs):
        """MOES-specific DP attributes."""

        # DP101 - Presence
        presence = ZCLAttributeDef(
            id=0x0065,
            type=t.Bool,
            access="rp",
            is_manufacturer_specific=True,
        )

        # DP102 - Sensitivity
        sensitivity = ZCLAttributeDef(
            id=0x0066,
            type=t.uint8_t,
            access="rw",
            is_manufacturer_specific=True,
        )

        # DP103 - Trigger Hold
        trigger_hold = ZCLAttributeDef(
            id=0x0067,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )

        # DP14 - Power-on behavior
        power_outage_memory = ZCLAttributeDef(
            id=0x000E,
            type=PowerOnBehavior,
            access="rw",
            is_manufacturer_specific=True,
        )

        # DP16 - Backlight
        backlight = ZCLAttributeDef(
            id=0x0010,
            type=t.Bool,
            access="rw",
            is_manufacturer_specific=True,
        )

        # DP104 - Auto On
        auto_on = ZCLAttributeDef(
            id=0x0068,
            type=AutoOnMode,
            access="rw",
            is_manufacturer_specific=True,
        )

        # DP105 - Auto Off
        auto_off = ZCLAttributeDef(
            id=0x0069,
            type=AutoOffMode,
            access="rw",
            is_manufacturer_specific=True,
        )

    # =====================================================
    # DP → ATTRIBUTE
    # =====================================================

    dp_to_attribute = {
        101: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "presence",
            converter=bool,
        ),
        102: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "sensitivity",
        ),
        103: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "trigger_hold",
        ),
        14: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "power_outage_memory",
            converter=PowerOnBehavior,
        ),
        16: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "backlight",
            converter=bool,
        ),
        104: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "auto_on",
            converter=AutoOnMode,
        ),
        105: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "auto_off",
            converter=AutoOffMode,
        ),
    }

    # =====================================================
    # DP HANDLERS
    # =====================================================

    data_point_handlers = {
        14: "_dp_2_attr_update",
        16: "_dp_2_attr_update",
        101: "_dp_2_attr_update",
        102: "_dp_2_attr_update",
        103: "_dp_2_attr_update",
        104: "_dp_2_attr_update",
        105: "_dp_2_attr_update",
    }


# =========================================================
# QUIRK
# =========================================================


(
    QuirkBuilder("_TZE200_llvwkkde", "TS0601")
    .replaces(PresenceSwitchCluster)
    .skip_configuration()
    # =====================================================
    # PRESENCE
    # =====================================================
    .binary_sensor(
        PresenceSwitchCluster.AttributeDefs.presence.name,
        PresenceSwitchCluster.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        entity_type=EntityType.STANDARD,
        fallback_name="Presence",
        translation_key="presence",
    )
    # =====================================================
    # SENSITIVITY
    # =====================================================
    .number(
        PresenceSwitchCluster.AttributeDefs.sensitivity.name,
        PresenceSwitchCluster.cluster_id,
        min_value=0,
        max_value=19,
        step=1,
        entity_type=EntityType.CONFIG,
        fallback_name="Sensitivity",
        translation_key="sensitivity",
    )
    # =====================================================
    # TRIGGER HOLD
    # =====================================================
    .number(
        PresenceSwitchCluster.AttributeDefs.trigger_hold.name,
        PresenceSwitchCluster.cluster_id,
        min_value=5,
        max_value=28800,
        step=1,
        entity_type=EntityType.CONFIG,
        fallback_name="Trigger Hold",
        translation_key="trigger_hold",
    )
    # =====================================================
    # POWER-ON BEHAVIOUR
    # =====================================================
    .enum(
        PresenceSwitchCluster.AttributeDefs.power_outage_memory.name,
        PowerOnBehavior,
        PresenceSwitchCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        fallback_name="Power-on Behaviour",
        translation_key="power_on_behavior",
    )
    # =====================================================
    # BACKLIGHT
    # =====================================================
    .switch(
        PresenceSwitchCluster.AttributeDefs.backlight.name,
        PresenceSwitchCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        fallback_name="Backlight",
        translation_key="backlight",
    )
    # =====================================================
    # AUTO ON
    # =====================================================
    .enum(
        PresenceSwitchCluster.AttributeDefs.auto_on.name,
        AutoOnMode,
        PresenceSwitchCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        fallback_name="Auto On",
        translation_key="auto_on",
    )
    # =====================================================
    # AUTO OFF
    # =====================================================
    .enum(
        PresenceSwitchCluster.AttributeDefs.auto_off.name,
        AutoOffMode,
        PresenceSwitchCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        fallback_name="Auto Off",
        translation_key="auto_off",
    )
    .add_to_registry()
)
