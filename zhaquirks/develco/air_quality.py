"""Develco Air Quality Sensor."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import CONCENTRATION_PARTS_PER_BILLION
import zigpy.types as t
from zigpy.zcl.foundation import (
    ZCL_CLUSTER_REVISION_ATTR,
    ZCL_REPORTING_STATUS_ATTR,
    BaseAttributeDefs,
    ZCLAttributeDef,
)

from zhaquirks.develco import DevelcoPowerConfiguration


class AQSZB110PowerConfiguration(DevelcoPowerConfiguration):
    """PowerConfiguration with device-specific voltage bounds."""

    MIN_VOLTS = 2.3
    MAX_VOLTS = 3.0


class DevelcoVOCMeasurement(CustomCluster):
    """Develco VOC cluster definition."""

    cluster_id = 0xFC03
    name = "VOC Level"
    ep_attribute = "develco_voc_level"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions, same as all the other `Measurement` clusters."""

        measured_value: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint16_t,  # In parts per billion
            access="rp",
            mandatory=True,
            is_manufacturer_specific=True,
        )
        min_measured_value: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            access="r",
            mandatory=True,
            is_manufacturer_specific=True,
        )
        max_measured_value: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            access="r",
            mandatory=True,
            is_manufacturer_specific=True,
        )
        tolerance: Final = ZCLAttributeDef(
            id=0x0003,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )

        cluster_revision: Final = ZCL_CLUSTER_REVISION_ATTR
        reporting_status: Final = ZCL_REPORTING_STATUS_ATTR


def measured_value_converter(value: int) -> int | None:
    """Ignore invalid value sent after initiation."""
    new_value = value if value < 0xFFFF else None
    return new_value


def value_to_caqi(value: int) -> str | None:
    """Convert raw VOC value to CAQI (0-5500 scale)."""
    if measured_value_converter(value) is None:
        return None

    if value < 66:
        return "Excellent"
    elif value < 221:
        return "Good"
    elif value < 661:
        return "Moderate"
    elif value < 2201:
        return "Poor"
    else:
        return "Bad"


(
    QuirkBuilder("frient A/S", "AQSZB-110")
    .applies_to("Develco Products A/S", "AQSZB-110")
    .replaces(DevelcoVOCMeasurement, endpoint_id=38)
    .replaces(AQSZB110PowerConfiguration, endpoint_id=38)
    .sensor(
        attribute_name=DevelcoVOCMeasurement.AttributeDefs.measured_value.name,
        cluster_id=DevelcoVOCMeasurement.cluster_id,
        endpoint_id=38,
        attribute_converter=measured_value_converter,
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        state_class=SensorStateClass.MEASUREMENT,
        unit=CONCENTRATION_PARTS_PER_BILLION,
        fallback_name="VOC level",
        unique_id_suffix="voc_level",
        reporting_config=ReportingConfig(
            min_interval=30,
            max_interval=900,
            reportable_change=10,  # TVOC fluctuates a lot
        ),
    )
    .sensor(
        attribute_name=DevelcoVOCMeasurement.AttributeDefs.measured_value.name,
        cluster_id=DevelcoVOCMeasurement.cluster_id,
        endpoint_id=38,
        attribute_converter=value_to_caqi,
        device_class=SensorDeviceClass.ENUM,
        unit=None,  # No unit for enum values
        fallback_name="CAQI",
        unique_id_suffix="caqi_index",
    )
    .add_to_registry()
)
