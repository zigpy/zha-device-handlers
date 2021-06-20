"""Tuya Air Quality sensor."""

import datetime
import logging
from typing import Any, List, Optional, Tuple, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TUYA_CLUSTER_ID,
    TUYA_DP_TYPE_BOOL,
    TUYA_DP_TYPE_ENUM,
    TUYA_DP_TYPE_FAULT,
    TUYA_DP_TYPE_RAW,
    TUYA_DP_TYPE_STRING,
    TUYA_DP_TYPE_VALUE,
    TUYA_GET_DATA,
    TUYA_SET_DATA,
    TUYA_SET_DATA_RESPONSE,
    TUYA_SET_TIME,
    TuyaCommand,
    TuyaTimePayload,
)


class TuyaNewManufCluster(CustomCluster):
    """Tuya manufacturer specific cluster."""

    name = "Tuya Manufacturer Specicific"
    cluster_id = TUYA_CLUSTER_ID
    ep_attribute = "tuya_manufacturer"

    manufacturer_server_commands = {
        TUYA_SET_DATA: ("set_data", (TuyaCommand,), False),
        TUYA_SET_TIME: ("set_time", (TuyaTimePayload,), False),
    }

    manufacturer_client_commands = {
        TUYA_GET_DATA: ("get_data", (TuyaCommand,), True),
        TUYA_SET_DATA_RESPONSE: ("set_data_response", (TuyaCommand,), True),
        TUYA_SET_TIME: ("set_time_request", (t.data16,), True),
    }

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Tuple,
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ) -> None:
        """Handle time request."""

        try:
            if hdr.is_reply:  # server_cluster -> client_cluster command
                handler_name = f"_handle_{self.client_commands[hdr.command_id][0]}"
            else:
                handler_name = f"_handle_{self.server_commands[hdr.command_id][0]}"
        except KeyError:
            self.debug(
                "Received unknown manufacturer command %s: %s", hdr.command_id, args
            )
            if not hdr.frame_control.disable_default_response:
                self.send_default_rsp(
                    hdr, status=foundation.Status.UNSUP_CLUSTER_COMMAND
                )
                return

        try:
            status = getattr(self, handler_name)(*args)
        except AttributeError:
            self.warning(
                "No '%s' handler found for %s command with '%s' args",
                handler_name,
                hdr.command_id,
                args,
            )
            status = foundation.Status.UNSUP_CLUSTER_COMMAND

        if not hdr.frame_control.disable_default_response:
            self.send_default_rsp(hdr, status=status)

    def _handle_get_data(self, command: TuyaCommand) -> foundation.Status:
        """Handle get_data response (report)."""
        self.debug("Handling DP report: %s", command.data)
        self._update_attribute(command.dp, command.data.payload)
        return foundation.Status.SUCCESS


class TuyaCO2Sensor(CustomDevice):
    """Tuya Air quality device."""

    signature = {
        # NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.0: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)]
        # device_version=1
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=81, device_version=1,
        # input_clusters=[0, 4, 5, 61184],
        # output_clusters=[25, 10])
        MODELS_INFO: [("_TZE200_8ygsuhe1", "TS0601")],
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
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaNewManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
