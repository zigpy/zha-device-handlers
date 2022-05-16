"""Tuya Valve."""

import logging
from typing import Dict

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks import DoublingPowerConfigurationCluster
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
    TuyaAttributesCluster,
    TuyaDPType,
    TuyaMCUCluster,
    TuyaOnOff,
)

_LOGGER = logging.getLogger(__name__)


class TuyaValveTimer(TuyaAttributesCluster):
    """Timer cluster."""

    cluster_id = 0x043E
    name = "Timer"
    ep_attribute = "timer"

    attributes = {
        0x000C: ("state", t.uint16_t),
        0x000B: ("time_left", t.uint16_t),
        0x000F: ("last_valve_open_duration", t.uint16_t),
    }


class TuyaValveWaterConsumed(Metering, TuyaLocalCluster):
    """Tuya Valve Water consumed cluster."""

    VOLUME_LITERS = 0x0007

    """Setting unit of measurement."""
    _CONSTANT_ATTRIBUTES = {0x0300: VOLUME_LITERS}


class TuyaValveManufCluster(TuyaMCUCluster):
    """On/Off Tuya cluster with extra device attributes."""

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            # Random attribute IDs
            0xEF06: ("dp_6", t.uint32_t, True),
        }
    )

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            dp_type=TuyaDPType.BOOL,
        ),
        5: DPToAttributeMapping(
            TuyaValveWaterConsumed.ep_attribute,
            "current_summ_delivered",
            TuyaDPType.VALUE,
        ),
        6: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "dp_6",
            TuyaDPType.VALUE,
        ),
        7: DPToAttributeMapping(
            DoublingPowerConfigurationCluster.ep_attribute,
            "battery_percentage_remaining",
            TuyaDPType.VALUE,
        ),
        11: DPToAttributeMapping(
            TuyaValveTimer.ep_attribute,
            "time_left",
            TuyaDPType.VALUE,
        ),
        12: DPToAttributeMapping(
            TuyaValveTimer.ep_attribute,
            "state",
            TuyaDPType.VALUE,
        ),
        15: DPToAttributeMapping(
            TuyaValveTimer.ep_attribute,
            "last_valve_open_duration",
            TuyaDPType.VALUE,
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        5: "_dp_2_attr_update",
        6: "_dp_2_attr_update",
        7: "_dp_2_attr_update",
        11: "_dp_2_attr_update",
        12: "_dp_2_attr_update",
        15: "_dp_2_attr_update",
    }


class TuyaValve(CustomDevice):
    """Tuya Valve."""

    signature = {
        MODELS_INFO: [("_TZE200_81isopgh", "TS0601")],
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=81, device_version=1,
        # input_clusters=[0, 4, 5, 61184], output_clusters=[25, 10])
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaValveManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOff,
                    TuyaValveWaterConsumed,
                    DoublingPowerConfigurationCluster,
                    TuyaValveTimer,
                    TuyaValveManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
