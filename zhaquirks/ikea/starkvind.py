"""Device handler for IKEA of Sweden STARKVIND Air purifier."""
import logging
import asyncio
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    Ota,
    Scenes,
    GreenPowerProxy,
)
from zigpy.zcl.clusters.hvac import Fan
from zhaquirks.ikea import IKEA
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    PM25,
)
from zhaquirks import Bus

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from zigpy.zcl import foundation

WWAH_CLUSTER_ID = 0xFC57  # decimal = 64599
_LOGGER = logging.getLogger(__name__)


class manuSpecificIkeaAirPurifier(CustomCluster):
    """Ikea Manufacturer Specific AirPurifier."""

    name: str = "Ikea Manufacturer Specific AirPurifier"
    cluster_id: t.uint16_t = 0xFC7D  # 64637  0xFC7D control air purifier with manufacturer-specific attributes
    ep_attribute: str = "ikea_manufacturer"

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
        self._update_attribute(
            0x0003, False
        )  # workaround for empty _attr_cache in https://github.com/zigpy/zigpy/blob/07a3345dd51e54765831cd675fe7eefb57a3aec0/zigpy/zcl/__init__.py#L741 because switch.py - create_entity won't create an entity without
        self._update_attribute(
            0x0005, False
        )  # workaround for empty _attr_cache in https://github.com/zigpy/zigpy/blob/07a3345dd51e54765831cd675fe7eefb57a3aec0/zigpy/zcl/__init__.py#L741 because switch.py - create_entity won't create an entity without
        self.endpoint.device.change_fan_mode_bus.add_listener(self)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == 0x0004:
            if (
                value is not None and value < 5500
            ):  # > 5500 = out of scale; if value is 65535 (0xFFFF), device is off
                self.endpoint.device.pm25_bus.listener_event("update_state", value)
        elif attrid == 0x0006:
            if value is not None:
                if value > 9 and value < 51:
                    value = value / 5
                self.endpoint.device.change_fan_mode_ha_bus.listener_event(
                    "update_fan_mode_ha", value
                )

    def update_fan_mode(self, value):
        """Update fanmode by calling send_fan_mode."""
        if value > 1 and value < 11:
            value = value * 5
        asyncio.create_task(self.send_fan_mode(value))

    async def send_fan_mode(self, value) -> None:
        """Write new fanmode to attribute fan_mode in IKEA cluster."""
        ikea_cluster = self.endpoint.device.endpoints[1].in_clusters[64637]
        new_fan_mode = {"fan_mode": value}
        await ikea_cluster.write_attributes(new_fan_mode)


class FanCluster(CustomCluster, Fan):
    """Fan input cluster, only used to relay fanmode to IKEA cluster."""

    cluster_id = Fan.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)
        self.endpoint.device.change_fan_mode_ha_bus.add_listener(self)

    def update_fan_mode_ha(self, value):
        """Update attribute in Fancluster."""
        super()._update_attribute(0x0000, value)  # FanMode = 0x0000

    def _update_attribute(self, attrid, value):
        """Ignore update_attribute because the fan cluster has only Off, Low, Medium, High, On, Auto and Smart."""
        asyncio.create_task(self.read_fan_mode())

    async def read_fan_mode(self) -> None:
        """Read current fanmode from IKEA Cluster."""
        ikea_cluster = self.endpoint.device.endpoints[1].in_clusters[64637]
        await ikea_cluster.read_attributes({"fan_mode"})

    async def write_attributes(self, attributes, manufacturer=None):
        """Ignore writing values to FAN cluster attributes and forward fanmode to update_fan_mode in IKEA cluster."""
        if "fan_mode" in attributes:
            fan_mode = attributes.get("fan_mode")
            if fan_mode is not None:
                self.endpoint.device.change_fan_mode_bus.listener_event(
                    "update_fan_mode", fan_mode
                )
        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


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

    def read_attributes(
        self, attributes, allow_cache=False, only_cache=False, manufacturer=None
    ):
        """Read attributes ZCL foundation command."""
        if "measured_value" in attributes:
            return (
                self.endpoint.device.endpoints[1]
                .in_clusters[64637]
                .read_attributes(
                    {"air_quality_25pm"},
                    allow_cache=allow_cache,
                    only_cache=only_cache,
                    manufacturer=manufacturer,
                )
            )
        else:
            return super().read_attributes(
                attributes, allow_cache=True, only_cache=True, manufacturer=manufacturer
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
        MODELS_INFO: [(IKEA, "STARKVIND Air purifier")],
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
                    manuSpecificIkeaAirPurifier.cluster_id,  # 64637  0xFC7D
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
                    FanCluster,  # 514
                    WWAH_CLUSTER_ID,  # 64599  0xFC57
                    manuSpecificIkeaAirPurifier,  # 64637  0xFC7D control air purifier with manufacturer-specific attributes
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
