"""Third Reality temperature and humidity sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import NumberDeviceClass, QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature
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
    .replaces(ThirdRealityTemperatureAndHumidityCluster)
    .removes(PollControl.cluster_id)
    .number(
        attribute_name=ThirdRealityTemperatureAndHumidityCluster.AttributeDefs.temperature_correction_celsius.name,
        cluster_id=ThirdRealityTemperatureAndHumidityCluster.cluster_id,
        min_value=-10000,
        max_value=10000,
        multiplier=0.01,
        step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="temperature_correction_celsius",
        fallback_name="Celsius correction",
    )
    .number(
        attribute_name=ThirdRealityTemperatureAndHumidityCluster.AttributeDefs.temperature_correction_fahrenheit.name,
        cluster_id=ThirdRealityTemperatureAndHumidityCluster.cluster_id,
        min_value=-10000,
        max_value=10000,
        multiplier=0.01,
        step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.FAHRENHEIT,
        translation_key="temperature_correction_fahrenheit",
        fallback_name="Fahrenheit correction",
    )
    .number(
        attribute_name=ThirdRealityTemperatureAndHumidityCluster.AttributeDefs.humidity_correction.name,
        cluster_id=ThirdRealityTemperatureAndHumidityCluster.cluster_id,
        min_value=-10000,
        max_value=10000,
        multiplier=0.01,
        step=0.1,
        device_class=NumberDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        translation_key="humidity_correction",
        fallback_name="Humidity Correction",
    )
    .add_to_registry()
)
