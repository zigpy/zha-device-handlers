"""Third Reality temperature and humidity sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import PollControl
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityTemperatureAndHumidityCluster(CustomCluster):
    """Third Reality's temperature and humidity sensor lite private cluster."""

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
    QuirkBuilder("Third Reality, Inc", "3RTHS0224Z")
    .also_applies_to("Third Reality","3RTHS0224Z")
    .replaces(ThirdRealityTemperatureAndHumidityCluster)
    .removes(PollControl.cluster_id)
    .number(
        attribute_name=ThirdRealityTemperatureAndHumidityCluster.AttributeDefs.temperature_correction_celsius.name,
        min_value=-1000,
        max_value=1000,
        step=1,
        # unit=UnitOfTemperature.CELSIUS,
        cluster_id=ThirdRealityTemperatureAndHumidityCluster.cluster_id,
        translation_key="temperature_correction_celsius",
        fallback_name="Celsius/100",
    )
    .number(
        attribute_name=ThirdRealityTemperatureAndHumidityCluster.AttributeDefs.temperature_correction_fahrenheit.name,
        min_value=-1800,
        max_value=1800,
        step=1,
        # unit=UnitOfTemperature.FAHRENHEIT,
        cluster_id=ThirdRealityTemperatureAndHumidityCluster.cluster_id,
        translation_key="temperature_correction_fahrenheit",
        fallback_name="Fahrenheit/100",
    )
    .number(
        attribute_name=ThirdRealityTemperatureAndHumidityCluster.AttributeDefs.humidity_correction.name,
        min_value=-5000,
        max_value=5000,
        step=1,
        # unit=PERCENTAGE,
        cluster_id=ThirdRealityTemperatureAndHumidityCluster.cluster_id,
        translation_key="humidity_correction",
        fallback_name="Humidity Correction/100",
    )
    .add_to_registry()
)
