"""Xiaomi Aqara EU plugs."""
import asyncio
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
    SKIP_CONFIGURATION,
)
from zhaquirks.xiaomi import (
    LUMI,
    AnalogInputCluster,
    BasicCluster,
    ElectricalMeasurementCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
)

_LOGGER = logging.getLogger(__name__)

XIAOMI_PROFILE_ID = 0xA1E0
XIAOMI_DEVICE_TYPE = 0x61
OPPLE_MFG_CODE = 0x115F


async def remove_from_ep(dev: zigpy.device.Device) -> None:
    """Remove devices that are in group 0 by default, so IKEA devices don't control them."""
    endpoint = dev.endpoints.get(1)
    if endpoint is not None:
        dev.debug("Removing endpoint 1 from group 0")
        await endpoint.remove_from_group(0)
        dev.debug("Removed endpoint 1 from group 0")


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
        SKIP_CONFIGURATION: True,
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
                    Metering.cluster_id,
                    ElectricalMeasurementCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.MAIN_POWER_OUTLET,
                INPUT_CLUSTERS: [AnalogInputCluster],
                OUTPUT_CLUSTERS: [AnalogInput.cluster_id, Groups.cluster_id],
            },
            242: {
                PROFILE_ID: XIAOMI_PROFILE_ID,
                DEVICE_TYPE: XIAOMI_DEVICE_TYPE,
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    ep_attribute = "opple_cluster"
    attributes = {
        0x0009: ("mode", types.uint8_t, True),
    }
    attr_config = {0x0009: 0x00}

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        await self.write_attributes(self.attr_config, manufacturer=OPPLE_MFG_CODE)
        return result


class PlugMAEU01(PlugMMEU01):
    """lumi.plug.maeu01 plug."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        asyncio.create_task(remove_from_ep(self))

    signature = {
        MODELS_INFO: [
            (LUMI, "lumi.plug.maeu01"),
        ],
        ENDPOINTS: PlugMMEU01.signature[ENDPOINTS],
    }

    replacement = {
        SKIP_CONFIGURATION: False,
        ENDPOINTS: {
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
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: XIAOMI_PROFILE_ID,
                DEVICE_TYPE: XIAOMI_DEVICE_TYPE,
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
