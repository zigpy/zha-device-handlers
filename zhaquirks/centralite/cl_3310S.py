"""Centralite 3310S implementation."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CENTRALITE

SMRT_THINGS_REL_HUM_CLSTR = 0xFC45


class SmartthingsRelativeHumidityCluster(CustomCluster):
    """Smart Things Relative Humidity Cluster."""

    cluster_id = SMRT_THINGS_REL_HUM_CLSTR
    name = "Smartthings Relative Humidity Measurement"
    ep_attribute = "humidity"

    class AttributeDefs(BaseAttributeDefs):
        """Cluster attributes."""

        # Relative Humidity Measurement Information
        measured_value = ZCLAttributeDef(
            id=0x0000, type=t.int16s, is_manufacturer_specific=True
        )


(
    QuirkBuilder(CENTRALITE, "3310-G")
    .applies_to(CENTRALITE, "3310-S")
    .applies_to(CENTRALITE, "3310")
    .replaces(
        replacement_cluster_class=PowerConfigurationCluster,
        cluster_id=PowerConfigurationCluster.cluster_id,
    )
    .replaces(
        replacement_cluster_class=SmartthingsRelativeHumidityCluster,
        cluster_id=SMRT_THINGS_REL_HUM_CLSTR,
    )
    .add_to_registry()
)
