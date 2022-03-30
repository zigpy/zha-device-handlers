"""Tuya ZGV1."""

import logging
from typing import Dict, Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, OnOff, Ota, PowerConfiguration, Time
from zigpy.zcl.clusters.measurement import FlowMeasurement

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    DPToAttributeMapping,
    TuyaCommand,
    TuyaData,
    TuyaDPType,
    TuyaLocalCluster,
    TuyaNewManufCluster,
)

_LOGGER = logging.getLogger(__name__)


class ZGV1WaterConsumed(FlowMeasurement, TuyaLocalCluster):
    """Tuya Water consumed cluster."""


class ZGV1Timer(TuyaLocalCluster):
    """Tuya Timer cluster."""

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
                _LOGGER.debug(
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


class ZGV1OnOff(OnOff, TuyaLocalCluster):
    """Tuya On Off."""

    def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default Cluster command."""

        if command_id in (0x0000, 0x0001):
            cmd_payload = TuyaCommand()
            cmd_payload.status = 0
            cmd_payload.tsn = self.endpoint.device.application.get_sequence()
            cmd_payload.dp = 1
            cmd_payload.data = TuyaData()
            cmd_payload.data.dp_type = TuyaDPType.BOOL
            cmd_payload.data.function = 0
            cmd_payload.data.raw = 0x0001 - command_id
            return self.endpoint.tuya_manufacturer.set_data(cmd_payload)

        return foundation.Status.UNSUP_CLUSTER_COMMAND


class ZGV1PowerConfiguration(PowerConfiguration, TuyaLocalCluster):
    """Tuya PowerConfiguration."""


class TuyaZGV1ManufCluster(TuyaNewManufCluster):
    """Tuya with ZGV1."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(ZGV1OnOff.ep_attribute, "on_off", lambda x: x),
        5: DPToAttributeMapping(
            ZGV1WaterConsumed.ep_attribute,
            "measured_value",
            lambda x: x / 33.8140226,
        ),
        7: DPToAttributeMapping(
            ZGV1PowerConfiguration.ep_attribute,
            "battery_percentage_remaining",
            lambda x: x,
        ),
        11: DPToAttributeMapping(ZGV1Timer.ep_attribute, "time_left", lambda x: x / 60),
        12: DPToAttributeMapping(ZGV1Timer.ep_attribute, "state", lambda x: x),
        15: DPToAttributeMapping(
            ZGV1Timer.ep_attribute, "last_valve_open_duration", lambda x: x / 60
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


class TuyaZGV1(CustomDevice):
    """Tuya Air quality device."""

    signature = {
        # NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.0: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)]
        # device_version=1
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=81, device_version=1,
        # input_clusters=[0, 4, 5, 61184],
        # output_clusters=[25, 10])
        MODELS_INFO: [("_TZE200_akjefhj5", "TS0601")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    4,
                    5,
                    TuyaZGV1ManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    4,
                    5,
                    TuyaZGV1ManufCluster,
                    ZGV1WaterConsumed,
                    ZGV1OnOff,
                    ZGV1PowerConfiguration,
                    ZGV1Timer,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
