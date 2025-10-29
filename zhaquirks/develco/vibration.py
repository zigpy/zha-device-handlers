"""frient Vibration Sensor WISZB-137."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, ReportingConfig, SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.develco import DevelcoIasZone


class FrientAccelerationMeasurement(CustomCluster):
    """Manufacturer specific acceleration measurement cluster."""

    cluster_id = 0xFC04
    manufacturer_id_override = 0x1015

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        measured_value_x: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.int16s,
            is_manufacturer_specific=True,
            access="rp",
        )

        measured_value_y: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.int16s,
            is_manufacturer_specific=True,
            access="rp",
        )

        measured_value_z: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.int16s,
            is_manufacturer_specific=True,
            access="rp",
        )


class FrientVibrationIasZone(DevelcoIasZone):
    """Custom IAS Zone cluster for frient vibration sensor with movement and vibration detection."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.zone_status.id:
            # According to the manual:
            # Bit0: Alarm 1 (Movement)
            # Bit1: Alarm 2 (Vibration)
            # Bit3: Battery
            # Bit4: Supervision reports
            # Bit5: Restore reports
            movement_state = bool(value & 0b00000001)  # Bit 0
            vibration_state = bool(value & 0b00000010)  # Bit 1

            super()._update_attribute(self.AttributeDefs.movement.id, movement_state)
            super()._update_attribute(self.AttributeDefs.vibration.id, vibration_state)

    class AttributeDefs(IasZone.AttributeDefs):
        """Attribute definitions."""

        movement: Final = ZCLAttributeDef(
            id=0xFFF0,  # Custom attribute ID for movement detection
            type=t.Bool,
        )

        vibration: Final = ZCLAttributeDef(
            id=0xFFF1,  # Custom attribute ID for vibration detection
            type=t.Bool,
        )

        number_of_zone_sensitivity_levels_supported: Final = ZCLAttributeDef(
            id=0x0012,
            type=t.uint8_t,
            access="r",
        )

        current_zone_sensitivity_level: Final = ZCLAttributeDef(
            id=0x0013,
            type=t.uint8_t,
            access="rw",
        )


# WISZB-137 (Vibration Sensor)
(
    QuirkBuilder("frient A/S", "WISZB-137")
    .applies_to("Develco Products A/S", "WISZB-137")
    .replaces(FrientAccelerationMeasurement, endpoint_id=45)
    .replaces(FrientVibrationIasZone, endpoint_id=45)
    .binary_sensor(
        attribute_name="vibration",
        cluster_id=IasZone.cluster_id,
        endpoint_id=45,
        entity_type="vibration",
        translation_key="vibration",
        fallback_name="Vibration",
    )
    .binary_sensor(
        attribute_name="movement",
        cluster_id=IasZone.cluster_id,
        endpoint_id=45,
        entity_type="motion",
        translation_key="movement",
        fallback_name="Movement",
    )
    .sensor(
        attribute_name="number_of_zone_sensitivity_levels_supported",
        cluster_id=IasZone.cluster_id,
        endpoint_id=45,
        translation_key="sensitivity_levels_supported",
        fallback_name="Sensitivity levels supported",
    )
    .number(
        attribute_name="current_zone_sensitivity_level",
        cluster_id=IasZone.cluster_id,
        endpoint_id=45,
        min_value=1,
        max_value=15,
        step=1,
        translation_key="sensitivity_level",
        fallback_name="Sensitivity level (1-15)",
    )
    .sensor(
        attribute_name=FrientAccelerationMeasurement.AttributeDefs.measured_value_x.name,
        cluster_id=FrientAccelerationMeasurement.cluster_id,
        endpoint_id=45,
        state_class=SensorStateClass.MEASUREMENT,
        unit="g",
        divisor=1000,
        translation_key="acceleration_x",
        fallback_name="Acceleration x",
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
        unit="g",
        divisor=1000,
        translation_key="acceleration_y",
        fallback_name="Acceleration y",
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
        unit="g",
        divisor=1000,
        translation_key="acceleration_z",
        fallback_name="Acceleration z",
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=900,
            reportable_change=50,
        ),
    )
    .prevent_default_entity_creation(endpoint_id=45, cluster_id=BinaryInput.cluster_id)
    .add_to_registry()
)