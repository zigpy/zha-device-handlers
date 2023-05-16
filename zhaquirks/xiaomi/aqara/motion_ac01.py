"""Quirk for aqara lumi.motion.ac01."""
from __future__ import annotations

import logging
import math
from typing import Any

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as types
from zigpy.zcl.clusters.general import Basic, DeviceTemperature, Identify, Ota
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.foundation import CommandSchema, ZCLCommandDef

from zhaquirks.const import (
    ARGS,
    COMMAND,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import XiaomiAqaraE1Cluster

MAX_REGIONS = 10
OCCUPANCY = 0x0000
PRESENCE = 0x0142
PRESENCE2 = 101
PRESENCE_EVENT = 0x0143
PRESENCE_EVENT2 = 102
MONITORING_MODE = 0x0144
MOTION_SENSITIVITY = 0x010C
APPROACH_DISTANCE = 0x0146
REGION_CONFIG = 0x150
REGION_PRESENCE_EVENT = 0x151
EXITS_CONFIG = 0x153
INTERFERENCE_CONFIG = 0x154
REPORT_POSITION = 0x155
EDGES_CONFIG = 0x156
RESET_NO_PRESENCE_STATUS = 0x0157
POSITION_EVENT = 0xFFF2
SENSOR = "sensor"
REGION = "region"
POSITION = "position"
REGION_ANY = "region_any"
REGION_FORMAT = "region_{}"

_LOGGER = logging.getLogger(__name__)


class AqaraPresenceEvents(types.enum8):
    """Aqara presence events."""

    Enter = 0x00
    Leave = 0x01
    Enter_Left = 0x02
    Leave_Right = 0x03
    Enter_Right = 0x04
    Leave_Left = 0x05
    Approach = 0x06
    Away = 0x07
    Unknown = 0xFF


class AqaraRegionEvents(types.enum8):
    """Aqara region events."""

    Region_Enter = 0x01
    Region_Leave = 0x02
    Region_Occupied = 0x04
    Region_Unoccupied = 0x08


class RegionEventPayload(types.Struct):
    """Aqara region event payload."""

    region: types.uint8_t
    event: AqaraRegionEvents


class PositionEventPayload(types.Struct):
    """Aqara raw sensor payload."""

    header: types.FixedList[types.uint8_t, 16]
    data_type: types.uint8_t
    distance: types.uint16_t_be = types.StructField(requires=lambda s: s.data_type == 1)
    angle: types.int8s = types.StructField(requires=lambda s: s.data_type == 1)
    other: types.FixedList[types.int8s, 4] = types.StructField(
        requires=lambda s: s.data_type == 1
    )


class RegionDefinitionCommand(CommandSchema):
    """Schema for FP1 region definition."""

    class Row(types.bitmap4):
        X1_Left = 0b0001
        X2 = 0b0010
        X3 = 0b0100
        X4_Right = 0b1000

    Y1_Near: None = types.StructField(type=Row, optional=True)
    Y2: None = types.StructField(type=Row, optional=True)
    Y3: None = types.StructField(type=Row, optional=True)
    Y4: None = types.StructField(type=Row, optional=True)
    Y5: None = types.StructField(type=Row, optional=True)
    Y6: None = types.StructField(type=Row, optional=True)
    Y7_Far: None = types.StructField(type=Row, optional=True)


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    ep_attribute = "opple_cluster"
    attributes = {
        PRESENCE: ("presence", types.uint8_t, True),
        MONITORING_MODE: ("monitoring_mode", types.uint8_t, True),
        MOTION_SENSITIVITY: ("motion_sensitivity", types.uint8_t, True),
        APPROACH_DISTANCE: ("approach_distance", types.uint8_t, True),
        RESET_NO_PRESENCE_STATUS: ("reset_no_presence_status", types.uint8_t, True),
        REGION_CONFIG: ("region_configuration", types.LVBytes, True),
        EXITS_CONFIG: ("exits_configuration", types.uint32_t, True),
        INTERFERENCE_CONFIG: ("interference_configuration", types.uint32_t, True),
        EDGES_CONFIG: ("edges_configuration", types.uint32_t, True),
        REPORT_POSITION: ("report_position", types.uint8_t, True),
    }

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)
        if attrid == PRESENCE or attrid == PRESENCE2:
            if value != 0xFF:
                self.endpoint.occupancy.update_attribute(OCCUPANCY, value)
        elif attrid == PRESENCE_EVENT or attrid == PRESENCE_EVENT2:
            self.listener_event(ZHA_SEND_EVENT, AqaraPresenceEvents(value).name, {})
        elif attrid == REGION_PRESENCE_EVENT:
            data, _ = RegionEventPayload.deserialize(value)
            if data.event == AqaraRegionEvents.Region_Occupied:
                self.endpoint.device.endpoints[
                    data.region + 1
                ].occupancy.update_attribute(OCCUPANCY, 1)
            elif data.event == AqaraRegionEvents.Region_Unoccupied:
                self.endpoint.device.endpoints[
                    data.region + 1
                ].occupancy.update_attribute(OCCUPANCY, 0)
            else:
                self.listener_event(
                    ZHA_SEND_EVENT,
                    data.event.name,
                    {REGION: data.region},
                )
        elif attrid == POSITION_EVENT:
            data, _ = PositionEventPayload.deserialize(value)
            if data.data_type != 1:
                return
            x = math.floor(3 - math.sin(math.radians(data.angle)) * data.distance / 100)
            y = math.floor(1 + math.cos(math.radians(data.angle)) * data.distance / 100)
            _LOGGER.debug(
                "Presence reported at y=%d, x=%d, (distance=%d, angle=%d)",
                y,
                x,
                data.distance,
                data.angle,
            )
            self.listener_event(
                ZHA_SEND_EVENT,
                POSITION,
                {"y": y, "x": x, "distance": data.distance, "angle": data.angle},
            )


class FP1OccupancySensing(CustomCluster, OccupancySensing):
    """Main occupancy sensor with commands for configuring."""

    server_commands = {
        0x0001: ZCLCommandDef(
            name="set_exits",
            schema=RegionDefinitionCommand,
            direction=False,
            is_manufacturer_specific=True,
        ),
        0x0002: ZCLCommandDef(
            name="set_interference",
            schema=RegionDefinitionCommand,
            direction=False,
            is_manufacturer_specific=True,
        ),
        0x0003: ZCLCommandDef(
            name="set_edges",
            schema=RegionDefinitionCommand,
            direction=False,
            is_manufacturer_specific=True,
        ),
        0x0004: ZCLCommandDef(
            name="report_position",
            schema={},
            direction=False,
            is_manufacturer_specific=True,
        ),
    }

    command_to_attribute_mapping = {
        0x0001: EXITS_CONFIG,
        0x0002: INTERFERENCE_CONFIG,
        0x0003: EDGES_CONFIG,
    }

    async def command(
        self,
        command_id,
        *args,
        **kwargs,
    ):
        if command_id == 0x0004:
            await self.endpoint.device.endpoints[1].opple_cluster.write_attributes(
                {
                    REPORT_POSITION: 1,
                }
            )
        else:
            y1 = kwargs.get("Y1_Near", RegionDefinitionCommand.Row(0))
            y2 = kwargs.get("Y2", RegionDefinitionCommand.Row(0))
            y3 = kwargs.get("Y3", RegionDefinitionCommand.Row(0))
            y4 = kwargs.get("Y4", RegionDefinitionCommand.Row(0))
            y5 = kwargs.get("Y5", RegionDefinitionCommand.Row(0))
            y6 = kwargs.get("Y6", RegionDefinitionCommand.Row(0))
            y7 = kwargs.get("Y7_Far", RegionDefinitionCommand.Row(0))

            attribute = self.command_to_attribute_mapping[command_id]
            payload = (
                y1
                + (y2 << 4)
                + (y3 << 8)
                + (y4 << 12)
                + (y5 << 16)
                + (y6 << 20)
                + (y7 << 24)
            )
            await self.endpoint.device.endpoints[1].opple_cluster.write_attributes(
                {
                    attribute: payload,
                }
            )


class FP1RegionOccupancySensing(CustomCluster, OccupancySensing):
    """Region occupancy sensor with commands for configuring."""

    server_commands = {
        0x0001: ZCLCommandDef(
            name="set_region",
            schema=RegionDefinitionCommand,
            direction=False,
            is_manufacturer_specific=True,
        ),
        0x0002: ZCLCommandDef(
            name="clear_region",
            schema={},
            direction=False,
            is_manufacturer_specific=True,
        ),
    }

    async def command(
        self,
        command_id,
        *args,
        **kwargs,
    ):
        if command_id == 0x0001:
            y1 = kwargs.get("Y1_Near", RegionDefinitionCommand.Row(0))
            y2 = kwargs.get("Y2", RegionDefinitionCommand.Row(0))
            y3 = kwargs.get("Y3", RegionDefinitionCommand.Row(0))
            y4 = kwargs.get("Y4", RegionDefinitionCommand.Row(0))
            y5 = kwargs.get("Y5", RegionDefinitionCommand.Row(0))
            y6 = kwargs.get("Y6", RegionDefinitionCommand.Row(0))
            y7 = kwargs.get("Y7_Far", RegionDefinitionCommand.Row(0))

            region_id = self.endpoint.endpoint_id - 1
            payload = [
                command_id,
                region_id,
                y1 + (y2 << 4),
                y3 + (y4 << 4),
                y5 + (y6 << 4),
                int(y7),
                0xFF,
            ]
            await self.endpoint.device.endpoints[1].opple_cluster.write_attributes(
                {
                    REGION_CONFIG: payload,
                }
            )
        elif command_id == 0x0002:
            region_id = self.endpoint.endpoint_id - 1
            payload = [command_id, region_id, 0, 0, 0, 0, 0]
            await self.endpoint.device.endpoints[1].opple_cluster.write_attributes(
                {
                    REGION_CONFIG: payload,
                }
            )


class AqaraLumiMotionAc01(CustomDevice):
    """Aqara lumi.motion.ac01 custom device implementation."""

    signature = {
        MODELS_INFO: [("aqara", "lumi.motion.ac01")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0xFFF0,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OppleCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0xFFF0,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    DeviceTemperature.cluster_id,
                    FP1OccupancySensing,
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
            **{
                i
                + 1: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                    INPUT_CLUSTERS: [
                        # Give each one a unique name for easier identification
                        type(
                            f"FP1Region{i}OccupancySensing",
                            (FP1RegionOccupancySensing,),
                            {},
                        ),
                    ],
                    OUTPUT_CLUSTERS: [],
                }
                for i in range(1, MAX_REGIONS + 1)
            },
        }
    }

    device_automation_triggers = {
        (AqaraPresenceEvents.Enter.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Enter.name
        },
        (AqaraPresenceEvents.Leave.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Leave.name
        },
        (AqaraPresenceEvents.Enter_Left.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Enter_Left.name
        },
        (AqaraPresenceEvents.Leave_Right.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Leave_Right.name
        },
        (AqaraPresenceEvents.Enter_Right.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Enter_Right.name
        },
        (AqaraPresenceEvents.Leave_Left.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Leave_Left.name
        },
        (AqaraPresenceEvents.Approach.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Approach.name
        },
        (AqaraPresenceEvents.Away.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Away.name
        },
        (AqaraPresenceEvents.Unknown.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Unknown.name
        },
        (AqaraRegionEvents.Region_Enter.name, REGION_ANY): {
            COMMAND: AqaraRegionEvents.Region_Enter.name
        },
        (AqaraRegionEvents.Region_Leave.name, REGION_ANY): {
            COMMAND: AqaraRegionEvents.Region_Leave.name
        },
        **{
            (AqaraRegionEvents.Region_Enter.name, REGION_FORMAT.format(i)): {
                COMMAND: AqaraRegionEvents.Region_Enter.name,
                ARGS: {REGION: i},
            }
            for i in range(1, MAX_REGIONS + 1)
        },
        **{
            (AqaraRegionEvents.Region_Leave.name, REGION_FORMAT.format(i)): {
                COMMAND: AqaraRegionEvents.Region_Leave.name,
                ARGS: {REGION: i},
            }
            for i in range(1, MAX_REGIONS + 1)
        },
    }
