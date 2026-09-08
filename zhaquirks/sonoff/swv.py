"""Sonoff SWV - Zigbee smart water valve."""

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    UnitOfTime,
    UnitOfVolume,
)
from zhaquirks.clusters import CustomCluster


class ValveState(t.enum8):
    """Water valve state."""

    Normal = 0
    Water_Shortage = 1
    Water_Leakage = 2
    Water_Shortage_And_Leakage = 3


def swap_endianness_32bit(value: int) -> int:
    """Byte-swap a 32-bit integer.

    The SWV-ZFE/SWV-ZFU firmware reports the two real-time counters
    big-endian instead of ZCL little-endian, so the value zigpy parses
    must be byte-swapped (zigbee2mqtt applies the same workaround).
    """
    return int.from_bytes(int(value).to_bytes(4, "little"), "big")


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


class CustomSonoffFlowCluster(CustomSonoffCluster):
    """Custom Sonoff cluster for the flow-meter valves (SWV-ZFE/SWV-ZFU)."""

    class AttributeDefs(CustomSonoffCluster.AttributeDefs):
        """Attribute definitions."""

        real_time_irrigation_duration = ZCLAttributeDef(
            id=0x5006,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        real_time_irrigation_volume = ZCLAttributeDef(
            id=0x5007,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        hour_irrigation_volume = ZCLAttributeDef(
            id=0x501B,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        hour_irrigation_duration = ZCLAttributeDef(
            id=0x501C,
            type=t.uint32_t,
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


(
    QuirkBuilder("SONOFF", "SWV-ZFE")
    .also_applies_to("SONOFF", "SWV-ZFU")
    .replaces(CustomSonoffFlowCluster)
    .binary_sensor(
        CustomSonoffFlowCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffFlowCluster.cluster_id,
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
        CustomSonoffFlowCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffFlowCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_converter=lambda x: x & ValveState.Water_Shortage,
        unique_id_suffix="water_supply_status",
        translation_key="water_supply",
        fallback_name="Water supply",
    )
    .sensor(
        CustomSonoffFlowCluster.AttributeDefs.real_time_irrigation_volume.name,
        CustomSonoffFlowCluster.cluster_id,
        suggested_display_precision=0,
        device_class=SensorDeviceClass.VOLUME,
        unit=UnitOfVolume.LITERS,
        attribute_converter=swap_endianness_32bit,
        translation_key="real_time_irrigation_volume",
        fallback_name="Real-time irrigation volume",
    )
    .sensor(
        CustomSonoffFlowCluster.AttributeDefs.real_time_irrigation_duration.name,
        CustomSonoffFlowCluster.cluster_id,
        suggested_display_precision=0,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        attribute_converter=swap_endianness_32bit,
        translation_key="real_time_irrigation_duration",
        fallback_name="Real-time irrigation duration",
    )
    .sensor(
        CustomSonoffFlowCluster.AttributeDefs.hour_irrigation_volume.name,
        CustomSonoffFlowCluster.cluster_id,
        suggested_display_precision=0,
        device_class=SensorDeviceClass.VOLUME,
        unit=UnitOfVolume.LITERS,
        translation_key="hour_irrigation_volume",
        fallback_name="Hourly irrigation volume",
    )
    .sensor(
        CustomSonoffFlowCluster.AttributeDefs.hour_irrigation_duration.name,
        CustomSonoffFlowCluster.cluster_id,
        suggested_display_precision=0,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        translation_key="hour_irrigation_duration",
        fallback_name="Hourly irrigation duration",
    )
    .add_to_registry()
)
