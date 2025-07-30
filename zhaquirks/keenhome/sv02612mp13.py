"""Smart vent quirk."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import DoublingPowerConfigurationCluster

KEEN1_CLUSTER_ID = 0xFC01  # decimal = 64513
KEEN2_CLUSTER_ID = 0xFC02  # decimal = 64514


(
    QuirkBuilder("Keen Home Inc", "SV01-410-MP-1.0")
    .applies_to("Keen Home Inc", "SV01-410-MP-1.1")
    .applies_to("Keen Home Inc", "SV01-410-MP-1.4")
    .applies_to("Keen Home Inc", "SV01-410-MP-1.5")
    .applies_to("Keen Home Inc", "SV02-410-MP-1.2")
    .applies_to("Keen Home Inc", "SV02-410-MP-1.3")
    .applies_to("Keen Home Inc", "SV01-412-MP-1.0")
    .applies_to("Keen Home Inc", "SV01-610-MP-1.0")
    .applies_to("Keen Home Inc", "SV02-610-MP-1.3")
    .applies_to("Keen Home Inc", "SV01-612-MP-1.0")
    .applies_to("Keen Home Inc", "SV02-612-MP-1.3")
    .replaces(
        replacement_cluster_class=DoublingPowerConfigurationCluster,
        cluster_id=DoublingPowerConfigurationCluster.cluster_id,
    )
    .add_to_registry()
)
