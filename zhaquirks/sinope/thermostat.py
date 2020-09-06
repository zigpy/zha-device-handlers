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

from . import SINOPE
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

SINOPE_MANUFACTURER_CLUSTER_ID = 0xFF01


class SinopeTechnologiesManufacturerCluster(CustomCluster):
    """SinopeTechnologiesManufacturerCluster manufacturer cluster."""

    cluster_id = SINOPE_MANUFACTURER_CLUSTER_ID
    name = "Sinopé Technologies Manufacturer specific"
    ep_attribute = "sinope_manufacturer_specific"
    manufacturer_attributes = {
        0x0010: ("outdoor_temp", t.int16s),
        0x0020: ("secs_since_2k", t.uint32_t),
    }


class SinopeTechnologiesThermostatCluster(CustomCluster, Thermostat):
    """SinopeTechnologiesThermostatCluster custom cluster."""

    manufacturer_attributes = {0x0400: ("set_occupancy", t.enum8)}


class SinopeTechnologiesThermostat(CustomDevice):
    """SinopeTechnologiesThermostat custom device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769
        # device_version=0 input_clusters=[0, 3, 4, 5, 513, 516, 1026, 2820,
        # 2821, 65281] output_clusters=[65281, 25]>
        MODELS_INFO: [(SINOPE, "TH1123ZB"), (SINOPE, "TH1124ZB"), (SINOPE, "TH1500ZB")],
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
        MODELS_INFO: [(SINOPE, "TH11400ZB")],
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
        MODELS_INFO: [(SINOPE, "TH11300ZB")],
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
