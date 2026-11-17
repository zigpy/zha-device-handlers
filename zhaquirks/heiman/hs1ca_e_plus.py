"""Heiman HS1CA-E-PLUS CO sensor."""

import zigpy.types as t
from zigpy.zcl.clusters.security import IasWd, IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
)
from zhaquirks.clusters import CustomCluster


class SmokeCoSirenEnum(t.enum8):
    """Smoke siren type."""

    Stop = 0
    Smoke_siren = 1
    CO_siren = 2


class CustomHeimanCluster(CustomCluster):
    """Heiman custom cluster."""

    cluster_id = 0xFC90

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        sensor_self_check_state = ZCLAttributeDef(
            id=0x0001,
            type=t.enum8,
            manufacturer_code=0x120B,
        )
        sensor_fault_state = ZCLAttributeDef(
            id=0x0002,
            type=t.uint8_t,
            manufacturer_code=0x120B,
        )
        sensor_mute_state = ZCLAttributeDef(
            id=0x0009,
            type=t.uint8_t,
            manufacturer_code=0x120B,
        )
        siren_for_automation = ZCLAttributeDef(
            id=0x0012,
            type=SmokeCoSirenEnum,
            manufacturer_code=0x120B,
        )
        interconnectable = ZCLAttributeDef(
            id=0x1007,
            type=t.uint8_t,
            manufacturer_code=0x120B,
        )
        rebooted_count = ZCLAttributeDef(
            id=0x0019,
            type=t.uint16_t,
            manufacturer_code=0x120B,
        )
        rejoined_count = ZCLAttributeDef(
            id=0x001A,
            type=t.uint16_t,
            manufacturer_code=0x120B,
        )
        reported_packages = ZCLAttributeDef(
            id=0x001B,
            type=t.uint16_t,
            manufacturer_code=0x120B,
        )
        remote_mute = ZCLAttributeDef(
            id=0x0008,
            type=t.uint8_t,
            manufacturer_code=0x120B,
        )
        remote_test = ZCLAttributeDef(
            id=0x1009,
            type=t.uint8_t,
            manufacturer_code=0x120B,
        )


(
    QuirkBuilder()
    .applies_to("HEIMAN", "HS1CA-E PLUS")
    .applies_to("HEIMAN", "HS1CA-E-PLUS")
    .friendly_name(manufacturer="HEIMAN", model="HS1CA-E-PLUS")
    .replaces(CustomHeimanCluster)
    # Replace the IAS WD siren (fixed tone, ZHA-limited to ~30 s) with an
    # attribute-controlled siren that supports tone selection and sounds until
    # turned off. Reuse the IAS WD siren's unique_id so existing entities migrate.
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=IasWd.cluster_id)
    .siren(
        CustomHeimanCluster.AttributeDefs.siren_for_automation.name,
        CustomHeimanCluster.cluster_id,
        available_tones={
            SmokeCoSirenEnum.Smoke_siren: "Smoke siren",
            SmokeCoSirenEnum.CO_siren: "CO siren",
        },
        off_value=SmokeCoSirenEnum.Stop,
        default_tone=SmokeCoSirenEnum.CO_siren,
        unique_id_suffix=str(IasWd.cluster_id),
        translation_key="siren",
        fallback_name="Siren",
    )
    .binary_sensor(
        CustomHeimanCluster.AttributeDefs.sensor_self_check_state.name,
        CustomHeimanCluster.cluster_id,
        reporting_config=ReportingConfig(
            min_interval=2, max_interval=0, reportable_change=1
        ),
        translation_key="self_test_state",
        fallback_name="Self-test",
    )
    .binary_sensor(
        CustomHeimanCluster.AttributeDefs.sensor_fault_state.name,
        CustomHeimanCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        fallback_name="Fault",
    )
    .binary_sensor(
        CustomHeimanCluster.AttributeDefs.sensor_mute_state.name,
        CustomHeimanCluster.cluster_id,
        translation_key="muted",
        fallback_name="Muted",
    )
    .binary_sensor(
        CustomHeimanCluster.AttributeDefs.interconnectable.name,
        CustomHeimanCluster.cluster_id,
        translation_key="interconnectable",
        fallback_name="Interconnectable",
    )
    .switch(
        CustomHeimanCluster.AttributeDefs.remote_mute.name,
        CustomHeimanCluster.cluster_id,
        translation_key="buzzer_manual_mute",
        fallback_name="Buzzer manual mute",
    )
    .command_button(
        IasZone.ServerCommandDefs.init_test_mode.name,
        IasZone.cluster_id,
        command_kwargs={"test_mode_duration": 5, "current_zone_sensitivity_level": 0},
        translation_key="remote_test",
        fallback_name="Remote test",
    )
    # Zigbee debug sensors:
    .sensor(
        CustomHeimanCluster.AttributeDefs.rebooted_count.name,
        CustomHeimanCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="rebooted_count",
        fallback_name="Rebooted count",
    )
    .sensor(
        CustomHeimanCluster.AttributeDefs.rejoined_count.name,
        CustomHeimanCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="rejoined_count",
        fallback_name="Rejoined count",
    )
    .sensor(
        CustomHeimanCluster.AttributeDefs.reported_packages.name,
        CustomHeimanCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="reported_packages",
        fallback_name="Reported packages",
    )
    .add_to_registry()
)
