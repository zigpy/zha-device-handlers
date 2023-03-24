"""Device handler for ADEO Lexman LDSENK08 smart door window sensor with vibration."""
from typing import Any, List, Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OFF,
    ON,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZONE_STATUS,
    ZONE_TYPE,
)


class IasMultiZoneCluster(CustomCluster, IasZone):
    """Multi Zone Cluster."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Standard_CIE}

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle a cluster command received on this cluster."""
        if hdr.command_id == 0:
            # If we have bit 2, it's a vibration
            if args[0] & 2:
                self.endpoint.device.endpoints[2].ias_zone.update_attribute(
                    ZONE_STATUS, ON
                )
            else:
                self.endpoint.device.endpoints[2].ias_zone.update_attribute(
                    ZONE_STATUS, OFF
                )
            # If we have bit 1, it's open
            if args[0] & 1:
                self.endpoint.device.endpoints[3].ias_zone.update_attribute(
                    ZONE_STATUS, ON
                )
            else:
                self.endpoint.device.endpoints[3].ias_zone.update_attribute(
                    ZONE_STATUS, OFF
                )
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


class VibrationCluster(LocalDataCluster, IasZone):
    """Vibration Sensor."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Vibration_Movement_Sensor}


class ContactCluster(LocalDataCluster, IasZone):
    """Open/close Sensor."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Contact_Switch}


class AdeoLdsenk08(CustomDevice):
    """Adeo contact and vibration sensor controller."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=1
        #  input_clusters=[0, 1, 3, 32, 1280, 2821]
        #  output_clusters=[25]>
        MODELS_INFO: [("ADEO", "LDSENK08")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,  # 260
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,  # 2048
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    PowerConfiguration.cluster_id,  # 1
                    Identify.cluster_id,  # 3
                    PollControl.cluster_id,  # 32
                    IasZone.cluster_id,  # 1280
                    Diagnostic.cluster_id,  # 2821
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],  # 25
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    PowerConfiguration.cluster_id,  # 1
                    Identify.cluster_id,  # 3
                    PollControl.cluster_id,  # 32
                    IasMultiZoneCluster,  # 1280
                    Diagnostic.cluster_id,  # 2821
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],  # 25
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    VibrationCluster,  # 1280
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    ContactCluster,  # 1280
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
