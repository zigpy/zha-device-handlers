"""Collection of Tuya Valve devices e.g. water valves, gas valve etc."""
from typing import Dict

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes, Time
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
    EnchantedDevice,
    TuyaDPType,
    TuyaMCUCluster,
    TuyaOnOff,
    TuyaPowerConfigurationCluster,
)


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
            0xEF01: ("time_left", t.uint32_t, True),
            0xEF02: ("state", t.enum8, True),
            0xEF03: ("last_valve_open_duration", t.uint32_t, True),
            0xEF04: ("dp_6", t.uint32_t, True),
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
            TuyaMCUCluster.ep_attribute,
            "time_left",
            TuyaDPType.VALUE,
        ),
        12: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "state",
            TuyaDPType.VALUE,
        ),
        15: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
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
    """Tuya valve device."""

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
                    TuyaValveManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }


class ParksideTuyaValveManufCluster(TuyaMCUCluster):
    """Manufacturer Specific Cluster for the _TZE200_htnnfasr water valve sold as PARKSIDE."""

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            0xEF11: ("timer_duration", t.uint32_t, True),
            0xEF12: ("timer_time_left", t.uint32_t, True),
            0xEF13: ("frost_lock", t.Bool, True),
            0xEF14: ("frost_lock_reset", t.Bool, True),  # 0 resets frost lock
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
            TuyaPowerConfigurationCluster.ep_attribute,
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

        When adding this device tuya gateway issues factory reset,
        we just need to reset the frost lock, because its state is unknown to us.
        """
        result = await super().bind()
        await self.write_attributes({self.attributes_by_name["frost_lock_reset"].id: 0})
        return result


class ParksidePSBZS(EnchantedDevice):
    """LIDL Parkside water without implemented scheduler."""

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
                    ParksideTuyaValveManufCluster.cluster_id,
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
                    TuyaPowerConfigurationCluster,
                    ParksideTuyaValveManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }
