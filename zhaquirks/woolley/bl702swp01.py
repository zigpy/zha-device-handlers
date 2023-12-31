"""Woolley CK-BL702-SWP-01 Smart Plug with Energy Monitoring"""
from zigpy.profiles import zha, zgp
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.lightlink import LightLink
from zhaquirks import LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID
)


class WoolleyManufacturerFC11(CustomCluster):
    """Custom energy monitoring cluster used by Woolley Zigbee 3.0 smart sockets (UK)"""
    cluster_id = 0xfc11
    CURRENT_ID = 0x7004
    VOLTAGE_ID = 0x7005
    POWER_ID = 0x7006

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        # Forward power monitoring data to ElectricalMeasurement cluster with appropriate scaling.
        # The values on this cluster are in mV, mA and mW and must be scaled to fit in 16-bit ints.
        # Current - no scaling
        # Voltage - /100
        # Power - /100
        if attrid == self.CURRENT_ID:
            self.endpoint.device.endpoints[1].electrical_measurement.update_attribute(
                ElectricalMeasurement.AttributeDefs.rms_current.id, value)
        elif attrid == self.VOLTAGE_ID:
            self.endpoint.device.endpoints[1].electrical_measurement.update_attribute(
                ElectricalMeasurement.AttributeDefs.rms_voltage.id, int(value / 100))
        elif attrid == self.POWER_ID:
            self.endpoint.device.endpoints[1].electrical_measurement.update_attribute(
                ElectricalMeasurement.AttributeDefs.active_power.id, int(value / 100))


class WoolleyManufacturerFC57(CustomCluster):
    """Unsupported manufacturer cluster"""
    cluster_id = 0xfc57


class EmulatedElectricalMeasurement(LocalDataCluster, ElectricalMeasurement):
    """Extended ElectricalMeasurement cluster to support passing through values."""
    CURRENT_ID = ElectricalMeasurement.AttributeDefs.rms_current.id
    VOLTAGE_ID = ElectricalMeasurement.AttributeDefs.rms_voltage.id
    POWER_ID = ElectricalMeasurement.AttributeDefs.active_power.id

    _CONSTANT_ATTRIBUTES = {
        # Scale factors to get back to V, A and W.
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
        ElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 10,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Emit dummy values during startup so that the sensors get created
        if self.CURRENT_ID not in self._attr_cache:
            self._update_attribute(self.CURRENT_ID, 0)
        if self.VOLTAGE_ID not in self._attr_cache:
            self._update_attribute(self.VOLTAGE_ID, 0)
        if self.POWER_ID not in self._attr_cache:
            self._update_attribute(self.POWER_ID, 0)


class BL702_SWP_01(CustomDevice):
    """Woolley/eWeLink CK-BL702-SWP-01 smart plug"""

    signature = {
        MODELS_INFO: [("eWeLink", "CK-BL702-SWP-01(7020)")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=9
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6, 4096, 64529, 64599]
            # output_clusters=[10, 25, 2820]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.MAIN_POWER_OUTLET,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LightLink.cluster_id,
                    WoolleyManufacturerFC11.cluster_id,
                    WoolleyManufacturerFC57.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                    ElectricalMeasurement.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=1
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [ ],
                OUTPUT_CLUSTERS: [ GreenPowerProxy.cluster_id ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LightLink.cluster_id,
                    WoolleyManufacturerFC11,
                    WoolleyManufacturerFC57,
                    EmulatedElectricalMeasurement,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=1
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [ ],
                OUTPUT_CLUSTERS: [ GreenPowerProxy.cluster_id ],
            },
        },
    }

