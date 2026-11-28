"""Plugwise Emma 170-01 smart thermostat.

The thermostat carries OpenTherm boiler telemetry in manufacturer-specific
attributes on the Thermostat cluster (0x0201), gated by manufacturer code
0x1172. The application and OEM fault codes are the high and low byte of
OpenTherm message ID 5.
"""

from typing import Final

import zigpy.types as t
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster

PLUGWISE: Final = "Plugwise"
PLUGWISE_MFG_CODE: Final = 0x1172


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


(
    QuirkBuilder(PLUGWISE, "170-01")
    .friendly_name(manufacturer=PLUGWISE, model="Emma thermostat")
    .replaces(EmmaThermostatCluster)
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
    .add_to_registry()
)
