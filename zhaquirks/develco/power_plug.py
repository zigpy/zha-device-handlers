"""Smart Plugs."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Alarms,
    Basic,
    DeviceTemperature,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.develco import DEVELCO


class DevelcoDeviceTemperature(CustomCluster, DeviceTemperature):
    """Device Temperature. Modify divisor."""

    DEV_TEMP_ID = 0x0000

    def _update_attribute(self, attrid, value):
        if attrid == self.DEV_TEMP_ID and value is not None:
            value = value * 100
        super()._update_attribute(attrid, value)


class DevelcoElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Electrical measurement. Fixes power factor."""

    RMS_VOLTAGE_ID = 0x0505
    RMS_CURRENT_ID = 0x0508
    ACTIVE_POWER_ID = 0x050B
    POWERFACTOR_ID = 0x0510

    """Use current/voltage reading to update power factor."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)

        if attrid == self.ACTIVE_POWER_ID:
            # Power reading is updated. Update power factor as well.
            self.updatePF()

    def updatePF(self):
        voltage = self._attr_cache.get(self.RMS_VOLTAGE_ID, 0)
        current = self._attr_cache.get(self.RMS_CURRENT_ID, 0)
        power = self._attr_cache.get(self.ACTIVE_POWER_ID, 0)
        pf = 0

        if voltage > 0 and current > 0:
            voltage = voltage / 100
            current = current / 1000
            pf = 100 * power / (voltage * current)

            if pf > 100:
                pf = 100
            elif pf < 0:
                pf = 0
        self._update_attribute(self.POWERFACTOR_ID, pf)


class SPLZB131(CustomDevice):
    """Custom device Develco smart plug device."""

    signature = {
        MODELS_INFO: [(DEVELCO, "SPLZB-131")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0xC0C9,
                DEVICE_TYPE: 1,
                INPUT_CLUSTERS: [
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Alarms.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                    OccupancySensing.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DevelcoDeviceTemperature,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Alarms.cluster_id,
                    Metering.cluster_id,
                    DevelcoElectricalMeasurement,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                    OccupancySensing.cluster_id,
                ],
            },
        }
    }
