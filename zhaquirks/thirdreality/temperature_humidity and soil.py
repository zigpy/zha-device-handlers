"""Third Reality Temperature humidity devices."""
from typing import Final
from zigpy.profiles import zha 
from zigpy.quirks import CustomDevice 
import zigpy.types as t 
from zigpy.zcl.clusters.general import Basic, Ota, PowerConfiguration 
from zigpy.zcl.clusters.measurement import TemperatureMeasurement ,RelativeHumidity 
from zhaquirks import CustomCluster 
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef 
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
)

from zhaquirks.const import ( 
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.thirdreality import THIRD_REALITY 

THIRDREALITY_CLUSTER_ID = 0xFF01


class ControlMode(t.int16s):  # noqa: D101

    pass

class ThirdRealityCluster(CustomCluster):
    """ThirdReality Temperature humidity Cluster."""

    cluster_id = THIRDREALITY_CLUSTER_ID

    class AttributeDefs(BaseAttributeDefs): 
        """Attribute definitions."""

        Celsius_degree_calibration: Final = ZCLAttributeDef( 
            id=0x0031,
            type=ControlMode,
            is_manufacturer_specific=True,
        )

        humidity_calibration: Final = ZCLAttributeDef(
            id=0x0032,
            type=ControlMode,
            is_manufacturer_specific=True,
        )

        Fahrenheit_degree_calibration: Final = ZCLAttributeDef( 
            id=0x0033,
            type=ControlMode,
            is_manufacturer_specific=True,
        )
  


class Temperature_humidity(CustomDevice):
    """ThirdReality Temperature humidity device."""

    signature = {
        MODELS_INFO: [(THIRD_REALITY, "3RTHS24BZ")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    #Identify.cluster_id,
                    #PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    ThirdRealityCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
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
                   # Identify.cluster_id,
                   # PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    ThirdRealityCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }


class Temperature_humidity_lite(CustomDevice):
    """ThirdReality Temperature humidity lite device."""

    signature = {
        MODELS_INFO: [(THIRD_REALITY, "3RTHS0224Z")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    #PollControl.cluster_id, # type: ignore
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    ThirdRealityCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
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
                    #PollControl.cluster_id, # type: ignore
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    ThirdRealityCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }


class Soil_Moisture_Sensor(CustomDevice):
    """ThirdReality Soil Moisture Sensor device."""

    signature = {
        MODELS_INFO: [(THIRD_REALITY, "3RSM0147Z")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    ThirdRealityCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
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
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    ThirdRealityCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }
