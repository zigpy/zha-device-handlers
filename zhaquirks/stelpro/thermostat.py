"""Module to handle Stelpro thermostats and heaters."""

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Groups, OnOff, Time
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.stelpro import STELPRO


class StelproFanHeater(CustomDevice):
    """StelproFanHeater custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=25, profile=260,
        # device_type=769, device_version=1,
        # input_clusters=[0, 3, 513, 516, 4, 1029],
        # output_clusters=[3, 10, 1026])>
        MODELS_INFO: [(STELPRO, "SORB")],
        ENDPOINTS: {
            25: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Thermostat.cluster_id,
                    UserInterface.cluster_id,
                    Groups.cluster_id,
                    RelativeHumidity.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    TemperatureMeasurement.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            25: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Thermostat.cluster_id,
                    UserInterface.cluster_id,
                    Groups.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    TemperatureMeasurement.cluster_id,
                ],
            }
        }
    }
