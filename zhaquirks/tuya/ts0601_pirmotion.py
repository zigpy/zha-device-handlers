"""Tuya Battery powered PIR motion and Illuminance sensor."""

import math
from typing import Dict

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Ota, Time
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement, OccupancySensing
from zigpy.zcl.clusters.security import IasZone

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


class TuyaIlluminanceMeasurement(IlluminanceMeasurement, TuyaLocalCluster):
    """Tuya local IlluminanceMeasurement cluster."""


class SensitivityLevel(t.enum8):
    """Sensitivity level enum."""

    LOW = 0x00
    MEDIUM = 0x01
    HIGH = 0x02


class OnTimeValues(t.enum8):
    """Sensitivity level enum."""

    _10_SEC = 0x00
    _30_SEC = 0x01
    _60_SEC = 0x02
    _120_SEC = 0x03


class PirMotionManufCluster(TuyaMCUCluster):
    """Neo manufacturer cluster."""

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update({0xEF09: ("sensitivity_level", SensitivityLevel)})
    attributes.update({0xEF0A: ("keep_time", OnTimeValues)})

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOccupancySensing.ep_attribute,
            "occupancy",
            converter=lambda x: IasZone.ZoneStatus.Alarm_1 if not x else 0,
        ),
        4: DPToAttributeMapping(
            TuyaPowerConfigurationCluster.ep_attribute,
            "battery_percentage_remaining",
        ),
        9: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "sensitivity_level",
            converter=lambda x: SensitivityLevel(x),
        ),
        10: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "keep_time",
            converter=lambda x: OnTimeValues(x),
        ),
        12: DPToAttributeMapping(
            TuyaIlluminanceMeasurement.ep_attribute,
            "measured_value",
            converter=lambda x: 10000 * math.log10(x) + 1 if x != 0 else 0,
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        4: "_dp_2_attr_update",
        9: "_dp_2_attr_update",
        10: "_dp_2_attr_update",
        12: "_dp_2_attr_update",
    }


class PirMotion(CustomDevice):
    """Tuya PIR motion sensor."""

    signature = {
        MODELS_INFO: [("_TZE200_3towulqd", "TS0601")],
        ENDPOINTS: {
            # endpoints=1 profile=260 device_type=0x0402
            # in_clusters=[0x0000, 0x0001, 0x0500],
            # out_clusters=[0x000a, 0x0019]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    TuyaPowerConfigurationCluster.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    TuyaPowerConfigurationCluster,
                    PirMotionManufCluster,
                    TuyaOccupancySensing,
                    TuyaIlluminanceMeasurement,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }
