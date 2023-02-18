"""Module to handle quirks of the  Sinopé Technologies thermostat.

manufacturer specific cluster implements attributes to control displaying
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

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.sinope import SINOPE

SINOPE_MANUFACTURER_CLUSTER_ID = 0xFF01


class SinopeTechnologiesManufacturerCluster(CustomCluster):
    """SinopeTechnologiesManufacturerCluster manufacturer cluster."""

    class keypadLock(t.enum8):
        """keypadLockout values."""

        Unlocked = 0x00
        Locked = 0x01

    class display(t.enum8):
        """config2ndDisplay values."""

        Auto = 0x00
        OutsideTemperature = 0x01
        Setpoint = 0x02

    class floorMode(t.enum8):
        """airFloorMode values."""

        airByFloor = 0x01
        Floor = 0x02

    class auxMode(t.enum8):
        """auxOutputMode values."""

        off = 0x00
        on = 0x01

    class sensorType(t.enum8):
        """tempSensorType values."""

        Ten_k = 0x00
        Twelve_k = 0x01

    class timeFormat(t.enum8):
        """timeFormat values."""

        Twenty_four_h = 0x00
        Twelve_h = 0x01

    class gfciStatus(t.enum8):
        """gfciStatus values."""

        ok = 0x00
        error = 0x01

    cluster_id = SINOPE_MANUFACTURER_CLUSTER_ID
    name = "Sinopé Technologies Manufacturer specific"
    ep_attribute = "sinope_manufacturer_specific"
    attributes = {
        0x0002: ("keypadLockout", keypadLock, True),
        0x0004: ("firmware_version", t.CharacterString, True),
        0x0010: ("outdoor_temp", t.int16s, True),
        0x0011: ("outdoor_temp_timeout", t.uint16_t, True),
        0x0012: ("config2ndDisplay", display, True),
        0x0020: ("secs_since_2k", t.uint32_t, True),
        0x0070: ("currentLoad", t.bitmap8, True),
        0x0071: ("ecoMode", t.int8s, True),
        0x0072: ("ecoMode1", t.uint8_t, True),
        0x0073: ("ecoMode2", t.uint8_t, True),
        0x0104: ("setpoint", t.int16s, True),
        0x0105: ("airFloorMode", floorMode, True),
        0x0106: ("auxOutputMode", auxMode, True),
        0x0107: ("FloorTemperature", t.int16s, True),
        0x0108: ("airMaxLimit", t.int16s, True),
        0x0109: ("floorMinSetpoint", t.int16s, True),
        0x010A: ("floorMaxSetpoint", t.int16s, True),
        0x010B: ("tempSensorType", sensorType, True),
        0x010C: ("floorLimitStatus", t.uint8_t, True),
        0x010D: ("RoomTemperature", t.int16s, True),
        0x0114: ("timeFormat", timeFormat, True),
        0x0115: ("gfciStatus", gfciStatus, True),
        0x0118: ("auxConnectedLoad", t.uint16_t, True),
        0x0119: ("ConnectedLoad", t.uint16_t, True),
        0x0128: ("pumpProtection", t.uint8_t, True),
        0x012D: ("reportLocalTemperature", t.int16s, True),
        0xFFFD: ("cluster_revision", t.uint16_t, True),
    }


class SinopeTechnologiesThermostatCluster(CustomCluster, Thermostat):
    """SinopeTechnologiesThermostatCluster custom cluster."""

    class occupancy(t.enum8):
        """set_occupancy values."""

        away = 0x01
        home = 0x02

    class backlight(t.enum8):
        """backlightAutoDimParam values."""

        on_demand = 0x00
        always_on = 0x01

    attributes = Thermostat.attributes.copy()
    attributes.update(
        {
            0x0400: ("set_occupancy", occupancy, True),
            0x0401: ("mainCycleOutput", t.uint16_t, True),
            0x0402: ("backlightAutoDimParam", backlight, True),
            0x0404: ("auxCycleOutput", t.uint16_t, True),
            0xFFFD: ("cluster_revision", t.uint16_t, True),
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
                    Basic,
                    Identify,
                    Groups,
                    Scenes,
                    UserInterface,
                    TemperatureMeasurement,
                    ElectricalMeasurement,
                    Diagnostic,
                    SinopeTechnologiesThermostatCluster,
                    SinopeTechnologiesManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [Ota, SINOPE_MANUFACTURER_CLUSTER_ID],
            },
            196: {INPUT_CLUSTERS: [PowerConfiguration]},
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
                    Basic,
                    Identify,
                    Groups,
                    Scenes,
                    UserInterface,
                    TemperatureMeasurement,
                    Metering,
                    Diagnostic,
                    SinopeTechnologiesThermostatCluster,
                    SinopeTechnologiesManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [Time, Ota, SINOPE_MANUFACTURER_CLUSTER_ID],
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
                    ElectricalMeasurement.cluster_id,
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
                    ElectricalMeasurement.cluster_id,
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
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
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
