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


(
    QuirkBuilder("frient A/S", "AQSZB-110")
    .applies_to("Develco Products A/S", "AQSZB-110")
    .replaces(DevelcoVOCMeasurement, endpoint_id=38)
    .replaces(DevelcoPowerConfiguration, endpoint_id=38)
    .sensor(
        attribute_name=DevelcoVOCMeasurement.AttributeDefs.measured_value.name,
        cluster_id=DevelcoVOCMeasurement.cluster_id,
        endpoint_id=38,
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
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
    .add_to_registry()
)
