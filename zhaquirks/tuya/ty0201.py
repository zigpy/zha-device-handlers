"""Tuya TY0201 temperature and humidity sensor."""

from zigpy.profiles import zha
from zigpy.profiles.zha import DeviceType
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya.air import TuyaAirQualityHumidity, TuyaAirQualityTemperature


class TuyaTempHumiditySensor(CustomDevice):
    """Temu/Aliexpress temperature and humidity sensor."""

    signature = {
        #  <SimpleDescriptor endpoint=1, profile=260, device_type="0x0302"
        #  input_clusters=["0x000", "0x0001", "0x0003", "0x0402", "0x0405"]
        #  output_clusters=["0x0019"]>
        MODELS_INFO: [
            ("_TZ3000_bjawzodf", "TY0201"),
            ("_TZ3000_zl1kmjqx", "TY0201"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TuyaAirQualityTemperature,
                    TuyaAirQualityHumidity,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
        },
    }


class TuyaTempHumiditySensorNoModel(TuyaTempHumiditySensor):
    """Temu/Aliexpress temperature and humidity sensor with empty model."""

    signature = {
        MODELS_INFO: [("_TZ3000_zl1kmjqx", "")],
        ENDPOINTS: TuyaTempHumiditySensor.signature[ENDPOINTS],
    }
