"""frient Vibration Sensor WISZB-137."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, ReportingConfig, SensorStateClass
from zigpy.quirks.v2.homeassistant import EntityType
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.develco import DEVELCO, FRIENT, DevelcoIasZone


class FrientAccelerationMeasurement(CustomCluster):
    """Manufacturer specific acceleration measurement cluster."""

    cluster_id = 0xFC04
    name = "Frient Acceleration Measurement"
    ep_attribute = "frient_acceleration_measurement"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        measured_value_x: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.int16s,
            access="rp",
            manufacturer_code=0x1015,
        )
        measured_value_y: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.int16s,
            access="rp",
            manufacturer_code=0x1015,
        )
        measured_value_z: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.int16s,
            access="rp",
            manufacturer_code=0x1015,
        )


# WISZB-137 (Vibration Sensor)
# According to the manual:
# zone_status Bit0: Alarm 1 (Movement)
# zone_status Bit1: Alarm 2 (Vibration)
(
    QuirkBuilder(FRIENT, "WISZB-137")
    .applies_to(DEVELCO, "WISZB-137")
    .replaces(FrientAccelerationMeasurement, endpoint_id=45)
    .replaces(DevelcoIasZone, endpoint_id=45)
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=45,
        device_class=BinarySensorDeviceClass.VIBRATION,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Alarm_2),
        unique_id_suffix="vibration",
        entity_type=EntityType.STANDARD,
        fallback_name="Vibration",
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=45,
        device_class=BinarySensorDeviceClass.MOTION,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Alarm_1),
        unique_id_suffix="movement",
        entity_type=EntityType.STANDARD,
        fallback_name="Movement",
    )
    .number(
        attribute_name=IasZone.AttributeDefs.current_zone_sensitivity_level.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=45,
        min_value=1,
        max_value=15,
        step=1,
        translation_key="sensitivity_level",
        fallback_name="Sensitivity level",
    )
    .sensor(
        attribute_name=FrientAccelerationMeasurement.AttributeDefs.measured_value_x.name,
        cluster_id=FrientAccelerationMeasurement.cluster_id,
        endpoint_id=45,
        state_class=SensorStateClass.MEASUREMENT,
        unit="g",  # g-force
        divisor=1000,
        translation_key="acceleration_x",
        fallback_name="Acceleration X",
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=900,
            reportable_change=50,
        ),
    )
    .sensor(
        attribute_name=FrientAccelerationMeasurement.AttributeDefs.measured_value_y.name,
        cluster_id=FrientAccelerationMeasurement.cluster_id,
        endpoint_id=45,
        state_class=SensorStateClass.MEASUREMENT,
        unit="g",  # g-force
        divisor=1000,
        translation_key="acceleration_y",
        fallback_name="Acceleration Y",
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=900,
            reportable_change=50,
        ),
    )
    .sensor(
        attribute_name=FrientAccelerationMeasurement.AttributeDefs.measured_value_z.name,
        cluster_id=FrientAccelerationMeasurement.cluster_id,
        endpoint_id=45,
        state_class=SensorStateClass.MEASUREMENT,
        unit="g",  # g-force
        divisor=1000,
        translation_key="acceleration_z",
        fallback_name="Acceleration Z",
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=900,
            reportable_change=50,
        ),
    )
    # This entity does not do anything
    .prevent_default_entity_creation(endpoint_id=45, cluster_id=BinaryInput.cluster_id)
    # This is the default IAS zone entity which triggers for both alarm bits,
    # so we disable it by default since we create separate entities.
    # ZHA creates it as a primary entity, which is good, as it would be called
    # "Vibration" if not. We can't fully remove this as it may be in use already.
    .change_entity_metadata(
        endpoint_id=45,
        cluster_id=IasZone.cluster_id,
        unique_id_suffix="45-1280",
        new_entity_registry_enabled_default=False,
    )
    .add_to_registry()
)
