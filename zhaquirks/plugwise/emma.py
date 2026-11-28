"""Plugwise Emma 170-01 smart thermostat.

The thermostat carries OpenTherm boiler telemetry in manufacturer-specific
attributes on the Thermostat cluster (0x0201), gated by manufacturer code
0x1172. The application and OEM fault codes are the high and low byte of
OpenTherm message ID 5. All temperatures are in hundredths of a degree.

External heat demand overrides the boiler water setpoint until the timeout
expires. The two maximum setpoints read 0 until the boiler has reported them
over OpenTherm, and writing them requires the boiler to allow external control.
"""

from typing import Final

import zigpy.types as t
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster

PLUGWISE: Final = "Plugwise"
PLUGWISE_MFG_CODE: Final = 0x1172


class EmmaBatteryType(t.enum8):
    """Battery chemistry the thermostat is running on."""

    Alkaline = 0x00
    NiMH = 0x01


class EmmaApplicationFaultCode(t.bitmap8):
    """OpenTherm application fault bits, the high byte of OpenTherm message ID 5."""

    ServiceRequest = 0b0000_0001
    LockoutReset = 0b0000_0010
    LowWaterPressure = 0b0000_0100
    GasFlameFault = 0b0000_1000
    AirPressureFault = 0b0001_0000
    WaterOverTemp = 0b0010_0000


class EmmaThermostatCluster(CustomCluster, Thermostat):
    """Thermostat cluster with the Emma OpenTherm telemetry attributes."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Thermostat attributes plus the Emma manufacturer-specific ones."""

        boiler_water_temperature: Final = ZCLAttributeDef(
            id=0xF002,
            type=t.int16s,
            access="rp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        dhw_temperature: Final = ZCLAttributeDef(
            id=0xF003,
            type=t.int16s,
            access="rp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        return_water_temperature: Final = ZCLAttributeDef(
            id=0xF004,
            type=t.int16s,
            access="rp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        application_fault_code: Final = ZCLAttributeDef(
            id=0xF005,
            type=EmmaApplicationFaultCode,
            access="rp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        oem_fault_code: Final = ZCLAttributeDef(
            id=0xF006,
            type=t.uint8_t,
            access="rp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        external_heat_demand: Final = ZCLAttributeDef(
            id=0xF000,
            type=t.uint16_t,
            access="rwp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        external_heat_demand_timeout: Final = ZCLAttributeDef(
            id=0xF001,
            type=t.uint16_t,
            access="rwp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        max_dhw_setpoint: Final = ZCLAttributeDef(
            id=0xF007,
            type=t.int16s,
            access="rwp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        max_boiler_setpoint: Final = ZCLAttributeDef(
            id=0xF008,
            type=t.int16s,
            access="rwp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )


class EmmaPowerConfigCluster(CustomCluster, PowerConfiguration):
    """Power Configuration cluster with the Emma battery type attribute."""

    class AttributeDefs(PowerConfiguration.AttributeDefs):
        """Power Configuration attributes plus the Emma battery type."""

        battery_type: Final = ZCLAttributeDef(
            id=0x007F,
            type=EmmaBatteryType,
            access="rwp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )


(
    QuirkBuilder(PLUGWISE, "170-01")
    .friendly_name(manufacturer=PLUGWISE, model="Emma thermostat")
    .replaces(EmmaThermostatCluster)
    .replaces(EmmaPowerConfigCluster)
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.boiler_water_temperature.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        divisor=100,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="boiler_water_temperature",
        fallback_name="Boiler water temperature",
    )
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.dhw_temperature.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        divisor=100,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="dhw_temperature",
        fallback_name="DHW temperature",
    )
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.return_water_temperature.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        divisor=100,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="return_water_temperature",
        fallback_name="Return water temperature",
    )
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.application_fault_code.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="application_fault_code",
        fallback_name="Application fault code",
    )
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.oem_fault_code.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="oem_fault_code",
        fallback_name="OEM fault code",
    )
    .number(
        attribute_name=EmmaThermostatCluster.AttributeDefs.external_heat_demand.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        min_value=0.0,
        max_value=90.0,
        step=0.5,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="external_heat_demand",
        fallback_name="External heat demand",
    )
    .number(
        attribute_name=EmmaThermostatCluster.AttributeDefs.external_heat_demand_timeout.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        min_value=300,
        max_value=3600,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="external_heat_demand_timeout",
        fallback_name="External heat demand timeout",
    )
    .number(
        attribute_name=EmmaThermostatCluster.AttributeDefs.max_dhw_setpoint.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        min_value=0.0,
        max_value=100.0,
        step=0.5,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="max_dhw_setpoint",
        fallback_name="Max DHW setpoint",
    )
    .number(
        attribute_name=EmmaThermostatCluster.AttributeDefs.max_boiler_setpoint.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        min_value=0.0,
        max_value=100.0,
        step=0.5,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="max_boiler_setpoint",
        fallback_name="Max boiler setpoint",
    )
    .enum(
        attribute_name=EmmaPowerConfigCluster.AttributeDefs.battery_type.name,
        enum_class=EmmaBatteryType,
        cluster_id=EmmaPowerConfigCluster.cluster_id,
        translation_key="battery_type",
        fallback_name="Battery type",
    )
    .add_to_registry()
)
