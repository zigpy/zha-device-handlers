"""Quirk for TS0501 fan switch."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes, Time
from zigpy.zcl.clusters.hvac import Fan

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID, TuyaManufCluster


class FanCluster(CustomCluster, Fan):
    """Custom fan cluster."""

    attr_config = {
        Fan.attributes_by_name["fan_mode_sequence"].id: Fan.FanModeSequence.Low_Med_High
    }

    async def bind(self):
        """Bind fan cluster and write attributes."""
        result = await super().bind()
        await self.write_attributes(self.attr_config)
        return result


class TS0501FanSwitch(CustomDevice):
    """TS0501 fan switch custom device implementation."""

    signature = {
        MODELS_INFO: [("_TZ3210_lzqq3u4r", "TS0501")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Fan.cluster_id,
                    TUYA_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    FanCluster,
                    TuyaManufCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }
