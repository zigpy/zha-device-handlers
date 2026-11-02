"""CTM Lyng outlet quirks."""

from zigpy.zcl import ClusterType

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTime,
)
from zhaquirks.ctm import (
    CTM_MANUF_NAME,
    CTMCooktopGuardCluster,
    CTMDiagnosticsCluster,
    CTMOnOffCluster,
)

(
    QuirkBuilder(CTM_MANUF_NAME, "mStikk Outlet")
    .applies_to(CTM_MANUF_NAME, "mStikk 16A")
    .applies_to(CTM_MANUF_NAME, "mStikk 25A")
    .applies_to(CTM_MANUF_NAME, "Tavlerele 25A")
    .replaces(CTMOnOffCluster)
    .replaces(CTMCooktopGuardCluster, cluster_type=ClusterType.Client)
    .replaces(CTMDiagnosticsCluster)
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
    .sensor(
        attribute_name=CTMDiagnosticsCluster.AttributeDefs.ctm_button_0_click_count.name,
        cluster_id=CTMDiagnosticsCluster.cluster_id,
        endpoint_id=1,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="button_click_count",
        fallback_name="Button click count",
    )
    .sensor(
        attribute_name=CTMDiagnosticsCluster.AttributeDefs.ctm_button_0_ms_click_duration.name,
        cluster_id=CTMDiagnosticsCluster.cluster_id,
        endpoint_id=1,
        unit=UnitOfTime.MILLISECONDS,
        device_class=SensorDeviceClass.DURATION,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="button_click_duration",
        fallback_name="Button click duration",
    )
    .add_to_registry()
)
