"""SONOFF SNZB02P - Zigbee Temperature And Humidity Sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class CustomSonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        TemperatureCompensation = ZCLAttributeDef(
            name="TemperatureCompensation",
            id=0x2003,
            type=t.int16s,
        )

        RelativeHumidityCompensation = ZCLAttributeDef(
            name="RelativeHumidityCompensation",
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
        "TemperatureCompensation",
        0xFC11,
        ClusterType.Server,
        1,
        -50.0,
        50.0,
        0.1,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="TemperatureCompensation",
        device_class=NumberDeviceClass.TEMPERATURE,
        fallback_name="TemperatureCompensation",
    )
    .number(
        "RelativeHumidityCompensation",
        0xFC11,
        ClusterType.Server,
        1,
        -50.0,
        50.0,
        0.1,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="RelativeHumidityCompensation",
        device_class=NumberDeviceClass.HUMIDITY,
        fallback_name="RelativeHumidityCompensation",
    )
    .add_to_registry()
)
