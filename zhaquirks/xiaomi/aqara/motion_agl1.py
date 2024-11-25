"""Quirk for aqara lumi.sensor_occupy.agl1."""

from __future__ import annotations

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

from zhaquirks import LocalDataCluster
from zhaquirks.xiaomi import XiaomiAqaraE1Cluster


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


class IasZoneLocal(LocalDataCluster, IasZone):
    """Virtual cluster for IasZone."""

    # required to make sure ZHA creates sensors when initially pairing
    _VALID_ATTRIBUTES = {IasZone.AttributeDefs.zone_status.id}


class OccupancySensingLocal(LocalDataCluster, OccupancySensing):
    """Virtual cluster for OccupancySensing."""

    # required to make sure ZHA creates sensors when initially pairing
    _VALID_ATTRIBUTES = {OccupancySensing.AttributeDefs.occupancy.id}


class OppleCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer cluster for the presence sensor FP1E."""

    class AttributeDefs(BaseAttributeDefs):
        """Manufacturer specific attributes."""

        # The configurable maximum detection distance in millimeters (default 600 = 6 meters).
        approach_distance = ZCLAttributeDef(
            id=0x015B,
            type=types.uint32_t,
            access="rw",
            is_manufacturer_specific=True,
        )

        # Detected motion (0x02 = no movement, 0x03 = large movement, 0x04 = small movement)
        motion = ZCLAttributeDef(
            id=0x0160,
            type=types.uint8_t,
            access="rp",
            is_manufacturer_specific=True,
        )

        # Distance to the detected motion in millimeters
        motion_distance = ZCLAttributeDef(
            id=0x015F,
            type=types.uint32_t,
            access="rp",
            is_manufacturer_specific=True,
        )

        # The configurable detection sensitivity (0x01 = low, 0x02 = medium, 0x03 = high, default 0x03 = high)
        motion_sensitivity = ZCLAttributeDef(
            id=0x010C,
            type=types.uint8_t,
            access="rw",
            is_manufacturer_specific=True,
        )

        # Occupancy detected (0x0 = absence, 0x01 = presence)
        occupancy = ZCLAttributeDef(
            id=0x0142,
            type=types.uint8_t,
            access="rp",
            is_manufacturer_specific=True,
        )

        # Trigger AI spatial learning (write 1 to tigger)
        reset_no_presence_status = ZCLAttributeDef(
            id=0x0157,
            type=types.uint8_t,
            access="w",
            is_manufacturer_specific=True,
        )

        # Trigger device restart (write 0 to tigger)
        restart_device = ZCLAttributeDef(
            id=0x00E8,
            type=types.Bool,
            access="w",
            is_manufacturer_specific=True,
        )

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.occupancy.id:
            self.endpoint.occupancy.update_attribute(
                OccupancySensing.AttributeDefs.occupancy.id,
                OccupancySensing.Occupancy(value),
            )
        elif attrid == self.AttributeDefs.motion.id:
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
    .adds(OccupancySensingLocal)
    .adds(
        IasZoneLocal,
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
        1,
        OppleCluster.cluster_id,
        translation_key="reset_no_presence_status",
        fallback_name="Presence status reset",
    )
    .write_attr_button(
        OppleCluster.AttributeDefs.restart_device.name,
        0,
        OppleCluster.cluster_id,
        # entity_type=EntityType.DIAGNOSTIC,
        translation_key="restart_device",
        fallback_name="Restart device",
    )
    .add_to_registry()
)
