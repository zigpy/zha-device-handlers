"""SONOFF SNZB02P - Zigbee Temperature And Humidity Sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import (
    UnitOfTemperature,
    PERCENTAGE,
)
import zigpy.types as t
from enum import Enum
from zigpy import types
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.quirks.registry import DeviceRegistry
from zigpy.zcl import ClusterType
from zigpy.quirks.v2 import (
    BinarySensorMetadata,
    CustomDeviceV2,
    EntityMetadata,
    EntityPlatform,
    EntityType,
    NumberMetadata,
    SwitchMetadata,
    WriteAttributeButtonMetadata,
    ZCLCommandButtonMetadata,
    ZCLSensorMetadata,
    add_to_registry_v2,
)

class CustomSonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        Temperature_Compensation = ZCLAttributeDef(
            name="Temperature_Compensation",
            id=0x2003,
            type=t.int16s,
        )

        Relative_Humidity_Compensation  = ZCLAttributeDef(
            name="Relative_Humidity_Compensation",
            id=0x2004,
            type=t.int16s,
        )

    @property
    def _is_manuf_specific(self):
        return False

    
(
    QuirkBuilder("eWeLink", "SNZB-02P")
    .replaces(CustomSonoffCluster, 0xFC11, ClusterType.Server, 1)
    .number(
        CustomSonoffCluster.AttributeDefs.Temperature_Compensation.name,
        CustomSonoffCluster.cluster_id,
        ClusterType.Server,
        1,
        -50.0,
        50.0,
        0.1,
        unit = UnitOfTemperature.CELSIUS,
        multiplier = 0.01,
        translation_key = "Temperature_Compensation",
        device_class = NumberDeviceClass.TEMPERATURE,
        fallback_name = "Temperature Compensation",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.Relative_Humidity_Compensation.name,
        CustomSonoffCluster.cluster_id,
        ClusterType.Server,
        1,
        -50.0,
        50.0,
        0.1,
        unit = PERCENTAGE,
        multiplier = 0.01,
        translation_key = "Relative_Humidity_Compensation",
        device_class = NumberDeviceClass.HUMIDITY,
        fallback_name = "Relative Humidity Compensation",
    )
    .add_to_registry()
)    