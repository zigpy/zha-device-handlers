"""Module to handle quirks of the Sinopé Technologies light.

Supported devices SW2500ZB, SW2500ZB-G2 dimmer DM2500ZB, DM2500ZB-G2, DM2550ZB,
DM2550ZB-G2.
"""

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    DeviceTemperature,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic, ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks import EventableCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.sinope import (
    LIGHT_DEVICE_TRIGGERS,
    SINOPE,
    SINOPE_MANUFACTURER_CLUSTER_ID,
    CustomDeviceTemperatureCluster,
)


class SinopeTechnologiesManufacturerCluster(CustomCluster):
    """SinopeTechnologiesManufacturerCluster manufacturer cluster."""

    class KeypadLock(t.enum8):
        """keypad_lockout values."""

        Unlocked = 0x00
        Locked = 0x01
        Partial_lock = 0x02

    class PhaseControl(t.enum8):
        """Phase control value, reverse / forward"""

        Forward = 0x00
        Reverse = 0x01

    class DoubleFull(t.enum8):
        """Double click up set full intensity"""

        Off = 0x00
        On = 0x01

    class Action(t.enum8):
        """action_report values."""

        Single_on = 0x01
        Single_release_on = 0x02
        Long_on = 0x03
        Double_on = 0x04
        Single_off = 0x11
        Single_release_off = 0x12
        Long_off = 0x13
        Double_off = 0x14

    cluster_id = SINOPE_MANUFACTURER_CLUSTER_ID
    name = "Sinopé Technologies Manufacturer specific"
    ep_attribute = "sinope_manufacturer_specific"
    attributes = {
        0x0002: ("keypad_lockout", KeypadLock, True),
        0x0003: ("firmware_number", t.uint16_t, True),
        0x0004: ("firmware_version", t.CharacterString, True),
        0x0010: ("on_intensity", t.int16s, True),
        0x0050: ("on_led_color", t.uint24_t, True),
        0x0051: ("off_led_color", t.uint24_t, True),
        0x0052: ("on_led_intensity", t.uint8_t, True),
        0x0053: ("off_led_intensity", t.uint8_t, True),
        0x0054: ("action_report", Action, True),
        0x0055: ("min_intensity", t.uint16_t, True),
        0x0056: ("phase_control", PhaseControl, True),
        0x0058: ("double_up_full", DoubleFull, True),
        0x0090: ("current_summation_delivered", t.uint32_t, True),
        0x00A0: ("timer", t.uint32_t, True),
        0x00A1: ("timer_countdown", t.uint32_t, True),
        0x0119: ("connected_load", t.uint16_t, True),
        0x0200: ("status", t.bitmap32, True),
        0xFFFD: ("cluster_revision", t.uint16_t, True),
    }


class LightManufacturerCluster(EventableCluster, SinopeTechnologiesManufacturerCluster):
    """LightManufacturerCluster: fire events corresponding to press type."""


class SinopeTechnologieslight(CustomDevice):
    """SinopeTechnologiesLight custom device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=259
        # device_version=0 input_clusters=[0, 2, 3, 4, 5, 6, 1794, 2821, 65281]
        # output_clusters=[3, 4, 25]>
        MODELS_INFO: [
            (SINOPE, "SW2500ZB"),
            (SINOPE, "SW2500ZB-G2"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
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
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CustomDeviceTemperatureCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    Diagnostic.cluster_id,
                    LightManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = LIGHT_DEVICE_TRIGGERS


class SinopeDM2500ZB(SinopeTechnologieslight):
    """DM2500ZB, DM2500ZB-G2 Dimmers."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=260 device_version=1
        # input_clusters=[0, 2, 3, 4, 5, 6, 8, 1794, 2821, 65281]
        # output_clusters=[3, 4, 25]>
        MODELS_INFO: [
            (SINOPE, "DM2500ZB"),
            (SINOPE, "DM2500ZB-G2"),
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
                    LevelControl.cluster_id,
                    Metering.cluster_id,
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
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CustomDeviceTemperatureCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    Diagnostic.cluster_id,
                    LightManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = LIGHT_DEVICE_TRIGGERS


class SinopeDM2550ZB(SinopeTechnologieslight):
    """DM2550ZB, DM2550ZB-G2 Dimmers."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=260 device_version=1
        # input_clusters=[0, 2, 3, 4, 5, 6, 8, 1794, 2820, 2821, 65281]
        # output_clusters=[3, 4, 10, 25]>
        MODELS_INFO: [
            (SINOPE, "DM2550ZB"),
            (SINOPE, "DM2550ZB-G2"),
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
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CustomDeviceTemperatureCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    LightManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = LIGHT_DEVICE_TRIGGERS
