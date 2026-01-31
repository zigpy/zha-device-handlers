"""Device handler for Shelly WS90 Weather Station."""

from __future__ import annotations

from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    BinarySensorDeviceClass,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    homeassistant,
)
from zigpy.zcl import foundation

from zhaquirks.shelly import SHELLY, SHELLY_MANUFACTURER_CODE


class ShellyWindCluster(CustomCluster):
    """Wind measurement cluster for Shelly WS90."""

    cluster_id = 0xFC01
    name = "Shelly Wind Cluster"
    ep_attribute = "shelly_wind_cluster"
    manufacturer_code = SHELLY_MANUFACTURER_CODE

    class AttributeDefs(foundation.BaseAttributeDefs):
        """Wind cluster attribute definitions."""

        wind_speed = foundation.ZCLAttributeDef(
            id=0x0000,
            type=types.uint16_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        wind_direction = foundation.ZCLAttributeDef(
            id=0x0004,
            type=types.uint16_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        gust_speed = foundation.ZCLAttributeDef(
            id=0x0007,
            type=types.uint16_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )


class ShellyUVCluster(CustomCluster):
    """UV index measurement cluster for Shelly WS90."""

    cluster_id = 0xFC02
    name = "Shelly UV Cluster"
    ep_attribute = "shelly_uv_cluster"
    manufacturer_code = SHELLY_MANUFACTURER_CODE

    class AttributeDefs(foundation.BaseAttributeDefs):
        """UV cluster attribute definitions."""

        uv_index = foundation.ZCLAttributeDef(
            id=0x0000,
            type=types.uint8_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )


class ShellyRainCluster(CustomCluster):
    """Rain measurement cluster for Shelly WS90."""

    cluster_id = 0xFC03
    name = "Shelly Rain Cluster"
    ep_attribute = "shelly_rain_cluster"
    manufacturer_code = SHELLY_MANUFACTURER_CODE

    class AttributeDefs(foundation.BaseAttributeDefs):
        """Rain cluster attribute definitions."""

        rain_status = foundation.ZCLAttributeDef(
            id=0x0000,
            type=types.Bool,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        precipitation = foundation.ZCLAttributeDef(
            id=0x0001,
            type=types.uint24_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )


(
    QuirkBuilder(SHELLY, "Ecowitt WS90")
    .replaces(ShellyWindCluster)
    .replaces(ShellyUVCluster)
    .replaces(ShellyRainCluster)
    .sensor(
        attribute_name="wind_speed",
        cluster_id=ShellyWindCluster.cluster_id,
        divisor=10,
        unit=homeassistant.UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="wind_speed",
        fallback_name="Wind Speed",
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=900, reportable_change=1
        ),
    )
    .sensor(
        attribute_name="wind_direction",
        cluster_id=ShellyWindCluster.cluster_id,
        divisor=10,
        unit=homeassistant.DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="wind_direction",
        fallback_name="Wind Direction",
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=900, reportable_change=1
        ),
    )
    .sensor(
        attribute_name="gust_speed",
        cluster_id=ShellyWindCluster.cluster_id,
        divisor=10,
        unit=homeassistant.UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="gust_speed",
        fallback_name="Gust Speed",
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=900, reportable_change=1
        ),
    )
    .sensor(
        attribute_name="uv_index",
        cluster_id=ShellyUVCluster.cluster_id,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="uv_index",
        fallback_name="UV Index",
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=900, reportable_change=1
        ),
    )
    .sensor(
        attribute_name="precipitation",
        cluster_id=ShellyRainCluster.cluster_id,
        divisor=10,
        unit=homeassistant.UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        translation_key="precipitation",
        fallback_name="Precipitation",
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=900, reportable_change=1
        ),
    )
    .binary_sensor(
        attribute_name="rain_status",
        cluster_id=ShellyRainCluster.cluster_id,
        device_class=BinarySensorDeviceClass.MOISTURE,
        translation_key="rain_status",
        fallback_name="Rain Detected",
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=900, reportable_change=1
        ),
    )
    .add_to_registry()
)
