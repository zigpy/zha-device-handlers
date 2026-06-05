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
    .add_to_registry()
)
