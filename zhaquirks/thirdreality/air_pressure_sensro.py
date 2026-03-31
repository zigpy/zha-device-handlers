"""Third Reality air pressure sensor devices."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import AnalogInput, PressureMeasurement


class CustomAnalogInputCluster(CustomCluster, AnalogInput):
    """Custom AnalogInput cluster with modified description and application_type."""

    _CONSTANT_ATTRIBUTES = {
        AnalogInput.AttributeDefs.application_type.id: 0x00040000,
        AnalogInput.AttributeDefs.description.id: "Dirty Level",
    }


(
    QuirkBuilder("Third Reality, Inc", "3RAP0149BZ")
    .adds(CustomAnalogInputCluster)
    .change_entity_metadata(
        endpoint_id=1,
        cluster_id=PressureMeasurement.cluster_id,
        new_primary=False,
        new_fallback_name="Pressure",
    )
    .add_to_registry()
)
