"""SONOFF SNZB02M - Zigbee Temperature And Humidity Sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfPressure, UnitOfTemperature
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class CustomSonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        Temperature_Compensation = ZCLAttributeDef(
            name="Temperature_Compensation",
            id=0x2003,
            type=t.int16s,
            manufacturer_code=None,
        )

        Relative_Humidity_Compensation = ZCLAttributeDef(
            name="Relative_Humidity_Compensation",
            id=0x2004,
            type=t.int16s,
            manufacturer_code=None,
        )

        Pressure_Compensation = ZCLAttributeDef(
            name="Pressure_Compensation",
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
        CustomSonoffCluster.AttributeDefs.Temperature_Compensation.name,
        CustomSonoffCluster.cluster_id,
        ClusterType.Server,
        1,
        -50.0,
        50.0,
        0.1,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="Temperature_Compensation",
        device_class=NumberDeviceClass.TEMPERATURE,
        fallback_name="Temperature Compensation",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.Relative_Humidity_Compensation.name,
        CustomSonoffCluster.cluster_id,
        ClusterType.Server,
        1,
        -50.0,
        50.0,
        0.1,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="Relative_Humidity_Compensation",
        device_class=NumberDeviceClass.HUMIDITY,
        fallback_name="Relative Humidity Compensation",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.Pressure_Compensation.name,
        CustomSonoffCluster.cluster_id,
        ClusterType.Server,
        1,
        -50.0,
        50.0,
        1,
        unit=UnitOfPressure.HPA,
        multiplier=0.01,
        translation_key="Pressure_Compensation",
        device_class=NumberDeviceClass.ATMOSPHERIC_PRESSURE,
        fallback_name="Pressure Compensation",
    )
    .add_to_registry()
)
