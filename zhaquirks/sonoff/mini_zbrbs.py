"""Sonoff Mini ZB RBS - Zigbee Cover."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityPlatform, EntityType, QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class SonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        external_trigger_mode = ZCLAttributeDef(
            id=0x0016,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        cover_calibrated = ZCLAttributeDef(
            id=0x5012,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        motor_state = ZCLAttributeDef(
            id=0x5013,
            type=t.uint8_t,
            manufacturer_code=None,
            access="r",
        )
        attrib_0010 = ZCLAttributeDef(  # factory value=515
            id=0x0010,
            type=t.uint32_t,
            manufacturer_code=None,
            access="r",
        )
        attrib_0012 = ZCLAttributeDef(  # factiry value=10
            id=0x0012,
            type=t.int16s,
            manufacturer_code=None,
        )
        limits_calibration = ZCLAttributeDef(  # 2: automatic calibration, 4: not_calibrated_+open 50% , 6: stop(in pairing)?, 7: manual pairing?+close, 8: stop+stop_pairing
            id=0x5001,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        cluster_revision = ZCLAttributeDef(
            id=0xFFFD,
            type=t.uint16_t,
            manufacturer_code=None,
        )


class SonoffCoverCalibrationStatus(t.enum8):
    """Cover calibration status."""

    not_calibrated = 0x00
    calibrated = 0x01


class SonoffMotorState(t.enum8):
    """Motor state (can be different from cover state)."""

    stopped = 0x00
    opening = 0x01
    closing = 0x02


class SonoffExternalSwitchTriggerType(t.enum8):
    """External switch trigger type."""

    edge_trigger = 0x00
    pulse_trigger = 0x01


(
    QuirkBuilder("SONOFF", "MINI-ZBRBS")
    .replaces(SonoffCluster)
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalSwitchTriggerType,
        SonoffCluster.cluster_id,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
    )
    .enum(
        SonoffCluster.AttributeDefs.cover_calibrated.name,
        SonoffCoverCalibrationStatus,
        SonoffCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="cover_calibrated",
        fallback_name="Calibrated",
    )
    .enum(
        SonoffCluster.AttributeDefs.motor_state.name,
        SonoffMotorState,
        SonoffCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="motor_state",
        fallback_name="Motor state",
    )
    .write_attr_button(
        SonoffCluster.AttributeDefs.limits_calibration.name,
        2,  # 2: automatic calibration
        SonoffCluster.cluster_id,
        translation_key="configure_limits",
        fallback_name="Configure cover limits",
    )
    .add_to_registry()
)
