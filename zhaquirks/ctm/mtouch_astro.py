"""CTM Lyng mTouch Astro"""
import zigpy.profiles.zha as zha
from zigpy import types as t
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes, Time
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks import Bus
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from zhaquirks.ctm import CTM, CtmDiagnosticsCluster, CtmGroupConfigCluster, CtmOnOffDataCluster


class CtmOnOffCluster(CustomCluster, OnOff):
    """CTM Lyng custom on/off cluster."""

    class DeviceMode(t.uint8_t):
        """Device modes of the astro clock."""

        Astro_Clock = 0x00
        Timer = 0x01
        Daily_Schedule = 0x02
        Weekly_Schedule = 0x03

    attributes = OnOff.attributes.copy()
    attributes.update(
        {
            0x2200: ("device_mode", DeviceMode),
            0x2201: ("device_enabled", t.Bool),
            0x2202: ("tamper_lock_enabled", t.Bool),
        }
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.on_off_bus.add_listener(self)

    async def write_device_enabled(self, value):
        return await self.write_attributes({"device_enabled": value}, manufacturer=None)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.attributes_by_name["device_enabled"].id:
            self.endpoint.device.device_enabled_bus.listener_event(
                "on_off_change", value
            )

    async def command(
        self, command_id, *args, manufacturer=None, expect_reply=False, tsn=None
    ):
        """Set expect_reply=False."""

        await super().command(
            command_id, *args, manufacturer=manufacturer, expect_reply=False, tsn=tsn
        )
        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.SUCCESS)


class CtmDeviceEnabledCluster(CtmOnOffDataCluster):
    """CTM Lyng custom onoff cluster for setting device_enabled."""

    name = "Device Enabled"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.device_enabled_bus.add_listener(self)

    async def write_on_off(self, value):
        return await self.endpoint.device.on_off_bus.async_event(
            "write_device_enabled", value
        )


class CtmLyngMTouchAstro(CustomDevice):
    """CTM Lyng custom device mTouch Astro."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.on_off_bus = Bus()
        self.device_enabled_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(CTM, "mTouch Astro")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6, 4096, 65191, 65261]
            # output_clusters=[3, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LightLink.cluster_id,
                    CtmGroupConfigCluster.cluster_id,
                    CtmDiagnosticsCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    CtmOnOffCluster,
                    LightLink.cluster_id,
                    CtmGroupConfigCluster,
                    CtmDiagnosticsCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    CtmDeviceEnabledCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
