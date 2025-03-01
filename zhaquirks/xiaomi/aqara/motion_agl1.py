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
from zigpy.quirks.v2.homeassistant import EntityType, UnitOfLength
from zigpy.zcl.clusters.general import DeviceTemperature
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.xiaomi import XiaomiAqaraE1Cluster


class AqaraMotion(types.enum8):
    """Aqara motion attribute values."""

    Idle = 0x02
    Moving = 0x03
    Still = 0x04


class AqaraMotionSensitivity(types.enum8):
    """Aqara motion sensitivity attribute values."""

    Low = 0x01
    Medium = 0x02
    High = 0x03


class AqaraOccupancy(types.enum8):
    """Aqara occupancy attribute values."""

    Unoccupied = 0x00
    Occupied = 0x01


class IasZoneLocal(LocalDataCluster, IasZone):
    """Virtual cluster for IasZone."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Motion_Sensor
    }
    _VALID_ATTRIBUTES = {IasZone.AttributeDefs.zone_status.id}


class OccupancySensingLocal(LocalDataCluster, OccupancySensing):
    """Virtual cluster for OccupancySensing."""

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

        # Detected motion
        motion = ZCLAttributeDef(
            id=0x0160,
            type=AqaraMotion,
            zcl_type=DataTypeId.uint8,
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

        # The configurable detection sensitivity
        motion_sensitivity = ZCLAttributeDef(
            id=0x010C,
            type=AqaraMotionSensitivity,
            zcl_type=DataTypeId.uint8,
            access="rw",
            is_manufacturer_specific=True,
        )

        # Detected occupancy
        occupancy = ZCLAttributeDef(
            id=0x0142,
            type=AqaraOccupancy,
            zcl_type=DataTypeId.uint8,
            access="rp",
            is_manufacturer_specific=True,
        )

        # Trigger AI spatial learning (write 1)
        reset_no_presence_status = ZCLAttributeDef(
            id=0x0157,
            type=types.uint8_t,
            access="w",
            is_manufacturer_specific=True,
        )

        # Trigger device restart (write 0)
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
                OccupancySensing.Occupancy.Occupied
                if value == AqaraOccupancy.Occupied
                else OccupancySensing.Occupancy.Unoccupied,
            )
        elif attrid == self.AttributeDefs.motion.id:
            self.endpoint.ias_zone.update_attribute(
                IasZone.AttributeDefs.zone_status.id,
                IasZone.ZoneStatus.Alarm_1 if value == AqaraMotion.Moving else 0,
            )


(
    QuirkBuilder("aqara", "lumi.sensor_occupy.agl1")
    .friendly_name(manufacturer="Aqara", model="Presence Sensor FP1E")
    .adds(DeviceTemperature)
    .adds(OccupancySensingLocal)
    .adds(IasZoneLocal)
    .replaces(OppleCluster)
    .number(
        OppleCluster.AttributeDefs.approach_distance.name,
        OppleCluster.cluster_id,
        min_value=0,
        max_value=6,
        step=0.1,
        unit=UnitOfLength.METERS,
        multiplier=0.01,
        device_class=NumberDeviceClass.DISTANCE,
        translation_key="approach_distance",
        fallback_name="Approach distance",
    )
    .sensor(
        OppleCluster.AttributeDefs.motion_distance.name,
        OppleCluster.cluster_id,
        unit=UnitOfLength.METERS,
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
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="restart_device",
        fallback_name="Restart device",
    )
    .add_to_registry()
)
