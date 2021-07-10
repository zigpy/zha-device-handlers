"""Module for Bitron/SMaBiT thermostats."""

import logging
from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic,
    PowerConfiguration,
    Identify,
    Time,
    PollControl,
    Ota,
)
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zhaquirks.bitron import BITRON, DIAGNOSTICS_CLUSTER_ID
from zhaquirks.const import (
    MODELS_INFO,
    ENDPOINTS,
    PROFILE_ID,
    DEVICE_TYPE,
    INPUT_CLUSTERS,
    OUTPUT_CLUSTERS,
)

_LOGGER = logging.getLogger(__name__)


class Av201032PowerConfigurationCluster(CustomCluster, PowerConfiguration):
    """Power configuration cluster for Bitron/SMaBiT AV2010/32 thermostats.

    This cluster takes the reported battery voltage and converts it into a
    battery percentage, since the thermostat does not report this value.
    """

    BATTERY_VOLTAGE_ATTRIBUTE_ID = 0x0020
    BATTERY_VOLTAGE_MAX_VALUE = 32
    BATTERY_VOLTAGE_MIN_VALUE = 25
    BATTERY_PERCENTAGE_ATTRIBUTE_ID = 0x0021
    BATTERY_PERCENTAGE_MAX_VALUE = 200  # hex = 0xC8
    BATTERY_PERCENTAGE_MIN_VALUE = 0
    BATTERY_PERCENTAGE_UNKNOWN_VALUE = 255  # hex = 0xFF

    cluster_id = PowerConfiguration.cluster_id

    def _calculate_percentage_from_voltage(self, value):
        if value > self.BATTERY_VOLTAGE_MAX_VALUE:
            percentage = self.BATTERY_PERCENTAGE_MAX_VALUE
        elif value < self.BATTERY_VOLTAGE_MIN_VALUE:
            percentage = self.BATTERY_PERCENTAGE_UNKNOWN_VALUE
        else:
            percentage = int(
                round(
                    self.BATTERY_PERCENTAGE_MIN_VALUE
                    + (
                        (
                            self.BATTERY_PERCENTAGE_MAX_VALUE
                            - self.BATTERY_PERCENTAGE_MIN_VALUE
                        )
                        / (
                            self.BATTERY_VOLTAGE_MAX_VALUE
                            - self.BATTERY_VOLTAGE_MIN_VALUE
                        )
                    )
                    * (value - self.BATTERY_VOLTAGE_MIN_VALUE)
                )
            )

        return percentage

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.BATTERY_VOLTAGE_ATTRIBUTE_ID:
            _LOGGER.debug("Received battery voltage update (value %d)", value)
            percentage = self._calculate_percentage_from_voltage(value)
            _LOGGER.debug("Updating battery percentage (value %d)", percentage)
            self._update_attribute(self.BATTERY_PERCENTAGE_ATTRIBUTE_ID, percentage)


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
                    DIAGNOSTICS_CLUSTER_ID,
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
                    DIAGNOSTICS_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }
