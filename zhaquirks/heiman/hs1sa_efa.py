"""Heiman HS1SA-E smoke sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, ReportingConfig
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t
from zigpy.zcl.clusters.security import IasWd, IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.quirk_ids import SIREN_BASIC


class SmokeSirenEnum(t.enum8):
    """Smoke siren type."""

    Stop = 0
    Smoke_siren = 1
    CO_siren = 2


class ChamberContaminationEnum(t.enum8):
    """Chamber contamination level."""

    Normal = 0
    Light_contamination = 1
    Medium_contamination = 2
    Critical_contamination = 3


class SmokeLevelUnitEnum(t.enum8):
    """Smoke level unit."""

    dbm = 0
    pct_ft_obs = 1


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
        heartbeat_indicator = ZCLAttributeDef(
            id=0x1004,
            type=t.uint8_t,
            manufacturer_code=0x120B,
        )
        siren_for_automation = ZCLAttributeDef(
            id=0x0012,
            type=SmokeSirenEnum,
            manufacturer_code=0x120B,
        )
        interconnectable = ZCLAttributeDef(
            id=0x1007,
            type=t.uint8_t,
            manufacturer_code=0x120B,
        )
        smoke_level = ZCLAttributeDef(
            id=0x0016,
            type=t.uint8_t,
            manufacturer_code=0x120B,
        )
        smoke_unit = ZCLAttributeDef(
            id=0x0018,
            type=SmokeLevelUnitEnum,
            manufacturer_code=0x120B,
        )
        chamber_contamination = ZCLAttributeDef(
            id=0x0017,
            type=ChamberContaminationEnum,
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
    QuirkBuilder("HEIMAN", "HS1SA-EF-3.0")
    .replaces(CustomHeimanCluster)
    .exposes_feature(SIREN_BASIC)
    .change_entity_metadata(
        endpoint_id=1,
        cluster_id=IasWd.cluster_id,
        new_primary=False,
        new_entity_category=EntityType.CONFIG,
    )
    .switch(
        CustomHeimanCluster.AttributeDefs.heartbeat_indicator.name,
        CustomHeimanCluster.cluster_id,
        translation_key="heartbeat_indicator",
        fallback_name="Heartbeat indicator",
    )
    # XXX: siren_for_automation should be added as a siren entity, needs zigpy API
    .enum(
        CustomHeimanCluster.AttributeDefs.chamber_contamination.name,
        ChamberContaminationEnum,
        CustomHeimanCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="chamber_contamination",
        fallback_name="Chamber contamination",
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
    # XXX: The unit depends on the smoke_unit attribute, so we can't use one at all
    .sensor(
        CustomHeimanCluster.AttributeDefs.smoke_level.name,
        CustomHeimanCluster.cluster_id,
        divisor=100,
        translation_key="smoke_level",
        fallback_name="Smoke level",
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
