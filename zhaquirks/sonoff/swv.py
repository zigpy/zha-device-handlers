"""Sonoff SWV - Zigbee smart water valve."""

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import BinarySensorDeviceClass, QuirkBuilder, ReportingConfig
from zhaquirks.clusters import CustomCluster


class ValveState(t.enum8):
    """Water valve state."""

    Normal = 0
    Water_Shortage = 1
    Water_Leakage = 2
    Water_Shortage_And_Leakage = 3


class CustomSonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        water_valve_state = ZCLAttributeDef(
            id=0x500C,
            type=ValveState,
            manufacturer_code=None,
        )

        auto_close_water_shortage = ZCLAttributeDef(
            id=0x5011,
            type=t.uint16_t,
            manufacturer_code=None,
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
    .switch(
        CustomSonoffCluster.AttributeDefs.auto_close_water_shortage.name,
        CustomSonoffCluster.cluster_id,
        off_value=0,
        on_value=30,
        translation_key="water_shortage_auto_close",
        fallback_name="Water shortage auto-close",
    )
    .add_to_registry()
)
