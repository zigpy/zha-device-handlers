"""IKEA VINDSTYRKA device."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
)
import zigpy.types as t
from zigpy.zcl.clusters.measurement import PM25  # Import the PM2.5 cluster
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.ikea import IKEA


class VOCIndex(CustomCluster):
    """IKEA VOC index cluster."""

    cluster_id: t.uint16_t = 0xFC7E
    name: str = "IKEA VOC Index"
    ep_attribute: str = "voc_index"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        measured_value: Final = ZCLAttributeDef(
            id=0x0000, type=t.Single, access="rp", is_manufacturer_specific=True
        )
        min_measured_value: Final = ZCLAttributeDef(
            id=0x0001, type=t.Single, access="r", is_manufacturer_specific=True
        )
        max_measured_value: Final = ZCLAttributeDef(
            id=0x0002, type=t.Single, access="r", is_manufacturer_specific=True
        )


class HPM25(CustomCluster, PM25):
    """PM2.5 cluster forced to override the IKEA default."""

    cluster_id = 0x042A


(
    QuirkBuilder(IKEA, "VINDSTYRKA")
    .replaces(VOCIndex)
    .sensor(
        VOCIndex.AttributeDefs.measured_value.name,
        VOCIndex.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.AQI,
        reporting_config=ReportingConfig(
            min_interval=60, max_interval=120, reportable_change=1
        ),
        translation_key="voc_index",
        fallback_name="VOC index",
    )
    .sensor(
        attribute_name="measured_value",
        cluster_id=HPM25.cluster_id,
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,
        reporting_config=ReportingConfig(
            min_interval=20,  # 20 seconds
            max_interval=120,  # 120 seconds max
            reportable_change=1,
        ),
        fallback_name="Particulate Matter 2.5",
    )
    .add_to_registry()
)
