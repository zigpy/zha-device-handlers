"""Quirk for Aqara lumi.sensor_occupy.agl8."""

from typing import Any, Final

from zigpy import types as t
from zigpy.quirks.v2 import QuirkBuilder, ReportingConfig
from zigpy.quirks.v2.homeassistant import (
    PERCENTAGE,
    EntityType,
    UnitOfLength,
    UnitOfTemperature,
    UnitOfTime,
)
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.xiaomi import (
    BATTERY_PERCENTAGE_REMAINING_ATTRIBUTE,
    BATTERY_VOLTAGE_MV,
    XiaomiAqaraE1Cluster,
    XiaomiPowerConfigurationPercent,
)

# Manufacturer-specific attribute keys present in the non-standard AQARA payloads
AQARA_MANUFACTURER_CODE: Final = 0x115F
MANU_ATTR_BATTERY_VOLTAGE: Final = "0xff01-23"
MANU_ATTR_BATTERY_PERCENT: Final = "0xff01-24"


#
# Enums matching Zigbee2MQTT converter semantics
#
class MotionSensitivity(t.enum8):
    """Presence / motion sensitivity."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


class PresenceDetectionMode(t.enum8):
    """Which sensors are used for presence."""

    BOTH = 0
    MMWAVE_ONLY = 1
    PIR_ONLY = 2


class TempHumiditySampling(t.enum8):
    """Sampling frequency for temperature & humidity."""

    OFF = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CUSTOM = 4


class ReportMode(t.enum8):
    """Reporting mode for temp/humidity/illuminance in custom mode."""

    THRESHOLD = 1
    INTERVAL = 2
    THRESHOLD_AND_INTERVAL = 3


class LightSampling(t.enum8):
    """Sampling frequency for illuminance."""

    OFF = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CUSTOM = 4


#
# Manufacturer specific cluster (0xFCC0)
#
class AqaraFP300ManuCluster(XiaomiAqaraE1Cluster):
    """Aqara FP300 manufacturer specific cluster (0xFCC0)."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for Aqara FP300 manu cluster."""

        #
        # Presence / motion
        #
        presence: Final = ZCLAttributeDef(
            id=0x0142,
            type=t.Bool,
            zcl_type=DataTypeId.uint8,
            access="rp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        pir_detection: Final = ZCLAttributeDef(
            id=0x014D,
            type=t.Bool,
            zcl_type=DataTypeId.uint8,
            access="rp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        motion_sensitivity: Final = ZCLAttributeDef(
            id=0x010C,
            type=MotionSensitivity,
            zcl_type=DataTypeId.uint8,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        absence_delay_timer: Final = ZCLAttributeDef(
            id=0x0197,
            type=t.uint32_t,
            zcl_type=DataTypeId.uint32,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        pir_detection_interval: Final = ZCLAttributeDef(
            id=0x014F,
            type=t.uint16_t,
            zcl_type=DataTypeId.uint16,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        presence_detection_options: Final = ZCLAttributeDef(
            id=0x0199,
            type=PresenceDetectionMode,
            zcl_type=DataTypeId.uint8,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        detection_range_raw: Final = ZCLAttributeDef(
            id=0x019A,
            type=t.LVBytes,
            zcl_type=DataTypeId.octstr,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        #
        # AI helpers
        #
        ai_interference_source_selfidentification: Final = ZCLAttributeDef(
            id=0x015E,
            type=t.uint8_t,
            zcl_type=DataTypeId.uint8,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        ai_sensitivity_adaptive: Final = ZCLAttributeDef(
            id=0x015D,
            type=t.uint8_t,
            zcl_type=DataTypeId.uint8,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        #
        # Target distance / tracking
        #
        target_distance: Final = ZCLAttributeDef(
            id=0x015F,
            type=t.uint32_t,
            zcl_type=DataTypeId.uint32,
            access="rp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        track_target_distance: Final = ZCLAttributeDef(
            id=0x0198,
            type=t.uint8_t,
            zcl_type=DataTypeId.uint8,
            access="w",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        #
        # Temp/humidity sampling + reporting
        #
        temp_humidity_sampling: Final = ZCLAttributeDef(
            id=0x0170,
            type=TempHumiditySampling,
            zcl_type=DataTypeId.uint8,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        temp_humidity_sampling_period: Final = ZCLAttributeDef(
            id=0x0162,
            type=t.uint32_t,
            zcl_type=DataTypeId.uint32,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        temp_reporting_interval: Final = ZCLAttributeDef(
            id=0x0163,
            type=t.uint32_t,
            zcl_type=DataTypeId.uint32,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        temp_reporting_threshold: Final = ZCLAttributeDef(
            id=0x0164,
            type=t.uint16_t,
            zcl_type=DataTypeId.uint16,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        temp_reporting_mode: Final = ZCLAttributeDef(
            id=0x0165,
            type=ReportMode,
            zcl_type=DataTypeId.uint8,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        humidity_reporting_interval: Final = ZCLAttributeDef(
            id=0x016A,
            type=t.uint32_t,
            zcl_type=DataTypeId.uint32,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        humidity_reporting_threshold: Final = ZCLAttributeDef(
            id=0x016B,
            type=t.uint16_t,
            zcl_type=DataTypeId.uint16,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        humidity_reporting_mode: Final = ZCLAttributeDef(
            id=0x016C,
            type=ReportMode,
            zcl_type=DataTypeId.uint8,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        #
        # Illuminance sampling + reporting
        #
        light_sampling: Final = ZCLAttributeDef(
            id=0x0192,
            type=LightSampling,
            zcl_type=DataTypeId.uint8,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        light_sampling_period: Final = ZCLAttributeDef(
            id=0x0193,
            type=t.uint32_t,
            zcl_type=DataTypeId.uint32,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        light_reporting_interval: Final = ZCLAttributeDef(
            id=0x0194,
            type=t.uint32_t,
            zcl_type=DataTypeId.uint32,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        light_reporting_threshold: Final = ZCLAttributeDef(
            id=0x0195,
            type=t.uint16_t,
            zcl_type=DataTypeId.uint16,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        light_reporting_mode: Final = ZCLAttributeDef(
            id=0x0196,
            type=ReportMode,
            zcl_type=DataTypeId.uint8,
            access="rwp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        #
        # Spatial learning / restart (FP1E-style maintenance actions)
        #
        spatial_learning: Final = ZCLAttributeDef(
            id=0x0157,
            type=t.uint8_t,
            zcl_type=DataTypeId.uint8,
            access="w",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        restart_device: Final = ZCLAttributeDef(
            id=0x00E8,
            type=t.Bool,
            zcl_type=DataTypeId.bool_,
            access="w",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

    def _parse_aqara_attributes(self, value: Any) -> dict[str, Any]:
        """Parse non-standard and fp300 specific attributes.

        Returns a mapping of attribute keys to values as extracted by the
        parent implementation, with a couple of manufacturer-specific keys
        renamed to common battery attribute names used in this project.
        """
        attributes = super()._parse_aqara_attributes(value)

        if MANU_ATTR_BATTERY_VOLTAGE in attributes:
            attributes[BATTERY_VOLTAGE_MV] = attributes.pop(MANU_ATTR_BATTERY_VOLTAGE)

        if MANU_ATTR_BATTERY_PERCENT in attributes:
            attributes[BATTERY_PERCENTAGE_REMAINING_ATTRIBUTE] = attributes.pop(
                MANU_ATTR_BATTERY_PERCENT
            )

        return attributes

    def _update_attribute(self, attrid: int, value: Any) -> Any:
        """Only delegate 0x019A to the FP300DetectionRangeCluster.

        If the attribute id corresponds to the raw detection-range payload we
        forward that to the local detection-range cluster which decodes the
        buffer into separate boolean range attributes. The result of the
        parent implementation is returned to the caller.
        """

        if attrid == self.AttributeDefs.detection_range_raw.id:
            dr_cluster = self.endpoint.in_clusters.get(
                FP300DetectionRangeCluster.cluster_id
            )
            if dr_cluster is not None:
                dr_cluster._update_from_raw(value)

        return super()._update_attribute(attrid, value)


class FP300DetectionRangeCluster(LocalDataCluster):
    """Local cluster for detection range handling."""

    cluster_id = 0xFC30

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for FP300 detection range cluster."""

        prefix: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint16_t,
            zcl_type=DataTypeId.uint16,
            access="rwp",
        )

        range_0_1m: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
            zcl_type=DataTypeId.bool_,
            access="rwp",
        )
        range_1_2m: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.Bool,
            zcl_type=DataTypeId.bool_,
            access="rwp",
        )
        range_2_3m: Final = ZCLAttributeDef(
            id=0x0003,
            type=t.Bool,
            zcl_type=DataTypeId.bool_,
            access="rwp",
        )
        range_3_4m: Final = ZCLAttributeDef(
            id=0x0004,
            type=t.Bool,
            zcl_type=DataTypeId.bool_,
            access="rwp",
        )
        range_4_5m: Final = ZCLAttributeDef(
            id=0x0005,
            type=t.Bool,
            zcl_type=DataTypeId.bool_,
            access="rwp",
        )
        range_5_6m: Final = ZCLAttributeDef(
            id=0x0006,
            type=t.Bool,
            zcl_type=DataTypeId.bool_,
            access="rwp",
        )

    def _update_from_raw(self, raw: t.LVBytes | bytes | bytearray | None) -> None:
        """Update local detection range from raw 0x019A buffer."""

        if isinstance(raw, t.LVBytes) or isinstance(raw, (bytes, bytearray)):
            data = bytes(raw)
        else:
            data = b""

        if len(data) >= 5:
            prefix = int.from_bytes(data[0:2], "little")
            mask = int.from_bytes(data[2:5], "little") & ((1 << 24) - 1)
        else:
            prefix = 0x0300
            mask = (1 << 24) - 1  # 0xFFFFFF

        super()._update_attribute(self.AttributeDefs.prefix.id, prefix)

        seg_defs = [
            (self.AttributeDefs.range_0_1m.id, 0),
            (self.AttributeDefs.range_1_2m.id, 4),
            (self.AttributeDefs.range_2_3m.id, 8),
            (self.AttributeDefs.range_3_4m.id, 12),
            (self.AttributeDefs.range_4_5m.id, 16),
            (self.AttributeDefs.range_5_6m.id, 20),
        ]

        for attr_id, start_bit in seg_defs:
            seg_mask = ((1 << 4) - 1) << start_bit
            enabled = (mask & seg_mask) != 0
            super()._update_attribute(attr_id, bool(enabled))

    def _build_raw(self) -> t.LVBytes:
        """Build raw 0x019A buffer for the manufacturer cluster from local range switches."""

        prefix = self._attr_cache.get(self.AttributeDefs.prefix.id, 0x0300)
        try:
            prefix_int = int(prefix) & 0xFFFF
        except (TypeError, ValueError):
            prefix_int = 0x0300

        seg_defs = [
            (self.AttributeDefs.range_0_1m.id, 0),
            (self.AttributeDefs.range_1_2m.id, 4),
            (self.AttributeDefs.range_2_3m.id, 8),
            (self.AttributeDefs.range_3_4m.id, 12),
            (self.AttributeDefs.range_4_5m.id, 16),
            (self.AttributeDefs.range_5_6m.id, 20),
        ]

        mask = 0
        for attr_id, start_bit in seg_defs:
            enabled = bool(self._attr_cache.get(attr_id, True))
            if enabled:
                mask |= ((1 << 4) - 1) << start_bit

        buf = prefix_int.to_bytes(2, "little") + mask.to_bytes(3, "little")
        return t.LVBytes(buf)

    async def write_attributes(
        self,
        attributes: dict[int, Any],
        manufacturer: int | None = None,
        **kwargs: Any,
    ) -> Any:
        """Override write_attributes to also update manu cluster."""

        res = await super().write_attributes(
            attributes, manufacturer=manufacturer, **kwargs
        )

        raw = self._build_raw()

        manu = self.endpoint.in_clusters.get(AqaraFP300ManuCluster.cluster_id)
        if manu is not None:
            await manu.write_attributes(
                {AqaraFP300ManuCluster.AttributeDefs.detection_range_raw.id: raw},
                manufacturer=manufacturer,
            )

        return res


#
# QuirkBuilder definition
#
FP300_QUIRK = (
    QuirkBuilder("Aqara", "lumi.sensor_occupy.agl8")
    .friendly_name(manufacturer="Aqara", model="Presence Sensor FP300")
    .replaces(AqaraFP300ManuCluster)
    .adds(XiaomiPowerConfigurationPercent)
    .adds(FP300DetectionRangeCluster)
    # Main presence entity (mmWave)
    .binary_sensor(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.presence.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        entity_type=EntityType.STANDARD,
        reporting_config=ReportingConfig(
            min_interval=1,
            max_interval=300,
            reportable_change=1,
        ),
        translation_key="presence",
        fallback_name="Presence",
    )
    # Diagnostic PIR detection
    .binary_sensor(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.pir_detection.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.MOTION,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=ReportingConfig(
            min_interval=1,
            max_interval=300,
            reportable_change=1,
        ),
        initially_disabled=True,
        translation_key="pir_detection",
        fallback_name="PIR detection",
    )
    # Target distance (from fp1eTargetDistance)
    .sensor(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.target_distance.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfLength.METERS,
        multiplier=0.01,  # raw = meters * 100
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="target_distance",
        fallback_name="Target distance",
    )
    # Button: start tracking current target distance
    .write_attr_button(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.track_target_distance.name,
        attribute_value=1,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="track_target_distance",
        fallback_name="Start target distance tracking",
    )
    # Motion / presence config
    .enum(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.motion_sensitivity.name,
        enum_class=MotionSensitivity,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="motion_sensitivity",
        fallback_name="Motion sensitivity",
    )
    .enum(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.presence_detection_options.name,
        enum_class=PresenceDetectionMode,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="presence_detection_options",
        fallback_name="Presence detection options",
    )
    .number(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.absence_delay_timer.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        device_class=NumberDeviceClass.DURATION,
        entity_type=EntityType.CONFIG,
        min_value=10,
        max_value=300,
        step=5,
        unit=UnitOfTime.SECONDS,
        translation_key="absence_delay_timer",
        fallback_name="Absence delay timer",
    )
    .number(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.pir_detection_interval.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        device_class=NumberDeviceClass.DURATION,
        entity_type=EntityType.CONFIG,
        min_value=2,
        max_value=300,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="pir_detection_interval",
        fallback_name="PIR detection interval",
    )
    # AI helper switches
    .switch(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.ai_interference_source_selfidentification.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="ai_interference_source_selfidentification",
        fallback_name="AI interference source self-identification",
    )
    .switch(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.ai_sensitivity_adaptive.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="ai_sensitivity_adaptive",
        fallback_name="AI adaptive sensitivity",
    )
    # Temp/humidity sampling & reporting
    .enum(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.temp_humidity_sampling.name,
        enum_class=TempHumiditySampling,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="temp_humidity_sampling",
        fallback_name="Temp & humidity sampling",
    )
    .number(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.temp_humidity_sampling_period.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        device_class=NumberDeviceClass.DURATION,
        entity_type=EntityType.CONFIG,
        min_value=0.5,
        max_value=3600.0,
        step=0.5,
        multiplier=0.001,  # ms -> s
        unit=UnitOfTime.SECONDS,
        translation_key="temp_humidity_sampling_period",
        fallback_name="Temp & humidity sampling period",
    )
    .number(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.temp_reporting_interval.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        device_class=NumberDeviceClass.DURATION,
        entity_type=EntityType.CONFIG,
        min_value=600,
        max_value=3600,
        step=600,
        multiplier=0.001,
        unit=UnitOfTime.SECONDS,
        translation_key="temp_reporting_interval",
        fallback_name="Temperature reporting interval",
    )
    .number(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.temp_reporting_threshold.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_type=EntityType.CONFIG,
        min_value=0.2,
        max_value=3.0,
        step=0.1,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="temp_reporting_threshold",
        fallback_name="Temperature reporting threshold",
    )
    .enum(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.temp_reporting_mode.name,
        enum_class=ReportMode,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="temp_reporting_mode",
        fallback_name="Temperature reporting mode",
    )
    .number(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.humidity_reporting_interval.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        device_class=NumberDeviceClass.DURATION,
        entity_type=EntityType.CONFIG,
        min_value=600,
        max_value=3600,
        step=600,
        multiplier=0.001,
        unit=UnitOfTime.SECONDS,
        translation_key="humidity_reporting_interval",
        fallback_name="Humidity reporting interval",
    )
    .number(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.humidity_reporting_threshold.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        device_class=NumberDeviceClass.HUMIDITY,
        entity_type=EntityType.CONFIG,
        min_value=2.0,
        max_value=20.0,
        step=0.5,
        multiplier=0.01,
        unit=PERCENTAGE,
        translation_key="humidity_reporting_threshold",
        fallback_name="Humidity reporting threshold",
    )
    .enum(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.humidity_reporting_mode.name,
        enum_class=ReportMode,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_reporting_mode",
        fallback_name="Humidity reporting mode",
    )
    # Illuminance sampling & reporting
    .enum(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.light_sampling.name,
        enum_class=LightSampling,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="light_sampling",
        fallback_name="Light sampling",
    )
    .number(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.light_sampling_period.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        device_class=NumberDeviceClass.DURATION,
        entity_type=EntityType.CONFIG,
        min_value=0.5,
        max_value=3600.0,
        step=0.5,
        multiplier=0.001,
        unit=UnitOfTime.SECONDS,
        translation_key="light_sampling_period",
        fallback_name="Light sampling period",
    )
    .number(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.light_reporting_interval.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        device_class=NumberDeviceClass.DURATION,
        entity_type=EntityType.CONFIG,
        min_value=20,
        max_value=3600,
        step=20,
        multiplier=0.001,
        unit=UnitOfTime.SECONDS,
        translation_key="light_reporting_interval",
        fallback_name="Light reporting interval",
    )
    .number(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.light_reporting_threshold.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        # Percentage change; omit device_class.
        entity_type=EntityType.CONFIG,
        min_value=3.0,
        max_value=20.0,
        step=0.5,
        multiplier=0.01,
        unit=PERCENTAGE,
        translation_key="light_reporting_threshold",
        fallback_name="Light reporting threshold",
    )
    .enum(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.light_reporting_mode.name,
        enum_class=ReportMode,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="light_reporting_mode",
        fallback_name="Light reporting mode",
    )
    # Maintenance buttons
    .write_attr_button(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.spatial_learning.name,
        attribute_value=1,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="spatial_learning",
        fallback_name="Start spatial learning",
    )
    .write_attr_button(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.restart_device.name,
        attribute_value=1,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="restart_device",
        fallback_name="Restart device",
    )
    # Detection range switches
    .switch(
        attribute_name=FP300DetectionRangeCluster.AttributeDefs.range_0_1m.name,
        cluster_id=FP300DetectionRangeCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="detection_range_0_1m",
        fallback_name="Detection range 0-1 m",
    )
    .switch(
        attribute_name=FP300DetectionRangeCluster.AttributeDefs.range_1_2m.name,
        cluster_id=FP300DetectionRangeCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="detection_range_1_2m",
        fallback_name="Detection range 1-2 m",
    )
    .switch(
        attribute_name=FP300DetectionRangeCluster.AttributeDefs.range_2_3m.name,
        cluster_id=FP300DetectionRangeCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="detection_range_2_3m",
        fallback_name="Detection range 2-3 m",
    )
    .switch(
        attribute_name=FP300DetectionRangeCluster.AttributeDefs.range_3_4m.name,
        cluster_id=FP300DetectionRangeCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="detection_range_3_4m",
        fallback_name="Detection range 3-4 m",
    )
    .switch(
        attribute_name=FP300DetectionRangeCluster.AttributeDefs.range_4_5m.name,
        cluster_id=FP300DetectionRangeCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="detection_range_4_5m",
        fallback_name="Detection range 4-5 m",
    )
    .switch(
        attribute_name=FP300DetectionRangeCluster.AttributeDefs.range_5_6m.name,
        cluster_id=FP300DetectionRangeCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="detection_range_5_6m",
        fallback_name="Detection range 5-6 m",
    )
    .add_to_registry()
)
