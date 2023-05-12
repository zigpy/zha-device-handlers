"""Nexturn VOC Sensor"""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef, ZCLCommandDef
from zigpy.zcl.clusters.general import Basic, PowerConfiguration, Identify
from zigpy.zcl.clusters.measurement import TemperatureMeasurement, RelativeHumidity, CarbonDioxideConcentration
from zigpy.zcl.clusters.hvac import Thermostat
from zhaquirks import LocalDataCluster

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class LifeControlMCLH08PowerConfiguration(LocalDataCluster, PowerConfiguration):
    '''Power configuration is reported and cannot be requested'''

    cluster_id = PowerConfiguration.cluster_id


class LifeControlMCLH08RelativeHumidity(LocalDataCluster, RelativeHumidity):
    '''Humidity is reported in temperature cluster and cannot be requested'''


class LifeControlMCLH08CarbonDioxideConcentration(LocalDataCluster, CarbonDioxideConcentration):
    '''CO2 is reported in temperature cluster and cannot be requested'''


class LifeControlMCLH08Temperature(LocalDataCluster, TemperatureMeasurement):
    '''Device reports all measurements as datapoints of temperature cluster and it cannot be queried'''

    cluster_id = TemperatureMeasurement.cluster_id

    def _update_attribute(self, attrid, value):
        if attrid == 0x0001:
            self.endpoint.humidity.update_attribute(0x0000, value)
        elif attrid == 0x0002:
            self.endpoint.carbon_dioxide_concentration.update_attribute(0x0000, value / 1000000)
        else:
            super()._update_attribute(attrid, value)


class LifeControlMCLH08AirQualitySensor(CustomDevice):
    """LifeControl MCLH-08 Air Quality Sensor"""

    signature = {
        MODELS_INFO: [
            ("Nexturn", "VOC_Sensor"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0301,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,                  # 0x0000
                    PowerConfiguration.cluster_id,     # 0x0001
                    Identify.cluster_id,               # 0x0003
                    Thermostat.cluster_id,             # 0x0201
                    TemperatureMeasurement.cluster_id, # 0x0402
                    RelativeHumidity.cluster_id,       # 0x0405
                ],
                OUTPUT_CLUSTERS: [],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: 0x0301,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    LifeControlMCLH08PowerConfiguration,
                    LifeControlMCLH08Temperature,
                    LifeControlMCLH08RelativeHumidity,
                    LifeControlMCLH08CarbonDioxideConcentration,
                ],
                OUTPUT_CLUSTERS: [],
            }
        }
    }
