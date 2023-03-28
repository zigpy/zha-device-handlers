"""Module to handle quirks of the Sinopé Technologies switches.

Supported devices, SP2600ZB, SP2610ZB, RM3250ZB, RM3500ZB,
VA4200WZ, VA4201WZ, VA4200ZB, VA4201ZB, VA4220ZB, VA4221ZB and MC3100ZB.
"""

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    BinaryInput,
    DeviceTemperature,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic, ElectricalMeasurement
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone
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


class SinopeManufacturerCluster(CustomCluster):
    """SinopeManufacturerCluster manufacturer cluster."""

    class KeypadLock(t.enum8):
        """keypad_lockout values."""

        Unlocked = 0x00
        Locked = 0x01

    class TankSize(t.enum8):
        """tank_size values."""

        Gal_40 = 0x01
        Gal_50 = 0x02
        Gal_60 = 0x03
        Gal_80 = 0x04

    class ColdStatus(t.enum8):
        """cold_load_pickup_status values."""

        Active = 0x00
        Off = 0x01

    cluster_id = SINOPE_MANUFACTURER_CLUSTER_ID
    name = "Sinopé Manufacturer specific"
    ep_attribute = "sinope_manufacturer_specific"
    attributes = {
        0x0002: ("keypad_lockout", KeypadLock, True),
        0x0004: ("firmware_version", t.CharacterString, True),
        0x0013: ("tank_size", TankSize, True),
        0x0060: ("connected_load", t.uint16_t, True),
        0x0070: ("current_load", t.bitmap8, True),
        0x0076: ("dr_config_water_temp_min", t.uint8_t, True),
        0x0077: ("dr_config_water_temp_time", t.uint8_t, True),
        0x0078: ("dr_wt_time_on", t.uint16_t, True),
        0x00A0: ("timer", t.uint32_t, True),
        0x0283: ("cold_load_pickup_status", ColdStatus, True),
        0xFFFD: ("cluster_revision", t.uint16_t, True),
    }


class CustomMeteringCluster(CustomCluster, Metering):
    """Custom Metering Cluster."""

    DIVISOR = 0x0302
    _CONSTANT_ATTRIBUTES = {DIVISOR: 1000}


class SinopeTechnologiesSwitch(CustomDevice):
    """SinopeTechnologiesSwitch custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=81, device_version=0,
        # input_clusters=[0, 3, 6, 1794, 2820, 65281]
        # output_clusters=[25]>
        MODELS_INFO: [
            (SINOPE, "SP2600ZB"),
            (SINOPE, "SP2610ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    CustomMeteringCluster,
                    ElectricalMeasurement.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }


class SinopeTechnologiesLoadController(CustomDevice):
    """SinopeTechnologiesLoadController custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=2, device_version=0,
        # input_clusters=[0, 3, 4, 5, 6, 1794, 2820, 2821, 65281]
        # output_clusters=[3, 4, 25]>
        MODELS_INFO: [
            (SINOPE, "RM3250ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
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
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }


class SinopeTechnologiesValve(CustomDevice):
    """SinopeTechnologiesValve custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=3, device_version=0,
        # input_clusters=[0, 1, 3, 4, 5, 6, 8, 2821, 65281]
        # output_clusters=[3, 25]>
        MODELS_INFO: [
            (SINOPE, "VA4200WZ"),
            (SINOPE, "VA4201WZ"),
            (SINOPE, "VA4200ZB"),
            (SINOPE, "VA4201ZB"),
            (SINOPE, "VA4220ZB"),
            (SINOPE, "VA4221ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.LEVEL_CONTROLLABLE_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
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
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }


class SinopeTechnologiesMultiController(CustomDevice):
    """SinopeTechnologiesMultiController custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=2, device_version=0,
        # input_clusters=[0, 1, 3, 4, 5, 6, 15, 1026, 1029, 2821, 65281]
        # output_clusters=[25]>
        MODELS_INFO: [(SINOPE, "MC3100ZB")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    BinaryInput.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    BinaryInput.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    BinaryInput.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    BinaryInput.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }


class SinopeTechnologiesCalypso(CustomDevice):
    """SinopeTechnologiesCalypso custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=260, device_version=0,
        # input_clusters=[0, 2, 3, 4, 5, 6, 1026, 1280, 1794, 2820, 2821, 65281]
        # output_clusters=[10, 25]>
        MODELS_INFO: [
            (SINOPE, "RM3500ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    TemperatureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    TemperatureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }


class SinopeTechnologiesNewSwitch(CustomDevice):
    """SinopeTechnologiesNewSwitch custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=81, device_version=0,
        # input_clusters=[0, 3, 6, 1794, 2820, 4096, 65281]
        # output_clusters=[25, 4096]>
        MODELS_INFO: [
            (SINOPE, "SP2600ZB"),
            (SINOPE, "SP2610ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    LightLink.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    LightLink.cluster_id,
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
                    OnOff.cluster_id,
                    CustomMeteringCluster,
                    ElectricalMeasurement.cluster_id,
                    LightLink.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }
