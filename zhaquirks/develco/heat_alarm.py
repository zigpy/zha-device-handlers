"""Frient Heat Detector."""

from zha.quirks import SIREN_BASIC
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasWd, IasZone

from zhaquirks.builder import EntityType, QuirkBuilder
from zhaquirks.develco import DevelcoIasZone, DevelcoPowerConfiguration

(
    QuirkBuilder("frient A/S", "HESZB-120")
    .applies_to("Develco Products A/S", "HESZB-120")
    .replaces(DevelcoIasZone, endpoint_id=35)
    .replaces(DevelcoPowerConfiguration, endpoint_id=35)
    # The device only has basic siren features, so hint that to ZHA
    .exposes_feature(SIREN_BASIC)
    # Hide the default binary input sensor
    .prevent_default_entity_creation(
        endpoint_id=35,
        cluster_id=BinaryInput.cluster_id,
    )
    # The IAS Zone sensor should be primary
    .change_entity_metadata(
        endpoint_id=35,
        cluster_id=IasZone.cluster_id,
        new_primary=True,
    )
    # Not the siren
    .change_entity_metadata(
        endpoint_id=35,
        cluster_id=IasWd.cluster_id,
        new_primary=False,
        new_entity_category=EntityType.CONFIG,
    )
    .add_to_registry()
)
