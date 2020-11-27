"""PLAID SYSTEMS PS-SPRZMS-SLP3 soil moisture sensor."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

from . import PLAID_SYSTEMS
from .. import PowerConfigurationCluster
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class PowerConfigurationClusterMains(PowerConfigurationCluster):
    """Common use power configuration cluster."""

    MAINS_VOLTAGE_ATTR = 0x0000
    ATTR_ID_BATT_SIZE = 0x0031
    ATTR_ID_BATT_QTY = 0x0033
    _CONSTANT_ATTRIBUTES = {ATTR_ID_BATT_SIZE: 0x08, ATTR_ID_BATT_QTY: 1}

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.MAINS_VOLTAGE_ATTR:
            super()._update_attribute(self.BATTERY_VOLTAGE_ATTR, round(value / 100))

    def _remap(self, attr):
        """Replace battery voltage attribute name/id with mains_voltage."""
        if attr in (self.BATTERY_VOLTAGE_ATTR, "battery_voltage"):
            return self.MAINS_VOLTAGE_ATTR
        return attr

    def read_attributes(self, attributes, *args, **kwargs):  # pylint: disable=W0221
        """Replace battery voltage with mains voltage."""
        return super().read_attributes(
            [self._remap(attr) for attr in attributes], *args, **kwargs
        )

    def configure_reporting(self, attribute, *args, **kwargs):  # pylint: disable=W0221
        """Replace battery voltage with mains voltage."""
        return super().configure_reporting(self._remap(attribute), *args, **kwargs)


class SoilMoisture(CustomDevice):
    """Custom device representing plaid systems soil sensors."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1029
        # device_version=0
        # input_clusters=[0, 1, 3, 1026, 1029]
        # output_clusters=[3, 25]>
        MODELS_INFO: [(PLAID_SYSTEMS, "PS-SPRZMS-SLP3")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 1029,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 1029,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationClusterMains,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }
