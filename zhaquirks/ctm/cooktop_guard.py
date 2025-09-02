"""CTM Lyng cooktop guard quirks."""

from zigpy.quirks.v2 import EntityType, QuirkBuilder, ReportingConfig
from zigpy.quirks.v2.homeassistant import EntityPlatform, UnitOfTemperature
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass

from zhaquirks.ctm import (
    CTM_MANUF_NAME,
    AlarmStatus,
    CTMCooktopGuardCluster,
    CTMDiagnosticsCluster,
)

(
    QuirkBuilder(CTM_MANUF_NAME, "mKomfy")
    .applies_to(CTM_MANUF_NAME, "mKomfy Tak")
    .applies_to(CTM_MANUF_NAME, "mKomfy Infinity")
    .replaces(CTMCooktopGuardCluster)
    .replaces(CTMDiagnosticsCluster)
    .sensor(
        cluster_id=CTMCooktopGuardCluster.cluster_id,
        endpoint_id=1,
        attribute_name=CTMCooktopGuardCluster.AttributeDefs.ctm_cooktop_temperature.name,
        translation_key="cooktop_temperature",
        fallback_name="Cooktop temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=0,
            reportable_change=1,
        ),
    )
    .enum(
        cluster_id=CTMCooktopGuardCluster.cluster_id,
        endpoint_id=1,
        attribute_name=CTMCooktopGuardCluster.AttributeDefs.ctm_alarm_status.name,
        translation_key="alarm_status",
        fallback_name="Alarm status",
        enum_class=AlarmStatus,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=0,
            reportable_change=1,
        ),
    )
    .binary_sensor(
        cluster_id=CTMCooktopGuardCluster.cluster_id,
        endpoint_id=1,
        attribute_name=CTMCooktopGuardCluster.AttributeDefs.ctm_battery_alarm.name,
        translation_key="battery_alarm",
        fallback_name="Battery alarm",
        entity_type=EntityType.STANDARD,
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=0,
            reportable_change=1,
        ),
    )
    .binary_sensor(
        cluster_id=CTMCooktopGuardCluster.cluster_id,
        endpoint_id=1,
        attribute_name=CTMCooktopGuardCluster.AttributeDefs.ctm_cooktop_active.name,
        translation_key="cooktop_active",
        fallback_name="Cooktop active",
        entity_type=EntityType.STANDARD,
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=0,
            reportable_change=1,
        ),
    )
    .sensor(
        cluster_id=CTMCooktopGuardCluster.cluster_id,
        endpoint_id=1,
        attribute_name=CTMCooktopGuardCluster.AttributeDefs.ctm_paired_with_address.name,
        translation_key="relay_address",
        fallback_name="Relay address",
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
    )
    .sensor(
        cluster_id=CTMDiagnosticsCluster.cluster_id,
        endpoint_id=1,
        attribute_name=CTMDiagnosticsCluster.AttributeDefs.ctm_reboot_counter.name,
        translation_key="reboot_counter",
        fallback_name="Reboot counter",
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
    )
    .add_to_registry()
)
