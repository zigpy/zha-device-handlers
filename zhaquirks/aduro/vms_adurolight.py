"""AduroSmart multi motion sensor devices."""

import math

from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    RelativeHumidity,
    TemperatureMeasurement,
)

from zhaquirks.builder import (
    LIGHT_LUX,
    PERCENTAGE,
    BinarySensorDeviceClass,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
)


def _illuminance_to_lux(value: int) -> int | None:
    """Convert ZCL logarithmic illuminance to lux."""
    if value == 0xFFFF:
        return None
    if value == 0:
        return 0
    return round(math.pow(10, (value - 1) / 10000))


(
    QuirkBuilder("AduroSmart ERIA", "VMS_ADUROLIGHT")
    .applies_to("ERIA", "VMS_ADUROLIGHT")
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=PowerConfiguration.cluster_id,
        function=lambda entity: entity.__class__.__name__ == "Battery",
    )
    .sensor(
        attribute_name=PowerConfiguration.AttributeDefs.battery_percentage_remaining.name,
        cluster_id=PowerConfiguration.cluster_id,
        divisor=2,
        unit=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix=str(PowerConfiguration.cluster_id),
        fallback_name="Battery",
        reporting_config=ReportingConfig(
            min_interval=3600,
            max_interval=65000,
            reportable_change=2,
        ),
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OccupancySensing.cluster_id,
        function=lambda entity: entity.__class__.__name__ == "Occupancy",
    )
    .binary_sensor(
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        cluster_id=OccupancySensing.cluster_id,
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        entity_type=EntityType.STANDARD,
        unique_id_suffix=str(OccupancySensing.cluster_id),
        fallback_name="Occupancy",
        reporting_config=ReportingConfig(
            min_interval=1,
            max_interval=3600,
            reportable_change=0,
        ),
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=TemperatureMeasurement.cluster_id,
        function=lambda entity: entity.__class__.__name__ == "Temperature",
    )
    .sensor(
        attribute_name=TemperatureMeasurement.AttributeDefs.measured_value.name,
        cluster_id=TemperatureMeasurement.cluster_id,
        divisor=100,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unique_id_suffix=str(TemperatureMeasurement.cluster_id),
        fallback_name="Temperature",
        reporting_config=ReportingConfig(
            min_interval=10,
            max_interval=3600,
            reportable_change=100,
        ),
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=RelativeHumidity.cluster_id,
        function=lambda entity: entity.__class__.__name__ == "Humidity",
    )
    .sensor(
        attribute_name=RelativeHumidity.AttributeDefs.measured_value.name,
        cluster_id=RelativeHumidity.cluster_id,
        divisor=100,
        unit=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        unique_id_suffix=str(RelativeHumidity.cluster_id),
        fallback_name="Humidity",
        reporting_config=ReportingConfig(
            min_interval=10,
            max_interval=3600,
            reportable_change=100,
        ),
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=IlluminanceMeasurement.cluster_id,
        function=lambda entity: entity.__class__.__name__ == "Illuminance",
    )
    .sensor(
        attribute_name=IlluminanceMeasurement.AttributeDefs.measured_value.name,
        cluster_id=IlluminanceMeasurement.cluster_id,
        attribute_converter=_illuminance_to_lux,
        unit=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
        unique_id_suffix=str(IlluminanceMeasurement.cluster_id),
        fallback_name="Illuminance",
        reporting_config=ReportingConfig(
            min_interval=5,
            max_interval=3600,
            reportable_change=100,
        ),
    )
    .add_to_registry()
)
