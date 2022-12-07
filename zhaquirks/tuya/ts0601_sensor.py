"""Tuya temp and humidity sensors."""

from typing import Any, Dict

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)
from zhaquirks.tuya import TuyaLocalCluster, TuyaPowerConfigurationCluster2AAA
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaDPType, TuyaMCUCluster


class TuyaTemperatureMeasurement(TemperatureMeasurement, TuyaLocalCluster):
    """Tuya local TemperatureMeasurement cluster."""


class TuyaRelativeHumidity(RelativeHumidity, TuyaLocalCluster):
    """Tuya local RelativeHumidity cluster with a device RH_MULTIPLIER factor."""

    def update_attribute(self, attr_name: str, value: Any) -> None:
        """Apply a correction factor to value."""

        if attr_name == "measured_value":
            value = value * (
                self.endpoint.device.RH_MULTIPLIER
                if hasattr(self.endpoint.device, "RH_MULTIPLIER")
                else 100
            )

        return super().update_attribute(attr_name, value)


class TemperatureHumidityManufCluster(TuyaMCUCluster):
    """Tuya Manufacturer Cluster with Temperature and Humidity data points."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaTemperatureMeasurement.ep_attribute,
            "measured_value",
            dp_type=TuyaDPType.VALUE,
            converter=lambda x: x * 10,  # decidegree to centidegree
        ),
        2: DPToAttributeMapping(
            TuyaRelativeHumidity.ep_attribute,
            "measured_value",
            dp_type=TuyaDPType.VALUE,
            # converter=lambda x: x * 10,  --> move conversion to TuyaRelativeHumidity cluster
        ),
        4: DPToAttributeMapping(
            TuyaPowerConfigurationCluster2AAA.ep_attribute,
            "battery_percentage_remaining",
            dp_type=TuyaDPType.VALUE,
            converter=lambda x: x * 2,  # double reported percentage
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        4: "_dp_2_attr_update",
    }


class TuyaTempHumiditySensor(CustomDevice):
    """Custom device representing tuya temp and humidity sensor with e-ink screen."""

    # RelativeHumidity multiplier
    RH_MULTIPLIER = 10

    signature = {
        # <SimpleDescriptor endpoint=1, profile=260, device_type=81
        # device_version=1
        # input_clusters=[4, 5, 61184, 0]
        # output_clusters=[25, 10]>
        MODELS_INFO: [("_TZE200_bjawzodf", "TS0601")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TemperatureHumidityManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            }
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    TemperatureHumidityManufCluster,  # Single bus for temp, humidity, and battery
                    TuyaTemperatureMeasurement,
                    TuyaRelativeHumidity,
                    TuyaPowerConfigurationCluster2AAA,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            }
        },
    }


class TuyaTempHumiditySensor_Square(CustomDevice):
    """Custom device representing tuya temp and humidity sensor with e-ink screen."""

    # RelativeHumidity multiplier
    # RH_MULTIPLIER = 100

    signature = {
        MODELS_INFO: [
            ("_TZE200_qoy0ekbd", "TS0601"),
            ("_TZE200_znbl8dj5", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                # "profile_id": 260, "device_type": "0x0302",
                # "in_clusters": ["0x0000","0x0001","0x0402","0x0405"],
                # "out_clusters": ["0x000a","0x0019"]
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    TuyaPowerConfigurationCluster2AAA.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            }
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    TuyaPowerConfigurationCluster2AAA,
                    TemperatureHumidityManufCluster,
                    TuyaTemperatureMeasurement,
                    TuyaRelativeHumidity,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            }
        },
    }


class TuyaTempHumiditySensorVar03(CustomDevice):
    """Tuya temp and humidity sensor (variation 03)."""

    signature = {
        # "profile_id": 260,
        # "device_type": "0x0051",
        # "in_clusters": ["0x0000","0x0004","0x0005","0xef00"],
        # "out_clusters": ["0x000a","0x0019"]
        MODELS_INFO: [("_TZE200_yjjdcqsq", "TS0601")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TemperatureHumidityManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            }
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TemperatureHumidityManufCluster,
                    TuyaTemperatureMeasurement,
                    TuyaRelativeHumidity,
                    TuyaPowerConfigurationCluster2AAA,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            }
        },
    }
