"""CTM Lyng MBD"""
import zigpy.profiles.zha as zha
from zigpy import types as t
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement, OccupancySensing

from zhaquirks import Bus
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from zhaquirks.ctm import CTM, CtmDiagnosticsCluster, CtmOnOffDataCluster


class CtmOnOffCluster(CustomCluster, OnOff):
    """CTM Lyng custom on/off cluster."""

    attributes = OnOff.attributes.copy()
    attributes.update(
        {
            0x5001: ("relay_state", t.Bool, True),
        }
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.on_off_bus.add_listener(self)

    async def write_relay_state(self, value):
        return await self.write_attributes({"relay_state": value}, manufacturer=None)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.attributes_by_name["relay_state"].id:
            self.endpoint.device.relay_state_bus.listener_event("on_off_change", value)


class CtmRelayStateCluster(CtmOnOffDataCluster):
    """CTM Lyng custom onoff cluster for setting relay_state."""

    name = "Relay State"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.relay_state_bus.add_listener(self)

    async def write_on_off(self, value):
        return await self.endpoint.device.on_off_bus.async_event(
            "write_relay_state", value
        )


class CtmLyngMBDS(CustomDevice):
    """CTM Lyng custom device MBD-S."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.on_off_bus = Bus()
        self.relay_state_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(CTM, "MBD-S")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=256
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6, 1024, 1030, 4096, 65261]
            # output_clusters=[3, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    OccupancySensing.cluster_id,
                    LightLink.cluster_id,
                    CtmDiagnosticsCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
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
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    CtmOnOffCluster,
                    IlluminanceMeasurement.cluster_id,
                    OccupancySensing.cluster_id,
                    LightLink.cluster_id,
                    CtmDiagnosticsCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    CtmRelayStateCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
