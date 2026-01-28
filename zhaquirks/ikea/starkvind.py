"""Device handler for IKEA of Sweden STARKVIND Air purifier."""

from __future__ import annotations

from typing import Any

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.hvac import Fan
from zigpy.zcl.clusters.measurement import PM25
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import Bus
from zhaquirks.ikea import IKEA


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
        if attrid == 0x0004:
            if (
                value is not None and value < 5500
            ):  # > 5500 = out of scale; if value is 65535 (0xFFFF), device is off
                self.endpoint.device.pm25_bus.listener_event("update_state", value)
        elif attrid in (0x0006, 0x0007):
            if value >= 10 and value <= 50:
                value = value // 5
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
                    ["air_quality_25pm"],
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


class IkeaSTARKVIND(CustomDeviceV2):
    """STARKVIND Air purifier by IKEA of Sweden."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.pm25_bus = Bus()
        self.change_fan_mode_bus = Bus()
        self.change_fan_mode_ha_bus = Bus()
        super().__init__(*args, **kwargs)


(
    QuirkBuilder(IKEA, "STARKVIND Air purifier")
    .applies_to(IKEA, "STARKVIND Air purifier table")
    .device_class(IkeaSTARKVIND)
    .removes(Fan, endpoint_id=1)
    .removes(PM25, cluster_type=ClusterType.Client, endpoint_id=1)
    .adds(PM25Cluster, cluster_type=ClusterType.Server, endpoint_id=1)
    .replaces(IkeaAirpurifier, endpoint_id=1)
    .add_to_registry()
)
