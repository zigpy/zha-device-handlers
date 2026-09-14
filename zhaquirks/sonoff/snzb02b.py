"""Sonoff SNZB-02D、SNZB02DR2 - Zigbee LCD smart temperature humidity sensor."""

import math

import zigpy.types as t
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.builder import (
    PERCENTAGE,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfPressure,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster


MEASURED_VALUE_ATTR = 0x0000


class CustomSonoffCluster(CustomCluster):
    """Sonoff custom cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        temperature_offset = ZCLAttributeDef(
            id=0x2003,
            type=t.int16s,
            manufacturer_code=None,
        )

        humidity_offset = ZCLAttributeDef(
            id=0x2004,
            type=t.int16s,
            manufacturer_code=None,
        )


class SonoffTemperatureCluster(CustomCluster, TemperatureMeasurement):
    """Temperature cluster that refreshes calculated climate values."""

    def _update_attribute(self, attrid, value):
        """Update temperature and refresh derived values."""
        super()._update_attribute(attrid, value)
        if (
            attrid == self.AttributeDefs.measured_value.id
            and hasattr(self.endpoint, SonoffCalculatedClimateCluster.ep_attribute)
        ):
            self.endpoint.sonoff_calculated_climate.update_calculated_values()


class SonoffRelativeHumidityCluster(CustomCluster, RelativeHumidity):
    """Relative humidity cluster that refreshes calculated climate values."""

    def _update_attribute(self, attrid, value):
        """Update relative humidity and refresh derived values."""
        super()._update_attribute(attrid, value)
        if (
            attrid == self.AttributeDefs.measured_value.id
            and hasattr(self.endpoint, SonoffCalculatedClimateCluster.ep_attribute)
        ):
            self.endpoint.sonoff_calculated_climate.update_calculated_values()


class SonoffCalculatedClimateCluster(LocalDataCluster):
    """Local cluster exposing values calculated from measured temperature and humidity."""

    cluster_id = 0xFC12
    ep_attribute = "sonoff_calculated_climate"

    class AttributeDefs(BaseAttributeDefs):
        """Calculated attribute definitions."""

        dew_point = ZCLAttributeDef(id=0x0000, type=t.int16s)
        saturation_vapor_pressure = ZCLAttributeDef(id=0x0001, type=t.uint16_t)
        vpd = ZCLAttributeDef(id=0x0002, type=t.uint16_t)

    @classmethod
    def calculate_dew_point(cls, temperature, humidity):
        """Calculate dew point using the Magnus formula."""
        if temperature is None or humidity is None:
            return None
        if humidity <= 0 or humidity > 100:
            return None

        a = 17.62
        b = 243.12

        try:
            ln_rh = math.log(humidity / 100.0)
            alpha = ln_rh + (a * temperature) / (b + temperature)
            return (b * alpha) / (a - alpha)
        except (ValueError, ZeroDivisionError):
            return None

    @classmethod
    def calculate_saturation_vapor_pressure(cls, temperature):
        """Calculate saturation vapor pressure using the Magnus formula."""
        if temperature is None:
            return None

        try:
            return 6.112 * math.exp((17.62 * temperature) / (temperature + 243.12))
        except (ValueError, ZeroDivisionError):
            return None

    @classmethod
    def calculate_vpd(cls, temperature, humidity):
        """Calculate Vapor Pressure Deficit (VPD)."""
        if temperature is None or humidity is None:
            return None
        if humidity <= 0 or humidity > 100:
            return None

        e_sat = cls.calculate_saturation_vapor_pressure(temperature)
        if e_sat is None:
            return None

        e_actual = (humidity / 100.0) * e_sat
        return e_sat - e_actual

    def update_calculated_values(self):
        """Update calculated attributes from the latest measured temperature and humidity."""
        temperature = self._temperature_celsius()
        humidity = self._relative_humidity_percent()

        saturation_vapor_pressure = self.calculate_saturation_vapor_pressure(
            temperature
        )
        if saturation_vapor_pressure is not None:
            self._update_attribute(
                self.AttributeDefs.saturation_vapor_pressure.id,
                round(saturation_vapor_pressure * 100),
            )

        dew_point = self.calculate_dew_point(temperature, humidity)
        if dew_point is not None:
            self._update_attribute(
                self.AttributeDefs.dew_point.id,
                round(dew_point * 100),
            )

        vpd = self.calculate_vpd(temperature, humidity)
        if vpd is not None:
            self._update_attribute(
                self.AttributeDefs.vpd.id,
                round(vpd * 100),
            )

    def _temperature_celsius(self):
        """Return the cached measured temperature in Celsius."""
        if not hasattr(self.endpoint, "temperature"):
            return None
        value = self.endpoint.temperature._attr_cache.get(MEASURED_VALUE_ATTR)
        if value is None or value == 0x8000:
            return None
        return value / 100

    def _relative_humidity_percent(self):
        """Return the cached measured relative humidity as a percentage."""
        if not hasattr(self.endpoint, "humidity"):
            return None
        value = self.endpoint.humidity._attr_cache.get(MEASURED_VALUE_ATTR)
        if value is None or value == 0xFFFF:
            return None
        return value / 100


(
    QuirkBuilder("SONOFF", "SNZB-02B")
    .replaces(CustomSonoffCluster)
    .replaces(SonoffTemperatureCluster)
    .replaces(SonoffRelativeHumidityCluster)
    .adds(SonoffCalculatedClimateCluster)
    .number(
        CustomSonoffCluster.AttributeDefs.temperature_offset.name,
        CustomSonoffCluster.cluster_id,
        min_value=-50,
        max_value=50,
        step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE_DELTA,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="temperature_offset",
        fallback_name="Temperature offset",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.humidity_offset.name,
        CustomSonoffCluster.cluster_id,
        min_value=-50,
        max_value=50,
        step=0.1,
        device_class=NumberDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="humidity_offset",
        fallback_name="Humidity offset",
    )
    .sensor(
        attribute_name=SonoffCalculatedClimateCluster.AttributeDefs.dew_point.name,
        cluster_id=SonoffCalculatedClimateCluster.cluster_id,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="dew_point",
        fallback_name="Dew Point",
    )
    .sensor(
        attribute_name=SonoffCalculatedClimateCluster.AttributeDefs.vpd.name,
        cluster_id=SonoffCalculatedClimateCluster.cluster_id,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPressure.HPA,
        multiplier=0.01,
        translation_key="vapor_pressure_deficit",
        fallback_name="VPD",
    )
    .add_to_registry()
)
