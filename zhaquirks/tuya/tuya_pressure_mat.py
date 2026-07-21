"""Custom ZHA Quirk for Tuya TS0601 _TZE200_seq9cm6u Pressure/Occupancy Mat."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Ota, Time
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaMCUCluster,
    TuyaPowerConfigurationCluster,
)


class TuyaOccupancySensing(OccupancySensing, TuyaLocalCluster):
    """Tuya local OccupancySensing cluster."""


class TuyaBedOccupancyMCUCluster(TuyaMCUCluster):
    """Tuya MCU Cluster for Bed Occupancy."""

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOccupancySensing.ep_attribute,
            "occupancy",
            converter=lambda x: not x,
        ),
        4: DPToAttributeMapping(
            TuyaPowerConfigurationCluster.ep_attribute,
            "battery_percentage_remaining",
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        4: "_dp_2_attr_update",
    }


class TuyaPressureMat(CustomDevice):
    """Tuya pressure mat replacement."""

    signature = {
        MODELS_INFO: [("_TZE200_seq9cm6u", "TS0601")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x000C,
                INPUT_CLUSTERS: [0x0000, 0xEF00],
                OUTPUT_CLUSTERS: [0x000A, 0x0019],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    TuyaBedOccupancyMCUCluster,
                    TuyaPowerConfigurationCluster,
                    TuyaOccupancySensing,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
