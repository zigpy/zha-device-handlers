"""Module to handle quirks of the Sinopé Technologies thermostats.

Manufacturer specific cluster implements attributes to control displaying
of outdoor temperature, setting occupancy on/off and setting device time.
"""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import Array

from zhaquirks.sinope import SINOPE, SINOPE_MANUFACTURER_CLUSTER_ID


class KeypadLock(t.enum8):
    """Keypad_lockout values."""

    Unlocked = 0x00
    Locked = 0x01
    Partial_lock = 0x02


class Display(t.enum8):
    """Config_2nd_display values."""

    Auto = 0x00
    Setpoint = 0x01
    Outside_temperature = 0x02


class FloorMode(t.enum8):
    """Air_floor_mode values."""

    Air_by_floor = 0x01
    Floor = 0x02


class AuxMode(t.enum8):
    """Aux_output_mode values."""

    Off = 0x00
    On = 0x01


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
    """Temp_sensor_type values."""

    Sensor_10k = 0x00
    Sensor_12k = 0x01


class TimeFormat(t.enum8):
    """Time_format values."""

    Format_24h = 0x00
    Format_12h = 0x01


class GfciStatus(t.enum8):
    """Gfci_status values."""

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
    """Set_occupancy values."""

    Away = 0x00
    Home = 0x01


class Backlight(t.enum8):
    """Backlight_auto_dim_param values."""

    On_demand = 0x00
    Always_on = 0x01
    Bedroom = 0x02


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


class SinopeTechnologiesManufacturerCluster(CustomCluster):
    """SinopeTechnologiesManufacturerCluster manufacturer cluster."""

    KeypadLock: Final = KeypadLock
    Display: Final = Display
    FloorMode: Final = FloorMode
    AuxMode: Final = AuxMode
    PumpStatus: Final = PumpStatus
    LimitStatus: Final = LimitStatus
    SensorType: Final = SensorType
    TimeFormat: Final = TimeFormat
    GfciStatus: Final = GfciStatus
    SystemMode: Final = SystemMode
    PumpDuration: Final = PumpDuration
    CycleLength: Final = CycleLength

    cluster_id: Final[t.uint16_t] = SINOPE_MANUFACTURER_CLUSTER_ID
    name: Final = "SinopeTechnologiesManufacturerCluster"
    ep_attribute: Final = "sinope_manufacturer_specific"

    class AttributeDefs(foundation.BaseAttributeDefs):
        """Sinope Manufacturer Cluster Attributes."""

        keypad_lockout: Final = foundation.ZCLAttributeDef(
            id=0x0002, type=KeypadLock, access="rwp", is_manufacturer_specific=True
        )
        firmware_number: Final = foundation.ZCLAttributeDef(
            id=0x0003, type=t.uint16_t, access="rp", is_manufacturer_specific=True
        )
        firmware_version: Final = foundation.ZCLAttributeDef(
            id=0x0004,
            type=t.CharacterString,
            access="rp",
            is_manufacturer_specific=True,
        )
        outdoor_temp: Final = foundation.ZCLAttributeDef(
            id=0x0010, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        outdoor_temp_timeout: Final = foundation.ZCLAttributeDef(
            id=0x0011, type=t.uint16_t, access="rwp", is_manufacturer_specific=True
        )
        config_2nd_display: Final = foundation.ZCLAttributeDef(
            id=0x0012, type=Display, access="rwp", is_manufacturer_specific=True
        )
        secs_since_2k: Final = foundation.ZCLAttributeDef(
            id=0x0020, type=t.uint32_t, access="rwp", is_manufacturer_specific=True
        )
        current_load: Final = foundation.ZCLAttributeDef(
            id=0x0070, type=t.bitmap8, access="rp", is_manufacturer_specific=True
        )
        eco_delta_setpoint: Final = foundation.ZCLAttributeDef(
            id=0x0071, type=t.int8s, access="rwp", is_manufacturer_specific=True
        )
        eco_max_pi_heating_demand: Final = foundation.ZCLAttributeDef(
            id=0x0072, type=t.uint8_t, access="rwp", is_manufacturer_specific=True
        )
        eco_safety_temperature_delta: Final = foundation.ZCLAttributeDef(
            id=0x0073, type=t.uint8_t, access="rwp", is_manufacturer_specific=True
        )
        unknown_attr_1: Final = foundation.ZCLAttributeDef(
            id=0x0101, type=Array, access="r", is_manufacturer_specific=True
        )
        setpoint: Final = foundation.ZCLAttributeDef(
            id=0x0104, type=t.int16s, access="rw", is_manufacturer_specific=True
        )
        air_floor_mode: Final = foundation.ZCLAttributeDef(
            id=0x0105, type=FloorMode, access="rw", is_manufacturer_specific=True
        )
        aux_output_mode: Final = foundation.ZCLAttributeDef(
            id=0x0106, type=AuxMode, access="rw", is_manufacturer_specific=True
        )
        floor_temperature: Final = foundation.ZCLAttributeDef(
            id=0x0107, type=t.int16s, access="r", is_manufacturer_specific=True
        )
        air_max_limit: Final = foundation.ZCLAttributeDef(
            id=0x0108, type=t.int16s, access="rw", is_manufacturer_specific=True
        )
        floor_min_setpoint: Final = foundation.ZCLAttributeDef(
            id=0x0109, type=t.int16s, access="rw", is_manufacturer_specific=True
        )
        floor_max_setpoint: Final = foundation.ZCLAttributeDef(
            id=0x010A, type=t.int16s, access="rw", is_manufacturer_specific=True
        )
        floor_sensor_type_param: Final = foundation.ZCLAttributeDef(
            id=0x010B, type=SensorType, access="rw", is_manufacturer_specific=True
        )
        floor_limit_status: Final = foundation.ZCLAttributeDef(
            id=0x010C, type=LimitStatus, access="rp", is_manufacturer_specific=True
        )
        room_temperature: Final = foundation.ZCLAttributeDef(
            id=0x010D, type=t.int16s, access="r", is_manufacturer_specific=True
        )
        time_format: Final = foundation.ZCLAttributeDef(
            id=0x0114, type=TimeFormat, access="rwp", is_manufacturer_specific=True
        )
        gfci_status: Final = foundation.ZCLAttributeDef(
            id=0x0115, type=GfciStatus, access="rp", is_manufacturer_specific=True
        )
        hvac_mode: Final = foundation.ZCLAttributeDef(
            id=0x0116, type=SystemMode, access="r", is_manufacturer_specific=True
        )
        aux_connected_load: Final = foundation.ZCLAttributeDef(
            id=0x0118, type=t.uint16_t, access="rw", is_manufacturer_specific=True
        )
        connected_load: Final = foundation.ZCLAttributeDef(
            id=0x0119, type=t.uint16_t, access="rw", is_manufacturer_specific=True
        )
        pump_protection_status: Final = foundation.ZCLAttributeDef(
            id=0x0128, type=PumpStatus, access="rw", is_manufacturer_specific=True
        )
        pump_protection_duration: Final = foundation.ZCLAttributeDef(
            id=0x012A, type=PumpDuration, access="rwp", is_manufacturer_specific=True
        )
        current_setpoint: Final = foundation.ZCLAttributeDef(
            id=0x012B, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        report_local_temperature: Final = foundation.ZCLAttributeDef(
            id=0x012D, type=t.int16s, access="rp", is_manufacturer_specific=True
        )
        unknown_attr_11: Final = foundation.ZCLAttributeDef(
            id=0x013B, type=t.bitmap8, access="rp", is_manufacturer_specific=True
        )
        status: Final = foundation.ZCLAttributeDef(
            id=0x0200, type=t.bitmap32, access="rp", is_manufacturer_specific=True
        )
        unknown_attr_12: Final = foundation.ZCLAttributeDef(
            id=0x0202, type=t.enum8, access="r", is_manufacturer_specific=True
        )
        cycle_length: Final = foundation.ZCLAttributeDef(
            id=0x0281, type=CycleLength, access="rwp", is_manufacturer_specific=True
        )
        cluster_revision: Final = foundation.ZCL_CLUSTER_REVISION_ATTR


class SinopeTechnologiesThermostatCluster(CustomCluster, Thermostat):
    """SinopeTechnologiesThermostatCluster custom cluster."""

    Occupancy: Final = Occupancy
    Backlight: Final = Backlight
    CycleOutput: Final = CycleOutput

    class AttributeDefs(Thermostat.AttributeDefs):
        """Sinope Manufacturer Thermostat Cluster Attributes."""

        set_occupancy: Final = foundation.ZCLAttributeDef(
            id=0x0400, type=Occupancy, access="rw", is_manufacturer_specific=True
        )
        main_cycle_output: Final = foundation.ZCLAttributeDef(
            id=0x0401, type=CycleOutput, access="rw", is_manufacturer_specific=True
        )
        backlight_auto_dim_param: Final = foundation.ZCLAttributeDef(
            id=0x0402, type=Backlight, access="rw", is_manufacturer_specific=True
        )
        aux_cycle_output: Final = foundation.ZCLAttributeDef(
            id=0x0404, type=CycleOutput, access="rw", is_manufacturer_specific=True
        )


class SinopeTechnologiesElectricalMeasurementCluster(
    CustomCluster, ElectricalMeasurement
):
    """SinopeTechnologiesElectricalMeasurementCluster custom cluster."""

    class AttributeDefs(ElectricalMeasurement.AttributeDefs):
        """Sinope Manufacturer ElectricalMeasurement Cluster Attributes."""

        current_summation_delivered: Final = foundation.ZCLAttributeDef(
            id=0x0551, type=t.uint32_t, access="rwp", is_manufacturer_specific=True
        )
        aux_setpoint_min: Final = foundation.ZCLAttributeDef(
            id=0x0552, type=t.uint32_t, access="rw", is_manufacturer_specific=True
        )
        aux_setpoint_max: Final = foundation.ZCLAttributeDef(
            id=0x0553, type=t.uint32_t, access="rw", is_manufacturer_specific=True
        )


(
    QuirkBuilder(SINOPE, "TH1123ZB")
    .applies_to(SINOPE, "TH1124ZB")
    .applies_to(SINOPE, "TH1500ZB")
    .applies_to(SINOPE, "TH1300ZB")
    .applies_to(SINOPE, "OTH3600-GA-ZB")
    .applies_to(SINOPE, "TH1123ZB-G2")
    .applies_to(SINOPE, "TH1124ZB-G2")
    .replaces(SinopeTechnologiesElectricalMeasurementCluster, endpoint_id=1)
    .replaces(SinopeTechnologiesThermostatCluster, endpoint_id=1)
    .replaces(SinopeTechnologiesManufacturerCluster, endpoint_id=1)
    .add_to_registry()
)


(
    QuirkBuilder(SINOPE, "TH1400ZB")
    .replaces(SinopeTechnologiesThermostatCluster, endpoint_id=1)
    .replaces(SinopeTechnologiesManufacturerCluster, endpoint_id=1)
    .add_to_registry()
)

(
    QuirkBuilder(SINOPE, "HP6000ZB-GE")
    .applies_to(SINOPE, "HP6000ZB-HS")
    .applies_to(SINOPE, "HP6000ZB-MA")
    .replaces(SinopeTechnologiesThermostatCluster, endpoint_id=1)
    .replaces(SinopeTechnologiesManufacturerCluster, endpoint_id=1)
    .replaces(SinopeTechnologiesThermostatCluster, endpoint_id=2)
    .replaces(SinopeTechnologiesManufacturerCluster, endpoint_id=2)
    .add_to_registry()
)
