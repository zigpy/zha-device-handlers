"""Tuya Doorbell."""

from typing import Optional, Tuple, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import CustomCluster
from zhaquirks.const import (
    COMMAND_SINGLE,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODEL,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZHA_SEND_EVENT,
)


class IasZoneDoorbellCluster(CustomCluster, IasZone):
    """Custom IasZone cluster for the doorbell."""

    cluster_id = IasZone.cluster_id

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Tuple[IasZone.ZoneStatus],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ) -> None:
        """Handle cluster request."""
        # args looks like [<ZoneStatus.Alarm_1: 1>, <bitmap8.0: 0>, 0, 0]
        # we are only interested in 3 bits of the ZoneStatus item

        # with thanks to
        # https://github.com/Koenkk/zigbee-herdsman-converters/blob/26553bfa9d747c1a8b6322090429c04cf612c3c1/converters/fromZigbee.js#L2193-L2206

        arg = args[0]
        if arg & IasZone.ZoneStatus.Alarm_1:
            self.listener_event(ZHA_SEND_EVENT, COMMAND_SINGLE, [])

        # the doorbell also sets (arg & IasZone.ZoneStatus.Tamper) and
        # (arg & IasZone.ZoneStatus.Battery) but those should eventually
        # be handled by a more generic IasZone handling


class TuyaDoorbell0211(CustomDevice):
    """Tuya doorbell."""

    # {
    #   "node_descriptor": "NodeDescriptor(
    #      logical_type=<LogicalType.EndDevice: 2>,
    #      complex_descriptor_available=0,
    #      user_descriptor_available=0,
    #      reserved=0,
    #      aps_flags=0,
    #      frequency_band=<FrequencyBand.Freq2400MHz: 8>,
    #      mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>,
    #      manufacturer_code=4619,
    #      maximum_buffer_size=82,
    #      maximum_incoming_transfer_size=82,
    #      server_mask=11264,
    #      maximum_outgoing_transfer_size=82,
    #      descriptor_capability_field=<DescriptorCapability.NONE: 0>,
    #      *allocate_address=True,
    #      *is_alternate_pan_coordinator=False,
    #      *is_coordinator=False,
    #      *is_end_device=True,
    #      *is_full_function_device=False,
    #      *is_mains_powered=False,
    #      *is_receiver_on_when_idle=False,
    #      *is_router=False,
    #      *is_security_capable=False)",
    #   "endpoints": {
    #     "1": {
    #       "profile_id": 260,
    #       "device_type": "0x0402",
    #       "in_clusters": [
    #         "0x0000",
    #         "0x0001",
    #         "0x0003",
    #         "0x0500",
    #         "0x0b05"
    #       ],
    #       "out_clusters": [
    #         "0x0019"
    #       ]
    #     }
    #   },
    #   "manufacturer": "_TZ1800_ladpngdx",
    #   "model": "TS0211",
    #   "class": "zhaquirks.tuya.ts0211.TuyaDoorbell0211"
    # }

    signature = {
        MODEL: "TS0211",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZoneDoorbellCluster,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
