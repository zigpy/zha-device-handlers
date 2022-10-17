"""Xiaomi Aqara EU plugs."""
import logging

import zigpy
from zigpy.profiles import zha
import zigpy.types as types
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

from zhaquirks import Bus
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import (
    LUMI,
    AnalogInputCluster,
    BasicCluster,
    ElectricalMeasurementCluster,
    MeteringCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
)

_LOGGER = logging.getLogger(__name__)

XIAOMI_PROFILE_ID = 0xA1E0
XIAOMI_DEVICE_TYPE = 0x61
OPPLE_MFG_CODE = 0x115F


async def remove_from_ep(dev: zigpy.device.Device) -> None:
    """
    Remove devices that are in group 0 by default, so IKEA devices don't control them.

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

    ep_attribute = "opple_cluster"
    attributes = {
        0x0009: ("mode", types.uint8_t, True),
        0x0201: ("power_outage_memory", types.Bool, True),
    }
    # This only exists on older firmware versions. Newer versions always have the behavior as if this was set to true
    attr_config = {0x0009: 0x01}

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        # Request seems to time out, but still writes the attribute successfully
        self.create_catching_task(
            self.write_attributes(self.attr_config, manufacturer=OPPLE_MFG_CODE)
        )
        await remove_from_ep(self.endpoint.device)
        return result


class PlugMMEU01(XiaomiCustomDevice):
    """lumi.plug.mmeu01 plug."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.voltage_bus = Bus()
        self.consumption_bus = Bus()
        self.power_bus = Bus()
        super().__init__(*args, **kwargs)

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
                PROFILE_ID: XIAOMI_PROFILE_ID,
                DEVICE_TYPE: XIAOMI_DEVICE_TYPE,
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
                PROFILE_ID: XIAOMI_PROFILE_ID,
                DEVICE_TYPE: XIAOMI_DEVICE_TYPE,
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
                PROFILE_ID: XIAOMI_PROFILE_ID,
                DEVICE_TYPE: XIAOMI_DEVICE_TYPE,
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
                PROFILE_ID: XIAOMI_PROFILE_ID,
                DEVICE_TYPE: XIAOMI_DEVICE_TYPE,
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = PlugMMEU01.replacement


class PlugMAEU01(PlugMMEU01):
    """lumi.plug.maeu01 plug."""

    signature = {
        MODELS_INFO: [
            (LUMI, "lumi.plug.maeu01"),
        ],
        ENDPOINTS: PlugMMEU01.signature[ENDPOINTS],
    }

    replacement = PlugMMEU01.replacement


class PlugMAEU01Alt1(PlugMAEU01):
    """lumi.plug.maeu01 plug with alternative signature."""

    signature = {
        MODELS_INFO: PlugMAEU01.signature[MODELS_INFO],
        ENDPOINTS: PlugMMEU01Alt1.signature[ENDPOINTS],
    }

    replacement = PlugMAEU01.replacement


class PlugMAEU01Alt2(PlugMAEU01):
    """lumi.plug.maeu01 plug with alternative signature."""

    signature = {
        MODELS_INFO: PlugMAEU01.signature[MODELS_INFO],
        ENDPOINTS: PlugMMEU01Alt2.signature[ENDPOINTS],
    }

    replacement = PlugMAEU01.replacement
