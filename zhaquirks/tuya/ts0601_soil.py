"""Quirk for HOBEIAN ZG-303Z soil sensor."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, PowerConfiguration
from zigpy.zcl.clusters.measurement import (
    RelativeHumidity,
    SoilMoisture,
    TemperatureMeasurement,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster


class HobeianRelativeHumidity(RelativeHumidity, TuyaLocalCluster):
    """Tuya local RelativeHumidity cluster."""


class HobeianSoilMoisture(SoilMoisture, TuyaLocalCluster):
    """Tuya local SoilMoisture cluster."""


class HobeianMcuCluster(TuyaMCUCluster):
    """Tuya Hobeian MCU cluster."""

    dp_to_attribute = {
        3: DPToAttributeMapping(
            HobeianSoilMoisture.ep_attribute,
            "measured_value",
            endpoint_id=2,
            converter=lambda x: x * 100,
        ),
        5: DPToAttributeMapping(
            TemperatureMeasurement.ep_attribute,
            "measured_value",
            converter=lambda x: x * 10,
        ),
        15: DPToAttributeMapping(
            PowerConfiguration.ep_attribute,
            "battery_percentage_remaining",
        ),
        109: DPToAttributeMapping(
            HobeianRelativeHumidity.ep_attribute,
            "measured_value",
            endpoint_id=3,
            converter=lambda x: x * 100,
        ),
    }

    data_point_handlers = {
        3: "_dp_2_attr_update",
        5: "_dp_2_attr_update",
        15: "_dp_2_attr_update",
        109: "_dp_2_attr_update",
    }


class HobeianZG303Z(CustomDevice):
    """Hobeian ZG-303Z soil sensor."""

    signature = {
        MODELS_INFO: [
            ("HOBEIAN", "ZG-303Z"),
            ("_TZE200_npj9bug3", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,  # Original signature shows RelativeHumidity on EP 1
                    0xEF00,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
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
                    TemperatureMeasurement.cluster_id,
                    HobeianMcuCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
            # Endpoint 2: Dedicated to Soil Moisture to prevent overwriting other values
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SIMPLE_SENSOR,
                INPUT_CLUSTERS: [
                    HobeianSoilMoisture,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # Endpoint 3: Dedicated to Relative Humidity to prevent overwriting other values
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SIMPLE_SENSOR,
                INPUT_CLUSTERS: [
                    HobeianRelativeHumidity,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
