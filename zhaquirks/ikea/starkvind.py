"""Device handler for IKEA of Sweden STARKVIND Air purifier."""
from __future__ import annotations

import logging
from typing import Any

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.hvac import Fan
from zigpy.zcl.clusters.measurement import PM25, IlluminanceMeasurement

from zhaquirks import Bus
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.ikea import IKEA, IKEA_CLUSTER_ID, WWAH_CLUSTER_ID

_LOGGER = logging.getLogger(__name__)


class IkeaAirpurifier(CustomCluster):
    """Ikea Manufacturer Specific AirPurifier."""

    name: str = "Ikea Airpurifier"
    cluster_id: t.uint16_t = 0xFC7D  # 64637  0xFC7D control air purifier with manufacturer-specific attributes
    ep_attribute: str = "ikea_airpurifier"

    attributes = {
        0x0000: ("filter_run_time", t.uint32_t, True),
        0x0001: ("replace_filter", t.uint8_t, True),
        0x0002: ("filter_life_time", t.uint32_t, True),
        0x0003: ("disable_led", t.Bool, True),
        0x0004: ("air_quality_25pm", t.uint16_t, True),
        0x0005: ("child_lock", t.Bool, True),
        0x0006: (
            "fan_mode",
            t.uint8_t,
            True,
        ),  # fan mode (Off, Auto, fanspeed 10 - 50)  read/write
        0x0007: (
            "fan_speed",
            t.uint8_t,
            True,
        ),  # current fan speed (only fan speed 10-50)
        0x0008: ("device_run_time", t.uint32_t, True),
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)
        self.endpoint.device.change_fan_mode_bus.add_listener(self)

    def _update_attribute(self, attrid, value):
        if attrid == 0x0004:
            if (
                value is not None and value < 5500
            ):  # > 5500 = out of scale; if value is 65535 (0xFFFF), device is off
                self.endpoint.device.pm25_bus.listener_event("update_state", value)
        elif attrid == 0x0006:
            if value > 9 and value < 51:
                value = value / 5
        super()._update_attribute(attrid, value)

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """Override wrong writes to thermostat attributes."""
        if "fan_mode" in attributes:
            fan_mode = attributes.get("fan_mode")
            if fan_mode and fan_mode > 1 and fan_mode < 11:
                fan_mode = fan_mode * 5
                return await super().write_attributes(
                    {"fan_mode": fan_mode}, manufacturer
                )
        return await super().write_attributes(attributes, manufacturer)


class PM25Cluster(CustomCluster, PM25):
    """PM25 input cluster, only used to show PM2.5 values from IKEA cluster."""

    cluster_id = PM25.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.pm25_bus.add_listener(self)

    def update_state(self, value):
        """25pm reported."""
        self._update_attribute(0x0000, value)

    def _update_attribute(self, attrid, value):
        """Check for a valid PM2.5 value."""
        if attrid == 0x0000:
            if value < 5500:
                super()._update_attribute(attrid, value)
        else:
            super()._update_attribute(attrid, value)

    async def read_attributes(
        self, attributes, allow_cache=False, only_cache=False, manufacturer=None
    ):
        """Read attributes ZCL foundation command."""
        if "measured_value" in attributes:
            return (
                await self.endpoint.device.endpoints[1]
                .in_clusters[64637]
                .read_attributes(
                    {"air_quality_25pm"},
                    allow_cache=allow_cache,
                    only_cache=only_cache,
                    manufacturer=manufacturer,
                )
            )
        else:
            return await super().read_attributes(
                attributes,
                allow_cache=allow_cache,
                only_cache=only_cache,
                manufacturer=manufacturer,
            )


class IkeaSTARKVIND(CustomDevice):
    """STARKVIND Air purifier by IKEA of Sweden."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.pm25_bus = Bus()
        self.change_fan_mode_bus = Bus()
        self.change_fan_mode_ha_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=7 (0x0007)
        # device_version=0
        # input_clusters=[0, 3, 4, 5, 514, 64599, 64637] output_clusters=[25, 1024, 1066]>
        MODELS_INFO: [
            (IKEA, "STARKVIND Air purifier"),
            (IKEA, "STARKVIND Air purifier table"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COMBINED_INTERFACE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    Fan.cluster_id,  # 514    0x0202
                    WWAH_CLUSTER_ID,  # 64599  0xFC57
                    IkeaAirpurifier.cluster_id,  # 64637  0xFC7D
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 25      0x0019
                    IlluminanceMeasurement.cluster_id,  # 1024    0x0400
                    PM25.cluster_id,  # 1066    0x042A PM2.5 Measurement Cluster
                ],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0
            # input_clusters=[33] output_clusters=[33]>
            242: {
                PROFILE_ID: 0xA1E0,  # 41440 (dec)
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,  # 0x0021 = GreenPowerProxy.cluster_id
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COMBINED_INTERFACE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    WWAH_CLUSTER_ID,  # 64599  0xFC57
                    IkeaAirpurifier,  # 64637  0xFC7D control air purifier with manufacturer-specific attributes
                    PM25Cluster,  # 1066    0x042A PM2.5 Measurement Cluster
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 25      0x0019
                    IlluminanceMeasurement.cluster_id,  # 1024    0x0400
                ],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0
            # input_clusters=[33] output_clusters=[33]>
            242: {
                PROFILE_ID: 0xA1E0,  # 41440 (dec)
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,  # 0x0021 = GreenPowerProxy.cluster_id
                ],
            },
        },
    }


class IkeaSTARKVIND_v2(IkeaSTARKVIND):
    """STARKVIND Air purifier by IKEA of Sweden."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=7 (0x0007)
        # device_version=0
        # input_clusters=[0, 3, 4, 5, 514, 64599, 64637] output_clusters=[25, 1024, 1066]>
        MODELS_INFO: IkeaSTARKVIND.signature[MODELS_INFO].copy(),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COMBINED_INTERFACE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    Fan.cluster_id,  # 514    0x0202
                    WWAH_CLUSTER_ID,  # 64599  0xFC57
                    IKEA_CLUSTER_ID,  # 64636  0xFC7C
                    IkeaAirpurifier.cluster_id,  # 64637  0xFC7D
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 25      0x0019
                    IlluminanceMeasurement.cluster_id,  # 1024    0x0400
                    PM25.cluster_id,  # 1066    0x042A PM2.5 Measurement Cluster
                ],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0
            # input_clusters=[33] output_clusters=[33]>
            242: {
                PROFILE_ID: 0xA1E0,  # 41440 (dec)
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,  # 0x0021 = GreenPowerProxy.cluster_id
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COMBINED_INTERFACE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    WWAH_CLUSTER_ID,  # 64599  0xFC57
                    IKEA_CLUSTER_ID,  # 64636  0xFC7C
                    IkeaAirpurifier,  # 64637  0xFC7D control air purifier with manufacturer-specific attributes
                    PM25Cluster,  # 1066    0x042A PM2.5 Measurement Cluster
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 25      0x0019
                    IlluminanceMeasurement.cluster_id,  # 1024    0x0400
                ],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0
            # input_clusters=[33] output_clusters=[33]>
            242: {
                PROFILE_ID: 0xA1E0,  # 41440 (dec)
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,  # 0x0021 = GreenPowerProxy.cluster_id
                ],
            },
        },
    }
