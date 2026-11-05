"""Danfoss Icon2 floor heating main controller.

The Icon2 main controller exposes one endpoint per configured room (zone),
numbered from 1 and up to 15, each with a Thermostat cluster. Endpoint 232 is
the controller itself.

Without a quirk, the standard ``pi_heating_demand`` and ``running_state``
attributes are not available on the zone endpoints, so ZHA cannot tell whether
a zone is heating. Danfoss reports this in the manufacturer specific
``output_status`` attribute instead. This quirk:

- adds the Danfoss attributes to the Thermostat cluster of every zone,
- exposes ``output_status`` as a heat binary sensor per zone,
- mirrors ``output_status`` into ``running_state`` so the climate entities get
  an HVAC action (heating / cooling / idle). Cooling is used when the
  controller reports cool water flow (``system_status_water`` on endpoint 232),
- adds the controller's diagnostic attributes on endpoint 232 (not exposed as
  entities: the controller has little room for attribute reporting, and the
  heat supply request stayed inactive while zones were heating).

Attribute ids and types follow the Zigbee2MQTT Danfoss Icon2 converter. The
controller rejects reporting configuration for ``output_status`` unless the
attribute is declared as enum8.
"""

from typing import Any, Final

import zigpy.types as t
from zigpy.zcl import AttributeUnsupportedEvent
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
)
from zhaquirks.danfoss.thermostat import DANFOSS, CustomizedStandardCluster

DANFOSS_MANUFACTURER_CODE = 0x1246

ICON2_BASIC_CONTROLLER = "0x0210"
ICON2_ADVANCED_CONTROLLER = "0x0211"

# Rooms are numbered from endpoint 1. Only configured rooms are present on the
# device.
MAX_ZONES = 15
ZONE_ENDPOINTS = tuple(range(1, MAX_ZONES + 1))
CONTROLLER_ENDPOINT = 232


class DanfossOutputStatus(t.enum8):
    """Zone actuator output."""

    Inactive = 0x00
    Active = 0x01


class DanfossHeatSupplyRequest(t.enum8):
    """Heat supply request from the controller to the heat source."""

    No_Request = 0x00
    Request = 0x01


class DanfossRoomStatusCode(t.bitmap16):
    """Room (zone) status code."""

    No_Error = 0x0000
    Missing_Room_Thermostat = 0x0101
    Room_Thermostat_Touch_Error = 0x0201
    Floor_Sensor_Short_Circuit = 0x0401
    Floor_Sensor_Disconnected = 0x0801


class DanfossRoomFloorSensorMode(t.enum8):
    """Room / floor sensor regulation mode."""

    Comfort = 0x00
    Floor_Only = 0x01
    Dual_Mode = 0x02


class DanfossSystemStatusWater(t.enum8):
    """Water flow direction in the system."""

    Hot_Water_Flow = 0x00
    Cool_Water_Flow = 0x01


class DanfossMultimasterRole(t.enum8):
    """Role of the controller in a multi-master installation."""

    Invalid_Unused = 0x00
    Master = 0x01
    Slave_1 = 0x02
    Slave_2 = 0x03


class DanfossIcon2ThermostatCluster(CustomizedStandardCluster, Thermostat):
    """Thermostat cluster of an Icon2 zone."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Danfoss Icon2 zone attributes."""

        room_status_code: Final = ZCLAttributeDef(
            id=0x4100,
            type=DanfossRoomStatusCode,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        )
        output_status: Final = ZCLAttributeDef(
            id=0x4110,
            type=DanfossOutputStatus,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        )
        room_floor_sensor_mode: Final = ZCLAttributeDef(
            id=0x4120,
            type=DanfossRoomFloorSensorMode,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        )
        floor_min_setpoint: Final = ZCLAttributeDef(
            id=0x4121,
            type=t.int16s,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        )
        floor_max_setpoint: Final = ZCLAttributeDef(
            id=0x4122,
            type=t.int16s,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        )

    def _update_attribute(
        self, attrid: int | t.uint16_t | ZCLAttributeDef, value: Any
    ) -> None:
        """Mirror the output status into running_state for the HVAC action."""
        super()._update_attribute(attrid, value)

        if isinstance(attrid, ZCLAttributeDef):
            attrid = attrid.id

        if attrid == self.AttributeDefs.output_status.id:
            self.update_running_state()

    def _cooling(self) -> bool:
        """Return True if the controller reports cool water flow."""
        controller = self.endpoint.device.endpoints.get(CONTROLLER_ENDPOINT)
        diagnostic = getattr(controller, Diagnostic.ep_attribute, None)
        if not isinstance(diagnostic, DanfossIcon2DiagnosticCluster):
            return False
        return (
            diagnostic.get(
                DanfossIcon2DiagnosticCluster.AttributeDefs.system_status_water.name
            )
            == DanfossSystemStatusWater.Cool_Water_Flow
        )

    def update_running_state(self) -> None:
        """Derive running_state from the output status and the water flow."""
        output_status = self.get(self.AttributeDefs.output_status.name)
        if output_status is None:
            return

        if output_status != DanfossOutputStatus.Active:
            running_state = Thermostat.RunningState.Idle
        elif self._cooling():
            running_state = Thermostat.RunningState.Cool_State_On
        else:
            running_state = Thermostat.RunningState.Heat_State_On

        super()._update_attribute(
            Thermostat.AttributeDefs.running_state.id, running_state
        )

    def _on_attribute_unsupported(self, event: AttributeUnsupportedEvent) -> None:
        """Keep the derived running_state when the device rejects reading it."""
        if event.attribute_id == Thermostat.AttributeDefs.running_state.id:
            return
        super()._on_attribute_unsupported(event)


class DanfossIcon2DiagnosticCluster(CustomizedStandardCluster, Diagnostic):
    """Diagnostic cluster of the Icon2 main controller."""

    class AttributeDefs(Diagnostic.AttributeDefs):
        """Danfoss Icon2 controller attributes."""

        system_status_code: Final = ZCLAttributeDef(
            id=0x4000,
            type=t.bitmap16,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        )
        heat_supply_request: Final = ZCLAttributeDef(
            id=0x4031,
            type=DanfossHeatSupplyRequest,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        )
        system_status_water: Final = ZCLAttributeDef(
            id=0x4200,
            type=DanfossSystemStatusWater,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        )
        multimaster_role: Final = ZCLAttributeDef(
            id=0x4201,
            type=DanfossMultimasterRole,
            access="rp",
            manufacturer_code=DANFOSS_MANUFACTURER_CODE,
        )

    def _update_attribute(
        self, attrid: int | t.uint16_t | ZCLAttributeDef, value: Any
    ) -> None:
        """Update the zones' running_state when the water flow changes."""
        super()._update_attribute(attrid, value)

        if isinstance(attrid, ZCLAttributeDef):
            attrid = attrid.id

        if attrid == self.AttributeDefs.system_status_water.id:
            for endpoint in self.endpoint.device.non_zdo_endpoints:
                thermostat = endpoint.in_clusters.get(Thermostat.cluster_id)
                if isinstance(thermostat, DanfossIcon2ThermostatCluster):
                    thermostat.update_running_state()


# Only configured rooms are present as endpoints, but quirks are static and a
# model may only have one quirk, so entities are declared for all possible zones.
# ZHA skips (and logs) the ones whose endpoint doesn't exist.
builder = (
    QuirkBuilder(DANFOSS, ICON2_BASIC_CONTROLLER)
    .applies_to(DANFOSS, ICON2_ADVANCED_CONTROLLER)
    .friendly_name(manufacturer=DANFOSS, model="Icon2 main controller")
    # Only zone endpoints have a Thermostat cluster
    .replace_cluster_occurrences(
        DanfossIcon2ThermostatCluster, replace_client_instances=False
    )
    .replaces(DanfossIcon2DiagnosticCluster, endpoint_id=CONTROLLER_ENDPOINT)
)

for zone in ZONE_ENDPOINTS:
    builder = builder.binary_sensor(
        DanfossIcon2ThermostatCluster.AttributeDefs.output_status.name,
        DanfossIcon2ThermostatCluster.cluster_id,
        endpoint_id=zone,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.HEAT,
        reporting_config=ReportingConfig(
            min_interval=0, max_interval=900, reportable_change=1
        ),
        fallback_name="Heat",
    )

builder.add_to_registry()
