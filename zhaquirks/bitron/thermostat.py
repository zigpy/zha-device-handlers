"""Module for Bitron/SMaBiT thermostats."""

import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
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

from zhaquirks import PowerConfigurationCluster
from zhaquirks.bitron import BITRON
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

_LOGGER = logging.getLogger(__name__)


class Av201032PowerConfigurationCluster(PowerConfigurationCluster):
    """Power configuration cluster for Bitron/SMaBiT AV2010/32 thermostats.

    This cluster takes the reported battery voltage and converts it into a
    battery percentage, since the thermostat does not report this value.
    """

    MIN_VOLTS = 2.5
    MAX_VOLTS = 3.0


class Av201032(CustomDevice):
    """Class for the AV2010/32 thermostat."""

    signature = {
        # SizePrefixedSimpleDescriptor(
        #   endpoint=1,
        #   profile=260,
        #   device_type=769,
        #   device_version=0,
        #   input_clusters=[0, 1, 3, 10, 32, 513, 516, 2821],
        #   output_clusters=[3, 25]
        # )
        MODELS_INFO: [(BITRON, "902010/32")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
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
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Av201032PowerConfigurationCluster,
                    Identify.cluster_id,
                    Time.cluster_id,
                    PollControl.cluster_id,
                    Thermostat.cluster_id,
                    UserInterface.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }
