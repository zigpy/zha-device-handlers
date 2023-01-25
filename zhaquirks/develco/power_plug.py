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


class DeviceTemperatureCluster(CustomCluster, DeviceTemperature):
    """Device Temperature. Modify divisor."""

    cluster_id = DeviceTemperature.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        if attrid == 0x0000 and value is not None and value >= 0:
            value = value * 100
        super()._update_attribute(attrid, value)


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
                    DeviceTemperatureCluster,
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
        }
    }
