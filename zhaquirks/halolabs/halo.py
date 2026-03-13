"""Device handler for Halo Smart Labs smoke & CO detectors."""

from typing import Final

import zigpy.types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, ReportingConfig
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant.binary_sensor import (
    BinarySensorDeviceClass,
)
from zigpy.quirks.v2.homeassistant.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.halolabs import HALO_SMART_LABS

HALO_MANUFACTURER_CODE = 0x1201

# -- Reporting configs --

HALO_STATUS_REPORT_CONFIG = ReportingConfig(
    min_interval=1, max_interval=900, reportable_change=1
)
CO_PPM_REPORT_CONFIG = ReportingConfig(
    min_interval=10, max_interval=3600, reportable_change=1
)


# -- Enum types --


class HaloAlertState(t.enum8):
    """Halo device alert state values."""

    Safe = 0x00
    Low_battery = 0x01
    End_of_life = 0x02
    Pre_smoke = 0x04
    Weather = 0x05
    Carbon_monoxide = 0x06
    Smoke = 0x07
    Other = 0x08
    Silenced = 0x09
    Very_low_battery = 0x0A
    Failed_battery = 0x0B
    CO_test = 0x0E
    Smoke_test = 0x10
    Interconnect_CO = 0x12
    Interconnect_smoke = 0x13


class HaloTestStatus(t.enum8):
    """Halo self-test result values."""

    Success = 0x00
    Fail_ion = 0x01
    Fail_photo = 0x02
    Fail_CO = 0x03
    Fail_temperature = 0x04
    Fail_weather = 0x05
    Fail_other = 0x06
    Running = 0x07


class HaloHushStatus(t.enum8):
    """Halo hush status values."""

    Success = 0x00
    Timeout = 0x01
    Ready = 0x02
    Disabled = 0x03


class HaloRoom(t.enum8):
    """Halo room assignment values."""

    Basement = 0x00
    Bedroom = 0x01
    Den = 0x02
    Dining_room = 0x03
    Downstairs = 0x04
    Entryway = 0x05
    Family_room = 0x06
    Game_room = 0x07
    Guest_bedroom = 0x08
    Hallway = 0x09
    Kids_bedroom = 0x0A
    Living_room = 0x0B
    Master_bedroom = 0x0C
    Office = 0x0D
    Study = 0x0E
    Upstairs = 0x0F
    Workout_room = 0x10
    No_room = 0xFF


class WeatherAlertCode(t.enum8):
    """NOAA/SAME weather alert code values."""

    NONE = 0x00
    AVA = 0x01
    AVW = 0x02
    BZW = 0x03
    CFA = 0x04
    CFW = 0x05
    DSW = 0x06
    EQW = 0x07
    FFA = 0x08
    FFS = 0x09
    FFW = 0x0A
    FLA = 0x0B
    FLS = 0x0C
    FLW = 0x0D
    FRW = 0x0E
    FSW = 0x0F
    FZW = 0x10
    HLS = 0x11
    HUA = 0x12
    HUW = 0x13
    HWA = 0x14
    HWW = 0x15
    SPS = 0x16
    SVA = 0x17
    SVR = 0x18
    SVS = 0x19
    TOA = 0x1A
    TOR = 0x1B
    TRA = 0x1C
    TRW = 0x1D
    TSA = 0x1E
    TSW = 0x1F
    VOW = 0x20
    WSA = 0x21
    WSW = 0x22
    ADR = 0x23
    NIC = 0x24
    NMN = 0x25
    CAE = 0x26
    LAE = 0x27
    TOE = 0x28
    DMO = 0x29
    NAT = 0x2A
    NPT = 0x2B
    NST = 0x2C
    RMT = 0x2D
    RWT = 0x2E
    CDW = 0x2F
    CEM = 0x30
    EAN = 0x31
    EAT = 0x32
    EVI = 0x33
    HMW = 0x34
    NUW = 0x35
    RHW = 0x36
    SPW = 0x37
    LEW = 0x38
    SMW = 0x39
    Unrecognized_S = 0x3A
    Unrecognized_M = 0x3B
    Unrecognized_E = 0x3C
    Unrecognized_A = 0x3D
    Unrecognized_W = 0x3E
    BHW = 0x3F
    BWW = 0x40
    CHW = 0x41
    CWW = 0x42
    DBA = 0x43
    DBW = 0x44
    DEW = 0x45
    EVA = 0x46
    FCW = 0x47
    IBW = 0x48
    IFW = 0x49
    LSW = 0x4A
    POS = 0x4B
    WFA = 0x4C
    WFW = 0x4D
    EWW = 0x4E
    SSA = 0x4F
    SSW = 0x50


# -- Custom clusters --


class HaloStatusCluster(CustomCluster):
    """Halo device status cluster (0xFD00)."""

    cluster_id: Final[t.uint16_t] = 0xFD00
    name: str = "Halo Device Status"
    ep_attribute: str = "halo_device_status"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        device_status: Final = ZCLAttributeDef(
            id=0x0000, type=HaloAlertState, manufacturer_code=HALO_MANUFACTURER_CODE
        )
        room: Final = ZCLAttributeDef(
            id=0x0002, type=HaloRoom, access="rwp",
            manufacturer_code=HALO_MANUFACTURER_CODE,
        )


class HaloControlCluster(CustomCluster):
    """Halo control cluster (0xFD01) for test and hush commands."""

    cluster_id: Final[t.uint16_t] = 0xFD01
    name: str = "Halo Control"
    ep_attribute: str = "halo_control"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        test_status: Final = ZCLAttributeDef(
            id=0x0000, type=HaloTestStatus,
            manufacturer_code=HALO_MANUFACTURER_CODE,
        )
        hush_status: Final = ZCLAttributeDef(
            id=0x0001, type=HaloHushStatus,
            manufacturer_code=HALO_MANUFACTURER_CODE,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        halo_test: Final = ZCLCommandDef(
            id=0x00,
            schema={"value": t.uint8_t},
            is_manufacturer_specific=True,
        )
        halo_hush: Final = ZCLCommandDef(
            id=0x01,
            schema={"value": t.uint8_t},
            is_manufacturer_specific=True,
        )


class HaloSensorsCluster(CustomCluster):
    """Halo sensors cluster (0xFD02) for CO PPM readings."""

    cluster_id: Final[t.uint16_t] = 0xFD02
    name: str = "Halo Sensors"
    ep_attribute: str = "halo_sensors"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        co_ppm: Final = ZCLAttributeDef(
            id=0x0002, type=t.int16s,
            manufacturer_code=HALO_MANUFACTURER_CODE,
        )


class HaloWeatherCluster(CustomCluster):
    """Halo weather cluster (0xFD03) for weather radio (Halo+ only)."""

    cluster_id: Final[t.uint16_t] = 0xFD03
    name: str = "Halo Weather"
    ep_attribute: str = "halo_weather"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        weather_alert_status: Final = ZCLAttributeDef(
            id=0x0000, type=WeatherAlertCode,
            manufacturer_code=HALO_MANUFACTURER_CODE,
        )
        weather_mute: Final = ZCLAttributeDef(
            id=0x0001, type=t.Bool,
            manufacturer_code=HALO_MANUFACTURER_CODE,
        )
        weather_location: Final = ZCLAttributeDef(
            id=0x0002, type=t.uint32_t, access="rwp",
            manufacturer_code=HALO_MANUFACTURER_CODE,
        )
        weather_event1: Final = ZCLAttributeDef(
            id=0x0003, type=t.bitmap32,
            manufacturer_code=HALO_MANUFACTURER_CODE,
        )
        weather_event2: Final = ZCLAttributeDef(
            id=0x0004, type=t.bitmap32,
            manufacturer_code=HALO_MANUFACTURER_CODE,
        )
        weather_event3: Final = ZCLAttributeDef(
            id=0x0005, type=t.bitmap32,
            manufacturer_code=HALO_MANUFACTURER_CODE,
        )
        weather_station: Final = ZCLAttributeDef(
            id=0x0006, type=t.uint8_t, access="rwp",
            manufacturer_code=HALO_MANUFACTURER_CODE,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        weather_scan: Final = ZCLCommandDef(
            id=0x00,
            schema={},
            is_manufacturer_specific=True,
        )
        weather_radio_play: Final = ZCLCommandDef(
            id=0x03,
            schema={"value": t.uint8_t},
            is_manufacturer_specific=True,
        )


class HaloColorCluster(CustomCluster, Color):
    """Fix color capabilities for the Halo nightlight LED on EP2.

    The device does not correctly report its color capabilities.
    Force HS color + color temperature support.
    """

    _CONSTANT_ATTRIBUTES = {
        Color.AttributeDefs.color_capabilities.id: (
            Color.ColorCapabilities.Hue_and_saturation
            | Color.ColorCapabilities.XY_attributes
        ),
        Color.AttributeDefs.color_temp_physical_min.id: 153,
        Color.AttributeDefs.color_temp_physical_max.id: 500,
    }


# -- Halo quirk (base smoke & CO detector) --

(
    QuirkBuilder(HALO_SMART_LABS, "halo")
    .replaces(HaloColorCluster, endpoint_id=2)
    .replaces(HaloStatusCluster, endpoint_id=4)
    .replaces(HaloControlCluster, endpoint_id=4)
    .replaces(HaloSensorsCluster, endpoint_id=4)
    # -- IAS Zone binary sensors (extra bits from zone_status) --
    # Tamper (EP1, zone_status bit 2)
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
        unique_id_suffix="tamper",
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Tamper",
    )
    # Battery low (EP1, zone_status bit 3)
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.BATTERY,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Battery),
        unique_id_suffix="battery_low",
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Battery low",
    )
    # Test mode (EP1, zone_status bit 8)
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=1,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Test),
        unique_id_suffix="test_mode",
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="test_mode",
        fallback_name="Test mode",
    )
    # Mains power connected (EP1, zone_status bit 7, inverted)
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.PLUG,
        attribute_converter=lambda value: not bool(value & IasZone.ZoneStatus.AC_mains),
        unique_id_suffix="mains_power",
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Mains power",
    )
    # -- Halo status cluster entities (EP4) --
    # Alert state (read-only diagnostic sensor)
    .enum(
        attribute_name=HaloStatusCluster.AttributeDefs.device_status.name,
        enum_class=HaloAlertState,
        cluster_id=HaloStatusCluster.cluster_id,
        endpoint_id=4,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=HALO_STATUS_REPORT_CONFIG,
        translation_key="halo_alert_state",
        fallback_name="Alert state",
    )
    # Weather alert active (derived from device_status == Weather)
    .binary_sensor(
        attribute_name=HaloStatusCluster.AttributeDefs.device_status.name,
        cluster_id=HaloStatusCluster.cluster_id,
        endpoint_id=4,
        attribute_converter=lambda value: value == HaloAlertState.Weather,
        unique_id_suffix="weather_alert",
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="weather_alert",
        fallback_name="Weather alert",
    )
    # Room assignment (writable select)
    .enum(
        attribute_name=HaloStatusCluster.AttributeDefs.room.name,
        enum_class=HaloRoom,
        cluster_id=HaloStatusCluster.cluster_id,
        endpoint_id=4,
        translation_key="room",
        fallback_name="Room",
    )
    # -- Halo control cluster entities (EP4) --
    # Test result (read-only diagnostic sensor)
    .enum(
        attribute_name=HaloControlCluster.AttributeDefs.test_status.name,
        enum_class=HaloTestStatus,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=HALO_STATUS_REPORT_CONFIG,
        translation_key="halo_test_result",
        fallback_name="Test result",
    )
    # Test in progress (derived from test_status == Running)
    .binary_sensor(
        attribute_name=HaloControlCluster.AttributeDefs.test_status.name,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        device_class=BinarySensorDeviceClass.RUNNING,
        attribute_converter=lambda value: value == HaloTestStatus.Running,
        unique_id_suffix="test_in_progress",
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Test in progress",
    )
    # Hush state (read-only diagnostic sensor)
    .enum(
        attribute_name=HaloControlCluster.AttributeDefs.hush_status.name,
        enum_class=HaloHushStatus,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=HALO_STATUS_REPORT_CONFIG,
        translation_key="halo_hush_state",
        fallback_name="Hush state",
    )
    # Hush active (derived from hush_status == Success)
    .binary_sensor(
        attribute_name=HaloControlCluster.AttributeDefs.hush_status.name,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        attribute_converter=lambda value: value == HaloHushStatus.Success,
        unique_id_suffix="hush_active",
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="hush_active",
        fallback_name="Hush active",
    )
    # Command buttons: test start/cancel
    .command_button(
        command_name=HaloControlCluster.ServerCommandDefs.halo_test.name,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        command_kwargs={"value": 0x01},
        unique_id_suffix="start_test",
        translation_key="start_test",
        fallback_name="Start test",
    )
    .command_button(
        command_name=HaloControlCluster.ServerCommandDefs.halo_test.name,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        command_kwargs={"value": 0x00},
        unique_id_suffix="cancel_test",
        translation_key="cancel_test",
        fallback_name="Cancel test",
    )
    # Command buttons: hush start/stop
    .command_button(
        command_name=HaloControlCluster.ServerCommandDefs.halo_hush.name,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        command_kwargs={"value": 0x00},
        unique_id_suffix="start_hush",
        translation_key="start_hush",
        fallback_name="Start hush",
    )
    .command_button(
        command_name=HaloControlCluster.ServerCommandDefs.halo_hush.name,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        command_kwargs={"value": 0x01},
        unique_id_suffix="stop_hush",
        translation_key="stop_hush",
        fallback_name="Stop hush",
    )
    # -- Halo sensors cluster entities (EP4) --
    # CO PPM reading
    .sensor(
        attribute_name=HaloSensorsCluster.AttributeDefs.co_ppm.name,
        cluster_id=HaloSensorsCluster.cluster_id,
        endpoint_id=4,
        device_class=SensorDeviceClass.CO,
        state_class=SensorStateClass.MEASUREMENT,
        reporting_config=CO_PPM_REPORT_CONFIG,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="co_ppm",
        fallback_name="CO",
    )
    .add_to_registry()
)


# -- Halo+ quirk (smoke & CO detector with weather radio) --

(
    QuirkBuilder(HALO_SMART_LABS, "halo+")
    .applies_to(HALO_SMART_LABS, "haloWX")
    .applies_to(HALO_SMART_LABS, "SABDA1")
    .replaces(HaloColorCluster, endpoint_id=2)
    .replaces(HaloStatusCluster, endpoint_id=4)
    .replaces(HaloControlCluster, endpoint_id=4)
    .replaces(HaloSensorsCluster, endpoint_id=4)
    .replaces(HaloWeatherCluster, endpoint_id=5)
    # -- IAS Zone binary sensors (same as base Halo) --
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
        unique_id_suffix="tamper",
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Tamper",
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.BATTERY,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Battery),
        unique_id_suffix="battery_low",
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Battery low",
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=1,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Test),
        unique_id_suffix="test_mode",
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="test_mode",
        fallback_name="Test mode",
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.PLUG,
        attribute_converter=lambda value: not bool(value & IasZone.ZoneStatus.AC_mains),
        unique_id_suffix="mains_power",
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Mains power",
    )
    # -- Halo status cluster entities (EP4) --
    .enum(
        attribute_name=HaloStatusCluster.AttributeDefs.device_status.name,
        enum_class=HaloAlertState,
        cluster_id=HaloStatusCluster.cluster_id,
        endpoint_id=4,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=HALO_STATUS_REPORT_CONFIG,
        translation_key="halo_alert_state",
        fallback_name="Alert state",
    )
    .binary_sensor(
        attribute_name=HaloStatusCluster.AttributeDefs.device_status.name,
        cluster_id=HaloStatusCluster.cluster_id,
        endpoint_id=4,
        attribute_converter=lambda value: value == HaloAlertState.Weather,
        unique_id_suffix="weather_alert",
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="weather_alert",
        fallback_name="Weather alert",
    )
    .enum(
        attribute_name=HaloStatusCluster.AttributeDefs.room.name,
        enum_class=HaloRoom,
        cluster_id=HaloStatusCluster.cluster_id,
        endpoint_id=4,
        translation_key="room",
        fallback_name="Room",
    )
    # -- Halo control cluster entities (EP4) --
    .enum(
        attribute_name=HaloControlCluster.AttributeDefs.test_status.name,
        enum_class=HaloTestStatus,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=HALO_STATUS_REPORT_CONFIG,
        translation_key="halo_test_result",
        fallback_name="Test result",
    )
    .binary_sensor(
        attribute_name=HaloControlCluster.AttributeDefs.test_status.name,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        device_class=BinarySensorDeviceClass.RUNNING,
        attribute_converter=lambda value: value == HaloTestStatus.Running,
        unique_id_suffix="test_in_progress",
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Test in progress",
    )
    .enum(
        attribute_name=HaloControlCluster.AttributeDefs.hush_status.name,
        enum_class=HaloHushStatus,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=HALO_STATUS_REPORT_CONFIG,
        translation_key="halo_hush_state",
        fallback_name="Hush state",
    )
    .binary_sensor(
        attribute_name=HaloControlCluster.AttributeDefs.hush_status.name,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        attribute_converter=lambda value: value == HaloHushStatus.Success,
        unique_id_suffix="hush_active",
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="hush_active",
        fallback_name="Hush active",
    )
    .command_button(
        command_name=HaloControlCluster.ServerCommandDefs.halo_test.name,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        command_kwargs={"value": 0x01},
        unique_id_suffix="start_test",
        translation_key="start_test",
        fallback_name="Start test",
    )
    .command_button(
        command_name=HaloControlCluster.ServerCommandDefs.halo_test.name,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        command_kwargs={"value": 0x00},
        unique_id_suffix="cancel_test",
        translation_key="cancel_test",
        fallback_name="Cancel test",
    )
    .command_button(
        command_name=HaloControlCluster.ServerCommandDefs.halo_hush.name,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        command_kwargs={"value": 0x00},
        unique_id_suffix="start_hush",
        translation_key="start_hush",
        fallback_name="Start hush",
    )
    .command_button(
        command_name=HaloControlCluster.ServerCommandDefs.halo_hush.name,
        cluster_id=HaloControlCluster.cluster_id,
        endpoint_id=4,
        command_kwargs={"value": 0x01},
        unique_id_suffix="stop_hush",
        translation_key="stop_hush",
        fallback_name="Stop hush",
    )
    # -- Halo sensors cluster entities (EP4) --
    .sensor(
        attribute_name=HaloSensorsCluster.AttributeDefs.co_ppm.name,
        cluster_id=HaloSensorsCluster.cluster_id,
        endpoint_id=4,
        device_class=SensorDeviceClass.CO,
        state_class=SensorStateClass.MEASUREMENT,
        reporting_config=CO_PPM_REPORT_CONFIG,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="co_ppm",
        fallback_name="CO",
    )
    # -- Halo weather cluster entities (EP5, Halo+ only) --
    # Current weather alert code (read-only)
    .enum(
        attribute_name=HaloWeatherCluster.AttributeDefs.weather_alert_status.name,
        enum_class=WeatherAlertCode,
        cluster_id=HaloWeatherCluster.cluster_id,
        endpoint_id=5,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=HALO_STATUS_REPORT_CONFIG,
        translation_key="current_weather_alert",
        fallback_name="Current weather alert",
    )
    # Weather radio playing state
    .binary_sensor(
        attribute_name=HaloWeatherCluster.AttributeDefs.weather_mute.name,
        cluster_id=HaloWeatherCluster.cluster_id,
        endpoint_id=5,
        attribute_converter=lambda value: bool(value),
        unique_id_suffix="weather_playing",
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="weather_playing",
        fallback_name="Weather radio playing",
    )
    # Weather station preset (writable, 1-7)
    .number(
        attribute_name=HaloWeatherCluster.AttributeDefs.weather_station.name,
        cluster_id=HaloWeatherCluster.cluster_id,
        endpoint_id=5,
        min_value=1,
        max_value=7,
        step=1,
        translation_key="weather_station",
        fallback_name="Weather station",
    )
    # Weather location SAME code (writable)
    .number(
        attribute_name=HaloWeatherCluster.AttributeDefs.weather_location.name,
        cluster_id=HaloWeatherCluster.cluster_id,
        endpoint_id=5,
        min_value=0,
        max_value=999999,
        step=1,
        mode="box",
        translation_key="weather_location",
        fallback_name="Weather location",
    )
    # Command buttons: weather radio play/stop
    .command_button(
        command_name=HaloWeatherCluster.ServerCommandDefs.weather_radio_play.name,
        cluster_id=HaloWeatherCluster.cluster_id,
        endpoint_id=5,
        command_kwargs={"value": 0x01},
        unique_id_suffix="play_weather_radio",
        translation_key="play_weather_radio",
        fallback_name="Play weather radio",
    )
    .command_button(
        command_name=HaloWeatherCluster.ServerCommandDefs.weather_radio_play.name,
        cluster_id=HaloWeatherCluster.cluster_id,
        endpoint_id=5,
        command_kwargs={"value": 0x00},
        unique_id_suffix="stop_weather_radio",
        translation_key="stop_weather_radio",
        fallback_name="Stop weather radio",
    )
    # Weather scan command
    .command_button(
        command_name=HaloWeatherCluster.ServerCommandDefs.weather_scan.name,
        cluster_id=HaloWeatherCluster.cluster_id,
        endpoint_id=5,
        unique_id_suffix="weather_scan",
        translation_key="weather_scan",
        fallback_name="Scan weather stations",
    )
    .add_to_registry()
)
