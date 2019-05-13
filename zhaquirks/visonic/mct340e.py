"""Visonic MCT340E device."""
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic, Identify, Ota, PollControl, PowerConfiguration)
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

OSRAM_DEVICE = 0x0810  # 2064 base 10
OSRAM_CLUSTER = 0xFD00  # 64768 base 10


_LOGGER = logging.getLogger(__name__)

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class MCT340E(CustomDevice):
    """Visonic MCT340E device."""

    class PowerConfigurationCluster(CustomCluster, PowerConfiguration):
        """Visonic power configuration cluster."""

        cluster_id = PowerConfiguration.cluster_id
        BATTERY_VOLTAGE_ATTR = 0x0020
        BATTERY_PERCENTAGE_REMAINING = 0x0021
        MIN_VOLTS = 2.1
        MAX_VOLTS = 3.0

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)
            if attrid == self.BATTERY_VOLTAGE_ATTR:
                super()._update_attribute(
                    self.BATTERY_PERCENTAGE_REMAINING,
                    self._calculate_battery_percentage(value)
                )

        def _calculate_battery_percentage(self, raw_value):
            if raw_value in (0, 255):
                return -1
            volts = raw_value / 10
            if volts < self.MIN_VOLTS:
                volts = self.MIN_VOLTS
            elif volts > self.MAX_VOLTS:
                volts = self.MAX_VOLTS

            percent = (
                (volts - self.MIN_VOLTS) / (self.MAX_VOLTS - self.MIN_VOLTS)
            ) * 200

            return round(min(200, percent), 2)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0
        # input_clusters=[0, 1, 3, 1026, 1280, 32, 2821]
        # output_clusters=[25]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.IAS_ZONE,
            'model': 'MCT-340 E',
            'manufacturer': 'Visonic',
            'input_clusters': [
                Basic.cluster_id,
                PowerConfigurationCluster.cluster_id,
                Identify.cluster_id,
                TemperatureMeasurement.cluster_id,
                IasZone.cluster_id,
                PollControl.cluster_id,
                DIAGNOSTICS_CLUSTER_ID
            ],
            'output_clusters': [
                Ota.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'model': 'MCT-340 E',
                'manufacturer': 'Visonic',
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    PollControl.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID
                ],
                'output_clusters': [
                    Ota.cluster_id
                ],
            },
        }
    }
