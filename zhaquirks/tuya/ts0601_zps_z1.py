"""ZHA custom quirk — Zemismart ZPS-Z1 24 GHz mmWave Presence Sensor."""

from typing import Final

import zigpy.types as t
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.zcl.foundation import ZCLAttributeDef
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster


# ── Enums ─────────────────────────────────────────────────────────────────────

class PresenceState(t.enum8):
    """ZPS-Z1 DP1 presence state."""
    absence      = 0x00
    presence     = 0x01
    sensor_close = 0x02


class AutoCalibrationState(t.enum8):
    """ZPS-Z1 DP103 auto-calibration state."""
    standby  = 0x00
    start    = 0x01
    learning = 0x02
    success  = 0x03
    fail     = 0x04
    cancel   = 0x05


class SensitivityPreset(t.enum8):
    """ZPS-Z1 DP112 sensitivity preset."""
    high   = 0x00
    medium = 0x01
    low    = 0x02
    custom = 0x03


# ── Custom Tuya MCU cluster ───────────────────────────────────────────────────

class ZpsZ1ManufCluster(TuyaMCUCluster):
    """ZPS-Z1 custom Tuya MCU cluster mapping all DPs to named attributes."""

    class AttributeDefs(TuyaMCUCluster.AttributeDefs):
        """ZPS-Z1 datapoint attribute definitions."""

        presence_state: Final = ZCLAttributeDef(
            id=0x0001,          # DP 1
            type=PresenceState,
            access="rp",
            is_manufacturer_specific=True,
        )
        detection_range: Final = ZCLAttributeDef(
            id=0x0002,          # DP 2
            type=t.uint32_t,
            access="rwp",
            is_manufacturer_specific=True,
        )
        illuminance: Final = ZCLAttributeDef(
            id=0x0065,          # DP 101 (0x65)
            type=t.uint32_t,
            access="rp",
            is_manufacturer_specific=True,
        )
        auto_calibration: Final = ZCLAttributeDef(
            id=0x0067,          # DP 103 (0x67)
            type=AutoCalibrationState,
            access="rwp",
            is_manufacturer_specific=True,
        )
        sensitivity_preset: Final = ZCLAttributeDef(
            id=0x0070,          # DP 112 (0x70)
            type=SensitivityPreset,
            access="rwp",
            is_manufacturer_specific=True,
        )
        presence_clear_cooldown: Final = ZCLAttributeDef(
            id=0x0077,          # DP 119 (0x77)
            type=t.uint32_t,
            access="rwp",
            is_manufacturer_specific=True,
        )
        led_indicator: Final = ZCLAttributeDef(
            id=0x007B,          # DP 123 (0x7B)
            type=t.Bool,
            access="rwp",
            is_manufacturer_specific=True,
        )

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            ep_attribute=TuyaMCUCluster.ep_attribute,
            attribute_name="presence_state",
            converter=PresenceState,
        ),
        2: DPToAttributeMapping(
            ep_attribute=TuyaMCUCluster.ep_attribute,
            attribute_name="detection_range",
        ),
        101: DPToAttributeMapping(
            ep_attribute=TuyaMCUCluster.ep_attribute,
            attribute_name="illuminance",
        ),
        103: DPToAttributeMapping(
            ep_attribute=TuyaMCUCluster.ep_attribute,
            attribute_name="auto_calibration",
            converter=AutoCalibrationState,
        ),
        112: DPToAttributeMapping(
            ep_attribute=TuyaMCUCluster.ep_attribute,
            attribute_name="sensitivity_preset",
            converter=SensitivityPreset,
        ),
        119: DPToAttributeMapping(
            ep_attribute=TuyaMCUCluster.ep_attribute,
            attribute_name="presence_clear_cooldown",
        ),
        123: DPToAttributeMapping(
            ep_attribute=TuyaMCUCluster.ep_attribute,
            attribute_name="led_indicator",
        ),
    }

    data_point_handlers = {
        1:   "_dp_2_attr_update",
        2:   "_dp_2_attr_update",
        101: "_dp_2_attr_update",
        103: "_dp_2_attr_update",
        112: "_dp_2_attr_update",
        119: "_dp_2_attr_update",
        123: "_dp_2_attr_update",
    }


# ── Quirk registration ────────────────────────────────────────────────────────

(
    QuirkBuilder("_TZE284_ft7qqpx3", "TS0601")
    .adds(ZpsZ1ManufCluster)
    .skip_configuration()

    # DP1 — occupancy binary sensor (true/false for automations)
    .binary_sensor(
        attribute_name=ZpsZ1ManufCluster.AttributeDefs.presence_state.name,
        cluster_id=TUYA_CLUSTER_ID,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        entity_type=EntityType.STANDARD,
        fallback_name="Occupancy",
        translation_key="occupancy",
        attribute_initialized_from_cache=False,
    )

    # DP1 — presence_state enum sensor (all 3 states visible)
    .enum(
        attribute_name=ZpsZ1ManufCluster.AttributeDefs.presence_state.name,
        enum_class=PresenceState,
        cluster_id=TUYA_CLUSTER_ID,
        endpoint_id=1,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        fallback_name="Presence state",
        translation_key="presence_state",
    )

    # DP101 — illuminance sensor (lux)
    .sensor(
        attribute_name=ZpsZ1ManufCluster.AttributeDefs.illuminance.name,
        cluster_id=TUYA_CLUSTER_ID,
        endpoint_id=1,
        fallback_name="Illuminance",
        translation_key="illuminance",
    )

    # DP2 — detection_range number (0–500 cm)
    .number(
        attribute_name=ZpsZ1ManufCluster.AttributeDefs.detection_range.name,
        cluster_id=TUYA_CLUSTER_ID,
        endpoint_id=1,
        min_value=0,
        max_value=500,
        step=50,
        fallback_name="Detection range",
        translation_key="detection_range",
        entity_type=EntityType.CONFIG,
    )

    # DP119 — presence_clear_cooldown number (2–60 s)
    .number(
        attribute_name=ZpsZ1ManufCluster.AttributeDefs.presence_clear_cooldown.name,
        cluster_id=TUYA_CLUSTER_ID,
        endpoint_id=1,
        min_value=2,
        max_value=60,
        step=1,
        fallback_name="Presence clear cooldown",
        translation_key="presence_clear_cooldown",
        entity_type=EntityType.CONFIG,
    )

    # DP103 — auto_calibration select
    .enum(
        attribute_name=ZpsZ1ManufCluster.AttributeDefs.auto_calibration.name,
        enum_class=AutoCalibrationState,
        cluster_id=TUYA_CLUSTER_ID,
        endpoint_id=1,
        entity_platform=EntityPlatform.SELECT,
        entity_type=EntityType.CONFIG,
        fallback_name="Auto calibration",
        translation_key="auto_calibration",
    )

    # DP112 — sensitivity_preset select
    .enum(
        attribute_name=ZpsZ1ManufCluster.AttributeDefs.sensitivity_preset.name,
        enum_class=SensitivityPreset,
        cluster_id=TUYA_CLUSTER_ID,
        endpoint_id=1,
        entity_platform=EntityPlatform.SELECT,
        entity_type=EntityType.CONFIG,
        fallback_name="Sensitivity preset",
        translation_key="sensitivity_preset",
    )

    # DP123 — led_indicator switch
    .switch(
        attribute_name=ZpsZ1ManufCluster.AttributeDefs.led_indicator.name,
        cluster_id=TUYA_CLUSTER_ID,
        endpoint_id=1,
        fallback_name="LED indicator",
        translation_key="led_indicator",
        entity_type=EntityType.CONFIG,
    )

    .add_to_registry()
)
