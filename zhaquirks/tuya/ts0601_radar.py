"""Tuya mmWave sensor quirk."""

from typing import Dict

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    AnalogOutput,
    Basic,
    GreenPowerProxy,
    Groups,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import NoManufacturerCluster, TuyaLocalCluster, TuyaNewManufCluster
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaAttributesCluster,
    TuyaMCUCluster,
)


class RangeSensing(t.enum8):
    """Radar range sensing enum."""

    METERS_0_5 = 0x00
    METERS_1_0 = 0x01
    METERS_1_5 = 0x02
    METERS_2_0 = 0x03
    METERS_2_5 = 0x04
    METERS_3_0 = 0x05
    METERS_3_5 = 0x06
    METERS_4_0 = 0x07
    METERS_4_5 = 0x08
    METERS_5_0 = 0x09


class MotionType(t.enum8):
    """Type of motion detected enum."""

    ERROR_LOW = 0x00
    CLEAR = 0x01
    ACTIVE = 0x02
    PRESENCE = 0x03
    ERROR_HIGH = 0x04


class TuyaOccupancySensing(OccupancySensing, TuyaLocalCluster):
    """Tuya local OccupancySensing cluster."""


class CooldownTime(TuyaAttributesCluster, AnalogOutput):
    """AnalogOutput cluster for cooldown time."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._update_attribute(
            self.attributes_by_name["description"].id, "Cooldown time"
        )
        self._update_attribute(
            self.attributes_by_name["max_present_value"].id,
            300,
        )
        self._update_attribute(
            self.attributes_by_name["min_present_value"].id,
            24,
        )
        self._update_attribute(self.attributes_by_name["resolution"].id, 1)
        # self._update_attribute(self.attributes_by_name["application_type"].id, 0 << 16)
        self._update_attribute(
            self.attributes_by_name["engineering_units"].id, 73
        )  # 73: seconds


class MmwRadarManufCluster(NoManufacturerCluster, TuyaMCUCluster):
    """Neo manufacturer cluster."""

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            # ramdom attribute IDs
            # 0xEF66: ("induction_delay", t.uint32_t, True),
            0xEF69: ("target_distance", RangeSensing, True),
            0xEF8D: ("motion_type", MotionType, True),
        }
    )

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        102: DPToAttributeMapping(
            CooldownTime.ep_attribute,
            "present_value",
        ),
        105: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "target_distance",
            converter=lambda x: RangeSensing(x),
        ),
        119: DPToAttributeMapping(
            TuyaOccupancySensing.ep_attribute,
            "occupancy",
        ),
        141: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "motion_type",
            converter=lambda x: MotionType(x),
        ),
    }

    data_point_handlers = {
        102: "_dp_2_attr_update",
        105: "_dp_2_attr_update",
        119: "_dp_2_attr_update",
        141: "_dp_2_attr_update",
    }


class MmwRadarMotionGPP(CustomDevice):
    """Millimeter wave occupancy sensor."""

    signature = {
        #  endpoint=1, profile=260, device_type=81, device_version=1,
        #  input_clusters=[4, 5, 61184, 0], output_clusters=[25, 10])
        MODELS_INFO: [
            ("_TZE200_9qayzqa8", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaNewManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # input_clusters=[]
                # output_clusters=[33]
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MmwRadarManufCluster,
                    TuyaOccupancySensing,
                    CooldownTime,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }
