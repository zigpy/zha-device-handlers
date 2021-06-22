"""Tuya Air Quality sensor."""
import dataclasses
from typing import Any, Callable, Dict, Optional, Tuple, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time
from zigpy.zcl.clusters.measurement import (
    CarbonDioxideConcentration,
    FormaldehydeConcentration,
    RelativeHumidity,
    TemperatureMeasurement,
)

from zhaquirks import LocalDataCluster
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
    TUYA_GET_DATA,
    TUYA_SET_DATA,
    TUYA_SET_DATA_RESPONSE,
    TUYA_SET_TIME,
    TuyaCommand,
    TuyaTimePayload,
)


class TuyaLocalCluster(LocalDataCluster):
    """Tuya virtual clusters."""

    def update_attribute(self, attr_name: str, value: Any) -> None:
        """Update attribute by attribute name."""

        try:
            attrid = self.attridx[attr_name]
        except KeyError:
            self.debug("no such attribute: %s", attr_name)
            return
        return self._update_attribute(attrid, value)


class TuyaAirQualityVOC(TuyaLocalCluster):
    """Tuya VOC level cluster."""

    cluster_id = 0x042E
    name = "VOC Level"
    ep_attribute = "voc_level"

    attributes = {
        0x0000: ("measured_value", t.Single),  # fraction of 1 (one)
        0x0001: ("min_measured_value", t.Single),
        0x0002: ("max_measured_value", t.Single),
        0x0003: ("tolerance", t.Single),
    }

    server_commands = {}
    client_commands = {}


class TuyaAirQualityTemperature(TemperatureMeasurement, TuyaLocalCluster):
    """Tuya temperature measurement."""

    pass


class TuyaAirQualityHumidity(RelativeHumidity, TuyaLocalCluster):
    """Tuya relative humidity measurement."""

    pass


class TuyaAirQualityCO2(CarbonDioxideConcentration, TuyaLocalCluster):
    """Tuya Carbon Dioxide concentration measurement."""

    pass


class TuyaAirQualityFormaldehyde(FormaldehydeConcentration, TuyaLocalCluster):
    """Tuya Formaldehyde concentration measurement."""

    pass


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

    data_point_handlers: Dict[int, str] = {}

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
                "No '%s' tuya handler found for %s",
                handler_name,
                args,
            )
            status = foundation.Status.UNSUP_CLUSTER_COMMAND

        if not hdr.frame_control.disable_default_response:
            self.send_default_rsp(hdr, status=status)

    def _handle_get_data(self, command: TuyaCommand) -> foundation.Status:
        """Handle get_data response (report)."""
        try:
            dp_handler = self.data_point_handlers[command.dp]
            getattr(self, dp_handler)(command)
        except (AttributeError, KeyError):
            self.debug("No datapoint handler for %s", command)
            return foundation.status.UNSUPPORTED_ATTRIBUTE

        return foundation.Status.SUCCESS


@dataclasses.dataclass
class DPToAttributeMapping:
    """Container for datapoint to cluster attribute update mapping."""

    ep_attribute: str
    attribute_name: str
    converter: Optional[Callable] = None
    endpoint_id: Optional[int] = None


class TuyaCO2ManufCluster(TuyaNewManufCluster):
    """Tuya with Air quality data points."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        2: DPToAttributeMapping(
            TuyaAirQualityCO2.ep_attribute,
            "measured_value",
            lambda x: x * 1e-6,
        ),
        18: DPToAttributeMapping(
            TuyaAirQualityTemperature.ep_attribute, "measured_value", lambda x: x * 10
        ),
        19: DPToAttributeMapping(
            TuyaAirQualityHumidity.ep_attribute, "measured_value", lambda x: x * 10
        ),
        21: DPToAttributeMapping(
            TuyaAirQualityVOC.ep_attribute, "measured_value", lambda x: x * 1e-6
        ),
        22: DPToAttributeMapping(
            TuyaAirQualityFormaldehyde.ep_attribute,
            "measured_value",
            lambda x: x * 1e-6,
        ),
    }

    data_point_handlers = {
        2: "_dp_handler",
        18: "_dp_handler",
        19: "_dp_handler",
        21: "_dp_handler",
        22: "_dp_handler",
    }

    def _dp_handler(self, command: TuyaCommand) -> None:
        """Handle data point to attribute report conversion."""
        try:
            dp_map = self.dp_to_attribute[command.dp]
        except KeyError:
            self.debug("No attribute mapping for %s data point", command.dp)
            return

        endpoint = self.endpoint
        if dp_map.endpoint_id:
            endpoint = self.endpoint.device.endpoints[dp_map.endpoint_id]
        cluster = getattr(endpoint, dp_map.ep_attribute)
        value = command.data.payload
        if dp_map.converter:
            value = dp_map.converter(value)

        cluster.update_attribute(dp_map.attribute_name, value)


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
                    TuyaCO2ManufCluster,
                    TuyaAirQualityCO2,
                    TuyaAirQualityFormaldehyde,
                    TuyaAirQualityHumidity,
                    TuyaAirQualityTemperature,
                    TuyaAirQualityVOC,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
