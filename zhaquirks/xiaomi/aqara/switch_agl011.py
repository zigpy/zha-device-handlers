"""Aqara H2 EU dimmer switch"""

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Basic,
    Groups,
    Identify,
    LevelControl,
    MultistateInput,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import (
    BasicCluster,
    ElectricalMeasurementCluster,
    MeteringCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
)


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    class Sensitivity(t.enum8):
        """Rotation sensitivity."""

        Low = 0x02D0  # 720
        Medium = 0x0168  # 360
        High = 0x00B4  # 180

    class MinBrightness(t.uint8_t):
        """Minimum brightness."""

        def __init__(self, value: int = 0):
            """Initialize with a default value."""
            super().__init__(value)
            if not (0 <= value <= 99):
                raise ValueError("Minimum brightness must be between 0 and 100.")

    class MaxBrightness(t.uint8_t):
        """Maximum brightness."""

        def __init__(self, value: int = 100):
            """Initialize with a default value."""
            super().__init__(value)
            if not (1 <= value <= 100):
                raise ValueError("Maximum brightness must be between 1 and 100.")

    class Phase(t.enum8):
        """Startup mode."""

        Forward = 0
        Reverse = 1

    attributes = {
        0x0234: ("sensitivity", Sensitivity),
        0x0515: ("min_brightness", MinBrightness),
        0x0516: ("max_brightness", MaxBrightness),
        0x030a: ("phase", t.enum8),
    }

    def _update_attribute(self, attrid, value):
        """Handle attribute updates."""
        super()._update_attribute(attrid, value)
        if attrid in [0x0234, 0x0515, 0x0516, 0x030a]:
            self.listener_event(
                ZHA_SEND_EVENT,
                {
                    "type": self.attributes[attrid][0],
                    "value": value,
                },
            )


class AqaraDimmerSwitchH2EU(XiaomiCustomDevice):
    """Aqara H2 EU dimmer switch (KD-R01D)"""

    signature = {
        MODELS_INFO: [("Aqara", "lumi.switch.agl011")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6, 8, 12, 1794, 2820, 64704]
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
                    LevelControl.cluster_id,
                    MultistateInput.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    OppleCluster.cluster_id
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=0
            # device_version=1
            # input_clusters=[64704]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [OppleCluster.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=0
            # device_version=1
            # input_clusters=[64704]
            # output_clusters=[]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [OppleCluster.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=21 profile=260 device_type=0
            # device_version=1
            # input_clusters=[12]
            # output_clusters=[]>
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=71 profile=260 device_type=0
            # device_version=1
            # input_clusters=[64704]
            # output_clusters=[]>
            71: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [OppleCluster.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=72 profile=260 device_type=0
            # device_version=1
            # input_clusters=[64704]
            # output_clusters=[]>
            72: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [OppleCluster.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    MultistateInput.cluster_id,
                    MeteringCluster,
                    ElectricalMeasurementCluster,
                    AqaraRotationSensitivityCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }


# 2025-05-29 21:14:28.721 DEBUG (MainThread) [bellows.ezsp.protocol] Received command incomingMessageHandler: {'type': <EmberIncomingMessageType.INCOMING_UNICAST: 0>, 'apsFrame': EmberApsFrame(profileId=260, clusterId=64704, sourceEndpoint=1, destinationEndpoint=1, options=<EmberApsOption.APS_OPTION_ENABLE_ROUTE_DISCOVERY: 256>, groupId=0, sequence=135), 'lastHopLqi': 204, 'lastHopRssi': -60, 'sender': 0xF686, 'bindingIndex': 255, 'addressIndex': 6, 'messageContents': b'\x1c_\x11S\n\x15\x05 A\x16\x05 d'}
# 2025-05-29 21:14:28.721 DEBUG (MainThread) [bellows.ezsp.protocol] Frame contains trailing data: b'\x04'
# 2025-05-29 21:14:28.721 DEBUG (MainThread) [bellows.zigbee.application] Received incomingMessageHandler frame with [<EmberIncomingMessageType.INCOMING_UNICAST: 0>, EmberApsFrame(profileId=260, clusterId=64704, sourceEndpoint=1, destinationEndpoint=1, options=<EmberApsOption.APS_OPTION_ENABLE_ROUTE_DISCOVERY: 256>, groupId=0, sequence=135), 204, -60, 0xF686, 255, 6, b'\x1c_\x11S\n\x15\x05 A\x16\x05 d']
# 2025-05-29 21:14:28.722 DEBUG (MainThread) [zigpy.application] Received a packet: ZigbeePacket(timestamp=datetime.datetime(2025, 5, 29, 19, 14, 28, 722327, tzinfo=datetime.timezone.utc), priority=0, src=AddrModeAddress(addr_mode=<AddrMode.NWK: 2>, address=0xF686), src_ep=1, dst=AddrModeAddress(addr_mode=<AddrMode.NWK: 2>, address=0x0000), dst_ep=1, source_route=None, extended_timeout=False, tsn=135, profile_id=260, cluster_id=64704, data=Serialized[b'\x1c_\x11S\n\x15\x05 A\x16\x05 d'], tx_options=<TransmitOptions.NONE: 0>, radius=0, non_member_radius=0, lqi=204, rssi=-60)
# 2025-05-29 21:14:28.723 DEBUG (MainThread) [zigpy.zcl] [0xF686:1:0xfcc0] Received ZCL frame: b'\x1c_\x11S\n\x15\x05 A\x16\x05 d'
# 2025-05-29 21:14:28.723 DEBUG (MainThread) [zigpy.zcl] [0xF686:1:0xfcc0] Decoded ZCL frame header: ZCLHeader(frame_control=FrameControl<0x1C>(frame_type=<FrameType.GLOBAL_COMMAND: 0>, is_manufacturer_specific=True, direction=<Direction.Server_to_Client: 1>, disable_default_response=1, reserved=0, *is_cluster=False, *is_general=True), manufacturer=4447, tsn=83, command_id=10, *direction=<Direction.Server_to_Client: 1>)
# 2025-05-29 21:14:28.725 DEBUG (MainThread) [zigpy.zcl] [0xF686:1:0xfcc0] Decoded ZCL frame: ManufacturerSpecificCluster:Report_Attributes(attribute_reports=[Attribute(attrid=0x0515, value=TypeValue(type=uint8_t, value=65)), Attribute(attrid=0x0516, value=TypeValue(type=uint8_t, value=100))])
# 2025-05-29 21:14:28.725 DEBUG (MainThread) [zigpy.zcl] [0xF686:1:0xfcc0] Received command 0x0A (TSN 83): Report_Attributes(attribute_reports=[Attribute(attrid=0x0515, value=TypeValue(type=uint8_t, value=65)), Attribute(attrid=0x0516, value=TypeValue(type=uint8_t, value=100))])
# 2025-05-29 21:14:28.729 DEBUG (MainThread) [zigpy.zcl] [0xF686:1:0xfcc0] Attribute report received: 0x0515=65, 0x0516=100
# 2025-05-29 21:14:28.729 DEBUG (MainThread) [zha.zigbee.cluster_handlers] [0xF686:1:0xfcc0]: cluster_handler[manufacturer_specific] attribute_updated - cluster[Manufacturer Specific] attr[1301] value[65]
# 2025-05-29 21:14:28.729 DEBUG (MainThread) [zha] Emitting event cluster_handler_attribute_updated with data ClusterAttributeUpdatedEvent(attribute_id=1301, attribute_name=1301, attribute_value=65, cluster_handler_unique_id='54:ef:44:10:01:1c:6f:78:1:0xfcc0', cluster_id=64704, event_type='cluster_handler_event', event='cluster_handler_attribute_updated') (0 listeners)
# 2025-05-29 21:14:28.730 DEBUG (MainThread) [zha.zigbee.cluster_handlers] [0xF686:1:0xfcc0]: cluster_handler[manufacturer_specific] attribute_updated - cluster[Manufacturer Specific] attr[1302] value[100]
# 2025-05-29 21:14:28.730 DEBUG (MainThread) [zha] Emitting event cluster_handler_attribute_updated with data ClusterAttributeUpdatedEvent(attribute_id=1302, attribute_name=1302, attribute_value=100, cluster_handler_unique_id='54:ef:44:10:01:1c:6f:78:1:0xfcc0', cluster_id=64704, event_type='cluster_handler_event', event='cluster_handler_attribute_updated') (0 listeners)
