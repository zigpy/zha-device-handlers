"""Frient Water Leak."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasWd, IasZone

from . import DevelcoIasZone, DevelcoPowerConfiguration

(
    QuirkBuilder("frient A/S", "FLSZB-110")
    .replaces(DevelcoIasZone, endpoint_id=35)
    .replaces(DevelcoPowerConfiguration, endpoint_id=35)
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
        new_entity_category=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)
