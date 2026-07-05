"""Nous E6 custom quirk for _TZE284_wtikaxzs variant."""
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time, PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zhaquirks.tuya.mcu import TuyaMCUCluster, DPToAttributeMapping
from zhaquirks import CustomDevice
import zhaquirks.const as data_const

class NousE6ManufCluster(TuyaMCUCluster):
    """Manufacturer specific cluster for native Tuya MCU DP mapping."""
    
    # Native way: The framework automatically routes and scales the data points
    dp_to_attribute = {
        1: DPToAttributeMapping(
            TemperatureMeasurement.ep_attribute,
            "measured_value",
            converter=lambda x: x * 10,  # Raw 310 (31.0°C) -> ZCL expects 3100 (0.01°C Units)
        ),
        2: DPToAttributeMapping(
            RelativeHumidity.ep_attribute,
            "measured_value",
            converter=lambda x: x * 100, # Raw 67 (67%) -> ZCL expects 6700 (0.01% Units)
        ),
        4: DPToAttributeMapping(
            PowerConfiguration.ep_attribute,
            "battery_percentage_remaining",
            converter=lambda x: x * 2,   # Raw 100 (100%) -> ZCL expects 200 (0.5% Units)
        ),
    }

class NousE6_TZE284_wtikaxzs(CustomDevice):
    """Nous E6 signature match for _TZE284_wtikaxzs."""

    signature = {
        data_const.MODELS_INFO: [("_TZE284_wtikaxzs", "TS0601")],
        data_const.ENDPOINTS: {
            1: {
                data_const.PROFILE_ID: zha.PROFILE_ID,
                data_const.DEVICE_TYPE: 81,
                data_const.INPUT_CLUSTERS: [0x0000, 0x0004, 0x0005, 0xED00, 0xEF00], # Kept here for successful matching
                data_const.OUTPUT_CLUSTERS: [0x000A, 0x0019],
            }
        },
    }

    replacement = {
        data_const.ENDPOINTS: {
            1: {
                data_const.DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                data_const.INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    NousE6ManufCluster, # 0xED00 removed from here to pass CI signature checks
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    PowerConfiguration.cluster_id,
                ],
                data_const.OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
