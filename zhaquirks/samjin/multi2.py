"""Samjin Multi 2019 Refresh Quirk."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType
from zigpy.quirks.v2.homeassistant.sensor import SensorStateClass
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legacy import signature_matches
from zhaquirks.samjin import SAMJIN
from zhaquirks.smartthings import SmartThingsAccelCluster

# <SimpleDescriptor endpoint=1 profile=260 device_type=1026 device_version=0
# input_clusters=[0, 1, 3, 32, 1026, 1280, 2821, 64514]
# output_clusters=[3, 25]>
SIGNATURE = {
    ENDPOINTS: {
        1: {
            PROFILE_ID: 0x0104,
            DEVICE_TYPE: 0x0402,
            INPUT_CLUSTERS: [
                Basic.cluster_id,
                PowerConfiguration.cluster_id,
                Identify.cluster_id,
                PollControl.cluster_id,
                TemperatureMeasurement.cluster_id,
                IasZone.cluster_id,
                Diagnostic.cluster_id,
                SmartThingsAccelCluster.cluster_id,
            ],
            OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
        }
    },
}

builder = (
    QuirkBuilder(SAMJIN, "multi")
    .filter(signature_matches(SIGNATURE))
    .replaces(SmartThingsAccelCluster)
)

# The device reports raw acceleration only while it is moving. All three axes
# are updated until the sensor is still again; the last values stay in place.
for axis in ("x_axis", "y_axis", "z_axis"):
    builder = builder.sensor(
        axis,
        SmartThingsAccelCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        unit="mg",
        initially_disabled=True,
        translation_key=axis,
        fallback_name=axis.replace("_", " ").capitalize(),
    )

# Despite its name, "motion_threshold_multiplier" is the actual threshold: the
# difference in mg from the last reported axis values that is needed before the
# sensor starts sending motion updates. The "motion_threshold" attribute has no
# observable effect on the device and is intentionally not exposed.
(
    builder.number(
        "motion_threshold_multiplier",
        SmartThingsAccelCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=255,
        step=1,
        unit="mg",
        translation_key="motion_detection_sensitivity",
        fallback_name="Motion detection sensitivity",
    ).add_to_registry()
)
