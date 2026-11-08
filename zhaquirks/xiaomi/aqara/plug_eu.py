"""Xiaomi Aqara EU plugs."""

from typing import Final

import zigpy
from zigpy import types
from zigpy.profiles import zgp, zha
from zigpy.zcl.clusters.general import (
    Alarms,
    AnalogInput,
    Basic,
    DeviceTemperature,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder, UnitOfPower, UnitOfTime
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legacy import signature_matches
from zhaquirks.xiaomi import (
    LUMI,
    AnalogInputCluster,
    BasicCluster,
    ElectricalMeasurementCluster,
    MeteringCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
)


async def remove_from_ep(dev: zigpy.device.Device) -> None:
    """Remove devices that are in group 0 by default, so IKEA devices don't control them.

    This is only needed for newer firmware versions. Only a downgrade will fully fix this but this should improve it.
    See https://github.com/zigpy/zha-device-handlers/pull/1656#issuecomment-1244750465 for details.
    """

    endpoint = dev.endpoints.get(1)
    if endpoint is not None:
        dev.debug("Removing endpoint 1 from group 0")
        await endpoint.remove_from_group(0)
        dev.debug("Removed endpoint 1 from group 0")


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        mode: Final = ZCLAttributeDef(
            id=0x0009, type=types.uint8_t, manufacturer_code=0x115F
        )
        power_outage_memory: Final = ZCLAttributeDef(
            id=0x0201, type=types.Bool, manufacturer_code=0x115F
        )
        consumer_connected: Final = ZCLAttributeDef(
            id=0x0207, type=types.Bool, manufacturer_code=0x115F
        )

    # This only exists on older firmware versions. Newer versions always have the behavior as if this was set to true
    attr_config = {0x0009: 0x01}

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        self.create_catching_task(self._enable_opple_mode())
        await remove_from_ep(self.endpoint.device)
        return result

    async def _enable_opple_mode(self) -> None:
        """Write OppleMode only if it isn't enabled yet.

        The plug keeps the value, but reboots on every write, even of the current
        value. It reboots before it responds, so the write times out and the retries
        can reboot it several more times.
        """
        success, _ = await self.read_attributes([self.AttributeDefs.mode.id])
        mode = success.get(self.AttributeDefs.mode.id)
        if mode is not None and mode != 1:
            await self.write_attributes(self.attr_config)


class PlugMMEU01(XiaomiCustomDevice):
    """lumi.plug.mmeu01 plug."""

    signature = {
        MODELS_INFO: [
            (LUMI, "lumi.plug.mmeu01"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=81
            # device_version=1
            # input_clusters=[0, 2, 3, 4, 5, 6, 9, 1794, 2820]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Alarms.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Alarms.cluster_id,
                    MeteringCluster,
                    ElectricalMeasurementCluster,
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [AnalogInputCluster],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }


class PlugMMEU01Alt1(PlugMMEU01):
    """lumi.plug.mmeu01 plug with alternative signature."""

    signature = {
        MODELS_INFO: PlugMMEU01.signature[MODELS_INFO],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=81
            # device_version=1
            # input_clusters=[0, 2, 3, 4, 5, 6, 64704]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    OppleCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=21 profile=260 device_type=81
            # device_version=1
            # input_clusters=[12]
            # output_clusters=[]>
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
            },
            # <SimpleDescriptor endpoint=31 profile=260 device_type=81
            # device_version=1
            # input_clusters=[12]
            # output_clusters=[]>
            31: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = PlugMMEU01.replacement


class PlugMMEU01Alt2(PlugMMEU01):
    """lumi.plug.mmeu01 plug with alternative signature."""

    signature = {
        MODELS_INFO: PlugMMEU01.signature[MODELS_INFO],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=81
            # device_version=1
            # input_clusters=[0, 2, 3, 4, 5, 6, 64704]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    OppleCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = PlugMMEU01.replacement


class PlugMMEU01Alt3(PlugMMEU01):
    """lumi.plug.mmeu01 plug with alternative signature."""

    signature = {
        MODELS_INFO: PlugMMEU01.signature[MODELS_INFO],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=81
            # device_version=1
            # input_clusters=[0, 2, 3, 4, 5, 6, 64704]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    OppleCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=21 profile=260 device_type=81
            # device_version=1
            # input_clusters=[12]
            # output_clusters=[]>
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
            },
            # <SimpleDescriptor endpoint=22 profile=260 device_type=81
            # device_version=1
            # input_clusters=[12]
            # output_clusters=[]>
            22: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = PlugMMEU01.replacement


class OppleClusterMAEU01(OppleCluster):
    """Opple cluster of the MAEU01 plug with its configuration attributes."""

    class AttributeDefs(OppleCluster.AttributeDefs):
        """Attribute definitions."""

        heartbeat_interval: Final = ZCLAttributeDef(
            id=0x00F6, type=types.uint16_t, manufacturer_code=0x115F
        )
        button_lock: Final = ZCLAttributeDef(
            id=0x0200, type=types.uint8_t, manufacturer_code=0x115F
        )
        auto_off: Final = ZCLAttributeDef(
            id=0x0202, type=types.Bool, manufacturer_code=0x115F
        )
        led_disabled: Final = ZCLAttributeDef(
            id=0x0203, type=types.Bool, manufacturer_code=0x115F
        )
        overload_protection: Final = ZCLAttributeDef(
            id=0x020B, type=types.Single, manufacturer_code=0x115F
        )


# The signatures the v1 quirk matched. ZHA has diagnostics of a MAEU01 with both
# the Aqara and the metering clusters on endpoint 1, which was never quirked.
MAEU01_SIGNATURES = tuple(
    signature_matches(quirk.signature)
    for quirk in (PlugMMEU01, PlugMMEU01Alt1, PlugMMEU01Alt2, PlugMMEU01Alt3)
)

(
    QuirkBuilder(LUMI, "lumi.plug.maeu01")
    .filter(lambda device: any(matches(device) for matches in MAEU01_SIGNATURES))
    # Same device as the v1 quirk produced for all known signatures
    .removes_endpoint(22)
    .removes_endpoint(31)
    .adds_endpoint(21, device_type=zha.DeviceType.SMART_PLUG)
    .replaces(BasicCluster)
    .replaces(MeteringCluster)
    .replaces(ElectricalMeasurementCluster)
    .replaces(OppleClusterMAEU01)
    .replaces(AnalogInputCluster, endpoint_id=21)
    .switch(
        attribute_name=OppleClusterMAEU01.AttributeDefs.led_disabled.name,
        cluster_id=OppleClusterMAEU01.cluster_id,
        translation_key="led_disabled_night",
        fallback_name="Disable LED at night",
    )
    .switch(
        attribute_name=OppleClusterMAEU01.AttributeDefs.button_lock.name,
        cluster_id=OppleClusterMAEU01.cluster_id,
        on_value=0,
        off_value=1,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .switch(
        # Turns the plug off when the load stays below 2 W for a while
        attribute_name=OppleClusterMAEU01.AttributeDefs.auto_off.name,
        cluster_id=OppleClusterMAEU01.cluster_id,
        translation_key="auto_off_when_idle",
        fallback_name="Auto off when idle",
    )
    .number(
        attribute_name=OppleClusterMAEU01.AttributeDefs.overload_protection.name,
        cluster_id=OppleClusterMAEU01.cluster_id,
        min_value=100,
        max_value=2300,
        step=1,
        unit=UnitOfPower.WATT,
        translation_key="overload_protection",
        fallback_name="Overload protection",
    )
    .number(
        # How often the plug sends voltage, power and energy, 300 s by default
        attribute_name=OppleClusterMAEU01.AttributeDefs.heartbeat_interval.name,
        cluster_id=OppleClusterMAEU01.cluster_id,
        min_value=5,
        max_value=300,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="reporting_interval",
        fallback_name="Reporting interval",
    )
    .add_to_registry()
)
