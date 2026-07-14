"""Third Reality air filter / pressure sensor (3RAP0149BZ)."""

from zigpy.zcl.clusters.general import AnalogInput
from zigpy.zcl.clusters.measurement import PressureMeasurement

from zhaquirks.builder import PERCENTAGE, QuirkBuilder, SensorStateClass

(
    QuirkBuilder("Third Reality, Inc", "3RAP0149BZ")
    # Device reports a bogus application_type (0xFFFF -> temperature/°C);
    # hide only ZHA's default AnalogInputSensor so the custom sensor survives.
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=AnalogInput.cluster_id,
        function=lambda entity: type(entity).__name__ == "AnalogInputSensor",
    )
    .sensor(
        attribute_name=AnalogInput.AttributeDefs.present_value.name,
        cluster_id=AnalogInput.cluster_id,
        endpoint_id=1,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        translation_key="dirty_level",
        fallback_name="Dirty level",
    )
    # Pressure is optional secondary functionality (enabled via the dial
    # switch), so don't let it become the primary entity that takes over
    # the device name; it gets its device-class name "Pressure" instead.
    .change_entity_metadata(
        endpoint_id=1,
        cluster_id=PressureMeasurement.cluster_id,
        new_primary=False,
    )
    .add_to_registry()
)
