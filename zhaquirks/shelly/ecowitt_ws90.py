"""Device handler for Shelly WS90 Weather Station."""

from __future__ import annotations

from zigpy import types
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    DEGREE,
    BinarySensorDeviceClass,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfPrecipitationDepth,
    UnitOfSpeed,
)
from zhaquirks.clusters import CustomCluster
from zhaquirks.shelly import SHELLY_MANUFACTURER_CODE


class ShellyWindCluster(CustomCluster):
    """Wind measurement cluster for Shelly devices."""

    cluster_id = 0xFC01
    name = "Shelly Wind Cluster"
    ep_attribute = "shelly_wind_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Wind cluster attribute definitions."""

        wind_speed = ZCLAttributeDef(
            id=0x0000,
            type=types.uint16_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        wind_direction = ZCLAttributeDef(
            id=0x0004,
            type=types.uint16_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        gust_speed = ZCLAttributeDef(
            id=0x0007,
            type=types.uint16_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )


class ShellyUVCluster(CustomCluster):
    """UV index measurement cluster for Shelly devices."""

    cluster_id = 0xFC02
    name = "Shelly UV Cluster"
    ep_attribute = "shelly_uv_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """UV cluster attribute definitions."""

        uv_index = ZCLAttributeDef(
            id=0x0000,
            type=types.uint8_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )


class ShellyRainCluster(CustomCluster):
    """Rain measurement cluster for Shelly devices."""

    cluster_id = 0xFC03
    name = "Shelly Rain Cluster"
    ep_attribute = "shelly_rain_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Rain cluster attribute definitions."""

        rain_status = ZCLAttributeDef(
            id=0x0000,
            type=types.Bool,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        precipitation = ZCLAttributeDef(
            id=0x0001,
            type=types.uint24_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )


(
    QuirkBuilder("Shelly", "Ecowitt WS90")
    .replaces(ShellyWindCluster)
    .replaces(ShellyUVCluster)
    .replaces(ShellyRainCluster)
    .sensor(
        attribute_name=ShellyWindCluster.AttributeDefs.wind_speed.name,
        cluster_id=ShellyWindCluster.cluster_id,
        divisor=10,
        unit=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=900, reportable_change=5
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
            min_interval=10, max_interval=900, reportable_change=50
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
            min_interval=10, max_interval=900, reportable_change=10
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
    .add_to_registry()
)
