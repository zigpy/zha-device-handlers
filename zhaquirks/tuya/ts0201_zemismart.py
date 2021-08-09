"""Zemismart temp and humidity sensor."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zdo.types import NodeDescriptor

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class ZemismartTempHumidity(CustomDevice):
    """Custom device representing Zemismart temp and humidity sensors."""

    def __init__(self, application, ieee, nwk, replaces):
        super().__init__(application, ieee, nwk, replaces)
        self.fix_mains_flag()

    async def get_node_descriptor(self) -> NodeDescriptor:
        super().get_node_descriptor()
        self.fix_mains_flag()
        return self.node_desc

    def fix_mains_flag(self):
        """Clear Mains Powered bit"""
        self.node_desc.mac_capability_flags &= (
            ~NodeDescriptor.MACCapabilityFlags.MainsPowered
        )

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=770
        # device_version=1
        # input_clusters=[0, 1, 3, 1029, 1026, 61183]
        # output_clusters=[3, 25]>
        MODELS_INFO: [("_TZ3000_lfa05ajd", "TS0201")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    RelativeHumidity.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    0xEEFF,  # Unknown
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    RelativeHumidity.cluster_id,
                    TemperatureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }
