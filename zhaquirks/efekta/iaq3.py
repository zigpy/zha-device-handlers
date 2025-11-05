"""Quirk for EfektaLab EFEKTA_iAQ3 air quality sensor."""

from __future__ import annotations

import logging
from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityType, NumberDeviceClass, QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.general import AnalogInput
from zigpy.zcl.clusters.measurement import (
    CarbonDioxideConcentration,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster

_LOGGER = logging.getLogger(__name__)

MEASURED_VALUE = 0x0000


class DisplayRotation(t.enum16):
    """Display rotation options."""

    Degrees_0 = 0
    Degrees_90 = 90
    Degrees_180 = 180
    Degrees_270 = 270


class TemperatureMeasurementConfig(CustomCluster, TemperatureMeasurement):
    """Temperature measurement cluster with calibration offset."""

    cluster_id = TemperatureMeasurement.cluster_id

    class AttributeDefs(TemperatureMeasurement.AttributeDefs):
        """Attribute definitions."""

        temperature_offset: Final = ZCLAttributeDef(
            id=0x0210, type=t.int16s, access="rw"
        )


class RelativeHumidityConfig(CustomCluster, RelativeHumidity):
    """Relative humidity cluster with calibration offset."""

    cluster_id = RelativeHumidity.cluster_id

    class AttributeDefs(RelativeHumidity.AttributeDefs):
        """Attribute definitions."""

        humidity_offset: Final = ZCLAttributeDef(id=0x0210, type=t.int16s, access="rw")


class CO2ConcentrationConfig(CustomCluster, CarbonDioxideConcentration):
    """CO2 concentration cluster with configuration attributes."""

    cluster_id = CarbonDioxideConcentration.cluster_id

    class AttributeDefs(CarbonDioxideConcentration.AttributeDefs):
        """Attribute definitions."""

        # CO2 sensor settings
        forced_recalibration: Final = ZCLAttributeDef(
            id=0x0202, type=t.Bool, access="rw"
        )
        auto_brightness: Final = ZCLAttributeDef(id=0x0203, type=t.Bool, access="rw")
        long_chart_period: Final = ZCLAttributeDef(id=0x0204, type=t.Bool, access="rw")
        set_altitude: Final = ZCLAttributeDef(id=0x0205, type=t.uint16_t, access="rw")
        factory_reset_co2: Final = ZCLAttributeDef(id=0x0206, type=t.Bool, access="rw")
        manual_forced_recalibration: Final = ZCLAttributeDef(
            id=0x0207, type=t.uint16_t, access="rw"
        )

        # CO2 gas control settings
        enable_co2: Final = ZCLAttributeDef(id=0x0220, type=t.Bool, access="rw")
        high_co2: Final = ZCLAttributeDef(id=0x0221, type=t.uint16_t, access="rw")
        low_co2: Final = ZCLAttributeDef(id=0x0222, type=t.uint16_t, access="rw")
        invert_logic_co2: Final = ZCLAttributeDef(id=0x0225, type=t.Bool, access="rw")

        # Display settings
        rotate: Final = ZCLAttributeDef(id=0x0285, type=t.uint16_t, access="rw")
        internal_or_external: Final = ZCLAttributeDef(
            id=0x0288, type=t.Bool, access="rw"
        )
        night_onoff_backlight: Final = ZCLAttributeDef(
            id=0x0401, type=t.Bool, access="rw"
        )
        automatic_scal: Final = ZCLAttributeDef(id=0x0402, type=t.Bool, access="rw")
        long_chart_period2: Final = ZCLAttributeDef(id=0x0404, type=t.Bool, access="rw")
        night_on_backlight: Final = ZCLAttributeDef(
            id=0x0405, type=t.uint8_t, access="rw"
        )
        night_off_backlight: Final = ZCLAttributeDef(
            id=0x0406, type=t.uint8_t, access="rw"
        )


class AnalogInputCluster(CustomCluster, AnalogInput):
    """Analog input cluster that relays VOC index to emulated VOC measurement cluster."""

    cluster_id = AnalogInput.cluster_id
    PRESENT_VALUE = 0x0055

    def _update_attribute(self, attrid, value):
        """Intercept present_value updates and relay to VOC cluster."""
        super()._update_attribute(attrid, value)
        if attrid == self.PRESENT_VALUE and value is not None:
            self.endpoint.voc_level._update_attribute(MEASURED_VALUE, value)


class EmulatedVOCMeasurement(LocalDataCluster):
    """VOC measurement cluster that receives relayed data from AnalogInput cluster.

    This cluster emulates a standard VOC Level cluster (0x042E) to expose
    VOC index readings from the device's AnalogInput cluster to Home Assistant.
    Using device_class=AQI ensures the value displays as dimensionless (0-500).
    """

    cluster_id = 0x042E  # Standard VOC Level cluster
    name = "VOC Level"
    ep_attribute = "voc_level"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        measured_value: Final = ZCLAttributeDef(
            id=MEASURED_VALUE, type=t.Single, access="rp"
        )

    async def bind(self):
        """Bind cluster and configure reporting on the physical AnalogInput cluster."""
        result = await self.endpoint.analog_input.bind()
        await self.endpoint.analog_input.configure_reporting(
            AnalogInputCluster.PRESENT_VALUE,
            30,  # min_interval: 30 seconds
            600,  # max_interval: 10 minutes
            1.0,  # reportable_change: 1 unit
        )
        return result


(
    QuirkBuilder("EfektaLab", "EFEKTA_iAQ3")
    # Replace standard clusters with config-enabled versions
    .replaces(TemperatureMeasurementConfig, endpoint_id=1)
    .replaces(RelativeHumidityConfig, endpoint_id=1)
    .replaces(CO2ConcentrationConfig, endpoint_id=1)
    # VOC sensor support (Endpoint 2)
    .replaces(AnalogInputCluster, endpoint_id=2)
    .adds(EmulatedVOCMeasurement, endpoint_id=2)
    # VOC sensor entity
    .sensor(
        EmulatedVOCMeasurement.AttributeDefs.measured_value.name,
        EmulatedVOCMeasurement.cluster_id,
        endpoint_id=2,
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="voc_index",
        fallback_name="VOC index",
    )
    # Temperature/Humidity offset configuration
    .number(
        TemperatureMeasurementConfig.AttributeDefs.temperature_offset.name,
        TemperatureMeasurementConfig.cluster_id,
        endpoint_id=1,
        min_value=-500,
        max_value=500,
        step=1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_offset",
        fallback_name="Temperature offset",
    )
    .number(
        RelativeHumidityConfig.AttributeDefs.humidity_offset.name,
        RelativeHumidityConfig.cluster_id,
        endpoint_id=1,
        min_value=-50,
        max_value=50,
        step=1,
        unit=PERCENTAGE,
        device_class=NumberDeviceClass.HUMIDITY,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_offset",
        fallback_name="Humidity offset",
    )
    # CO2 sensor settings
    .number(
        CO2ConcentrationConfig.AttributeDefs.set_altitude.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=3000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="set_altitude",
        fallback_name="Altitude above sea level",
    )
    .number(
        CO2ConcentrationConfig.AttributeDefs.manual_forced_recalibration.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=5000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="manual_forced_recalibration",
        fallback_name="Manual CO2 calibration (ppm)",
    )
    .switch(
        CO2ConcentrationConfig.AttributeDefs.forced_recalibration.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="forced_recalibration",
        fallback_name="Force CO2 recalibration",
    )
    .switch(
        CO2ConcentrationConfig.AttributeDefs.factory_reset_co2.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="factory_reset_co2",
        fallback_name="Factory reset CO2 sensor",
    )
    .switch(
        CO2ConcentrationConfig.AttributeDefs.automatic_scal.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="automatic_scal",
        fallback_name="Automatic CO2 calibration",
    )
    # Display settings
    # Use internal temperature/humidity sensor for display if ON, external if OFF
    .switch(
        CO2ConcentrationConfig.AttributeDefs.internal_or_external.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="internal_or_external",
        fallback_name="Use internal TH sensor",
        off_value=0,
        on_value=1,
    )
    .enum(
        CO2ConcentrationConfig.AttributeDefs.rotate.name,
        DisplayRotation,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="rotate",
        fallback_name="Display rotation",
    )
    .switch(
        CO2ConcentrationConfig.AttributeDefs.auto_brightness.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="auto_brightness",
        fallback_name="Automatic brightness",
    )
    .switch(
        CO2ConcentrationConfig.AttributeDefs.night_onoff_backlight.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="night_onoff_backlight",
        fallback_name="Night mode backlight off",
    )
    .number(
        CO2ConcentrationConfig.AttributeDefs.night_on_backlight.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=23,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="night_on_backlight",
        fallback_name="Night mode start hour",
    )
    .number(
        CO2ConcentrationConfig.AttributeDefs.night_off_backlight.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=23,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="night_off_backlight",
        fallback_name="Night mode end hour",
    )
    # Chart period settings (OFF=1H, ON=24H)
    .switch(
        CO2ConcentrationConfig.AttributeDefs.long_chart_period.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="long_chart_period",
        fallback_name="CO2 chart period 24H",
        off_value=0,
        on_value=1,
    )
    .switch(
        CO2ConcentrationConfig.AttributeDefs.long_chart_period2.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="long_chart_period2",
        fallback_name="VOC chart period 24H",
        off_value=0,
        on_value=1,
    )
    # CO2 gas/relay control settings
    .switch(
        CO2ConcentrationConfig.AttributeDefs.enable_co2.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="enable_co2",
        fallback_name="Enable CO2-based relay control",
    )
    .switch(
        CO2ConcentrationConfig.AttributeDefs.invert_logic_co2.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="invert_logic_co2",
        fallback_name="Invert CO2 relay logic",
    )
    .number(
        CO2ConcentrationConfig.AttributeDefs.high_co2.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        min_value=400,
        max_value=5000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="high_co2",
        fallback_name="CO2 high threshold (ppm)",
    )
    .number(
        CO2ConcentrationConfig.AttributeDefs.low_co2.name,
        CO2ConcentrationConfig.cluster_id,
        endpoint_id=1,
        min_value=400,
        max_value=5000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="low_co2",
        fallback_name="CO2 low threshold (ppm)",
    )
    .add_to_registry()
)
