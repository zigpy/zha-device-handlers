"""SONOFF SNZB02M - Zigbee Temperature And Humidity Sensor."""

import math

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfPressure, UnitOfTemperature
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster

MEASURED_VALUE_ATTR = 0x0000


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
    def _is_manuf_specific(self):  # pragma: no cover
        return False


class SonoffTemperatureCluster(CustomCluster, TemperatureMeasurement):  # pragma: no cover
    """Temperature cluster that refreshes calculated climate values."""

    def _update_attribute(self, attrid, value):
        """Update temperature and refresh derived values."""
        super()._update_attribute(attrid, value)
        if (
            attrid == self.AttributeDefs.measured_value.id
            and hasattr(self.endpoint, SonoffCalculatedClimateCluster.ep_attribute)
        ):
            self.endpoint.sonoff_calculated_climate.update_calculated_values()


class SonoffRelativeHumidityCluster(CustomCluster, RelativeHumidity):  # pragma: no cover
    """Relative humidity cluster that refreshes calculated climate values."""

    def _update_attribute(self, attrid, value):
        """Update relative humidity and refresh derived values."""
        super()._update_attribute(attrid, value)
        if (
            attrid == self.AttributeDefs.measured_value.id
            and hasattr(self.endpoint, SonoffCalculatedClimateCluster.ep_attribute)
        ):
            self.endpoint.sonoff_calculated_climate.update_calculated_values()


class SonoffCalculatedClimateCluster(LocalDataCluster):  # pragma: no cover
    """Local cluster exposing values calculated from temperature and humidity."""

    cluster_id = 0xFC12
    ep_attribute = "sonoff_calculated_climate"

    class AttributeDefs(BaseAttributeDefs):
        """Calculated attribute definitions."""

        dew_point = ZCLAttributeDef(id=0x0000, type=t.int16s)
        saturation_vapor_pressure = ZCLAttributeDef(id=0x0001, type=t.uint16_t)
        vpd = ZCLAttributeDef(id=0x0002, type=t.uint16_t)  # 新增 VPD 属性

    @classmethod
    def calculate_dew_point(cls, temperature, humidity):
        """Calculate dew point using Magnus formula.

        Args:
            temperature: Temperature in Celsius
            humidity: Relative humidity in percentage (0-100)

        Returns:
            Dew point in Celsius, or None if invalid input

        """
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
        """Calculate saturation vapor pressure using Magnus formula.

        Args:
            temperature: Temperature in Celsius

        Returns:
            Saturation vapor pressure in hPa, or None if invalid input

        """
        if temperature is None:
            return None

        try:
            return 6.112 * math.exp((17.62 * temperature) / (temperature + 243.12))
        except (ValueError, ZeroDivisionError):
            return None

    @classmethod
    def calculate_vpd(cls, temperature, humidity):
        """Calculate Vapor Pressure Deficit (VPD).

        VPD = e_sat(T) - e_actual
        where e_actual = (RH / 100) * e_sat(T)

        Args:
            temperature: Temperature in Celsius
            humidity: Relative humidity in percentage (0-100)

        Returns:
            VPD in hPa, or None if invalid input

        """
        if temperature is None or humidity is None:
            return None
        if humidity < 0 or humidity > 100:
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

        # 计算饱和水汽压
        saturation_vapor_pressure = self.calculate_saturation_vapor_pressure(
            temperature
        )
        if saturation_vapor_pressure is not None:
            self._update_attribute(
                self.AttributeDefs.saturation_vapor_pressure.id,
                round(saturation_vapor_pressure * 100),
            )

        # 计算露点
        dew_point = self.calculate_dew_point(temperature, humidity)
        if dew_point is not None:
            self._update_attribute(
                self.AttributeDefs.dew_point.id,
                round(dew_point * 100),
            )

        # 计算 VPD
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
    QuirkBuilder("SONOFF", "SNZB-02M")
    .replaces(CustomSonoffCluster)
    .replaces(SonoffTemperatureCluster)
    .replaces(SonoffRelativeHumidityCluster)
    .adds(SonoffCalculatedClimateCluster)
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
        attribute_name=SonoffCalculatedClimateCluster.AttributeDefs.vpd.name,  # 改为 vpd
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
