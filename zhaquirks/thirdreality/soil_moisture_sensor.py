"""Third Reality soil moisture sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import NumberDeviceClass, QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealitySoilMoistureCluster(CustomCluster):
    """Third Reality's soil moisture sensor private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        temperature_offset_fahrenheit: Final = ZCLAttributeDef(
            id=0x0033,
            type=t.int16s,
            is_manufacturer_specific=True,
        )

        temperature_offset_celsius: Final = ZCLAttributeDef(
            id=0x0031,
            type=t.int16s,
            is_manufacturer_specific=True,
        )

        humidity_offset: Final = ZCLAttributeDef(
            id=0x0032,
            type=t.int16s,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RSM0147Z")
    .applies_to("Third Reality, Inc", "3RSM0347Z")
    .replaces(ThirdRealitySoilMoistureCluster)
    .number(
        attribute_name=ThirdRealitySoilMoistureCluster.AttributeDefs.temperature_offset_celsius.name,
        cluster_id=ThirdRealitySoilMoistureCluster.cluster_id,
        min_value=-10000,
        max_value=10000,
        multiplier=0.01,
        step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="temperature_offset",
        fallback_name="Temperature offset",
    )
    .number(
        attribute_name=ThirdRealitySoilMoistureCluster.AttributeDefs.humidity_offset.name,
        cluster_id=ThirdRealitySoilMoistureCluster.cluster_id,
        min_value=-10000,
        max_value=10000,
        multiplier=0.01,
        step=0.1,
        device_class=NumberDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        translation_key="humidity_offset",
        fallback_name="Humidity offset",
    )
    .add_to_registry()
)
