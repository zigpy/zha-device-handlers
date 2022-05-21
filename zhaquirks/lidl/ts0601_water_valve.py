"""LIDL PSBZS A1 water valve."""
from __future__ import annotations

import asyncio
import logging

from typing import Dict

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes, Time
from zigpy.quirks import CustomDevice
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaOnOff,
    TuyaDPType,
    TuyaMCUCluster,
    TuyaNewPowerConfigurationCluster,
)

_LOGGER = logging.getLogger(__name__)


class TuyaWaterValveManufCluster(TuyaMCUCluster):
    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            0xEF01: ("timer", t.uint32_t, True),
            0xEF02: ("timer_time_left", t.uint32_t, True),
            0xEF03: ("frost_lock", t.Bool, True),
            0xEF04: ("frost_lock_reset", t.Bool, True),  # 0 resets frost lock
        }
    )

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            TuyaDPType.BOOL,
        ),
        5: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "timer_duration",
            TuyaDPType.VALUE,
        ),
        6: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "timer_time_left",
            TuyaDPType.VALUE,
        ),
        11: DPToAttributeMapping(
            TuyaNewPowerConfigurationCluster.ep_attribute,
            "battery_percentage_remaining",
            TuyaDPType.VALUE,
        ),
        108: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "frost_lock",
            TuyaDPType.BOOL,
            lambda x: not x,  # invert for lock entity
        ),
        109: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "frost_lock_reset",
            TuyaDPType.BOOL,
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        5: "_dp_2_attr_update",
        6: "_dp_2_attr_update",
        11: "_dp_2_attr_update",
        108: "_dp_2_attr_update",
        109: "_dp_2_attr_update",
    }

    async def bind(self):
        """
        Bind cluster.
        When adding this device tuya gateway issues a factory reset,
        we just reset the frost lock, because its state is unknown to us.
        """
        result = await super().bind()
        await self.write_attributes({self.attributes_by_name["frost_lock_reset"].id: 0})
        return result


class ParksidePSBZS(CustomDevice):
    """LIDL Parkside water without implemented scheduler."""

    def __init__(self, *args, **kwargs):
        """Initialize with task."""
        super().__init__(*args, **kwargs)

        # cast_tuya_magic_spell(self, tries=3)
        self._init_plug_task = asyncio.create_task(self.spell())

    async def spell(self) -> None:
        """Initialize device so that all endpoints become available."""
        basic_cluster = self.endpoints[1].in_clusters[0]

        _LOGGER.debug("Device class will cast Tuya Magic Spell")
        attr_to_read = [4, 0, 1, 5, 7, 0xFFFE]
        await basic_cluster.read_attributes(attr_to_read)

    signature = {
        MODELS_INFO: [("_TZE200_htnnfasr", "TS0601")],  # HG06875
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0
            # device_version=1
            # input_clusters=[0, 1, 3, 4, 5, 6, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaWaterValveManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOff,
                    TuyaNewPowerConfigurationCluster,
                    TuyaWaterValveManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }
