"""Quirk for aqara lumi.sensor_occupy.agl1."""

from __future__ import annotations

import logging
from typing import Any

from zigpy import types
from zigpy.quirks.v2 import (
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.zcl.clusters.general import DeviceTemperature
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.xiaomi import XiaomiAqaraE1Cluster

APPROACH_DISTANCE_ATTR_ID = 0x015B  # UINT32 The configurable maximum detection distance in millimeters (default 600 = 6 meters).
MOTION_ATTR_ID = 0x0160  # UINT8 Detected motion (0x02 = no movement, 0x03 = large movement, 0x04 = small movement)
MOTION_DISTANCE_ATTR_ID = 0x015F  # UINT32 Distance to the detected motion (mm)
MOTION_SENSITIVITY_ATTR_ID = 0x010C  # UINT8 The configurable detection sensitivity (0x01 = low, 0x02 = medium, 0x03 = high, default 0x03 = High)
OCCUPANCY_ATTR_ID = 0x0142  # UINT8 Occupancy detected 0x0 = absence, 0x01 = presence
RESET_NO_PRESENCE_STATUS_ATTR_ID = 0x0157  # UINT8 Trigger AI spatial learning
RESTART_DEVICE_ATTR_ID = 0x00E8  # BOOL Trigger device restart

RESET_NO_PRESENCE_STATUS_WRITE_VALUE = 1
RESTART_DEVICE_WRITE_VALUE = 0

_LOGGER = logging.getLogger(__name__)


class AqaraMotionSensitivity(types.enum8):
    """Aqara motion sensitivity."""

    Low = 0x01
    Medium = 0x02
    High = 0x03


class AqaraMotion(types.enum8):
    """Aqara motion."""

    Unknown_0 = 0x00
    Unknown_1 = 0x01
    Idle = 0x02
    Moving = 0x03
    Still = 0x04


class OppleCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer cluster for the FP1E presence sensor."""

    class AttributeDefs(BaseAttributeDefs):
        """Manufacturer specific attributes."""

        approach_distance = ZCLAttributeDef(
            id=APPROACH_DISTANCE_ATTR_ID,
            type=types.uint32_t,
            access="rw",
            is_manufacturer_specific=True,
        )

        motion = ZCLAttributeDef(
            id=MOTION_ATTR_ID,
            type=types.uint8_t,
            access="rp",
            is_manufacturer_specific=True,
        )

        motion_distance = ZCLAttributeDef(
            id=MOTION_DISTANCE_ATTR_ID,
            type=types.uint32_t,
            access="rp",
            is_manufacturer_specific=True,
        )

        motion_sensitivity = ZCLAttributeDef(
            id=MOTION_SENSITIVITY_ATTR_ID,
            type=types.uint8_t,
            access="rw",
            is_manufacturer_specific=True,
        )

        occupancy = ZCLAttributeDef(
            id=OCCUPANCY_ATTR_ID,
            type=types.uint8_t,
            access="rp",
            is_manufacturer_specific=True,
        )

        reset_no_presence_status = ZCLAttributeDef(
            id=RESET_NO_PRESENCE_STATUS_ATTR_ID,
            type=types.uint8_t,
            access="w",
            is_manufacturer_specific=True,
        )

        restart_device = ZCLAttributeDef(
            id=RESTART_DEVICE_ATTR_ID,
            type=types.Bool,
            access="w",
            is_manufacturer_specific=True,
        )

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)
        if attrid == OCCUPANCY_ATTR_ID:
            self.endpoint.occupancy.update_attribute(
                OccupancySensing.AttributeDefs.occupancy.id,
                OccupancySensing.Occupancy(value),
            )
        elif attrid == MOTION_ATTR_ID:
            self.endpoint.ias_zone.update_attribute(
                IasZone.AttributeDefs.zone_status.id,
                IasZone.ZoneStatus(
                    IasZone.ZoneStatus.Alarm_1 if value == AqaraMotion.Moving else 0
                ),
            )


(
    QuirkBuilder("aqara", "lumi.sensor_occupy.agl1")
    .friendly_name(model="Presence Sensor FP1E", manufacturer="Aqara")
    .adds(DeviceTemperature)
    .adds(OccupancySensing)
    .adds(
        IasZone,
        constant_attributes={
            IasZone.AttributeDefs.zone_type: IasZone.ZoneType.Motion_Sensor
        },
    )
    .replaces(OppleCluster)
    .number(
        OppleCluster.AttributeDefs.approach_distance.name,
        OppleCluster.cluster_id,
        min_value=0,
        max_value=6,
        step=0.1,
        # unit=UnitOfLength.METERS,
        multiplier=0.01,
        device_class=NumberDeviceClass.DISTANCE,
        translation_key="approach_distance",
        fallback_name="Approach distance",
    )
    .sensor(
        OppleCluster.AttributeDefs.motion_distance.name,
        OppleCluster.cluster_id,
        # unit=UnitOfLength.METERS,
        multiplier=0.01,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="motion_distance",
        fallback_name="Motion distance",
    )
    .enum(
        OppleCluster.AttributeDefs.motion_sensitivity.name,
        AqaraMotionSensitivity,
        OppleCluster.cluster_id,
        translation_key="motion_sensitivity",
        fallback_name="Motion sensitivity",
    )
    .write_attr_button(
        OppleCluster.AttributeDefs.reset_no_presence_status.name,
        RESET_NO_PRESENCE_STATUS_WRITE_VALUE,
        OppleCluster.cluster_id,
        translation_key="reset_no_presence_status",
        fallback_name="Presence status reset",
    )
    .write_attr_button(
        OppleCluster.AttributeDefs.restart_device.name,
        RESTART_DEVICE_WRITE_VALUE,
        OppleCluster.cluster_id,
        # entity_type=EntityType.DIAGNOSTIC,
        translation_key="restart_device",
        fallback_name="Restart device",
    )
    .add_to_registry()
)
