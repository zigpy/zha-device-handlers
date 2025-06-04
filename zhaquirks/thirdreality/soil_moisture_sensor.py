"""Third Reality soil moisture sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.measurement import SoilMoisture


class ThirdRealitySoilMoistureCluster(CustomCluster):
    """Third Reality's soil moisture sensor private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        temperature_correction_fahrenheit: Final = ZCLAttributeDef(
            id=0x0033,
            type=t.int16s,
            is_manufacturer_specific=True,
        )

        temperature_correction_celsius: Final = ZCLAttributeDef(
            id=0x0031,
            type=t.int16s,
            is_manufacturer_specific=True,
        )

        humidity_correction: Final = ZCLAttributeDef(
            id=0x0032,
            type=t.int16s,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RSM0147Z")
    .replaces(ThirdRealitySoilMoistureCluster)
    .replaces(SoilMoisture)
    .number(
        attribute_name=ThirdRealitySoilMoistureCluster.AttributeDefs.temperature_correction_celsius.name,
        min_value=-10,
        max_value=10,
        multiplier=0.01,
        # unit=UnitOfTemperature.CELSIUS,
        cluster_id=ThirdRealitySoilMoistureCluster.cluster_id,
        translation_key="temperature_correction_celsius",
        fallback_name="Celsius correction",
    )
    .number(
        attribute_name=ThirdRealitySoilMoistureCluster.AttributeDefs.temperature_correction_fahrenheit.name,
        min_value=-18,
        max_value=18,
        multiplier=0.01,
        # unit=UnitOfTemperature.FAHRENHEIT,
        cluster_id=ThirdRealitySoilMoistureCluster.cluster_id,
        translation_key="temperature_correction_fahrenheit",
        fallback_name="Fahrenheit correction",
    )
    .number(
        attribute_name=ThirdRealitySoilMoistureCluster.AttributeDefs.humidity_correction.name,
        min_value=-50,
        max_value=50,
        multiplier=0.01,
        # unit=PERCENTAGE,
        cluster_id=ThirdRealitySoilMoistureCluster.cluster_id,
        translation_key="humidity_correction",
        fallback_name="Humidity correction",
    )
    .add_to_registry()
)
