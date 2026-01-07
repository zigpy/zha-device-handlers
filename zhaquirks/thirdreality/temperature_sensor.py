"""Third Reality temperature and humidity sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import NumberDeviceClass, QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature
import zigpy.types as t
from zigpy.zcl.clusters.general import PollControl
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityCluster(CustomCluster):
    """Third Reality's temperature and humidity sensor private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

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

        # intentionally not exposed as an entity
        temperature_offset_fahrenheit: Final = ZCLAttributeDef(
            id=0x0033,
            type=t.int16s,
            is_manufacturer_specific=True,
        )


base_quirk = (
    QuirkBuilder()
    .replaces(ThirdRealityCluster)
    .number(
        attribute_name=ThirdRealityCluster.AttributeDefs.temperature_offset_celsius.name,
        cluster_id=ThirdRealityCluster.cluster_id,
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
        attribute_name=ThirdRealityCluster.AttributeDefs.humidity_offset.name,
        cluster_id=ThirdRealityCluster.cluster_id,
        min_value=-10000,
        max_value=10000,
        multiplier=0.01,
        step=0.1,
        device_class=NumberDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        translation_key="humidity_offset",
        fallback_name="Humidity offset",
    )
)

(
    base_quirk.clone()
    .applies_to("Third Reality, Inc", "3RTHS24BZ")
    .add_to_registry()
)  # fmt: skip

(
    base_quirk.clone()
    .applies_to("Third Reality, Inc", "3RTHS0224Z")
    .removes(PollControl.cluster_id)
    .add_to_registry()
)
