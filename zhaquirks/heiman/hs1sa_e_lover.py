"""Heiman HS1SA-E Lover smoke sensor."""

import zigpy.types as t
from zigpy.zcl.clusters.security import IasWd, IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import EntityType, QuirkBuilder
from zhaquirks.clusters import CustomCluster


class SmokeSirenEnum(t.enum8):
    """Smoke siren type."""

    Stop = 0
    Smoke_siren = 1
    CO_siren = 2


class CustomHeimanCluster(CustomCluster):
    """Heiman custom cluster."""

    cluster_id = 0xFC90

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        siren_for_automation = ZCLAttributeDef(
            id=0x0012,
            type=SmokeSirenEnum,
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


(
    QuirkBuilder()
    .applies_to("HEIMAN", "SmokeSensor-EF2-3.0")
    .friendly_name(manufacturer="HEIMAN", model="HS1SA-E-Lover")
    .replaces(CustomHeimanCluster)
    # Replace the IAS WD siren (fixed tone, ZHA-limited to ~30 s) with an
    # attribute-controlled siren that supports tone selection and sounds until
    # turned off. Reuse the IAS WD siren's unique_id so existing entities migrate.
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=IasWd.cluster_id)
    .siren(
        CustomHeimanCluster.AttributeDefs.siren_for_automation.name,
        CustomHeimanCluster.cluster_id,
        available_tones={
            SmokeSirenEnum.Smoke_siren: "Smoke siren",
            SmokeSirenEnum.CO_siren: "CO siren",
        },
        off_value=SmokeSirenEnum.Stop,
        default_tone=SmokeSirenEnum.Smoke_siren,
        unique_id_suffix=str(IasWd.cluster_id),
        translation_key="siren",
        fallback_name="Siren",
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
