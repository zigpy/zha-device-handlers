"""ZHA quirk for the Securifi Peanut Plug (PP-WHT-US)."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic, ElectricalMeasurement

from zhaquirks.builder import QuirkBuilder, SensorDeviceClass
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legacy import signature_matches

PEANUT_SIGNATURE = {
    ENDPOINTS: {
        1: {
            PROFILE_ID: zha.PROFILE_ID,
            DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
            INPUT_CLUSTERS: [
                Basic.cluster_id,
                PowerConfiguration.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                ElectricalMeasurement.cluster_id,
                Diagnostic.cluster_id,
            ],
            OUTPUT_CLUSTERS: [
                Basic.cluster_id,
                PowerConfiguration.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                Ota.cluster_id,
                ElectricalMeasurement.cluster_id,
                Diagnostic.cluster_id,
            ],
        }
    }
}

# The Peanut Plug does not report a model identifier. QuirkBuilder(..., None)
# matches any model from this manufacturer, so the signature filter below is
# required to restrict this quirk to the Peanut Plug endpoint signature.
(
    QuirkBuilder("Securifi Ltd.", None)
    .filter(signature_matches(PEANUT_SIGNATURE))
    .friendly_name(
        manufacturer="Securifi",
        model="Peanut Plug PP-WHT-US",
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=ElectricalMeasurement.cluster_id,
        function=lambda entity: entity.device_class == SensorDeviceClass.FREQUENCY,
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=ElectricalMeasurement.cluster_id,
        function=lambda entity: entity.device_class == SensorDeviceClass.POWER_FACTOR,
    )
    .add_to_registry()
)
