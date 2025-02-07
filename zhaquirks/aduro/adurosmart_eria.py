"""ADUROSMART Eria SceneSwitch 81847 device."""
from __future__ import annotations

from typing import Any
from zigpy.typing import AddressingMode
from zigpy.profiles import zha
from zigpy.profiles.zha import DeviceType
from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.zcl import foundation
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks import EventableCluster, PowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MANUFACTURER,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZHA_SEND_EVENT,
)

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFCCC  # decimal = 64716

# Define the unknown cluster (0xFCCC)
class AduroSmartCluster(CustomCluster, ManufacturerSpecificCluster):
    """Custom cluster for handling unknown cluster command 0xFCCC."""
    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: AddressingMode | None = None,
    ):
        """Handle incoming cluster commands."""
        if hdr.command_id == 0x00:
            data = args[0]
            if data == b"\x00\x00\x00":
                self.listener_event(ZHA_SEND_EVENT, "BUTTON_PRESS_0", args)
            elif data == b"\x00\x01\x00":
                self.listener_event(ZHA_SEND_EVENT, "BUTTON_PRESS_1", args)
            elif data == b"\x00\x02\x00":
                self.listener_event(ZHA_SEND_EVENT, "BUTTON_PRESS_2", args)
            elif data == b"\x00\x03\x00":
                self.listener_event(ZHA_SEND_EVENT, "BUTTON_PRESS_3", args)
            else:
                self.debug("Unknown args for cluster command 0: %s", args)

            return

        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

class AduroSmartCSC(CustomDevice):
    """ADUROSMART Eria SceneSwitch 81847 device."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID

    # <SimpleDescriptor endpoint=1 profile=49246 device_type=2064
    # device_version=2
    # input_clusters=[ 0, 1, 3, 4, 5, 6, 8, 768, 4096, 64716 ]
    # output_clusters=[ 0, 3, 4, 5, 6, 8, 768, 4096, 64716 ]>
    signature = {
        MANUFACTURER: "AduroSmart Eria",
        MODELS_INFO: [("ADUROLIGHT_CSC", "AduroSmart Eria")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0xc05e,
                DEVICE_TYPE: DeviceType.COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    AduroSmartCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    AduroSmartCluster.cluster_id,
                ],
            },
            2: {
                "profile_id": 0xC05E,
                "device_type": 0x03F2,
                "input_clusters": [LightLink.cluster_id],
                "output_clusters": [LightLink.cluster_id],
            },
        },
    }
