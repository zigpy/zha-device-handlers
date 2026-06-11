"""SONOFF SNZB02M - Zigbee Temperature And Humidity Sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import NumberDeviceClass, QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfPressure, UnitOfTemperature
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class CustomSonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        temperature_compensation = ZCLAttributeDef(
            id=0x2003,
            type=t.int16s,
            manufacturer_code=None,
        )

        relative_humidity_compensation = ZCLAttributeDef(
            id=0x2004,
            type=t.int16s,
            manufacturer_code=None,
        )

        pressure_compensation = ZCLAttributeDef(
            id=0x2007,
            type=t.int16s,
            manufacturer_code=None,
        )

    @property
    def _is_manuf_specific(self):
        return False


(
    QuirkBuilder("SONOFF", "SNZB-02M")
    .replaces(CustomSonoffCluster, 0xFC11, ClusterType.Server, 1)
    .number(
        CustomSonoffCluster.AttributeDefs.temperature_compensation.name,
        CustomSonoffCluster.cluster_id,
        ClusterType.Server,
        1,
        -50.0,
        50.0,
        0.1,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="temperature_compensation",
        device_class=NumberDeviceClass.TEMPERATURE,
        fallback_name="Temperature compensation",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.relative_humidity_compensation.name,
        CustomSonoffCluster.cluster_id,
        ClusterType.Server,
        1,
        -50.0,
        50.0,
        0.1,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="relative_humidity_compensation",
        device_class=NumberDeviceClass.HUMIDITY,
        fallback_name="Relative humidity compensation",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.pressure_compensation.name,
        CustomSonoffCluster.cluster_id,
        ClusterType.Server,
        1,
        -50.0,
        50.0,
        1,
        unit=UnitOfPressure.HPA,
        multiplier=0.01,
        translation_key="pressure_compensation",
        device_class=NumberDeviceClass.ATMOSPHERIC_PRESSURE,
        fallback_name="Pressure compensation",
    )
    .add_to_registry()
)
