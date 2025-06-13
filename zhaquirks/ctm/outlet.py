"""CTM Lyng outlet quirks."""

from zigpy.quirks.v2 import EntityType, QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.zcl import ClusterType

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
    # .sensor(
    #     cluster_id=CTMCooktopGuardCluster.cluster_id,
    #     cluster_type=ClusterType.Client,
    #     endpoint_id=1,
    #     attribute_name=CTMCooktopGuardCluster.AttributeDefs.ctm_paired_with_address.name,
    #     translation_key="cooktop_guard_sensor_address",
    #     fallback_name="Cooktop guard sensor address",
    #     entity_type=EntityType.DIAGNOSTIC,
    #     initially_disabled=True,
    # )
    .sensor(
        cluster_id=CTMDiagnosticsCluster.cluster_id,
        endpoint_id=1,
        attribute_name=CTMDiagnosticsCluster.AttributeDefs.ctm_reboot_counter.name,
        translation_key="reboot_counter",
        fallback_name="Reboot counter",
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
    )
    .sensor(
        cluster_id=CTMDiagnosticsCluster.cluster_id,
        endpoint_id=1,
        attribute_name=CTMDiagnosticsCluster.AttributeDefs.ctm_button_0_click_counter.name,
        translation_key="button_click_counter",
        fallback_name="Button click counter",
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
    )
    .sensor(
        cluster_id=CTMDiagnosticsCluster.cluster_id,
        endpoint_id=1,
        attribute_name=CTMDiagnosticsCluster.AttributeDefs.ctm_button_0_ms_click_duration.name,
        translation_key="button_click_duration",
        fallback_name="Button click duration",
        unit=UnitOfTime.MILLISECONDS,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
    )
    .add_to_registry()
)
