"""CTM Lyng cooktop guard quirks."""

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
)
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
        attribute_name=CTMCooktopGuardCluster.AttributeDefs.ctm_cooktop_temperature.name,
        cluster_id=CTMCooktopGuardCluster.cluster_id,
        endpoint_id=1,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=3600,
            reportable_change=1,
        ),
        translation_key="cooktop_temperature",
        fallback_name="Cooktop temperature",
    )
    .enum(
        attribute_name=CTMCooktopGuardCluster.AttributeDefs.ctm_alarm_status.name,
        cluster_id=CTMCooktopGuardCluster.cluster_id,
        endpoint_id=1,
        enum_class=AlarmStatus,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=3600,
            reportable_change=1,
        ),
        translation_key="alarm_status",
        fallback_name="Alarm status",
    )
    .binary_sensor(
        attribute_name=CTMCooktopGuardCluster.AttributeDefs.ctm_battery_alarm.name,
        cluster_id=CTMCooktopGuardCluster.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.BATTERY,
        attribute_converter=bool,
        entity_type=EntityType.STANDARD,
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=3600,
            reportable_change=1,
        ),
        translation_key="battery_alarm",
        fallback_name="Battery alarm",
    )
    .binary_sensor(
        attribute_name=CTMCooktopGuardCluster.AttributeDefs.ctm_cooktop_active.name,
        cluster_id=CTMCooktopGuardCluster.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.RUNNING,
        attribute_converter=bool,
        entity_type=EntityType.STANDARD,
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=3600,
            reportable_change=1,
        ),
        translation_key="cooktop_active",
        fallback_name="Cooktop active",
    )
    .sensor(
        attribute_name=CTMCooktopGuardCluster.AttributeDefs.ctm_paired_with_address.name,
        cluster_id=CTMCooktopGuardCluster.cluster_id,
        endpoint_id=1,
        attribute_converter=str,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="relay_address",
        fallback_name="Relay address",
    )
    .sensor(
        attribute_name=CTMDiagnosticsCluster.AttributeDefs.ctm_rebooted_count.name,
        cluster_id=CTMDiagnosticsCluster.cluster_id,
        endpoint_id=1,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="rebooted_count",
        fallback_name="Rebooted count",
    )
    .add_to_registry()
)
