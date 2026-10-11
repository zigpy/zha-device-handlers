"""Shelly Ecowitt WS90 weather station: wind, UV and rain, plus calculated values.

Based on the upstream zhaquirks/shelly/ecowitt_ws90.py (same clusters, attribute names
and entity names, so the entity unique IDs stay the same), extended with:

- sensors calculated from the measurements (dew point, humidex, wind chill, apparent
  temperature, heat stress, rain rate, pressure trend and weather condition), ported
  from the Zigbee2MQTT converter so both stacks give the same values
- non-value markers and the all-zero frames the station sometimes sends are dropped
  before they reach the cache and the calculations
- the pressure only changes by more than 1 hPa (the station flips between two whole
  hPa values on every report), and the pressure trend is a fitted line through the
  readings of the last 3 hours instead of a difference of two flipping values
- battery voltage and the solar capacitor voltage (battery 2 voltage)
"""

from __future__ import annotations

from collections import deque
import enum
import math
import time
from typing import Any

from zigpy import types as t
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    PressureMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.builder import (
    DEGREE,
    PERCENTAGE,
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricPotential,
    UnitOfPrecipitationDepth,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolumetricFlux,
)
from zhaquirks.clusters import CustomCluster
from zhaquirks.shelly import SHELLY_MANUFACTURER_CODE

# ZCL non-value markers (all bits set) the station reports when a reading is unavailable
NON_VALUE_UINT8 = 0xFF
NON_VALUE_UINT16 = 0xFFFF
NON_VALUE_UINT24 = 0xFFFFFF

# Calculated attributes are stored as integers in tenths
CALCULATED_SCALE = 10

# Rain rate is capped like in Zigbee2MQTT (mm/h)
RAIN_RATE_MAX = 300
# A rain rate needs at least a minute between two precipitation samples
RAIN_RATE_MIN_INTERVAL = 60
# The pressure comes in whole hPa and flips by 1 hPa between reports, so the published
# pressure ignores changes of this size or less (in hPa)
PRESSURE_DEAD_BAND = 1
# The pressure trend is the least squares slope over all readings of this window (s),
# which averages the flipping out. It needs this much history and this many readings
# before it moves, and is recalculated at most this often (s)
PRESSURE_TREND_WINDOW = 3 * 3600
PRESSURE_TREND_MIN_SPAN = 30 * 60
PRESSURE_TREND_MIN_SAMPLES = 6
PRESSURE_TREND_UPDATE_INTERVAL = 5 * 60

# Weather conditions, named like the Home Assistant weather entity conditions. The
# value is what is stored in the attribute, the name is the state of the enum sensor
WeatherCondition = enum.Enum(
    "WeatherCondition",
    {
        "sunny": 0,
        "clear-night": 1,
        "partlycloudy": 2,
        "cloudy": 3,
        "rainy": 4,
        "pouring": 5,
        "snowy": 6,
        "hail": 7,
        "windy": 8,
        "windy-variant": 9,
    },
)


def _round1(value: float) -> float:
    """Round to one decimal, halves up like Math.round in Zigbee2MQTT."""
    return math.floor(value * 10 + 0.5) / 10


def illuminance_lux(measured_value: int) -> int:
    """Convert the ZCL illuminance measured value to lux."""
    if measured_value <= 0:
        return 0
    return round(10 ** ((measured_value - 1) / 10000))


def calculate_dew_point(temp: float, humidity: float) -> float | None:
    """Dew point in °C (Magnus formula)."""
    if humidity <= 0:
        return None
    a = 17.27
    b = 237.7
    alpha = (a * temp) / (b + temp) + math.log(humidity / 100)
    return _round1((b * alpha) / (a - alpha))


def calculate_humidex(temp: float, humidity: float) -> float | None:
    """Humidex in °C (feels-like for warm and humid conditions)."""
    dew_point = calculate_dew_point(temp, humidity)
    if dew_point is None:
        return None
    ee = 6.11 * math.exp(5417.753 * (1 / 273.15 - 1 / (273.15 + dew_point)))
    return _round1(temp + 0.5555 * (ee - 10))


def calculate_wind_chill(temp: float, wind_ms: float) -> float:
    """Wind chill in °C, only below 10 °C and above 4.8 km/h wind, else the temperature."""
    wind_kmh = wind_ms * 3.6
    if temp > 10 or wind_kmh < 4.8:
        return _round1(temp)
    return _round1(
        13.12 + 0.6215 * temp - 11.37 * wind_kmh**0.16 + 0.3965 * temp * wind_kmh**0.16
    )


def calculate_apparent_temperature(
    temp: float, humidity: float | None, wind_ms: float | None
) -> float:
    """Apparent temperature in °C: wind chill when colder, humidex when warmer."""
    wind_chill = calculate_wind_chill(temp, wind_ms) if wind_ms is not None else None
    humidex = calculate_humidex(temp, humidity) if humidity is not None else None
    if wind_chill is not None and wind_chill < temp:
        return wind_chill
    if humidex is not None and humidex > temp:
        return humidex
    return _round1(temp)


def calculate_heat_stress(
    temp: float,
    humidity: float | None,
    lux: float | None,
    wind_ms: float | None,
    raining: bool,
) -> int:
    """Heat stress in percent (0 to 100), a sigmoid over temperature, humidity, sun, wind and rain.

    Rain takes 3 degrees off while the station reports it is raining. (Zigbee2MQTT
    passes the cumulative precipitation counter here, which made it always apply.)
    """
    solar = (lux or 0) / 100
    base = temp + solar / 100 + (humidity or 0) / 10
    cooled = base - (wind_ms or 0) / 2
    adjusted = cooled - (3 if raining else 0)
    scaled = (adjusted - 18) / (42 - 18)
    sigmoid = 1 / (1 + math.e ** (-4 * (scaled - 0.5)))
    return max(math.floor(sigmoid * 100 + 0.5), 0)


def calculate_weather_condition(
    *,
    temp: float | None,
    lux: float,
    raining: bool,
    wind_ms: float | None,
    rain_rate: float | None,
    pressure: float | None,
    pressure_trend: float | None,
) -> enum.Enum:
    """Weather condition from the measurements (same rules as Zigbee2MQTT)."""
    rate = rain_rate or 0
    is_raining = raining and rate > 0
    is_pouring = is_raining and rate > 10
    is_windy = wind_ms is not None and wind_ms > 10
    is_night = lux < 10

    is_low_pressure = pressure is not None and pressure < 1000
    is_pressure_falling = pressure_trend is not None and pressure_trend < -2

    is_hail = (
        is_raining
        and rate > 5
        and lux < 5000
        and wind_ms is not None
        and wind_ms > 5
        and (is_low_pressure or is_pressure_falling)
    )
    is_snowing = is_raining and temp is not None and temp < 1 and not is_hail

    if is_hail:
        return WeatherCondition["hail"]
    if is_snowing:
        return WeatherCondition["snowy"]
    if is_pouring:
        return WeatherCondition["pouring"]
    if is_raining:
        return WeatherCondition["rainy"]

    if is_night:
        return (
            WeatherCondition["windy"] if is_windy else WeatherCondition["clear-night"]
        )

    if lux > 40000:
        return WeatherCondition["windy"] if is_windy else WeatherCondition["sunny"]
    if lux > 10000:
        return (
            WeatherCondition["windy-variant"]
            if is_windy
            else WeatherCondition["partlycloudy"]
        )
    return WeatherCondition["cloudy"]


class ShellyWS90CalculatedCluster(LocalDataCluster):
    """Local cluster holding the values calculated from the station measurements."""

    cluster_id = 0xFC80
    name = "Shelly WS90 Calculated Cluster"
    ep_attribute = "shelly_ws90_calculated"

    class AttributeDefs(BaseAttributeDefs):
        """Calculated attribute definitions, temperatures and rates in tenths."""

        dew_point = ZCLAttributeDef(id=0x0000, type=t.int16s, access="rp")
        humidex = ZCLAttributeDef(id=0x0001, type=t.int16s, access="rp")
        wind_chill = ZCLAttributeDef(id=0x0002, type=t.int16s, access="rp")
        apparent_temperature = ZCLAttributeDef(id=0x0003, type=t.int16s, access="rp")
        heat_stress = ZCLAttributeDef(id=0x0004, type=t.uint8_t, access="rp")
        rain_rate = ZCLAttributeDef(id=0x0005, type=t.uint16_t, access="rp")
        pressure_trend = ZCLAttributeDef(id=0x0006, type=t.int16s, access="rp")
        weather_condition = ZCLAttributeDef(id=0x0007, type=t.uint8_t, access="rp")

    # These two need history that is gone after a restart, so they read 0 until it is built
    _DEFAULT_VALUES = {
        AttributeDefs.rain_rate.id: 0,
        AttributeDefs.pressure_trend.id: 0,
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init, the sampling histories only live as long as the cluster."""
        super().__init__(*args, **kwargs)
        self._precipitation_history: tuple[float, float] | None = None
        self._pressure_samples: deque[tuple[float, float]] = deque()
        self._last_trend_update: float | None = None

    def _input(self, ep_attribute: str, attribute_name: str) -> Any:
        """Read a cached value of a sibling cluster."""
        cluster = getattr(self.endpoint, ep_attribute, None)
        if cluster is None:
            return None
        return cluster.get(attribute_name)

    def _calculated(self, attribute_name: str) -> float | None:
        """Read a cached calculated value in its real unit."""
        value = self.get(attribute_name)
        if value is None:
            return None
        return value / CALCULATED_SCALE

    def _set(
        self, attribute_name: str, value: float | None, scale: int = CALCULATED_SCALE
    ) -> None:
        """Store a calculated value as an integer, in tenths unless `scale` says otherwise."""
        if value is None:
            return
        self._update_attribute(
            self.find_attribute(attribute_name).id, round(value * scale)
        )

    def _update_rain_rate(self, precipitation: float) -> None:
        """Rain rate in mm/h from the precipitation counter, sampled at least a minute apart."""
        now = time.monotonic()
        history = self._precipitation_history

        if history is None:
            # No history after a restart: the rate stays as it is until the next sample
            self._precipitation_history = (precipitation, now)
            return

        last_value, last_time = history
        elapsed = now - last_time
        if elapsed < RAIN_RATE_MIN_INTERVAL:
            return

        self._precipitation_history = (precipitation, now)
        delta = precipitation - last_value
        if delta < 0:
            # The counter was reset (battery change, restart), start over on the new counter
            self._set("rain_rate", 0)
            return

        rate = delta / (elapsed / 3600)
        self._set("rain_rate", min(_round1(rate), RAIN_RATE_MAX))

    def add_pressure_sample(self, pressure: float) -> None:
        """Add a pressure reading to the trend, also one the published pressure ignores."""
        now = time.monotonic()
        samples = self._pressure_samples
        samples.append((now, pressure))
        while samples[0][0] < now - PRESSURE_TREND_WINDOW:
            samples.popleft()

        if (
            self._last_trend_update is not None
            and now - self._last_trend_update < PRESSURE_TREND_UPDATE_INTERVAL
        ):
            return
        self._last_trend_update = now
        self._update_pressure_trend()
        self.recalculate("pressure_trend")

    def _update_pressure_trend(self) -> None:
        """Pressure trend in hPa/h, the slope of a line fitted through the recent readings."""
        samples = self._pressure_samples
        if (
            len(samples) < PRESSURE_TREND_MIN_SAMPLES
            or samples[-1][0] - samples[0][0] < PRESSURE_TREND_MIN_SPAN
        ):
            # Not enough history yet, also right after a restart: the trend stays as it is
            return

        count = len(samples)
        mean_time = sum(moment for moment, _ in samples) / count
        mean_pressure = sum(pressure for _, pressure in samples) / count
        spread = sum((moment - mean_time) ** 2 for moment, _ in samples)
        if spread == 0:
            return
        slope = (
            sum(
                (moment - mean_time) * (pressure - mean_pressure)
                for moment, pressure in samples
            )
            / spread
        )
        self._set("pressure_trend", _round1(slope * 3600))

    def _readings(self) -> dict[str, float | bool | None]:
        """Return the cached readings in real units, None for the ones not seen yet."""
        temp_raw = self._input("temperature", "measured_value")
        humidity_raw = self._input("humidity", "measured_value")
        pressure_raw = self._input("pressure", "measured_value")
        illuminance_raw = self._input("illuminance", "measured_value")
        wind_raw = self._input("shelly_wind_cluster", "wind_speed")
        precipitation_raw = self._input("shelly_rain_cluster", "precipitation")
        return {
            "temp": None if temp_raw is None else temp_raw / 100,
            "humidity": None if humidity_raw is None else humidity_raw / 100,
            # The ZCL pressure measured value is in units of 0.1 kPa, which is 1 hPa
            "pressure": None if pressure_raw is None else float(pressure_raw),
            "lux": None
            if illuminance_raw is None
            else illuminance_lux(illuminance_raw),
            "wind": None if wind_raw is None else wind_raw / 10,
            "precipitation": (
                None if precipitation_raw is None else precipitation_raw / 10
            ),
            "raining": bool(self._input("shelly_rain_cluster", "rain_status")),
        }

    def _stateless_values(self) -> dict[str, tuple[float, int]]:
        """Calculate the values that only depend on the current readings.

        Returns the value and the scale it is stored with, for every value that can be
        calculated from the readings seen so far.
        """
        r = self._readings()
        temp, humidity, wind, lux = r["temp"], r["humidity"], r["wind"], r["lux"]
        values: dict[str, tuple[float, int]] = {}

        if temp is not None and humidity is not None:
            dew_point = calculate_dew_point(temp, humidity)
            humidex = calculate_humidex(temp, humidity)
            if dew_point is not None:
                values["dew_point"] = (dew_point, CALCULATED_SCALE)
            if humidex is not None:
                values["humidex"] = (humidex, CALCULATED_SCALE)
            values["heat_stress"] = (
                calculate_heat_stress(temp, humidity, lux, wind, r["raining"]),
                1,
            )
        if temp is not None and wind is not None:
            values["wind_chill"] = (calculate_wind_chill(temp, wind), CALCULATED_SCALE)
        if temp is not None:
            values["apparent_temperature"] = (
                calculate_apparent_temperature(temp, humidity, wind),
                CALCULATED_SCALE,
            )
        if lux is not None:
            condition = calculate_weather_condition(
                temp=temp,
                lux=lux,
                raining=r["raining"],
                wind_ms=wind,
                rain_rate=self._calculated("rain_rate"),
                pressure=r["pressure"],
                pressure_trend=self._calculated("pressure_trend"),
            )
            values["weather_condition"] = (condition.value, 1)
        return values

    def get(self, key: int | str, default: Any = None) -> Any:
        """Return a cached value, or calculate it from the cached readings.

        The calculated values are not restored after a restart, so until the next
        reading arrives they are worked out from the readings that are.
        """
        value = super().get(key)
        if value is not None:
            return value
        try:
            name = self.find_attribute(key).name
        except KeyError:
            return default
        calculated = self._stateless_values().get(name)
        if calculated is None:
            return default
        return round(calculated[0] * calculated[1])

    def recalculate(self, source: str) -> None:
        """Update the calculated values after the input `source` changed."""
        precipitation = self._readings()["precipitation"]
        if source == "precipitation" and precipitation is not None:
            self._update_rain_rate(precipitation)

        for name, (value, scale) in self._stateless_values().items():
            self._set(name, value, scale=scale)


class WS90InputMixin:
    """Drop readings that cannot be real, and trigger the calculations on new ones."""

    # Short name of the input as used by ShellyWS90CalculatedCluster.recalculate
    CALCULATION_SOURCE: str = ""

    def _is_glitch(self, attribute_name: str, value: Any) -> bool:
        """Return True if the value cannot be a real reading, compared to the last one."""
        return False

    def _on_reading(self, attribute_name: str, value: Any) -> None:
        """Handle every reading that is not a glitch, before it is published."""

    def _is_noise(self, attribute_name: str, value: Any) -> bool:
        """Return True for a real reading that differs too little to publish."""
        return False

    def _update_attribute(self, attrid: int | t.uint16_t, value: Any) -> None:
        """Ignore unusable readings, and update the calculated values after a new one."""
        try:
            attribute_name = self.find_attribute(attrid).name
        except KeyError:
            super()._update_attribute(attrid, value)
            return

        if self._is_glitch(attribute_name, value):
            self.debug("ignoring %s reading %s", attribute_name, value)
            return

        self._on_reading(attribute_name, value)
        if self._is_noise(attribute_name, value):
            return

        super()._update_attribute(attrid, value)

        calculated = getattr(
            self.endpoint, ShellyWS90CalculatedCluster.ep_attribute, None
        )
        if calculated is not None:
            calculated.recalculate(self._calculation_source(attribute_name))

    def _calculation_source(self, attribute_name: str) -> str:
        """Return the input name for an attribute."""
        return self.CALCULATION_SOURCE or attribute_name


class ShellyWindCluster(WS90InputMixin, CustomCluster):
    """Wind measurement cluster for Shelly devices."""

    cluster_id = 0xFC01
    name = "Shelly Wind Cluster"
    ep_attribute = "shelly_wind_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Wind cluster attribute definitions."""

        wind_speed = ZCLAttributeDef(
            id=0x0000,
            type=t.uint16_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        wind_direction = ZCLAttributeDef(
            id=0x0004,
            type=t.uint16_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        gust_speed = ZCLAttributeDef(
            id=0x0007,
            type=t.uint16_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )

    def _is_glitch(self, attribute_name: str, value: Any) -> bool:
        """Return True for the 0xFFFF the station sends when a wind reading is unavailable."""
        return value == NON_VALUE_UINT16


class ShellyUVCluster(WS90InputMixin, CustomCluster):
    """UV index measurement cluster for Shelly devices."""

    cluster_id = 0xFC02
    name = "Shelly UV Cluster"
    ep_attribute = "shelly_uv_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """UV cluster attribute definitions."""

        uv_index = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )

    def _is_glitch(self, attribute_name: str, value: Any) -> bool:
        """Return True for the 0xFF the station sends when the UV reading is unavailable."""
        return value == NON_VALUE_UINT8


class ShellyRainCluster(WS90InputMixin, CustomCluster):
    """Rain measurement cluster for Shelly devices."""

    cluster_id = 0xFC03
    name = "Shelly Rain Cluster"
    ep_attribute = "shelly_rain_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Rain cluster attribute definitions."""

        rain_status = ZCLAttributeDef(
            id=0x0000,
            type=t.Bool,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        precipitation = ZCLAttributeDef(
            id=0x0001,
            type=t.uint24_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )

    def _is_glitch(self, attribute_name: str, value: Any) -> bool:
        """Drop the non-value marker, and a counter that falls to 0 for a moment.

        The station now and then sends a frame with every measurement at 0. A real
        counter reset starts at 0.1 or 0.2, not 0, and a dropped zero would otherwise be
        counted as the whole total again by Home Assistant (total increasing).
        """
        if attribute_name != "precipitation":
            return False
        if value == NON_VALUE_UINT24:
            return True
        previous = self.get(attribute_name)
        return value == 0 and previous is not None and previous > 0


class ShellyWS90Temperature(WS90InputMixin, CustomCluster, TemperatureMeasurement):
    """Temperature measurement, dropping the all-zero frames."""

    CALCULATION_SOURCE = "temperature"

    def _is_glitch(self, attribute_name: str, value: Any) -> bool:
        """0 °C while the previous reading was more than 2 °C away from it."""
        if attribute_name != "measured_value":
            return False
        previous = self.get(attribute_name)
        return value == 0 and previous is not None and abs(previous) > 200


class ShellyWS90Humidity(WS90InputMixin, CustomCluster, RelativeHumidity):
    """Relative humidity measurement, dropping the all-zero frames."""

    CALCULATION_SOURCE = "humidity"

    def _is_glitch(self, attribute_name: str, value: Any) -> bool:
        """0 % while the previous reading was above 5 %."""
        if attribute_name != "measured_value":
            return False
        previous = self.get(attribute_name)
        return value == 0 and previous is not None and previous > 500


class ShellyWS90Pressure(WS90InputMixin, CustomCluster, PressureMeasurement):
    """Pressure measurement, dropping the all-zero frames and the 1 hPa flipping."""

    CALCULATION_SOURCE = "pressure"

    def _is_glitch(self, attribute_name: str, value: Any) -> bool:
        """Return True for a pressure of 0 hPa, which is never real."""
        return attribute_name == "measured_value" and value == 0

    def _on_reading(self, attribute_name: str, value: Any) -> None:
        """Feed every reading to the trend, including the ones that are not published."""
        if attribute_name != "measured_value":
            return
        calculated = getattr(
            self.endpoint, ShellyWS90CalculatedCluster.ep_attribute, None
        )
        if calculated is not None:
            calculated.add_pressure_sample(float(value))

    def _is_noise(self, attribute_name: str, value: Any) -> bool:
        """Return True for a change of 1 hPa or less, the station flips between two values."""
        if attribute_name != "measured_value":
            return False
        previous = self.get(attribute_name)
        return previous is not None and abs(value - previous) <= PRESSURE_DEAD_BAND


class ShellyWS90Illuminance(WS90InputMixin, CustomCluster, IlluminanceMeasurement):
    """Illuminance measurement, dropping the all-zero frames."""

    CALCULATION_SOURCE = "illuminance"

    def _is_glitch(self, attribute_name: str, value: Any) -> bool:
        """0 lx while the previous reading was above 50 lx."""
        if attribute_name != "measured_value":
            return False
        previous = self.get(attribute_name)
        return value == 0 and previous is not None and illuminance_lux(previous) > 50


CALCULATED = ShellyWS90CalculatedCluster

(
    QuirkBuilder("Shelly", "Ecowitt WS90")
    .replaces(ShellyWindCluster)
    .replaces(ShellyUVCluster)
    .replaces(ShellyRainCluster)
    .replaces(ShellyWS90Temperature)
    .replaces(ShellyWS90Humidity)
    .replaces(ShellyWS90Pressure)
    .replaces(ShellyWS90Illuminance)
    .adds(ShellyWS90CalculatedCluster)
    .sensor(
        attribute_name=ShellyWindCluster.AttributeDefs.wind_speed.name,
        cluster_id=ShellyWindCluster.cluster_id,
        divisor=10,
        unit=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        reporting_config=ReportingConfig(
            min_interval=10,
            max_interval=900,
            reportable_change=5,
        ),
        fallback_name="Wind speed",
    )
    .sensor(
        attribute_name=ShellyWindCluster.AttributeDefs.wind_direction.name,
        cluster_id=ShellyWindCluster.cluster_id,
        divisor=10,
        unit=DEGREE,
        device_class=SensorDeviceClass.WIND_DIRECTION,
        state_class=SensorStateClass.MEASUREMENT_ANGLE,
        reporting_config=ReportingConfig(
            min_interval=10,
            max_interval=900,
            reportable_change=50,
        ),
        fallback_name="Wind direction",
    )
    .sensor(
        attribute_name=ShellyWindCluster.AttributeDefs.gust_speed.name,
        cluster_id=ShellyWindCluster.cluster_id,
        divisor=10,
        unit=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        reporting_config=ReportingConfig(
            min_interval=10,
            max_interval=900,
            reportable_change=10,
        ),
        translation_key="gust_speed",
        fallback_name="Gust speed",
    )
    .sensor(
        attribute_name=ShellyUVCluster.AttributeDefs.uv_index.name,
        cluster_id=ShellyUVCluster.cluster_id,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        reporting_config=ReportingConfig(
            min_interval=300, max_interval=900, reportable_change=1
        ),
        translation_key="uv_index",
        fallback_name="UV index",
    )
    .sensor(
        attribute_name=ShellyRainCluster.AttributeDefs.precipitation.name,
        cluster_id=ShellyRainCluster.cluster_id,
        divisor=10,
        unit=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        reporting_config=ReportingConfig(
            min_interval=300, max_interval=900, reportable_change=1
        ),
        fallback_name="Precipitation",
    )
    .binary_sensor(
        attribute_name=ShellyRainCluster.AttributeDefs.rain_status.name,
        cluster_id=ShellyRainCluster.cluster_id,
        device_class=BinarySensorDeviceClass.MOISTURE,
        reporting_config=ReportingConfig(
            min_interval=0, max_interval=900, reportable_change=1
        ),
        translation_key="rain_detected",
        fallback_name="Rain detected",
    )
    # Calculated values
    .sensor(
        attribute_name=CALCULATED.AttributeDefs.dew_point.name,
        cluster_id=CALCULATED.cluster_id,
        divisor=CALCULATED_SCALE,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="dew_point",
        fallback_name="Dew point",
    )
    .sensor(
        attribute_name=CALCULATED.AttributeDefs.humidex.name,
        cluster_id=CALCULATED.cluster_id,
        divisor=CALCULATED_SCALE,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="humidex",
        fallback_name="Humidex",
    )
    .sensor(
        attribute_name=CALCULATED.AttributeDefs.wind_chill.name,
        cluster_id=CALCULATED.cluster_id,
        divisor=CALCULATED_SCALE,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="wind_chill",
        fallback_name="Wind chill",
    )
    .sensor(
        attribute_name=CALCULATED.AttributeDefs.apparent_temperature.name,
        cluster_id=CALCULATED.cluster_id,
        divisor=CALCULATED_SCALE,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="apparent_temperature",
        fallback_name="Apparent temperature",
    )
    .sensor(
        attribute_name=CALCULATED.AttributeDefs.heat_stress.name,
        cluster_id=CALCULATED.cluster_id,
        unit=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="heat_stress",
        fallback_name="Heat stress",
    )
    .sensor(
        attribute_name=CALCULATED.AttributeDefs.rain_rate.name,
        cluster_id=CALCULATED.cluster_id,
        divisor=CALCULATED_SCALE,
        unit=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="rain_rate",
        fallback_name="Rain rate",
    )
    .sensor(
        attribute_name=CALCULATED.AttributeDefs.pressure_trend.name,
        cluster_id=CALCULATED.cluster_id,
        divisor=CALCULATED_SCALE,
        unit="hPa/h",
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="pressure_trend",
        fallback_name="Pressure trend",
    )
    .enum(
        attribute_name=CALCULATED.AttributeDefs.weather_condition.name,
        enum_class=WeatherCondition,
        cluster_id=CALCULATED.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="weather_condition",
        fallback_name="Weather condition",
    )
    # Battery and solar capacitor voltage
    .sensor(
        attribute_name=PowerConfiguration.AttributeDefs.battery_voltage.name,
        cluster_id=PowerConfiguration.cluster_id,
        divisor=10,
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=ReportingConfig(
            min_interval=3600, max_interval=65000, reportable_change=1
        ),
        translation_key="battery_voltage",
        fallback_name="Battery voltage",
    )
    .sensor(
        attribute_name=PowerConfiguration.AttributeDefs.battery_2_voltage.name,
        cluster_id=PowerConfiguration.cluster_id,
        divisor=10,
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=3600, reportable_change=1
        ),
        translation_key="capacitor_voltage",
        fallback_name="Capacitor voltage",
    )
    .add_to_registry()
)
