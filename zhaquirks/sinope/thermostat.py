"""Module to handle quirks of the  Sinopé Technologies thermostat.

Manufacturer specific cluster implements attributes to control displaying
of outdoor temperature, setting occupancy on/off and setting device time.
"""

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic, ElectricalMeasurement
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import Array

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.sinope import SINOPE, SINOPE_MANUFACTURER_CLUSTER_ID


class SinopeTechnologiesManufacturerCluster(CustomCluster):
    """SinopeTechnologiesManufacturerCluster manufacturer cluster."""

    class KeypadLock(t.enum8):
        """keypad_lockout values."""

        Unlocked = 0x00
        Locked = 0x01

    class Display(t.enum8):
        """config_2nd_display values."""

        Auto = 0x00
        Setpoint = 0x01
        Outside_temperature = 0x02

    class FloorMode(t.enum8):
        """air_floor_mode values."""

        Air_by_floor = 0x01
        Floor = 0x02

    class AuxMode(t.enum8):
        """aux_output_mode values."""

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
        """temp_sensor_type values."""

        Sensor_10k = 0x00
        Sensor_12k = 0x01

    class TimeFormat(t.enum8):
        """time_format values."""

        Format_24h = 0x00
        Format_12h = 0x01

    class GfciStatus(t.enum8):
        """gfci_status values."""

        Ok = 0x00
        Error = 0x01

    class SystemMode(t.enum8):
        """system mode values."""

        Off = 0x00
        Auto = 0x01
        Cool = 0x03
        Heat = 0x04

    class PumpDuration(t.enum8):
        """Pump protection duration period values"""

        T5 = 0x05
        T10 = 0x0A
        T15 = 0x0F
        T20 = 0x14
        T30 = 0x1E
        T60 = 0x3C

    cluster_id = SINOPE_MANUFACTURER_CLUSTER_ID
    name = "Sinopé Technologies Manufacturer specific"
    ep_attribute = "sinope_manufacturer_specific"
    attributes = {
        0x0002: ("keypad_lockout", KeypadLock, True),
        0x0003: ("firmware_number", t.uint16_t, True),
        0x0004: ("firmware_version", t.CharacterString, True),
        0x0010: ("outdoor_temp", t.int16s, True),
        0x0011: ("outdoor_temp_timeout", t.uint16_t, True),
        0x0012: ("config_2nd_display", Display, True),
        0x0020: ("secs_since_2k", t.uint32_t, True),
        0x0070: ("current_load", t.bitmap8, True),
        0x0071: ("eco_delta_setpoint", t.int8s, True),
        0x0072: ("eco_max_pi_heating_demand", t.uint8_t, True),
        0x0073: ("eco_safety_temperature_delta", t.uint8_t, True),
        0x0101: ("unknown_attr_1", Array, True),
        0x0104: ("setpoint", t.int16s, True),
        0x0105: ("air_floor_mode", FloorMode, True),
        0x0106: ("aux_output_mode", AuxMode, True),
        0x0107: ("floor_temperature", t.int16s, True),
        0x0108: ("air_max_limit", t.int16s, True),
        0x0109: ("floor_min_setpoint", t.int16s, True),
        0x010A: ("floor_max_setpoint", t.int16s, True),
        0x010B: ("floor_sensor_type_param", SensorType, True),
        0x010C: ("floor_limit_status", LimitStatus, True),
        0x010D: ("room_temperature", t.int16s, True),
        0x0114: ("time_format", TimeFormat, True),
        0x0115: ("gfci_status", GfciStatus, True),
        0x0116: ("aux_mode", SystemMode, True),
        0x0118: ("aux_connected_load", t.uint16_t, True),
        0x0119: ("connected_load", t.uint16_t, True),
        0x0128: ("pump_protection_status", PumpStatus, True),
        0x012A: ("pump_protection_duration", PumpDuration, True),
        0x012B: ("current_setpoint", t.int16s, True),
        0x012D: ("report_local_temperature", t.int16s, True),
        0x0200: ("status", t.bitmap32, True),
        0xFFFD: ("cluster_revision", t.uint16_t, True),
    }


class SinopeTechnologiesThermostatCluster(CustomCluster, Thermostat):
    """SinopeTechnologiesThermostatCluster custom cluster."""

    class Occupancy(t.enum8):
        """set_occupancy values."""

        Home = 0x00
        Away = 0x01

    class Backlight(t.enum8):
        """backlight_auto_dim_param values."""

        On_demand = 0x00
        Always_on = 0x01

    class CycleOutput(t.uint16_t):
        """main and aux cycle period values."""

        Sec_15 = 0x000F
        Min_5 = 0x012C
        Min_10 = 0x0258
        Min_15 = 0x0384
        Min_20 = 0x04B0
        Min_25 = 0x05DC
        Min_30 = 0x0708
        Off = 0xFFFF

    attributes = Thermostat.attributes.copy()
    attributes.update(
        {
            0x0400: ("set_occupancy", Occupancy, True),
            0x0401: ("main_cycle_output", CycleOutput, True),
            0x0402: ("backlight_auto_dim_param", Backlight, True),
            0x0404: ("aux_cycle_output", CycleOutput, True),
            0xFFFD: ("cluster_revision", t.uint16_t, True),
        }
    )


class SinopeTechnologiesElectricalMeasurementCluster(
    CustomCluster, ElectricalMeasurement
):
    """SinopeTechnologiesElectricalMeasurementCluster custom cluster."""

    attributes = ElectricalMeasurement.attributes.copy()
    attributes.update(
        {
            0x0551: ("current_summation_delivered", t.uint32_t, True),
            0x0552: ("aux_setpoint_min", t.uint32_t, True),
            0x0553: ("aux_setpoint_max", t.uint32_t, True),
        }
    )


class SinopeTechnologiesThermostat(CustomDevice):
    """SinopeTechnologiesThermostat custom device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769
        # device_version=0 input_clusters=[0, 3, 4, 5, 513, 516, 1026, 2820,
        # 2821, 65281] output_clusters=[65281, 25]>
        MODELS_INFO: [
            (SINOPE, "TH1123ZB"),
            (SINOPE, "TH1124ZB"),
            (SINOPE, "TH1500ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Thermostat.cluster_id,
                    UserInterface.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, SINOPE_MANUFACTURER_CLUSTER_ID],
            },
            # <SimpleDescriptor endpoint=196 profile=49757 device_type=769
            # device_version=0 input_clusters=[1] output_clusters=[]>
            196: {
                PROFILE_ID: 0xC25D,
                DEVICE_TYPE: zha_p.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [PowerConfiguration.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    UserInterface.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeTechnologiesElectricalMeasurementCluster,
                    SinopeTechnologiesThermostatCluster,
                    SinopeTechnologiesManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
            },
            196: {INPUT_CLUSTERS: [PowerConfiguration.cluster_id]},
        }
    }


class SinopeTH1400ZB(SinopeTechnologiesThermostat):
    """TH1400ZB thermostat."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769 device_version=1
        # input_clusters=[0, 3, 4, 5, 513, 516, 1026, 1794, 2821, 65281]
        # output_clusters=[10, 65281, 25]>
        MODELS_INFO: [(SINOPE, "TH1400ZB")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Thermostat.cluster_id,
                    UserInterface.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    Metering.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    UserInterface.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    Metering.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeTechnologiesThermostatCluster,
                    SinopeTechnologiesManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
            }
        }
    }


class SinopeTH1300ZB(SinopeTechnologiesThermostat):
    """TH1300ZB thermostat."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769 device_version=1
        # input_clusters=[0, 3, 4, 5, 513, 516, 1026, 1794, 2820, 2821, 65281]
        # output_clusters=[10, 25, 65281]>
        MODELS_INFO: [(SINOPE, "TH1300ZB")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Thermostat.cluster_id,
                    UserInterface.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    UserInterface.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    Metering.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeTechnologiesElectricalMeasurementCluster,
                    SinopeTechnologiesThermostatCluster,
                    SinopeTechnologiesManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
            }
        }
    }


class SinopeLineThermostats(SinopeTechnologiesThermostat):
    """TH1123ZB, TH1124ZB, TH1500ZB and OTH3600-GA-ZB thermostats."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769 device_version=1
        # input_clusters=[0, 3, 4, 5, 513, 516, 1026, 1794, 2820, 2821, 65281]
        # output_clusters=[10, 25, 65281]>
        MODELS_INFO: [
            (SINOPE, "TH1123ZB"),
            (SINOPE, "TH1124ZB"),
            (SINOPE, "TH1500ZB"),
            (SINOPE, "OTH3600-GA-ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Thermostat.cluster_id,
                    UserInterface.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    UserInterface.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    Metering.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeTechnologiesElectricalMeasurementCluster,
                    SinopeTechnologiesThermostatCluster,
                    SinopeTechnologiesManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
            }
        }
    }


class SinopeG2Thermostats(SinopeTechnologiesThermostat):
    """TH1123ZB-G2 and TH1124ZB-G2 thermostats."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769 device_version=1
        # input_clusters=[0, 3, 4, 5, 513, 516, 1026, 1794, 2820, 2821, 65281]
        # output_clusters=[3, 10, 25]>
        MODELS_INFO: [
            (SINOPE, "TH1123ZB-G2"),
            (SINOPE, "TH1124ZB-G2"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Thermostat.cluster_id,
                    UserInterface.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    UserInterface.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    Metering.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeTechnologiesElectricalMeasurementCluster,
                    SinopeTechnologiesThermostatCluster,
                    SinopeTechnologiesManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }
