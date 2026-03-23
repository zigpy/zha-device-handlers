"""Door/Windows sensors."""

from zigpy.quirks.v2 import BinarySensorDeviceClass, QuirkBuilder
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster

from . import DevelcoIasZone


class DevelcoPowerConfiguration(PowerConfigurationCluster):
    """Power configuration cluster."""

    MIN_VOLTS = 2.5  # advised voltage to replace batteries, device will blink red when this state hits.
    MAX_VOLTS = 3.0


(
    QuirkBuilder("frient A/S", "WISZB-131")
    .applies_to("Develco Products A/S", "WISZB-120")
    .applies_to("frient A/S", "WISZB-120")
    .applies_to("Develco Products A/S", "WISZB-121")
    .applies_to("frient A/S", "WISZB-121")
    .replaces(DevelcoIasZone, endpoint_id=35)
    .replaces(DevelcoPowerConfiguration, endpoint_id=35)
    # The binary input cluster is a duplicate
    .prevent_default_entity_creation(endpoint_id=35, cluster_id=BinaryInput.cluster_id)
    .binary_sensor(
        endpoint_id=35,
        cluster_id=IasZone.cluster_id,
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
        unique_id_suffix="tamper",
        fallback_name="Tamper",
    )
    .add_to_registry()
)
