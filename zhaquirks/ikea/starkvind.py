"""Device handler for IKEA of Sweden STARKVIND Air purifier."""

from __future__ import annotations

from zigpy.profiles import zgp, zha
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
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

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


class IkeaAirpurifier(CustomCluster):
    """Ikea Manufacturer Specific AirPurifier."""

    name: str = "Ikea Airpurifier"
    cluster_id: t.uint16_t = 0xFC7D  # 64637  0xFC7D control air purifier with manufacturer-specific attributes
    ep_attribute: str = "ikea_airpurifier"

    class AttributeDefs(BaseAttributeDefs):
        """Cluster attributes."""

        filter_run_time = ZCLAttributeDef(
            id=0x0000, type=t.uint32_t, manufacturer_code=0x1002
        )
        replace_filter = ZCLAttributeDef(
            id=0x0001, type=t.uint8_t, manufacturer_code=0x1002
        )
        filter_life_time = ZCLAttributeDef(
            id=0x0002, type=t.uint32_t, manufacturer_code=0x1002
        )
        disable_led = ZCLAttributeDef(id=0x0003, type=t.Bool, manufacturer_code=0x1002)
        air_quality_25pm = ZCLAttributeDef(
            id=0x0004, type=t.uint16_t, manufacturer_code=0x1002
        )
        child_lock = ZCLAttributeDef(id=0x0005, type=t.Bool, manufacturer_code=0x1002)
        fan_mode = ZCLAttributeDef(
            id=0x0006, type=t.uint8_t, manufacturer_code=0x1002
        )  # fan mode (Off, Auto, fanspeed 10 - 50)  read/write
        fan_speed = ZCLAttributeDef(
            id=0x0007, type=t.uint8_t, manufacturer_code=0x1002
        )  # current fan speed (only fan speed 10-50)
        device_run_time = ZCLAttributeDef(
            id=0x0008, type=t.uint32_t, manufacturer_code=0x1002
        )

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)
        self.endpoint.device.change_fan_mode_bus.add_listener(self)

    def _update_attribute(self, attrid, value):
        # Forward PM2.5 readings to the bus for the PM25Cluster
        if attrid == self.AttributeDefs.air_quality_25pm.id:
            if value is not None and value < 5500:
                self.endpoint.device.pm25_bus.listener_event("update_state", value)
        super()._update_attribute(attrid, value)

    def report_attribute_override_fan_mode(self, value: int) -> int:
        """Transform fan_mode from device scale (10-50) to logical scale (2-10)."""
        if value >= 10 and value <= 50:
            return value // 5
        return value

    def report_attribute_override_fan_speed(self, value: int) -> int:
        """Transform fan_speed from device scale (10-50) to logical scale (2-10)."""
        if value >= 10 and value <= 50:
            return value // 5
        return value

    def write_attribute_transform_fan_mode(self, value: int) -> int:
        """Transform fan_mode value before writing (multiply by 5)."""
        if value > 1 and value < 11:
            return value * 5
        return value


class PM25Cluster(CustomCluster, PM25):
    """PM25 input cluster, only used to show PM2.5 values from IKEA cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.pm25_bus.add_listener(self)

    def update_state(self, value):
        """25pm reported."""
        self._update_attribute(0x0000, value)

    def report_attribute_override_measured_value(self, value: int) -> int | None:
        """Filter invalid PM2.5 values >= 5500."""
        if value >= 5500:
            return None
        return value

    async def read_attribute_override_measured_value(self) -> t.uint16_t:
        """Read measured_value from IkeaAirpurifier air_quality_25pm."""
        ikea_airpurifier = self.endpoint.device.endpoints[1].ikea_airpurifier
        success, failure = await ikea_airpurifier.read_attributes(
            [IkeaAirpurifier.AttributeDefs.air_quality_25pm]
        )
        return success[IkeaAirpurifier.AttributeDefs.air_quality_25pm]


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
                PROFILE_ID: zgp.PROFILE_ID,  # 41440 (dec)
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
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
                PROFILE_ID: zgp.PROFILE_ID,  # 41440 (dec)
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
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
                PROFILE_ID: zgp.PROFILE_ID,  # 41440 (dec)
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
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
                PROFILE_ID: zgp.PROFILE_ID,  # 41440 (dec)
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,  # 0x0021 = GreenPowerProxy.cluster_id
                ],
            },
        },
    }
