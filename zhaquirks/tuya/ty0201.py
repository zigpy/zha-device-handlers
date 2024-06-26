"""Tuya TY0201 temperature and humidity sensor."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota
from zigpy.zcl.clusters.measurement import (
    RelativeHumidity,
    TemperatureMeasurement,
)
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


class TuyaTemperatureMeasurement(TemperatureMeasurement, TuyaLocalCluster):
    """Tuya local TemperatureMeasurement cluster."""

class TuyaRelativeHumidity(RelativeHumidity, TuyaLocalCluster):
    """Tuya local RelativeHumidity cluster."""

class TuyaTempHumiditySensor(CustomDevice):
        """Tuya temp and humidity sensor."""

        signature = {
                # "profile_id": 260,
                # "device_type": "0x0302",
                # "in_cluster": ["0x0000","0x0001","0x0003","0x0402","0x0405"],
                # "out_cluster": ["0x0019"]
                MODELS_INFO: [
                        ("_TZ3000_bjawzodf", "TY0201"),
                ],
                ENDPOINTS: {
                        1: {
                                PROFILE_ID: zha.PROFILE_ID,
                                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                                INPUT_CLUSTERS: [
                                        Basic.cluster_id,
                                        Identify.cluster_id,
                                        TuyaPowerConfigurationCluster2AAA.cluster_id,
                                        RelativeHumidity.cluster_id,
                                        TemperatureMeasurement.cluster_id,
                                ],
                                OUTPUT_CLUSTERS: [
                                        Ota.cluster_id,
                                ]
                        }
                },
        }

        replacement = {
                SKIP_CONFIGURATION: True,
                ENDPOINTS: {
                        1: {
                                INPUT_CLUSTERS: [
                                        Basic.cluster_id,
                                        Identify.cluster_id,
                                        TuyaPowerConfigurationCluster2AAA,
                                        TuyaTemperatureMeasurement,
                                        TuyaRelativeHumidity,
                                ],
                                OUTPUT_CLUSTERS: [Ota.cluster_id],
                        }
                },
        }
