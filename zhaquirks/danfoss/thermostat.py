"""Module to handle quirks of the  Fanfoss thermostat.

manufacturer specific attributes to control displaying and specific configuration.
"""

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
    Time,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface

from . import DANFOSS
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class DanfossThermostatCluster(CustomCluster, Thermostat):
    """Danfoss custom cluster."""

    manufacturer_attributes = {
        0x4000: ("etrv_open_windows_detection", t.enum8),
        0x4003: ("external_open_windows_detected", t.Bool),
        0x4014: ("orientation", t.Bool),
    }


class DanfossUserInterfaceCluster(CustomCluster, UserInterface):
    """Danfoss custom cluster."""

    manufacturer_attributes = {0x4000: ("viewing_direction", t.enum8)}


class DanfossThermostat(CustomDevice):
    """DanfossThermostat custom device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769
        # device_version=0 input_clusters=[0, 1, 3, 10,32, 513, 516, 1026, 2821]
        # output_clusters=[0, 25]>
        MODELS_INFO: [(DANFOSS, "eTRV0100")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Time.cluster_id,
                    PollControl.cluster_id,
                    Thermostat.cluster_id,
                    UserInterface.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic,
                    PowerConfiguration,
                    Identify,
                    Time,
                    PollControl,
                    DanfossThermostatCluster,
                    DanfossUserInterfaceCluster,
                    Diagnostic,
                ],
                OUTPUT_CLUSTERS: [Basic, Ota],
            }
        }
    }
