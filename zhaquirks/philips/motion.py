"""Quirk for Philips motion sensors."""

from typing import Final

from zigpy.profiles import zha, zll
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    TemperatureMeasurement,
)
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.philips import PHILIPS, SIGNIFY, PhilipsOccupancySensing


class BasicCluster(CustomCluster, Basic):
    """Hue Motion Basic cluster."""

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute definitions."""

        trigger_indicator: Final = ZCLAttributeDef(
            id=0x0033, type=t.Bool, is_manufacturer_specific=True
        )




# Old Philips motion sensors (SML001, SML002) with dual endpoints
(
    QuirkBuilder(PHILIPS, "SML001")
    .applies_to(PHILIPS, "SML002")
    .replaces(replacement_cluster_class=BasicCluster, endpoint_id=2)
    .replaces(replacement_cluster_class=PhilipsOccupancySensing, endpoint_id=2)
    .add_to_registry()
)

# New Signify motion sensors (SML003, SML004) with single endpoint
(
    QuirkBuilder(SIGNIFY, "SML003")
    .applies_to(SIGNIFY, "SML004")
    .replaces(replacement_cluster_class=BasicCluster, endpoint_id=2)
    .replaces(replacement_cluster_class=PhilipsOccupancySensing, endpoint_id=2)
    .add_to_registry()
)
