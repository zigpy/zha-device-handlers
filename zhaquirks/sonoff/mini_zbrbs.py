"""Sonoff Mini ZB RBS - Zigbee Cover."""

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.builder import EntityPlatform, EntityType, QuirkBuilder
from zhaquirks.clusters import CustomCluster

# ============================================================
# Quirk Metadata
# ============================================================
QUIRK_METADATA = {
    "name": "SONOFF MINI-ZBRBS",
    "model": "MINI-ZBRBS",
    "version": "1.0",
    "update_date": "2026-11-24",
    "author": "SONOFF",
    "manufacturer": "SONOFF",
    "description": "SONOFF MINI-ZBRBS - Window covering roller shutter motor controller.",
}




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


class SonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        external_trigger_mode = ZCLAttributeDef(
            id=0x0016,
            type=SonoffExternalSwitchTriggerType,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        single_switch_mode = ZCLAttributeDef(
            id=0x6038,
            type=t.Bool,
            zcl_type=DataTypeId.bool_,
            manufacturer_code=None,
        )
        cover_calibrated = ZCLAttributeDef(
            id=0x5012,
            type=SonoffCoverCalibrationStatus,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        motor_state = ZCLAttributeDef(
            id=0x5013,
            type=SonoffMotorState,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
            access="r",
        )
        attrib_0010 = ZCLAttributeDef(  # factory value=515
            id=0x0010,
            type=t.uint32_t,
            manufacturer_code=None,
            access="r",
        )
        attrib_0012 = ZCLAttributeDef(  # factory value=10
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

    async def write_attributes(self, attributes, manufacturer=None):
        """Enforce rules between external trigger mode (0x0016) and single switch mode (0x6038).

        - Single switch mode is only usable with pulse (momentary) switches.
        - Switching to edge trigger mode disables single switch mode.
        - Enabling single switch mode switches the external trigger mode back to pulse.
        """
        normalized = {}
        for key, value in attributes.items():
            if isinstance(key, str):
                attr_def = self.attributes_by_name.get(key)
                key = attr_def.id if attr_def is not None else key
            normalized[key] = value

        trigger_id = self.AttributeDefs.external_trigger_mode.id
        single_switch_id = self.AttributeDefs.single_switch_mode.id

        # Enabling single switch mode: force the external switch back to pulse (momentary).
        if normalized.get(single_switch_id):
            normalized[trigger_id] = SonoffExternalSwitchTriggerType.pulse_trigger

        # Edge (maintained) switches are incompatible: disable single switch mode.
        if normalized.get(trigger_id) == SonoffExternalSwitchTriggerType.edge_trigger:
            normalized[single_switch_id] = False

        return await super().write_attributes(normalized, manufacturer)


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
    .switch(
        SonoffCluster.AttributeDefs.single_switch_mode.name,
        SonoffCluster.cluster_id,
        translation_key="single_switch_mode",
        fallback_name="Single switch mode",
    )
    .enum(
        SonoffCluster.AttributeDefs.cover_calibrated.name,
        SonoffCoverCalibrationStatus,
        SonoffCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="calibrated",
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
