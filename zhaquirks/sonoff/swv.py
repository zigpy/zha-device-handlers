"""Sonoff SWV - Zigbee smart water valve."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, ReportingConfig
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ValveState(t.enum8):
    """Water valve state."""

    Normal = 0
    Water_Shortage = 1
    Water_Leakage = 2
    Water_Shortage_And_Leakage = 3


class CustomSonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11
    manufacturer_id_override: t.uint16_t = foundation.ZCLHeader.NO_MANUFACTURER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        water_valve_state = ZCLAttributeDef(
            id=0x500C,
            type=ValveState,
        )


(
    QuirkBuilder("SONOFF", "SWV")
    .replaces(CustomSonoffCluster)
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        device_class=BinarySensorDeviceClass.MOISTURE,
        attribute_converter=lambda x: x & ValveState.Water_Leakage,
        unique_id_suffix="water_leak_status",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="water_leak",
        fallback_name="Water leak",
    )
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_converter=lambda x: x & ValveState.Water_Shortage,
        unique_id_suffix="water_supply_status",
        translation_key="water_supply",
        fallback_name="Water supply",
    )
    .add_to_registry()
)
