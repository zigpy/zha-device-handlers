"""ZHA quirk for Danfoss Icon2 main controller (model 0x0210).

Uses the QuirkV2 builder API so that Home Assistant automatically creates
entities for all manufacturer-specific attributes — no ZHA Toolkit needed.
Supports 1 to 16 zone endpoints; entities are only created for endpoints
that actually exist on the paired device.

Entities created automatically per zone endpoint (1–16):
  binary_sensor  output_status          – zone valve actively heating   (standard)
  binary_sensor  icon2_pre_heat_status  – pre-heat cycle running        (diagnostic)
  sensor         room_status_code       – zone error flags (raw bitmap)  (diagnostic)
  select         room_floor_sensor_mode – floor sensor operating mode   (config)
  select         schedule_type_used     – regular vs vacation schedule   (config)
  switch         icon2_pre_heat         – enable/disable pre-heat        (config)

Entities created automatically on endpoint 232 (main controller):
  binary_sensor  heat_supply_request        – pump/boiler relay active      (standard)
  sensor         system_status_code         – system error flags (raw bitmap)(diagnostic)
  sensor         system_status_water        – hot/cool water in pipes        (diagnostic)
  sensor         multimaster_role           – master/slave role              (diagnostic)
  select         icon_forced_heating_cooling – force heating or cooling mode (config)

Standard entities (climate per zone, floor temp sensor, humidity sensor, battery)
are created automatically by ZHA from the standard clusters without any quirk.

Note on bitmap sensors (system_status_code, room_status_code): ZHA shows the
raw integer. To check an individual error flag in a template sensor, use:
  {{ (states('sensor.icon2_system_status_code') | int) | bitwise_and(1) != 0 }}
(bit 0 = missing_expansion_board, bit 1 = missing_radio_module, etc.)
"""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef

DANFOSS_MANUFACTURER_CODE = 0x1246

# ---------------------------------------------------------------------------
# Enum / bitmap types matching Z2M converter values
# ---------------------------------------------------------------------------


class DanfossOutputStatus(t.enum8):
    """Zone actuator state – is this zone's valve open and heating."""

    inactive = 0x00
    active = 0x01


class DanfossRoomStatusCode(t.bitmap16):
    """Zone thermostat error flags (multiple bits may be set simultaneously)."""

    no_error = 0x0000
    missing_rt = 0x0001
    rt_touch_error = 0x0002
    floor_sensor_short_circuit = 0x0004
    floor_sensor_disconnected = 0x0008


class DanfossRoomFloorSensorMode(t.enum8):
    """Floor sensor operating mode."""

    comfort = 0x00
    floor_only = 0x01
    dual_mode = 0x02


class DanfossScheduleTypeUsed(t.enum8):
    """Which schedule is currently active on this zone."""

    regular_schedule_selected = 0x00
    vacation_schedule_selected = 0x01


class DanfossPreHeat(t.enum8):
    """Preheat feature enabled or disabled."""

    disable = 0x00
    enable = 0x01


class DanfossPreHeatStatus(t.enum8):
    """Preheat cycle currently running."""

    disable = 0x00
    enable = 0x01


class DanfossSystemStatusCode(t.bitmap16):
    """Main controller system error/status bitmap."""

    no_error = 0x0000
    missing_expansion_board = 0x0001
    missing_radio_module = 0x0002
    missing_command_module = 0x0004
    missing_master_rail = 0x0008
    missing_slave_rail_no_1 = 0x0010
    missing_slave_rail_no_2 = 0x0020
    pt1000_input_short_circuit = 0x0040
    pt1000_input_open_circuit = 0x0080
    error_on_one_or_more_output = 0x0100


class DanfossHeatSupplyRequest(t.enum8):
    """Main controller heat demand – drives the pump/boiler relay output."""

    none = 0x00
    heat_supply_request = 0x01


class DanfossSystemStatusWater(t.enum8):
    """Water flow direction in the hydronic circuit."""

    hot_water_flow_in_pipes = 0x00
    cool_water_flow_in_pipes = 0x01


class DanfossMultimasterRole(t.enum8):
    """Role of this controller in a multimaster setup."""

    invalid_unused = 0x00
    master = 0x01
    slave_1 = 0x02
    slave_2 = 0x03


class DanfossIconForcedHeatingCooling(t.enum8):
    """Forced heating or cooling override mode."""

    force_heating = 0x00
    force_cooling = 0x01
    none = 0x02


# ---------------------------------------------------------------------------
# Extend Thermostat.attributes with Danfoss zone manufacturer attributes.
#
# Using .replaces() per zone endpoint crashes with KeyError when the device
# has fewer than 16 zones, because zigpy tries to remove the original cluster
# from each endpoint before adding the replacement. Extending the base class
# attributes dict avoids this: entity declarations already skip missing
# endpoints gracefully, so no replacement is needed.
# ---------------------------------------------------------------------------

Thermostat.attributes = Thermostat.attributes.copy()
Thermostat.attributes.update(
    {
        0x4100: ZCLAttributeDef(
            "room_status_code",
            type=DanfossRoomStatusCode,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        ),
        0x4110: ZCLAttributeDef(
            "output_status",
            type=DanfossOutputStatus,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        ),
        0x4120: ZCLAttributeDef(
            "room_floor_sensor_mode",
            type=DanfossRoomFloorSensorMode,
            access="rwp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        ),
        0x4121: ZCLAttributeDef(
            "floor_min_setpoint",
            type=t.int16s,
            access="rwp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        ),
        0x4122: ZCLAttributeDef(
            "floor_max_setpoint",
            type=t.int16s,
            access="rwp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        ),
        0x4130: ZCLAttributeDef(
            "schedule_type_used",
            type=DanfossScheduleTypeUsed,
            access="rwp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        ),
        0x4131: ZCLAttributeDef(
            "icon2_pre_heat",
            type=DanfossPreHeat,
            access="rwp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        ),
        0x414F: ZCLAttributeDef(
            "icon2_pre_heat_status",
            type=DanfossPreHeatStatus,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        ),
    }
)
# zigpy keeps a parallel name→def dict that must be rebuilt after patching attributes
Thermostat.attributes_by_name = {
    attr_def.name: attr_def
    for attr_def in Thermostat.attributes.values()
    if attr_def.name is not None
}


# ---------------------------------------------------------------------------
# Custom cluster: diagnostic on endpoint 232 (main controller)
# heat_supply_request (0x4031) is the key attribute: it indicates the pump
# relay is active and the boiler/heat source is being called.
# ---------------------------------------------------------------------------


class DanfossMainDiagnosticCluster(CustomCluster, Diagnostic):
    """Diagnostic cluster on endpoint 232 with Danfoss system-level attributes."""

    attributes = Diagnostic.attributes.copy()
    attributes.update(
        {
            0x4000: ZCLAttributeDef(
                "system_status_code",
                type=DanfossSystemStatusCode,
                access="rp",
                manufacturer_code=DANFOSS_MANUFACTURER_CODE,
            ),
            0x4031: ZCLAttributeDef(
                "heat_supply_request",
                type=DanfossHeatSupplyRequest,
                access="rwp",
                manufacturer_code=DANFOSS_MANUFACTURER_CODE,
            ),
            0x4100: ZCLAttributeDef(
                "system_status_flags",
                type=t.bitmap16,
                access="rp",
                manufacturer_code=DANFOSS_MANUFACTURER_CODE,
            ),
            0x4200: ZCLAttributeDef(
                "system_status_water",
                type=DanfossSystemStatusWater,
                access="rp",
                manufacturer_code=DANFOSS_MANUFACTURER_CODE,
            ),
            0x4201: ZCLAttributeDef(
                "multimaster_role",
                type=DanfossMultimasterRole,
                access="rp",
                manufacturer_code=DANFOSS_MANUFACTURER_CODE,
            ),
            0x4210: ZCLAttributeDef(
                "icon_application",
                type=t.uint8_t,
                access="rp",
                manufacturer_code=DANFOSS_MANUFACTURER_CODE,
            ),
            0x4220: ZCLAttributeDef(
                "icon_forced_heating_cooling",
                type=DanfossIconForcedHeatingCooling,
                access="rwp",
                manufacturer_code=DANFOSS_MANUFACTURER_CODE,
            ),
            0x4300: ZCLAttributeDef(
                "system_string_4300",
                type=t.CharacterString,
                access="rwp",
                manufacturer_code=DANFOSS_MANUFACTURER_CODE,
            ),
        }
    )


# ---------------------------------------------------------------------------
# QuirkV2 builder registration
#
# Zone endpoints (1–16): no .replaces() — attributes are injected into the
# base Thermostat class above. Entity declarations are registered for all 16
# possible zone endpoints; ZHA silently ignores endpoints that don't exist on
# the actual device, so a 4-zone unit will only get entities for endpoints 1–4.
#
# Endpoint 232 is the main controller. .replaces() is safe here because
# endpoint 232 always exists on the Icon2.
# ---------------------------------------------------------------------------

_builder = QuirkBuilder("Danfoss", "0x0210")

# Zone endpoints 1–16
for _ep in range(1, 17):
    _builder = (
        _builder.binary_sensor(
            attribute_name="output_status",
            cluster_id=Thermostat.cluster_id,
            endpoint_id=_ep,
            device_class=BinarySensorDeviceClass.HEAT,
            translation_key="output_status",
            fallback_name=f"Zone {_ep} heating",
        )
        .binary_sensor(
            attribute_name="icon2_pre_heat_status",
            cluster_id=Thermostat.cluster_id,
            endpoint_id=_ep,
            device_class=BinarySensorDeviceClass.HEAT,
            translation_key="icon2_pre_heat_status",
            fallback_name=f"Zone {_ep} pre-heat active",
            entity_type=EntityType.DIAGNOSTIC,
        )
        .sensor(
            attribute_name="room_status_code",
            cluster_id=Thermostat.cluster_id,
            endpoint_id=_ep,
            state_class=SensorStateClass.MEASUREMENT,
            translation_key="room_status_code",
            fallback_name=f"Zone {_ep} room status",
            entity_type=EntityType.DIAGNOSTIC,
        )
        .enum(
            attribute_name="room_floor_sensor_mode",
            enum_class=DanfossRoomFloorSensorMode,
            cluster_id=Thermostat.cluster_id,
            endpoint_id=_ep,
            translation_key="room_floor_sensor_mode",
            fallback_name=f"Zone {_ep} floor sensor mode",
            entity_type=EntityType.CONFIG,
        )
        .enum(
            attribute_name="schedule_type_used",
            enum_class=DanfossScheduleTypeUsed,
            cluster_id=Thermostat.cluster_id,
            endpoint_id=_ep,
            translation_key="schedule_type_used",
            fallback_name=f"Zone {_ep} schedule",
            entity_type=EntityType.CONFIG,
        )
        .switch(
            attribute_name="icon2_pre_heat",
            cluster_id=Thermostat.cluster_id,
            endpoint_id=_ep,
            on_value=DanfossPreHeat.enable,
            off_value=DanfossPreHeat.disable,
            translation_key="icon2_pre_heat",
            fallback_name=f"Zone {_ep} pre-heat",
            entity_type=EntityType.CONFIG,
        )
    )

# Main controller (endpoint 232)
(
    _builder.replaces(DanfossMainDiagnosticCluster, endpoint_id=232)
    .binary_sensor(
        attribute_name="heat_supply_request",
        cluster_id=Diagnostic.cluster_id,
        endpoint_id=232,
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="heat_supply_request",
        fallback_name="Pump running",
    )
    .sensor(
        attribute_name="system_status_code",
        cluster_id=Diagnostic.cluster_id,
        endpoint_id=232,
        translation_key="system_status_code",
        fallback_name="System status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .enum(
        attribute_name="system_status_water",
        enum_class=DanfossSystemStatusWater,
        cluster_id=Diagnostic.cluster_id,
        endpoint_id=232,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="system_status_water",
        fallback_name="Water flow mode",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .enum(
        attribute_name="multimaster_role",
        enum_class=DanfossMultimasterRole,
        cluster_id=Diagnostic.cluster_id,
        endpoint_id=232,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="multimaster_role",
        fallback_name="Controller role",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .enum(
        attribute_name="icon_forced_heating_cooling",
        enum_class=DanfossIconForcedHeatingCooling,
        cluster_id=Diagnostic.cluster_id,
        endpoint_id=232,
        translation_key="icon_forced_heating_cooling",
        fallback_name="Forced heating/cooling mode",
        entity_type=EntityType.CONFIG,
    )
    .also_applies_to("Danfoss", "0x8020")
    .add_to_registry()
)
