"""Tuya Garden Watering"""

import logging
import zigpy.types as t
from typing import Dict, Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time, PowerConfiguration, AnalogInput

from zigpy.zcl.clusters.measurement import FlowMeasurement
from zigpy.zcl import foundation
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from zhaquirks.tuya import TuyaManufCluster, TuyaData, TuyaLocalCluster, TuyaCommand
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaOnOff, TuyaOnOffManufCluster, TuyaDPType, TuyaMCUCluster

_LOGGER = logging.getLogger(__name__)


class TuyaGardenWateringTimer(TuyaLocalCluster):
    """Timer cluster."""

    cluster_id = 0x043E
    name = "Timer"
    ep_attribute = "timer"

    attributes = {
        0x000C: ("state", t.uint16_t),
        0x000B: ("time_left", t.uint16_t),
        0x000F: ("last_valve_open_duration", t.uint16_t),
    }

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer attributes writing to the set_data tuya command."""

        records = self._write_attr_records(attributes)

        for record in records:
            if record.attrid not in (0x000B, 0x000C):
                _LOGGER.warning(
                    "[0x%04x:%s:0x%04x] Unautorize write attribute : 0x%04x",
                    self.endpoint.device.nwk,
                    self.endpoint.endpoint_id,
                    self.cluster_id,
                    record.attrid,
                )
                continue
            attr_name = self.attributes[record.attrid][0]
            _LOGGER.debug(
                "[0x%04x:%s:0x%04x] Mapping standard %s (0x%04x) with value %s",
                self.endpoint.device.nwk,
                self.endpoint.endpoint_id,
                self.cluster_id,
                attr_name,
                record.attrid,
                repr(record.value.value),
            )
            cmd_payload = TuyaCommand()
            cmd_payload.status = 0
            cmd_payload.tsn = self.endpoint.device.application.get_sequence()
            cmd_payload.dp = record.attrid
            cmd_payload.data = TuyaData()
            cmd_payload.data.function = 0
            if record.attrid == 0x000B:
                cmd_payload.data.dp_type = TuyaDPType.VALUE
                cmd_payload.data.raw = record.value.value.to_bytes(
                    4, byteorder="little"
                )
            else:
                cmd_payload.data.dp_type = TuyaDPType.ENUM
                cmd_payload.data.raw = record.value.value.to_bytes(
                    1, byteorder="little"
                )
            _LOGGER.debug(
                "[0x%04x:%s:0x%04x] Tuya data : %s",
                self.endpoint.device.nwk,
                self.endpoint.endpoint_id,
                self.cluster_id,
                repr(cmd_payload),
            )
            await self.endpoint.tuya_manufacturer.set_data(cmd_payload)
        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    server_commands = {}
    client_commands = {}


class TuyaGardenWateringWaterConsumed(FlowMeasurement, TuyaLocalCluster):
    """Tuya Water consumed cluster."""


class TuyaGardenWateringPowerConfiguration(PowerConfiguration, TuyaLocalCluster):
    """Tuya PowerConfiguration."""


class TuyaGardenManufCluster(TuyaMCUCluster):
    """On/Off Tuya cluster with extra device attributes."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            dp_type=TuyaDPType.BOOL,
        ),
        5: DPToAttributeMapping(
            TuyaGardenWateringWaterConsumed.ep_attribute,
            "measured_value",
            TuyaDPType.VALUE,
        ),
        7: DPToAttributeMapping(
            TuyaGardenWateringPowerConfiguration.ep_attribute,
            "battery_percentage_remaining",
            TuyaDPType.VALUE,
            # I don't know why but I had to multiply the value to get it right in HA
            lambda x: x * 2,
        ),
        11: DPToAttributeMapping(
            TuyaGardenWateringTimer.ep_attribute,
            "time_left",
            TuyaDPType.VALUE,
            lambda x: x / 60
        ),
        12: DPToAttributeMapping(
            TuyaGardenWateringTimer.ep_attribute,
            "state",
            TuyaDPType.VALUE,
            # lambda x: x,
        ),
        15: DPToAttributeMapping(
            TuyaGardenWateringTimer.ep_attribute,
            "last_valve_open_duration",
            TuyaDPType.VALUE,
            lambda x: x / 60
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        5: "_dp_2_attr_update",
        7: "_dp_2_attr_update",
        11: "_dp_2_attr_update",
        12: "_dp_2_attr_update",
        15: "_dp_2_attr_update",
    }


class TuyaGardenWatering(CustomDevice):
    """Tuya Garden Watering"""

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
                    TuyaGardenManufCluster.cluster_id,
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
                    TuyaGardenWateringWaterConsumed,
                    TuyaGardenWateringPowerConfiguration,
                    TuyaGardenWateringTimer,
                    TuyaGardenManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }