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
    .sensor(
        attribute_name=CTMDiagnosticsCluster.AttributeDefs.ctm_reboot_counter.name,
        cluster_id=CTMDiagnosticsCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="reboot_counter",
        fallback_name="Reboot counter",
    )
    .sensor(
        attribute_name=CTMDiagnosticsCluster.AttributeDefs.ctm_button_0_click_counter.name,
        cluster_id=CTMDiagnosticsCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="button_click_counter",
        fallback_name="Button click counter",
    )
    .sensor(
        attribute_name=CTMDiagnosticsCluster.AttributeDefs.ctm_button_0_ms_click_duration.name,
        cluster_id=CTMDiagnosticsCluster.cluster_id,
        endpoint_id=1,
        unit=UnitOfTime.MILLISECONDS,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="button_click_duration",
        fallback_name="Button click duration",
    )
    .add_to_registry()
)
