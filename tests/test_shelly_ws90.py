"""Tests for the Shelly Ecowitt WS90 quirk.

Run against zha-quirks 2.2.2 (what HA ships) with the fixtures of zha-device-handlers:
copy or symlink this file into the `tests` directory of that repository (at the commit
before the 2.3.0 bump) and run pytest there. See the WS90 entry in .claude/MEMORY.md.
"""

from types import SimpleNamespace

import pytest
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    PressureMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)

from zhaquirks.shelly import ecowitt_ws90 as ws90

CLUSTERS = {
    PowerConfiguration.cluster_id: ClusterType.Server,
    IlluminanceMeasurement.cluster_id: ClusterType.Server,
    TemperatureMeasurement.cluster_id: ClusterType.Server,
    PressureMeasurement.cluster_id: ClusterType.Server,
    RelativeHumidity.cluster_id: ClusterType.Server,
    0xFC01: ClusterType.Server,
    0xFC02: ClusterType.Server,
    0xFC03: ClusterType.Server,
}


@pytest.fixture
def station(zigpy_device_from_v2_quirk):
    """Return a WS90 with the quirk applied."""
    device = zigpy_device_from_v2_quirk(
        "Shelly", "Ecowitt WS90", endpoint_ids=[1], cluster_ids={1: CLUSTERS}
    )
    ep = device.endpoints[1]
    assert isinstance(ep.shelly_ws90_calculated, ws90.ShellyWS90CalculatedCluster)
    return ep


@pytest.fixture
def clock(monkeypatch):
    """Provide a controllable monotonic clock for the quirk."""
    now = [1000.0]
    monkeypatch.setattr(ws90, "time", SimpleNamespace(monotonic=lambda: now[0]))
    return now


def feed(
    ep, *, temp=None, rh=None, pressure=None, lux_raw=None, wind=None, precip=None
):
    """Feed measurements like the station reports them (raw ZCL values)."""
    if temp is not None:
        ep.temperature.update_attribute(0x0000, round(temp * 100))
    if rh is not None:
        ep.humidity.update_attribute(0x0000, round(rh * 100))
    if pressure is not None:
        ep.pressure.update_attribute(0x0000, pressure)
    if lux_raw is not None:
        ep.illuminance.update_attribute(0x0000, lux_raw)
    if wind is not None:
        ep.shelly_wind_cluster.update_attribute(0x0000, round(wind * 10))
    if precip is not None:
        ep.shelly_rain_cluster.update_attribute(0x0001, round(precip * 10))


def calc(ep, name):
    """Return a calculated value in its real unit."""
    value = ep.shelly_ws90_calculated.get(name)
    if value is None:
        return None
    if name in ("heat_stress", "weather_condition"):
        return value
    return value / 10


def condition(ep):
    """Name of the calculated weather condition."""
    return ws90.WeatherCondition(calc(ep, "weather_condition")).name


def test_local_quirk_wins_over_upstream(station):
    """The local quirk is applied, not the upstream one."""
    assert type(station.shelly_wind_cluster) is ws90.ShellyWindCluster


def test_live_values_match_zigbee2mqtt(station):
    """The values Z2M published for 17.7 C, 89 %, 18785 lx, 0.5 m/s, 451.6 mm counter."""
    feed(
        station, temp=17.7, rh=89, pressure=1017, lux_raw=42739, wind=0.5, precip=451.6
    )
    assert calc(station, "dew_point") == 15.9
    assert calc(station, "humidex") == 22.3
    assert calc(station, "apparent_temperature") == 22.3
    assert calc(station, "wind_chill") == 17.7
    # Z2M says 31: it counts the rain counter as rain, the quirk only real rain
    assert calc(station, "heat_stress") == 43
    assert condition(station) == "partlycloudy"


def test_heat_stress_drops_while_raining(station):
    """Rain takes 3 degrees off, only while the station reports rain."""
    feed(station, temp=17.7, rh=89, lux_raw=42739, wind=0.5, precip=451.6)
    assert calc(station, "heat_stress") == 43
    station.shelly_rain_cluster.update_attribute(0x0000, True)
    assert calc(station, "heat_stress") == 31
    station.shelly_rain_cluster.update_attribute(0x0000, False)
    assert calc(station, "heat_stress") == 43


def test_wind_chill_and_apparent_temperature_when_cold(station):
    """Below 10 C with wind the apparent temperature is the wind chill."""
    feed(station, temp=2.0, rh=80, wind=5.0)
    assert calc(station, "wind_chill") == -2.4
    assert calc(station, "apparent_temperature") == -2.4


def test_calculations_wait_for_inputs(station):
    """Without humidity there is no dew point, humidex or heat stress."""
    feed(station, temp=20.0)
    assert calc(station, "dew_point") is None
    assert calc(station, "humidex") is None
    assert calc(station, "heat_stress") is None
    assert calc(station, "wind_chill") is None
    assert calc(station, "apparent_temperature") == 20.0


def test_non_value_markers_are_dropped(station):
    """0xFFFF wind, 0xFF UV and 0xFFFFFF precipitation never reach the cache."""
    feed(station, temp=15, rh=50, wind=2.0, precip=10.0)
    station.shelly_wind_cluster.update_attribute(0x0000, 0xFFFF)
    station.shelly_wind_cluster.update_attribute(0x0007, 0xFFFF)
    station.shelly_uv_cluster.update_attribute(0x0000, 0xFF)
    station.shelly_rain_cluster.update_attribute(0x0001, 0xFFFFFF)
    assert station.shelly_wind_cluster.get("wind_speed") == 20
    assert station.shelly_wind_cluster.get("gust_speed") is None
    assert station.shelly_uv_cluster.get("uv_index") is None
    assert station.shelly_rain_cluster.get("precipitation") == 100


def test_all_zero_frame_is_dropped(station):
    """An all-zero frame changes nothing, a genuine zero from a zero state does."""
    feed(station, temp=17.7, rh=89, pressure=1017, lux_raw=42739, precip=451.6)
    for cluster, attr in (
        (station.temperature, 0x0000),
        (station.humidity, 0x0000),
        (station.pressure, 0x0000),
        (station.illuminance, 0x0000),
        (station.shelly_rain_cluster, 0x0001),
    ):
        cluster.update_attribute(attr, 0)
    assert station.temperature.get("measured_value") == 1770
    assert station.humidity.get("measured_value") == 8900
    assert station.pressure.get("measured_value") == 1017
    assert station.illuminance.get("measured_value") == 42739
    assert station.shelly_rain_cluster.get("precipitation") == 4516

    # real values near zero still go through
    feed(station, temp=0.0)
    station.temperature.update_attribute(0x0000, 100)
    station.temperature.update_attribute(0x0000, 0)
    assert station.temperature.get("measured_value") == 0
    station.humidity.update_attribute(0x0000, 300)
    station.humidity.update_attribute(0x0000, 0)
    assert station.humidity.get("measured_value") == 0


def test_rain_rate(station, clock):
    """Rain rate follows the counter, resets with it, and is capped."""
    feed(station, precip=100.0)
    assert calc(station, "rain_rate") == 0

    clock[0] += 30  # too soon, no new sample
    feed(station, precip=100.5)
    assert calc(station, "rain_rate") == 0

    clock[0] += 1770  # 30 minutes after the baseline
    feed(station, precip=101.0)
    assert calc(station, "rain_rate") == 2.0

    clock[0] += 3600
    feed(station, precip=101.0)
    assert calc(station, "rain_rate") == 0

    clock[0] += 3600
    feed(station, precip=0.2)  # counter reset
    assert calc(station, "rain_rate") == 0

    clock[0] += 60
    feed(station, precip=400.0)  # absurd jump, capped
    assert calc(station, "rain_rate") == 300


def run_pressure(station, clock, *, minutes, step_s, value):
    """Report `value(minute)` every `step_s` seconds for `minutes` minutes."""
    start = clock[0]
    while clock[0] - start < minutes * 60:
        feed(station, pressure=value((clock[0] - start) / 60))
        clock[0] += step_s


def test_pressure_dead_band(station):
    """A change of 1 hPa or less is not published, a bigger one is."""
    feed(station, pressure=1007)
    feed(station, pressure=1008)
    assert station.pressure.get("measured_value") == 1007
    feed(station, pressure=1007)
    feed(station, pressure=1006)
    assert station.pressure.get("measured_value") == 1007
    feed(station, pressure=1009)
    assert station.pressure.get("measured_value") == 1009
    feed(station, pressure=1004)
    assert station.pressure.get("measured_value") == 1004


def test_pressure_flipping_gives_no_trend(station, clock):
    """The station flipping between 1007 and 1008 gives a flat trend and no new states."""
    published = []
    station.pressure.add_listener(
        SimpleNamespace(
            attribute_updated=lambda attrid, value, _=None: published.append(value)
        )
    )
    run_pressure(
        station,
        clock,
        minutes=210,
        step_s=100,
        value=lambda minute: 1007 + int(minute * 60 / 100) % 2,
    )
    assert abs(calc(station, "pressure_trend")) <= 0.2
    assert published == [1007]


@pytest.mark.parametrize("rate", [-4.0, -1.0, 0.5, 3.0])
def test_pressure_trend_in_hpa_per_hour(station, clock, rate):
    """The trend follows a real change of the pressure in hPa per hour."""
    run_pressure(
        station,
        clock,
        minutes=180,
        step_s=60,
        value=lambda minute: round(1010 + rate * minute / 60),
    )
    assert calc(station, "pressure_trend") == pytest.approx(rate, abs=0.3)


def test_pressure_trend_waits_for_history(station, clock):
    """Nothing but a zero before half an hour of history, then the fitted slope."""
    run_pressure(
        station, clock, minutes=20, step_s=60, value=lambda m: round(1010 - 3 * m / 60)
    )
    assert calc(station, "pressure_trend") == 0
    run_pressure(
        station, clock, minutes=40, step_s=60, value=lambda m: round(1009 - 3 * m / 60)
    )
    assert calc(station, "pressure_trend") != 0


def test_trend_survives_restart(station, clock):
    """After a restart (no history) the last trend is kept until there is enough."""
    station.shelly_ws90_calculated._update_attribute(0x0006, -25)
    run_pressure(station, clock, minutes=10, step_s=60, value=lambda m: 1010)
    assert calc(station, "pressure_trend") == -2.5
    run_pressure(station, clock, minutes=60, step_s=60, value=lambda m: 1010)
    assert calc(station, "pressure_trend") == 0


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"lux_raw": 1}, "clear-night"),
        ({"lux_raw": 1, "wind": 11}, "windy"),
        ({"lux_raw": 50000}, "sunny"),  # ~10^4.9999 = 99,977 lx
        ({"lux_raw": 50000, "wind": 12}, "windy"),
        ({"lux_raw": 42739}, "partlycloudy"),
        ({"lux_raw": 42739, "wind": 12}, "windy-variant"),
        ({"lux_raw": 30000}, "cloudy"),
    ],
)
def test_weather_conditions_dry(station, kwargs, expected):
    """Dry conditions follow the illuminance and wind."""
    feed(station, temp=15, rh=50, pressure=1015, **kwargs)
    assert condition(station) == expected


def test_weather_conditions_rain(station, clock):
    """Rain, pouring, snow and hail."""
    feed(station, temp=12, rh=90, pressure=1015, lux_raw=42739, wind=1, precip=10.0)
    station.shelly_rain_cluster.update_attribute(0x0000, True)
    clock[0] += 3600
    feed(station, precip=10.5)  # 0.5 mm/h
    assert condition(station) == "rainy"
    clock[0] += 3600
    feed(station, precip=25.0)  # 14.5 mm/h
    assert condition(station) == "pouring"
    feed(station, temp=0.5)
    clock[0] += 3600
    feed(station, precip=26.0)  # 1 mm/h, below 1 C
    assert condition(station) == "snowy"

    # hail needs more than 5 mm/h, dark sky, wind above 5 m/s and low pressure
    feed(station, temp=12, pressure=990, lux_raw=30000, wind=6)
    clock[0] += 3600
    feed(station, precip=36.0)  # 10 mm/h
    assert condition(station) == "hail"


def test_hail_with_falling_pressure():
    """Hail also needs a pressure that falls by more than 2 hPa/h, not only a low one."""
    kwargs = {
        "temp": 12,
        "lux": 3000,
        "raining": True,
        "wind_ms": 6,
        "rain_rate": 12,
        "pressure": 1010,
    }
    assert ws90.calculate_weather_condition(pressure_trend=-3, **kwargs).name == "hail"
    assert (
        ws90.calculate_weather_condition(pressure_trend=-1, **kwargs).name == "pouring"
    )


def test_history_based_values_read_zero_before_any_data(station):
    """Rain rate and pressure trend are 0 right after a start, not unknown."""
    assert calc(station, "rain_rate") == 0
    assert calc(station, "pressure_trend") == 0
    cluster = station.shelly_ws90_calculated
    assert cluster.get("rain_rate") == 0
    assert cluster.get("pressure_trend") == 0
    # the other calculated values wait for their inputs
    assert calc(station, "dew_point") is None
    assert calc(station, "weather_condition") is None


def test_calculated_values_come_back_after_a_restart(station):
    """With nothing cached, the values are worked out from the cached readings."""
    feed(station, temp=17.7, rh=89, pressure=1017, lux_raw=42739, wind=0.5, precip=10)
    names = (
        "dew_point",
        "humidex",
        "wind_chill",
        "apparent_temperature",
        "heat_stress",
        "weather_condition",
    )
    expected = {name: calc(station, name) for name in names}
    assert all(value is not None for value in expected.values())

    station.shelly_ws90_calculated._attr_cache.clear()  # what a restart does
    assert {name: calc(station, name) for name in names} == expected
    assert calc(station, "rain_rate") == 0
    assert calc(station, "pressure_trend") == 0


def test_illuminance_below_the_measurable_range_is_zero_lux():
    """The ZCL value 0 (and anything lower) stands for no light at all."""
    assert ws90.illuminance_lux(0) == 0
    assert ws90.illuminance_lux(-1) == 0
    assert ws90.illuminance_lux(10001) == 10


def test_missing_inputs_give_no_value(station):
    """A sibling cluster that is not there, or a value not worked out yet, reads as None."""
    cluster = station.shelly_ws90_calculated
    assert cluster._input("no_such_cluster", "measured_value") is None
    assert cluster._calculated("dew_point") is None

    cluster._set("dew_point", None)
    assert cluster._attr_cache.get(cluster.find_attribute("dew_point").id) is None


def test_unknown_attribute_of_the_calculated_cluster_gives_the_default(station):
    """Only the attributes of the cluster are worked out, anything else is a plain lookup."""
    assert station.shelly_ws90_calculated.get(0xFFEE, "fallback") == "fallback"


def test_unknown_attribute_of_an_input_cluster_is_passed_on(station):
    """Attributes the quirk does not know about are cached like on any other cluster."""
    station.temperature.update_attribute(0xFFEE, 5)
    assert station.temperature._attr_cache[0xFFEE] == 5


def test_default_hooks_keep_every_reading():
    """Without an override a reading is neither a glitch nor noise."""
    mixin = ws90.WS90InputMixin()
    assert mixin._is_glitch("measured_value", 0) is False
    assert mixin._is_noise("measured_value", 0) is False
    assert mixin._on_reading("measured_value", 0) is None


@pytest.mark.parametrize(
    ("cluster_name", "measured", "other"),
    [
        ("temperature", 1770, 0),
        ("humidity", 8900, 0),
        ("illuminance", 42739, 0),
        ("pressure", 1017, 1018),
    ],
)
def test_only_the_measured_value_is_filtered(station, cluster_name, measured, other):
    """The other attributes of the measurement clusters are stored as they come."""
    cluster = getattr(station, cluster_name)
    cluster.update_attribute(0x0000, measured)
    cluster.update_attribute(0x0001, other)  # min_measured_value
    assert cluster.get(0x0001) == other


def test_other_pressure_attributes_do_not_feed_the_trend(station, clock):
    """Only readings of the measured value count as samples for the trend."""
    station.pressure.update_attribute(0x0000, 1017)
    samples = len(station.shelly_ws90_calculated._pressure_samples)
    station.pressure.update_attribute(0x0001, 900)
    assert len(station.shelly_ws90_calculated._pressure_samples) == samples
