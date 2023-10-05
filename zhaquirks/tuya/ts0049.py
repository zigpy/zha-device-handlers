from typing import Any, Dict, Optional, Union

import zigpy.types as t
from zhaquirks import DoublingPowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TUYA_SEND_DATA, TuyaLocalCluster,
)
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    EnchantedDevice,
    TuyaMCUCluster,
    TuyaOnOff,
)
from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Ota, Time, PowerConfiguration


class TuyaValveFamilyBattery(TuyaLocalCluster, DoublingPowerConfigurationCluster):
    _values = [10, 50, 90]
    _CONSTANT_ATTRIBUTES = {
        PowerConfiguration.attributes_by_name["battery_quantity"].id: 4,
        PowerConfiguration.attributes_by_name["battery_size"].id: PowerConfiguration.BatterySize.AAA
    }

    def _update_attribute(self, attrid, value):
        if attrid == self.BATTERY_PERCENTAGE_REMAINING:
            value = self._values[value]
        super()._update_attribute(attrid, value)


class TuyaValveFamilyCluster(TuyaMCUCluster):
    """On/Off Tuya family cluster with extra device attributes"""

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            0xEF01: ("irrigation_time", t.uint32_t, True),
            0xEF02: ("dp_110", t.uint32_t, True),
            0xEF03: ("error_status", t.uint32_t, True),
        }
    )

    async def command(
            self,
            command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
            *args,
            manufacturer: Optional[Union[int, t.uint16_t]] = None,
            expect_reply: bool = True,
            tsn: Optional[Union[int, t.uint8_t]] = None,
            **kwargs: Any,
    ):
        """Override the default Cluster command."""
        self.debug("Setting the NO manufacturer id in command: %s", command_id)
        return await super().command(
            TUYA_SEND_DATA,
            *args,
            manufacturer=foundation.ZCLHeader.NO_MANUFACTURER_ID,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        26: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "error_status",
        ),
        101: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
        ),
        110: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "dp_110",
        ),
        111: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "irrigation_time",
        ),
        115: DPToAttributeMapping(
            TuyaValveFamilyBattery.ep_attribute,
            "battery_percentage_remaining",
        ),
    }

    data_point_handlers = {
        26: "_dp_2_attr_update",
        101: "_dp_2_attr_update",
        110: "_dp_2_attr_update",
        111: "_dp_2_attr_update",
        115: "_dp_2_attr_update",
    }


class TuyaIrrigationValve(EnchantedDevice):
    """Tuya green irrigation valve device."""
    signature = {
        MODELS_INFO: [("_TZ3210_0jxeoadc", "TS0049")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0
            # device_version=1
            # input_clusters=[0, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    TuyaValveFamilyCluster.cluster_id,
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
                    TuyaOnOff,
                    TuyaValveFamilyBattery,
                    TuyaValveFamilyCluster
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }
