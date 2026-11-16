"""Excellux NTCHT01 (ZG-105NTH) temperature/humidity sensor with external probe.

Tuya TS0601 device that reports TWO temperatures on two datapoints with
DIFFERENT scales, plus humidity and battery:

    dp 1    probe (external) temperature   raw = TENTHS of a degree
    dp 5    body (internal) temperature    raw = HUNDREDTHS of a degree
    dp 118  humidity                       raw = HUNDREDTHS of a percent
    dp 4    battery                        raw = percent (0-100)

Reference: zigbee-herdsman-converters, src/devices/tuya.ts, model "ZG-105NTH"
(fingerprint Excellux / NTCHT01):

    [1,   "probe_temperature", tuya.valueConverter.divideBy10]
    [5,   "temperature",       tuya.valueConverter.divideBy100]
    [118, "humidity",          tuya.valueConverter.divideBy100]
    [4,   "battery",           tuya.valueConverter.raw]

The device also periodically emits a standard ZCL Report_Attributes on the
0x0402 cluster carrying the probe reading as raw tenths (e.g. 243 == 24.3 C).
The standard 0x0402 cluster expects hundredths of a degree, so such a report
displays a value exactly 10x too small (2.43 C) until the next Tuya datapoint
report arrives. Zigbee2MQTT avoids this by converting only the Tuya
datapoints, so this quirk does the same: Ntcht01LocalCluster drops
device-originated Report_Attributes on the virtual 0x0402 / 0x0405 clusters
and keeps the Tuya datapoint path as the single source of state.
"""

from zigpy import types as t
from zigpy.typing import AddressingMode
from zigpy.zcl import foundation
from zigpy.zcl.foundation import ZCLHeader

from zhaquirks.builder import (
    PERCENTAGE,
    EntityPlatform,
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.tuya.builder import (
    TuyaLocalCluster,
    TuyaQuirkBuilder,
    TuyaRelativeHumidity,
    TuyaTemperatureMeasurement,
)


class Ntcht01ProbeTempWarning(t.enum8):
    """Tuya probe temperature warning enum."""

    Normal = 0x00
    Low = 0x01
    High = 0x02


class Ntcht01TempWarning(t.enum8):
    """Tuya body temperature warning enum."""

    Normal = 0x00
    Low = 0x01
    High = 0x02


class Ntcht01HumiWarning(t.enum8):
    """Tuya humidity warning enum."""

    Normal = 0x00
    Low = 0x01
    High = 0x02


class Ntcht01LocalCluster(TuyaLocalCluster):
    """A Tuya local cluster that is fed only from Tuya datapoint reports.

    The device periodically emits a standard ZCL Report_Attributes frame on
    the 0x0402/0x0405 clusters carrying the raw reading in the wrong decimal
    scale (see module docstring). Like Zigbee2MQTT's ZG-105NTH definition,
    state here is fed exclusively from the Tuya datapoint converter, so
    device-originated attribute reports on this virtual cluster are dropped
    (with a debug log) instead of corrupting the last good value. A default
    response is still sent when the device asks for one.

    The datapoint path is unaffected: it reaches the attribute through
    ``update_attribute(name, value)``, not through the ZCL request path
    intercepted here.
    """

    def handle_cluster_general_request(
        self,
        hdr: ZCLHeader,
        args: list,
        *,
        dst_addressing: AddressingMode | None = None,
    ) -> None:
        """Ignore the device's periodic raw attribute reports."""
        if hdr.command_id == foundation.GeneralCommand.Report_Attributes:
            if not hdr.frame_control.disable_default_response:
                self.send_default_rsp(hdr, foundation.Status.SUCCESS)
            self.debug(
                "Ignoring device Report_Attributes on %s; "
                "state is fed from Tuya datapoints only",
                self.cluster_id,
            )
            return
        super().handle_cluster_general_request(hdr, args, dst_addressing=dst_addressing)


class Ntcht01TemperatureMeasurement(Ntcht01LocalCluster, TuyaTemperatureMeasurement):
    """0x0402 Temperature cluster, datapoint-driven only (no raw reports)."""


class Ntcht01RelativeHumidity(Ntcht01LocalCluster, TuyaRelativeHumidity):
    """0x0405 Relative Humidity cluster, datapoint-driven only (no raw reports)."""


# Excellux ZG-105NTH Temperature and Humidity Sensor with Probe
# White-label: ZG-106NTH (NTCHT02), EZ-L01NTH (NTCHT03)
(
    TuyaQuirkBuilder("Excellux", "NTCHT01")
    .applies_to("Excellux", "NTCHT02")
    .applies_to("Excellux", "NTCHT03")
    .applies_to("NTCHT01", "Excellux")
    .tuya_temperature(
        dp_id=5,
        scale=1,
        temp_cfg=Ntcht01TemperatureMeasurement,
    )
    .tuya_battery(dp_id=4)
    .tuya_sensor(
        dp_id=1,
        attribute_name="probe_temperature",
        type=t.int16s,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="probe_temperature",
        fallback_name="Probe temperature",
    )
    .tuya_humidity(dp_id=118, scale=1, rh_cfg=Ntcht01RelativeHumidity)
    .tuya_number(
        dp_id=101,
        attribute_name="sampling_interval",
        type=t.uint16_t,
        unit=UnitOfTime.SECONDS,
        min_value=5,
        max_value=1200,
        step=5,
        entity_type=EntityType.CONFIG,
        translation_key="sampling_interval",
        fallback_name="Sampling interval",
    )
    .tuya_number(
        dp_id=108,
        attribute_name="probe_temperature_calibration",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-2,
        max_value=2,
        step=0.1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="probe_temperature_calibration",
        fallback_name="Probe temperature calibration",
    )
    .tuya_number(
        dp_id=109,
        attribute_name="probe_temperature_v0_set",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-40,
        max_value=125,
        step=0.1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="probe_temperature_v0_set",
        fallback_name="Probe temperature v0 threshold",
    )
    .tuya_number(
        dp_id=110,
        attribute_name="probe_temperature_v1_set",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-40,
        max_value=125,
        step=0.1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="probe_temperature_v1_set",
        fallback_name="Probe temperature v1 threshold",
    )
    .tuya_enum(
        dp_id=112,
        attribute_name="probe_temperature_warning",
        enum_class=Ntcht01ProbeTempWarning,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="probe_temperature_warning",
        fallback_name="Probe temperature warning",
    )
    .tuya_number(
        dp_id=114,
        attribute_name="temperature_calibration",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-2,
        max_value=2,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_calibration",
        fallback_name="Temperature calibration",
    )
    .tuya_number(
        dp_id=115,
        attribute_name="temperature_v0_set",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-40,
        max_value=85,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_v0_set",
        fallback_name="Temperature v0 threshold",
    )
    .tuya_number(
        dp_id=116,
        attribute_name="temperature_v1_set",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-40,
        max_value=85,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_v1_set",
        fallback_name="Temperature v1 threshold",
    )
    .tuya_enum(
        dp_id=117,
        attribute_name="temperature_warning",
        enum_class=Ntcht01TempWarning,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="temperature_warning",
        fallback_name="Temperature warning",
    )
    .tuya_number(
        dp_id=119,
        attribute_name="humidity_calibration",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=-10,
        max_value=10,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_calibration",
        fallback_name="Humidity calibration",
    )
    .tuya_number(
        dp_id=120,
        attribute_name="humidity_v0_set",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=0,
        max_value=100,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_v0_set",
        fallback_name="Humidity v0 threshold",
    )
    .tuya_number(
        dp_id=121,
        attribute_name="humidity_v1_set",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=0,
        max_value=100,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_v1_set",
        fallback_name="Humidity v1 threshold",
    )
    .tuya_enum(
        dp_id=122,
        attribute_name="humidity_warning",
        enum_class=Ntcht01HumiWarning,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="humidity_warning",
        fallback_name="Humidity warning",
    )
    .skip_configuration()
    .add_to_registry()
)
