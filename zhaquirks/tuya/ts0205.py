import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZONE_STATUS,
    ZONE_TYPE,
)
from zhaquirks.tuya import TuyaManufClusterAttributes

_LOGGER = logging.getLogger(__name__)

TUYA_SMOKE_DETECTED_ATTR = 0x0401  # [0]/[1] [Detected]/[Clear]!


class TuyaSmokeDetectorCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the TS0205 smoke detector."""

    attributes = {
        TUYA_SMOKE_DETECTED_ATTR: ("smoke_detected", t.uint8_t, True),
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == TUYA_SMOKE_DETECTED_ATTR:
            if value == 0:
                self.endpoint.device.ias_bus.listener_event(
                    "update_zone_status", IasZone.ZoneStatus.Alarm_1
                )
            else:
                self.endpoint.device.ias_bus.listener_event("update_zone_status", 0)
        else:
            _LOGGER.warning(
                "[0x%04x:%s:0x%04x] unhandled attribute: 0x%04x",
                self.endpoint.device.nwk,
                self.endpoint.endpoint_id,
                self.cluster_id,
                attrid,
            )


class TuyaIasZone(CustomCluster, IasZone):
    """IAS Zone."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Fire_Sensor}

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.ias_bus.add_listener(self)

    def update_zone_status(self, value):
        """Update IAS status."""
        super()._update_attribute(ZONE_STATUS, value)


class TuyaSmokeDetectorTS0205(CustomDevice):
    """Tuya smoke sensor PST-YG500A"""

    # {
    #   "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4417, maximum_buffer_size=66, maximum_incoming_transfer_size=66, server_mask=10752, maximum_outgoing_transfer_size=66, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
    #   "endpoints": {
    #     "1": {
    #       "profile_id": "0x0104",
    #       "device_type": "0x0402",
    #       "input_clusters": [
    #         "0x0000",
    #         "0x0001",
    #         "0x0004",
    #         "0x0005",
    #         "0x0500"
    #       ],
    #       "output_clusters": [
    #         "0x0003",
    #         "0x0004",
    #         "0x0006",
    #         "0x000a",
    #         "0x0019",
    #         "0x1000"
    #       ]
    #     }
    #   },
    #   "manufacturer": "_TZ3210_up3pngle",
    #   "model": "TS0205",
    #   "class": "zigpy.device.Device"
    # }

    def __init__(self, *args, **kwargs):
        """Init."""
        self.ias_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [("_TZ3210_up3pngle", "TS0205")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    PowerConfiguration.cluster_id,  # 0x0001
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    IasZone.cluster_id,  # 0x0500
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    OnOff.cluster_id,  # 0x0006
                    Time.cluster_id,  # 0x000a
                    Ota.cluster_id,  # 0x0019
                    LightLink.cluster_id,  # 0x1000
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    PowerConfiguration.cluster_id,  # 0x0001
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    TuyaIasZone,  # 0x0500
                    TuyaSmokeDetectorCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Ota.cluster_id,  # 0x0019
                ],
            }
        }
    }
