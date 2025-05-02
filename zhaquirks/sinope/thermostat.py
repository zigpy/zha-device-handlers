"""Module to handle quirks of the Sinopé Technologies thermostats.

Manufacturer specific cluster implements attributes to control displaying
of outdoor temperature, setting occupancy on/off and setting device time.
"""

from typing import Final

import zigpy.profiles.zha as zha_p
import zigpy.types as t

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.sinope import SINOPE, SINOPE_MANUFACTURER_CLUSTER_ID

from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.quirks.v2 import (
    BinarySensorDeviceClass,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import (
    UnitOfTemperature,
    UnitOfTime,
)
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic, ElectricalMeasurement
from zigpy.zcl.clusters.hvac import Fan, Thermostat, UserInterface
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    ZCLAttributeDef,
    ZCL_CLUSTER_REVISION_ATTR,
)


class KeypadLock(t.enum8):
    """Keypad lockout values."""

    Unlocked = 0x00
    Locked = 0x01
    Partial_lock = 0x02


class Display(t.enum8):
    """Config 2nd display values."""

    Auto = 0x00
    Setpoint = 0x01
    Outside_temperature = 0x02
    Room_temperature = 0x04


class FloorMode(t.enum8):
    """Air floor mode values."""

    Air_by_floor = 0x01
    Floor = 0x02


class AuxMode(t.enum8):
    """Aux output mode values."""

    Off = 0x00
    On_15m = 0x01
    On_15s = 0x02
    Exp_module = 0x03


class DeviceStatus(t.bitmap32):
    """Device general status."""

    Ok = 0x00000000
    Floor_sensor = 0x00000020
    Temp_sensor = 0x00000040


class PumpStatus(t.uint8_t):
    """Pump protection status."""

    Off = 0x00
    On = 0x01


class LimitStatus(t.uint8_t):
    """Floor limit status values."""

    Ok = 0x00
    Low_reached = 0x01
    Max_reached = 0x02
    Max_air_reached = 0x03


class SensorType(t.enum8):
    """Temp sensor type values."""

    Sensor_10k = 0x00
    Sensor_12k = 0x01


class TimeFormat(t.enum8):
    """Time format values."""

    Format_24h = 0x00
    Format_12h = 0x01


class WeatherIcon(t.enum8):
    """weather icons values."""

    Cloud = 0x05
    Cloud2 = 0x08
    Cloud3 = 0x09
    Cloudfog = 0x11
    Cloudlightning = 0x0B
    Cloudlightning2 = 0x0C
    Cloudmoon = 0x13
    Cloudmoon2 = 0x14
    Cloudmoon3 = 0x15
    Cloudrain = 0x0A
    Cloudrain2 = 0x1C
    Cloudrain3 = 0x1D
    Cloudrainmoon = 0x17
    Cloudrainmoon2 = 0x18
    Cloudrainmoon3 = 0x19
    Cloudrainmoon4 = 0x1F
    Cloudrainmoon5 = 0x21
    Cloudrainsun = 0x06
    Cloudrainsun2 = 0x07
    Cloudrainsun3 = 0x1E
    Cloudrainsun4 = 0x20
    Cloudsnow = 0x0D
    Cloudsnow2 = 0x0E
    Cloudsnow3 = 0x0F
    Cloudsnow4 = 0x10
    Cloudsnow5 = 0x16
    Cloudsnow6 = 0x1A
    Cloudsun = 0x03
    Cloudsun2 = 0x04
    Hide = 0x00
    Moonstar = 0x12
    Sun = 0x01
    Sun2 = 0x02


class GfciStatus(t.enum8):
    """Gfci status values."""

    Ok = 0x00
    Error = 0x01


class SystemMode(t.enum8):
    """System mode values."""

    Off = 0x00
    Auto = 0x01
    Cool = 0x03
    Heat = 0x04


class PumpDuration(t.enum8):
    """Pump protection duration period values."""

    T5 = 0x05
    T10 = 0x0A
    T15 = 0x0F
    T20 = 0x14
    T30 = 0x1E
    T60 = 0x3C


class CycleLength(t.uint16_t):
    """Cycle length, 15 sec (15) or 15 min (900 sec)."""

    Sec_15 = 0x000F
    Min_15 = 0x0384


class Occupancy(t.enum8):
    """Set occupancy values."""

    Home = 0x00
    Away = 0x01


class Backlight(t.enum8):
    """Backlight auto dim param values for G2 devices."""

    On_demand = 0x00
    Always_on = 0x01
    Bedroom = 0x02


class Simplebacklight(t.enum8):
    """Backlight auto dim param values for first gen devices."""

    On_demand = 0x00
    Always_on = 0x01


class CycleOutput(t.uint16_t):
    """Main and aux cycle period values."""

    Sec_15 = 0x000F
    Min_5 = 0x012C
    Min_10 = 0x0258
    Min_15 = 0x0384
    Min_20 = 0x04B0
    Min_25 = 0x05DC
    Min_30 = 0x0708
    Off = 0xFFFF


class Language(t.enum8):
    """Display language values."""

    En = 0x00
    Fr = 0x01


class TempFormat(t.enum8):
    """Change temperature display format"""

    Celsius = 0x00
    Fahrenheit = 0x01


class SinopeTechnologiesManufacturerCluster(CustomCluster):
    """SinopeTechnologiesManufacturerCluster manufacturer cluster."""

    KeypadLock: Final = KeypadLock
    Display: Final = Display
    FloorMode: Final = FloorMode
    AuxMode: Final = AuxMode
    PumpStatus: Final = PumpStatus
    Language: Final = Language
    LimitStatus: Final = LimitStatus
    SensorType: Final = SensorType
    TimeFormat: Final = TimeFormat
    WeatherIcon: Final = WeatherIcon
    GfciStatus: Final = GfciStatus
    SystemMode: Final = SystemMode
    PumpDuration: Final = PumpDuration
    CycleLength: Final = CycleLength
    DeviceStatus: Final = DeviceStatus

    cluster_id: Final[t.uint16_t] = SINOPE_MANUFACTURER_CLUSTER_ID
    name: Final = "SinopeTechnologiesManufacturerCluster"
    ep_attribute: Final = "sinope_manufacturer_specific"

    class AttributeDefs(BaseAttributeDefs):
        """Sinope Manufacturer Cluster Attributes."""

        keypad_lockout: Final = ZCLAttributeDef(
            id=0x0002, type=KeypadLock, access="rwp", is_manufacturer_specific=True
        )
        firmware_number: Final = ZCLAttributeDef(
            id=0x0003, type=t.uint16_t, access="rp", is_manufacturer_specific=True
        )
        firmware_version: Final = ZCLAttributeDef(
            id=0x0004,
            type=t.CharacterString,
            access="rp",
            is_manufacturer_specific=True,
        )
        display_language: Final = ZCLAttributeDef(
            id=0x0005, type=Language, access="rwp", is_manufacturer_specific=True
        )
        outdoor_temp: Final = ZCLAttributeDef(
            id=0x0010, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        outdoor_temp_timeout: Final = ZCLAttributeDef(
            id=0x0011, type=t.uint16_t, access="rwp", is_manufacturer_specific=True
        )
        config_2nd_display: Final = ZCLAttributeDef(
            id=0x0012, type=Display, access="rwp", is_manufacturer_specific=True
        )
        weather_icons: Final = ZCLAttributeDef(
            id=0x0013, type=WeatherIcon, access="rwp", is_manufacturer_specific=True
        )
        secs_since_2k: Final = ZCLAttributeDef(
            id=0x0020, type=t.uint32_t, access="rwp", is_manufacturer_specific=True
        )
        current_load: Final = ZCLAttributeDef(
            id=0x0070, type=t.bitmap8, access="rp", is_manufacturer_specific=True
        )
        eco_delta_setpoint: Final = ZCLAttributeDef(
            id=0x0071, type=t.int8s, access="rwp", is_manufacturer_specific=True
        )
        eco_max_pi_heating_demand: Final = ZCLAttributeDef(
            id=0x0072, type=t.uint8_t, access="rwp", is_manufacturer_specific=True
        )
        eco_safety_temperature_delta: Final = ZCLAttributeDef(
            id=0x0073, type=t.uint8_t, access="rwp", is_manufacturer_specific=True
        )
        unknown_attr_1: Final = ZCLAttributeDef(
            id=0x0101, type=Array, access="r", is_manufacturer_specific=True
        )
        setpoint: Final = ZCLAttributeDef(
            id=0x0104, type=t.int16s, access="rw", is_manufacturer_specific=True
        )
        air_floor_mode: Final = ZCLAttributeDef(
            id=0x0105, type=FloorMode, access="rw", is_manufacturer_specific=True
        )
        aux_output_mode: Final = ZCLAttributeDef(
            id=0x0106, type=AuxMode, access="rw", is_manufacturer_specific=True
        )
        floor_temperature: Final = ZCLAttributeDef(
            id=0x0107, type=t.int16s, access="r", is_manufacturer_specific=True
        )
        air_max_limit: Final = ZCLAttributeDef(
            id=0x0108, type=t.int16s, access="rw", is_manufacturer_specific=True
        )
        floor_min_setpoint: Final = ZCLAttributeDef(
            id=0x0109, type=t.int16s, access="rw", is_manufacturer_specific=True
        )
        floor_max_setpoint: Final = ZCLAttributeDef(
            id=0x010A, type=t.int16s, access="rw", is_manufacturer_specific=True
        )
        floor_sensor_type_param: Final = ZCLAttributeDef(
            id=0x010B, type=SensorType, access="rw", is_manufacturer_specific=True
        )
        floor_limit_status: Final = ZCLAttributeDef(
            id=0x010C, type=LimitStatus, access="rp", is_manufacturer_specific=True
        )
        room_temperature: Final = ZCLAttributeDef(
            id=0x010D, type=t.int16s, access="r", is_manufacturer_specific=True
        )
        time_format: Final = ZCLAttributeDef(
            id=0x0114, type=TimeFormat, access="rwp", is_manufacturer_specific=True
        )
        gfci_status: Final = ZCLAttributeDef(
            id=0x0115, type=GfciStatus, access="rp", is_manufacturer_specific=True
        )
        hvac_mode: Final = ZCLAttributeDef(
            id=0x0116, type=SystemMode, access="r", is_manufacturer_specific=True
        )
        aux_connected_load: Final = ZCLAttributeDef(
            id=0x0118, type=t.uint16_t, access="rw", is_manufacturer_specific=True
        )
        connected_load: Final = ZCLAttributeDef(
            id=0x0119, type=t.uint16_t, access="rw", is_manufacturer_specific=True
        )
        pump_protection_status: Final = ZCLAttributeDef(
            id=0x0128, type=PumpStatus, access="rw", is_manufacturer_specific=True
        )
        pump_protection_duration: Final = ZCLAttributeDef(
            id=0x012A, type=PumpDuration, access="rwp", is_manufacturer_specific=True
        )
        current_setpoint: Final = ZCLAttributeDef(
            id=0x012B, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        report_local_temperature: Final = ZCLAttributeDef(
            id=0x012D, type=t.int16s, access="rp", is_manufacturer_specific=True
        )
        balance_point: Final = ZCLAttributeDef(
            id=0x0134, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        weather_icons_timeout: Final = ZCLAttributeDef(
            id=0x0136, type=t.uint16_t, access="rwp", is_manufacturer_specific=True
        )
        abs_min_heat_setpoint_limit: Final = ZCLAttributeDef(
            id=0x0137, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        heat_lockout_temperature: Final = ZCLAttributeDef(
            id=0x0139, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        cool_lockout_temperature: Final = ZCLAttributeDef(
            id=0x013A, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        unknown_attr_11: Final = ZCLAttributeDef(
            id=0x013B, type=t.bitmap8, access="rp", is_manufacturer_specific=True
        )
        status: Final = ZCLAttributeDef(
            id=0x0200, type=DeviceStatus, access="rp", is_manufacturer_specific=True
        )
        unknown_attr_12: Final = ZCLAttributeDef(
            id=0x0202, type=t.enum8, access="r", is_manufacturer_specific=True
        )
        hc_model_mac_addr: Final = ZCLAttributeDef(
            id=0x0267, type=t.EUI64, access="rwp", is_manufacturer_specific=True
        )
        min_heat_setpoint_limit: Final = ZCLAttributeDef(
            id=0x026B, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        max_heat_setpoint_limit: Final = ZCLAttributeDef(
            id=0x026C, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        min_cool_setpoint_limit: Final = ZCLAttributeDef(
            id=0x026D, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        max_cool_setpoint_limit: Final = ZCLAttributeDef(
            id=0x026E, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        cycle_length: Final = ZCLAttributeDef(
            id=0x0281, type=CycleLength, access="rwp", is_manufacturer_specific=True
        )
        cool_cycle_length: Final = ZCLAttributeDef(
            id=0x0282, type=CycleLength, access="rwp", is_manufacturer_specific=True
        )
        cluster_revision: Final = ZCL_CLUSTER_REVISION_ATTR


class SinopeTechnologiesThermostatCluster(CustomCluster, Thermostat):
    """SinopeTechnologiesThermostatCluster custom cluster."""

    Occupancy: Final = Occupancy
    Backlight: Final = Backlight
    CycleOutput: Final = CycleOutput

    class AttributeDefs(Thermostat.AttributeDefs):
        """Sinope Manufacturer Thermostat Cluster Attributes."""

        set_occupancy: Final = ZCLAttributeDef(
            id=0x0400, type=Occupancy, access="rw", is_manufacturer_specific=True
        )
        main_cycle_output: Final = ZCLAttributeDef(
            id=0x0401, type=CycleOutput, access="rw", is_manufacturer_specific=True
        )
        backlight_auto_dim_param: Final = ZCLAttributeDef(
            id=0x0402, type=Backlight, access="rw", is_manufacturer_specific=True
        )
        aux_cycle_output: Final = ZCLAttributeDef(
            id=0x0404, type=CycleOutput, access="rw", is_manufacturer_specific=True
        )


class SinopeTechnologiesElectricalMeasurementCluster(
    CustomCluster, ElectricalMeasurement
):
    """SinopeTechnologiesElectricalMeasurementCluster custom cluster."""

    class AttributeDefs(ElectricalMeasurement.AttributeDefs):
        """Sinope Manufacturer ElectricalMeasurement Cluster Attributes."""

        current_summation_delivered: Final = ZCLAttributeDef(
            id=0x0551, type=t.uint32_t, access="rwp", is_manufacturer_specific=True
        )
        aux_setpoint_min: Final = ZCLAttributeDef(
            id=0x0552, type=t.uint32_t, access="rw", is_manufacturer_specific=True
        )
        aux_setpoint_max: Final = ZCLAttributeDef(
            id=0x0553, type=t.uint32_t, access="rw", is_manufacturer_specific=True
        )


(
    # <SimpleDescriptor endpoint=1 profile=260 device_type=769
    # device_version=0 input_clusters=[0, 3, 4, 5, 513, 516, 1026, 2820,
    # 2821, 65281] output_clusters=[65281, 25]>
    # <SimpleDescriptor endpoint=196 profile=49757 device_type=769
    # device_version=0 input_clusters=[1] output_clusters=[]>
    QuirkBuilder(SINOPE, "TH1123ZB")
    .applies_to(SINOPE, "TH1124ZB")
    .applies_to(SINOPE, "TH1500ZB")
    .replaces(SinopeTechnologiesElectricalMeasurementCluster)
    .replaces(SinopeTechnologiesThermostatCluster)
    .replaces(SinopeTechnologiesManufacturerCluster)
    .enum( # Keypad lock
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.keypad_lockout.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=KeypadLock,
        translation_key="keypad_lockout",
        fallback_name="Keypad lockout",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Config second display
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.config_2nd_display.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=Display,
        translation_key="config_2nd_display",
        fallback_name="Config 2nd display",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Config backlight auto dim
        attribute_name=SinopeTechnologiesThermostatCluster.AttributeDefs.backlight_auto_dim_param.name,
        cluster_id=SinopeTechnologiesThermostatCluster.cluster_id,
        enum_class=Simplebacklight,
        translation_key="backlight_auto_dim",
        fallback_name="Backlight auto dim",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Temperature format
        attribute_name=UserInterface.AttributeDefs.temperature_display_mode.name,
        cluster_id=UserInterface.cluster_id,
        enum_class=TempFormat,
        translation_key="temperature_display_mode",
        fallback_name="Temperature display mode",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Time format
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.time_format.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=TimeFormat,
        translation_key="time_format",
        fallback_name="Time format",
        entity_type=EntityType.CONFIG,
    )
    .number( # eco delta setpoint
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.eco_delta_setpoint.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        step=1,
        min_value=-128,
        max_value=100,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="eco_delta_setpoint",
        fallback_name="Eco delta setpoint",
    )
    .sensor( # Device status
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.status.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)

(
    # <SimpleDescriptor endpoint=1 profile=260 device_type=769 device_version=1
    # input_clusters=[0, 3, 4, 5, 513, 516, 1026, 1794, 2821, 65281]
    # output_clusters=[10, 65281, 25]>
    QuirkBuilder(SINOPE, "TH1400ZB")
    .replaces(SinopeTechnologiesThermostatCluster)
    .replaces(SinopeTechnologiesManufacturerCluster)
    .enum( # Keypad lock
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.keypad_lockout.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=KeypadLock,
        translation_key="keypad_lockout",
        fallback_name="Keypad lockout",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Config second display
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.config_2nd_display.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=Display,
        translation_key="config_2nd_display",
        fallback_name="Config 2nd display",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Pump protection duration
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.pump_protection_duration.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=PumpDuration,
        translation_key="pump_protection_duration",
        fallback_name="Pump protection duration",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Config backlight auto dim
        attribute_name=SinopeTechnologiesThermostatCluster.AttributeDefs.backlight_auto_dim_param.name,
        cluster_id=SinopeTechnologiesThermostatCluster.cluster_id,
        enum_class=Simplebacklight,
        translation_key="backlight_auto_dim",
        fallback_name="Backlight auto dim",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Temperature format
        attribute_name=UserInterface.AttributeDefs.temperature_display_mode.name,
        cluster_id=UserInterface.cluster_id,
        enum_class=TempFormat,
        translation_key="temperature_display_mode",
        fallback_name="Temperature display mode",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Time format
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.time_format.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=TimeFormat,
        translation_key="time_format",
        fallback_name="Time format",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Aux mode
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.aux_output_mode.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=AuxMode,
        translation_key="aux_output_mode",
        fallback_name="Aux output mode",
        entity_type=EntityType.CONFIG,
    )
    .sensor( # floor_limit_status
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.floor_limit_status.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=3600, reportable_change=1
        ),
        translation_key="floor_limit_status",
        fallback_name="Floor limit status",
        entity_type=EntityType.CONFIG,
    )
    .switch( # Pump protection status
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.pump_protection_status.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        endpoint_id=1,
        translation_key="pump_protection_status",
        fallback_name="Pump protection status",
        entity_type=EntityType.CONFIG,
    )
    .number( # eco delta setpoint
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.eco_delta_setpoint.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        step=1,
        min_value=-128,
        max_value=100,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="eco_delta_setpoint",
        fallback_name="Eco delta setpoint",
    )
    .sensor( # Device status
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.status.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)

(
    # <SimpleDescriptor endpoint=1 profile=260 device_type=769 device_version=1
    # input_clusters=[0, 3, 4, 5, 513, 516, 1026, 1794, 2820, 2821, 65281]
    # output_clusters=[10, 25, 65281]>
    QuirkBuilder(SINOPE, "TH1300ZB")
    .replaces(SinopeTechnologiesElectricalMeasurementCluster)
    .replaces(SinopeTechnologiesThermostatCluster)
    .replaces(SinopeTechnologiesManufacturerCluster)
    .enum( # Keypad lock
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.keypad_lockout.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=KeypadLock,
        translation_key="keypad_lockout",
        fallback_name="Keypad lockout",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Config second display
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.config_2nd_display.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=Display,
        translation_key="config_2nd_display",
        fallback_name="Config 2nd display",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Config air floor mode
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.air_floor_mode.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=FloorMode,
        translation_key="air_floor_mode",
        fallback_name="Air floor mode",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Pump protection duration
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.pump_protection_duration.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=PumpDuration,
        translation_key="pump_protection_duration",
        fallback_name="Pump protection duration",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Config backlight auto dim
        attribute_name=SinopeTechnologiesThermostatCluster.AttributeDefs.backlight_auto_dim_param.name,
        cluster_id=SinopeTechnologiesThermostatCluster.cluster_id,
        enum_class=Simplebacklight,
        translation_key="backlight_auto_dim",
        fallback_name="Backlight auto dim",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Temperature format
        attribute_name=UserInterface.AttributeDefs.temperature_display_mode.name,
        cluster_id=UserInterface.cluster_id,
        enum_class=TempFormat,
        translation_key="temperature_display_mode",
        fallback_name="Temperature display mode",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Time format
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.time_format.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=TimeFormat,
        translation_key="time_format",
        fallback_name="Time format",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Aux mode
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.aux_output_mode.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=AuxMode,
        translation_key="aux_output_mode",
        fallback_name="Aux output mode",
        entity_type=EntityType.CONFIG,
    )
    .sensor( # floor_limit_status
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.floor_limit_status.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=3600, reportable_change=1
        ),
        translation_key="floor_limit_status",
        fallback_name="Floor limit status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor( # Gfci status
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.gfci_status.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=3600, reportable_change=1
        ),
        translation_key="gfci_status",
        fallback_name="Gfci status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .switch( # Floor sensor type
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.floor_sensor_type_param.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        endpoint_id=1,
        translation_key="floor_sensor_type",
        fallback_name="Floor sensor type",
        entity_type=EntityType.CONFIG,
    )
    .number( # eco delta setpoint
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.eco_delta_setpoint.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        step=1,
        min_value=-128,
        max_value=100,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="eco_delta_setpoint",
        fallback_name="Eco delta setpoint",
    )
    .sensor( # Device status
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.status.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)

(
    # <SimpleDescriptor endpoint=1 profile=260 device_type=769 device_version=1
    # input_clusters=[0, 3, 4, 5, 513, 516, 1026, 1794, 2820, 2821, 65281]
    # output_clusters=[10, 25, 65281]>
    QuirkBuilder(SINOPE, "TH1123ZB")
    .applies_to(SINOPE, "TH1124ZB")
    .applies_to(SINOPE, "TH1500ZB")
    .applies_to(SINOPE, "OTH3600-GA-ZB")
    .replaces(SinopeTechnologiesElectricalMeasurementCluster)
    .replaces(SinopeTechnologiesThermostatCluster)
    .replaces(SinopeTechnologiesManufacturerCluster)
    .enum( # Keypad lock
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.keypad_lockout.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=KeypadLock,
        translation_key="keypad_lockout",
        fallback_name="Keypad lockout",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Config second display
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.config_2nd_display.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=Display,
        translation_key="config_2nd_display",
        fallback_name="Config 2nd display",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Config backlight auto dim
        attribute_name=SinopeTechnologiesThermostatCluster.AttributeDefs.backlight_auto_dim_param.name,
        cluster_id=SinopeTechnologiesThermostatCluster.cluster_id,
        enum_class=Simplebacklight,
        translation_key="backlight_auto_dim",
        fallback_name="Backlight auto dim",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Temperature format
        attribute_name=UserInterface.AttributeDefs.temperature_display_mode.name,
        cluster_id=UserInterface.cluster_id,
        enum_class=TempFormat,
        translation_key="temperature_display_mode",
        fallback_name="Temperature display mode",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Time format
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.time_format.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=TimeFormat,
        translation_key="time_format",
        fallback_name="Time format",
        entity_type=EntityType.CONFIG,
    )
    .number( # eco delta setpoint
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.eco_delta_setpoint.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        step=1,
        min_value=-128,
        max_value=100,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="eco_delta_setpoint",
        fallback_name="Eco delta setpoint",
    )
    .sensor( # Device status
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.status.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)

(
    # <SimpleDescriptor endpoint=1 profile=260 device_type=769 device_version=1
    # input_clusters=[0, 3, 4, 5, 513, 516, 1026, 1794, 2820, 2821, 65281]
    # output_clusters=[3, 10, 25]>
    QuirkBuilder(SINOPE, "TH1123ZB-G2")
    .applies_to(SINOPE, "TH1124ZB-G2")
    .replaces(SinopeTechnologiesElectricalMeasurementCluster)
    .replaces(SinopeTechnologiesThermostatCluster)
    .replaces(SinopeTechnologiesManufacturerCluster)
    .enum( # Keypad lock
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.keypad_lockout.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=KeypadLock,
        translation_key="keypad_lockout",
        fallback_name="Keypad lockout",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Config second display
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.config_2nd_display.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=Display,
        translation_key="config_2nd_display",
        fallback_name="Config 2nd display",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Config backlight auto dim
        attribute_name=SinopeTechnologiesThermostatCluster.AttributeDefs.backlight_auto_dim_param.name,
        cluster_id=SinopeTechnologiesThermostatCluster.cluster_id,
        enum_class=Backlight,
        translation_key="backlight_auto_dim",
        fallback_name="Backlight auto dim",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Temperature format
        attribute_name=UserInterface.AttributeDefs.temperature_display_mode.name,
        cluster_id=UserInterface.cluster_id,
        enum_class=TempFormat,
        translation_key="temperature_display_mode",
        fallback_name="Temperature display mode",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Time format
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.time_format.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=TimeFormat,
        translation_key="time_format",
        fallback_name="Time format",
        entity_type=EntityType.CONFIG,
    )
    .number( # eco delta setpoint
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.eco_delta_setpoint.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        step=1,
        min_value=-128,
        max_value=100,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="eco_delta_setpoint",
        fallback_name="Eco delta setpoint",
    )
    .sensor( # Device status
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.status.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)

(
    # <SimpleDescriptor endpoint=1 profile=260 device_type=775 device_version=1
    # input_clusters=[0, 3, 4, 5, 8, 513, 514, 516, 1026, 2821, 65281]
    # output_clusters=[25]>
    # <SimpleDescriptor endpoint=2 profile=260 device_type=775 device_version=1
    # input_clusters=[0, 3, 4, 5, 8, 513, 514, 516, 1026, 2821, 65281]
    # output_clusters=[25]>
    QuirkBuilder(SINOPE, "HP6000ZB-GE")
    .applies_to(SINOPE, "HP6000ZB-HS")
    .applies_to(SINOPE, "HP6000ZB-MA")
    .adds_endpoint(1, device_type=zha_p.DeviceType.MINI_SPLIT_AC)
    .adds_endpoint(2, device_type=zha_p.DeviceType.MINI_SPLIT_AC)
    .replaces(SinopeTechnologiesThermostatCluster, endpoint_id=1)
    .replaces(SinopeTechnologiesManufacturerCluster, endpoint_id=1)
    .replaces(SinopeTechnologiesThermostatCluster, endpoint_id=2)
    .replaces(SinopeTechnologiesManufacturerCluster, endpoint_id=2)
    .enum( # Keypad lock
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.keypad_lockout.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=KeypadLock,
        translation_key="keypad_lockout",
        fallback_name="Keypad lockout",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Config second display
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.config_2nd_display.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=Display,
        translation_key="config_2nd_display",
        fallback_name="Config 2nd display",
        entity_type=EntityType.CONFIG,
    )
    .number( # eco delta setpoint
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.eco_delta_setpoint.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        step=1,
        min_value=-128,
        max_value=100,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="eco_delta_setpoint",
        fallback_name="Eco delta setpoint",
    )
    .sensor( # Device status
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.status.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)

(
    # <SimpleDescriptor endpoint=1 profile=260 device_type=769 device_version=1
    # input_clusters=[0, 3, 4, 5, 513, 514, 516, 1026, 1794, 2820, 2821, 65281]
    # output_clusters=[3, 10, 25]>
    QuirkBuilder(SINOPE, "TH1134ZB-HC")
    .replaces(SinopeTechnologiesElectricalMeasurementCluster)
    .replaces(SinopeTechnologiesThermostatCluster)
    .replaces(SinopeTechnologiesManufacturerCluster)
    .enum( # Keypad lock
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.keypad_lockout.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=KeypadLock,
        translation_key="keypad_lockout",
        fallback_name="Keypad lockout",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Config second display
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.config_2nd_display.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=Display,
        translation_key="config_2nd_display",
        fallback_name="Config 2nd display",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Display language
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.display_language.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=Language,
        translation_key="display_language",
        fallback_name="Display language",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Weather icons
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.weather_icons.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=WeatherIcon,
        translation_key="weather_icons",
        fallback_name="Weather icons",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Config backlight auto dim
        attribute_name=SinopeTechnologiesThermostatCluster.AttributeDefs.backlight_auto_dim_param.name,
        cluster_id=SinopeTechnologiesThermostatCluster.cluster_id,
        enum_class=Backlight,
        translation_key="backlight_auto_dim",
        fallback_name="Backlight auto dim",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Temperature format
        attribute_name=UserInterface.AttributeDefs.temperature_display_mode.name,
        cluster_id=UserInterface.cluster_id,
        enum_class=TempFormat,
        translation_key="temperature_display_mode",
        fallback_name="Temperature display mode",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Time format
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.time_format.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=TimeFormat,
        translation_key="time_format",
        fallback_name="Time format",
        entity_type=EntityType.CONFIG,
    )
    .enum( # Aux mode
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.aux_output_mode.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        enum_class=AuxMode,
        translation_key="aux_output_mode",
        fallback_name="Aux output mode",
        entity_type=EntityType.CONFIG,
    )
    .number( # weather icons timeout
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.weather_icons_timeout.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        step=10,
        min_value=0,
        max_value=18000,
        translation_key="icons_timeout",
        fallback_name="Icons timeout",
        unit=UnitOfTime.SECONDS,
    )
    .number( # eco delta setpoint
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.eco_delta_setpoint.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        step=1,
        min_value=-128,
        max_value=100,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="eco_delta_setpoint",
        fallback_name="Eco delta setpoint",
    )
    .sensor( # Device status
        attribute_name=SinopeTechnologiesManufacturerCluster.AttributeDefs.status.name,
        cluster_id=SinopeTechnologiesManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)
