"""Aqara Curtain Driver E1 device."""
from __future__ import annotations

import logging
from typing import Any

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration, Time
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster
from zigpy.zdo.types import NodeDescriptor

from zhaquirks import Bus, CustomCluster, LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import LUMI, XiaomiCluster, XiaomiCustomDevice

_LOGGER = logging.getLogger(__name__)


class XiaomiAqaraCurtainE1(XiaomiCluster, ManufacturerSpecificCluster):
    """Xiaomi mfg cluster implementation specific for E1 Curtain."""

    cluster_id = 0xFCC0

    attributes = XiaomiCluster.attributes.copy()
    attributes.update(
        {
            0x0402: ("positions_stored", t.Bool, True),
            0x0407: ("store_position", t.uint8_t, True),
        }
    )


class WindowCoveringE1(CustomCluster, WindowCovering):
    """Xiaomi Window Covering configuration cluster."""

    def _update_attribute(self, attrid, value):
        if attrid == 8:
            if self.__getitem__(0x0017) == 1:
                value = 100 - value
        _LOGGER.info("WindowCovering - Attribute: %d Value: %d", attrid, value)
        super()._update_attribute(attrid, value)


class PowerConfigurationCurtainE1(PowerConfiguration, LocalDataCluster):
    """Xiaomi power configuration cluster implementation."""

    BATTERY_PERCENTAGE_REMAINING = 0x0021

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.power_bus_percentage.add_listener(self)

    def update_battery_percentage(self, value: int) -> None:
        """Doubles the battery percentage to the Zigbee spec's expected 200% maximum."""
        super()._update_attribute(
            self.BATTERY_PERCENTAGE_REMAINING,
            (value * 2),
        )


class E1Curtain(XiaomiCustomDevice):
    """Aqara Curtain Driver E1 device."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        self.power_bus_percentage: Bus = Bus()  # type: ignore
        super().__init__(*args, **kwargs)  # type: ignore

    signature = {
        MODELS_INFO: [(LUMI, "lumi.curtain.agl001")],
        ENDPOINTS: {
            # <SizePrefixedSimpleDescriptor endpoint=1 profile=260 device_type=256
            # device_version=1
            # input_clusters=[0, 2, 3, 4, 5, 6, 9, 64704, 13, 19, 258]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0107,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Time.cluster_id,
                    WindowCovering.cluster_id,
                    XiaomiAqaraCurtainE1.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                    XiaomiAqaraCurtainE1.cluster_id,
                ],
            }
        },
    }
    replacement = {
        NODE_DESCRIPTOR: NodeDescriptor(
            0x02, 0x40, 0x80, 0x115F, 0x7F, 0x0064, 0x2C00, 0x0064, 0x00
        ),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCurtainE1,
                    Identify.cluster_id,
                    Time.cluster_id,
                    WindowCoveringE1,
                    XiaomiAqaraCurtainE1,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                    XiaomiAqaraCurtainE1,
                ],
            }
        },
    }
