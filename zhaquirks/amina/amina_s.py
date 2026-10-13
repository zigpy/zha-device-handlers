"""Quirk for the Amina S EV charger.

Based on the "Zigbee in Amina S" specification (Revision E) published by
Amina Distribution AS.
"""

from __future__ import annotations

import asyncio
from typing import Any, Final

from zigpy.exceptions import ZigbeeException
import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import BaseAttributeDefs, GeneralCommand, ZCLAttributeDef

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster

AMINA_MANUFACTURER_CODE: Final = 0x143B
AMINA_ENDPOINT_ID: Final = 10

# The charger accepts charging currents between 6 A and 32 A. The upper bound
# can be lowered further by the physical current selector, which the device
# reports as LevelControl.max_level.
MIN_CHARGE_CURRENT: Final = 6
MAX_CHARGE_CURRENT: Final = 32


class EvStatus(t.bitmap16):
    """EV status bits."""

    EV_Connected = 1 << 0
    Relays_Active = 1 << 1
    Power_Delivered = 1 << 2
    Charging_Paused = 1 << 3
    EV_Ready = 1 << 4
    Derated = 1 << 15


class Alarms(t.bitmap16):
    """Alarm bits."""

    Welded_Relays = 1 << 0
    Wrong_Voltage_Balance = 1 << 1
    RDC_DD_DC_Leakage = 1 << 2
    RDC_DD_AC_Leakage = 1 << 3
    Temperature_Error = 1 << 4
    Overvoltage = 1 << 5
    Undervoltage = 1 << 6
    Overcurrent = 1 << 7
    Car_Communication_Error = 1 << 8
    Charger_Processing_Error = 1 << 9
    Critical_Overcurrent = 1 << 10
    Critical_Powerloss = 1 << 11


ALARM_NAMES: Final = {
    Alarms.Welded_Relays: "Welded relay(s)",
    Alarms.Wrong_Voltage_Balance: "Wrong voltage balance",
    Alarms.RDC_DD_DC_Leakage: "RDC-DD DC leakage",
    Alarms.RDC_DD_AC_Leakage: "RDC-DD AC leakage",
    Alarms.Temperature_Error: "Temperature error",
    Alarms.Overvoltage: "Overvoltage",
    Alarms.Undervoltage: "Undervoltage",
    Alarms.Overcurrent: "Overcurrent",
    Alarms.Car_Communication_Error: "Car communication error",
    Alarms.Charger_Processing_Error: "Charger processing error",
    Alarms.Critical_Overcurrent: "Critical overcurrent",
    Alarms.Critical_Powerloss: "Critical powerloss",
}


def ev_status_text(value: int) -> str:
    """Summarize the EV status bitmap as a human-readable charging state."""
    status = EvStatus(value)

    if EvStatus.EV_Connected not in status:
        text = "Not connected"
    elif EvStatus.Power_Delivered in status:
        text = "Charging"
    elif EvStatus.Charging_Paused in status:
        text = "Paused"
    elif EvStatus.EV_Ready in status or EvStatus.Relays_Active in status:
        text = "Ready to charge"
    else:
        text = "EV connected"

    if EvStatus.Derated in status:
        text += " (derated)"

    return text


def alarms_text(value: int) -> str:
    """List the active alarms, or "No alarm" if none are set."""
    active = [
        ALARM_NAMES.get(Alarms(1 << bit), f"Alarm bit {bit}")
        for bit in range(16)
        if value & (1 << bit)
    ]
    return ", ".join(active) if active else "No alarm"


class AminaControlCluster(CustomCluster):
    """Amina S manufacturer-specific control cluster."""

    cluster_id: Final = 0xFEE7
    name: Final = "Amina S Control"
    ep_attribute: Final = "amina_control"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        alarms: Final = ZCLAttributeDef(
            id=0x0002,
            type=Alarms,
            access="rp",
            manufacturer_code=AMINA_MANUFACTURER_CODE,
        )
        ev_status: Final = ZCLAttributeDef(
            id=0x0003,
            type=EvStatus,
            access="rp",
            manufacturer_code=AMINA_MANUFACTURER_CODE,
        )
        connect_status: Final = ZCLAttributeDef(
            id=0x0004,
            type=t.bitmap16,
            access="rp",
            manufacturer_code=AMINA_MANUFACTURER_CODE,
        )
        single_phase: Final = ZCLAttributeDef(
            id=0x0005, type=t.uint8_t, manufacturer_code=AMINA_MANUFACTURER_CODE
        )
        offline_current: Final = ZCLAttributeDef(
            id=0x0006, type=t.uint8_t, manufacturer_code=AMINA_MANUFACTURER_CODE
        )
        offline_single_phase: Final = ZCLAttributeDef(
            id=0x0007, type=t.uint8_t, manufacturer_code=AMINA_MANUFACTURER_CODE
        )
        time_to_offline: Final = ZCLAttributeDef(
            id=0x0008, type=t.uint16_t, manufacturer_code=AMINA_MANUFACTURER_CODE
        )
        enable_offline: Final = ZCLAttributeDef(
            id=0x0009, type=t.uint8_t, manufacturer_code=AMINA_MANUFACTURER_CODE
        )
        total_active_energy: Final = ZCLAttributeDef(
            id=0x0010,
            type=t.uint32_t,
            access="r",
            manufacturer_code=AMINA_MANUFACTURER_CODE,
        )
        last_session_energy: Final = ZCLAttributeDef(
            id=0x0011,
            type=t.uint32_t,
            access="r",
            manufacturer_code=AMINA_MANUFACTURER_CODE,
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the cluster."""
        super().__init__(*args, **kwargs)
        self._last_total_active_energy: int | None = None

    def _update_attribute(self, attrid: int, value: Any) -> None:
        # Total active energy is a lifetime counter, exposed as a
        # `total_increasing` sensor. The charger occasionally returns a corrupt,
        # lower value, which would be recorded as a meter reset and inflate the
        # long-term statistics once the real value returns. Drop those reads.
        if attrid == self.AttributeDefs.total_active_energy.id and value is not None:
            if (
                self._last_total_active_energy is not None
                and value < self._last_total_active_energy
            ):
                self.debug(
                    "Ignoring total_active_energy decrease from %s to %s",
                    self._last_total_active_energy,
                    value,
                )
                return
            self._last_total_active_energy = value

        super()._update_attribute(attrid, value)


async def _refresh_amina_attributes(endpoint, attributes: list[str]) -> None:
    """Read attributes from the Amina control cluster on the given endpoint."""
    await endpoint.amina_control.read_attributes(attributes)


class AminaOnOff(CustomCluster, OnOff):
    """On/Off cluster that never sends Toggle and refreshes the EV status.

    The specification warns that Toggle "may result in unwanted results", so it
    is replaced with an explicit On or Off, defaulting to Off when the state is
    unknown.
    """

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)
        if attrid == OnOff.AttributeDefs.on_off.id:
            # The charger does not always report its EV status after being
            # (dis)armed, so read it to keep the status entities current.
            self.create_catching_task(
                _refresh_amina_attributes(
                    self.endpoint, [AminaControlCluster.AttributeDefs.ev_status.name]
                )
            )

    async def command(
        self,
        command_id: GeneralCommand | int | t.uint8_t,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Replace Toggle with an explicit On or Off command."""
        if command_id == OnOff.ServerCommandDefs.toggle.id:
            on_off = self.get(OnOff.AttributeDefs.on_off.id)
            command_id = (
                OnOff.ServerCommandDefs.on.id
                if on_off is not None and not on_off
                else OnOff.ServerCommandDefs.off.id
            )

        return await super().command(command_id, *args, **kwargs)


class AminaElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Electrical Measurement cluster that refreshes the energy counters.

    The energy counters on the Amina control cluster cannot be reported, so they
    are read whenever a total active power update arrives.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the cluster."""
        super().__init__(*args, **kwargs)
        self._refresh_lock = asyncio.Lock()

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)
        if attrid == ElectricalMeasurement.AttributeDefs.total_active_power.id:
            self.create_catching_task(self._refresh_energy())

    async def _refresh_energy(self) -> None:
        # Skip instead of queueing if a previous refresh is still in flight:
        # overlapping reads are when the charger returns corrupt values, and the
        # next power update is never far away.
        if self._refresh_lock.locked():
            return

        async with self._refresh_lock:
            await _refresh_amina_attributes(
                self.endpoint,
                [
                    # The charger does not always report its EV status when
                    # charging stops, so refresh it along with the counters.
                    AminaControlCluster.AttributeDefs.ev_status.name,
                    AminaControlCluster.AttributeDefs.total_active_energy.name,
                    AminaControlCluster.AttributeDefs.last_session_energy.name,
                ],
            )


class AminaLevelControl(CustomCluster, LevelControl):
    """Level Control cluster that sets the charging current via MoveToLevel.

    The charger only accepts the charging current through a MoveToLevel command,
    so `current_level` writes are translated into one. The plain MoveToLevel is
    used, as MoveToLevelWithOnOff would also arm the charger. The requested
    current is clamped to the device's min and max level.
    """

    async def _get_level_limits(self) -> tuple[int, int]:
        min_level = self.get(LevelControl.AttributeDefs.min_level.id)
        max_level = self.get(LevelControl.AttributeDefs.max_level.id)

        if min_level is None or max_level is None:
            try:
                await self.read_attributes(
                    [
                        LevelControl.AttributeDefs.min_level.name,
                        LevelControl.AttributeDefs.max_level.name,
                    ]
                )
            except (TimeoutError, ZigbeeException) as exc:
                self.debug("Failed to read the level limits: %s", exc)

            min_level = self.get(
                LevelControl.AttributeDefs.min_level.id, MIN_CHARGE_CURRENT
            )
            max_level = self.get(
                LevelControl.AttributeDefs.max_level.id, MAX_CHARGE_CURRENT
            )

        return min_level, max_level

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs: Any,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Translate current level writes into a MoveToLevel command."""
        remaining = {}
        records = []

        for attr, value in attributes.items():
            if self.find_attribute(attr) != LevelControl.AttributeDefs.current_level:
                remaining[attr] = value
                continue

            min_level, max_level = await self._get_level_limits()
            level = max(min_level, min(max_level, int(value)))

            await self.move_to_level(level=level, transition_time=0)
            self._update_attribute(LevelControl.AttributeDefs.current_level.id, level)
            records.append(
                foundation.WriteAttributesStatusRecord(
                    status=foundation.Status.SUCCESS,
                    attrid=LevelControl.AttributeDefs.current_level.id,
                )
            )

        if remaining:
            result = await super().write_attributes(
                remaining, manufacturer=manufacturer, **kwargs
            )
            records.extend(result[0])

        return [records]


(
    QuirkBuilder("amina distribution AS", "amina S")
    .replaces(AminaControlCluster, endpoint_id=AMINA_ENDPOINT_ID)
    .replaces(AminaOnOff, endpoint_id=AMINA_ENDPOINT_ID)
    .replaces(AminaLevelControl, endpoint_id=AMINA_ENDPOINT_ID)
    .replaces(AminaElectricalMeasurement, endpoint_id=AMINA_ENDPOINT_ID)
    # Charging current
    .number(
        attribute_name=LevelControl.AttributeDefs.current_level.name,
        cluster_id=LevelControl.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        min_value=MIN_CHARGE_CURRENT,
        max_value=MAX_CHARGE_CURRENT,
        step=1,
        unit=UnitOfElectricCurrent.AMPERE,
        device_class=NumberDeviceClass.CURRENT,
        entity_type=EntityType.STANDARD,
        translation_key="charge_limit",
        fallback_name="Charge current limit",
    )
    .sensor(
        attribute_name=LevelControl.AttributeDefs.max_level.name,
        cluster_id=LevelControl.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        suggested_display_precision=0,
        unit=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        translation_key="hardware_current_limit",
        fallback_name="Hardware current limit",
    )
    # EV status
    .sensor(
        attribute_name=AminaControlCluster.AttributeDefs.ev_status.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        attribute_converter=ev_status_text,
        reporting_config=ReportingConfig(
            min_interval=0, max_interval=900, reportable_change=1
        ),
        unique_id_suffix="ev_status_text",
        translation_key="ev_status",
        fallback_name="EV status",
    )
    .binary_sensor(
        attribute_name=AminaControlCluster.AttributeDefs.ev_status.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.PLUG,
        attribute_converter=lambda value: EvStatus.EV_Connected in EvStatus(value),
        unique_id_suffix="ev_connected",
        translation_key="ev_connected",
        fallback_name="EV connected",
    )
    .binary_sensor(
        attribute_name=AminaControlCluster.AttributeDefs.ev_status.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        attribute_converter=lambda value: EvStatus.Power_Delivered in EvStatus(value),
        unique_id_suffix="charging",
        translation_key="charging",
        fallback_name="Charging",
    )
    .binary_sensor(
        attribute_name=AminaControlCluster.AttributeDefs.ev_status.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        attribute_converter=lambda value: EvStatus.EV_Ready in EvStatus(value),
        unique_id_suffix="ev_ready",
        translation_key="ev_ready",
        fallback_name="EV ready",
    )
    .binary_sensor(
        attribute_name=AminaControlCluster.AttributeDefs.ev_status.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        attribute_converter=lambda value: EvStatus.Charging_Paused in EvStatus(value),
        unique_id_suffix="paused",
        translation_key="charging_paused",
        fallback_name="Charging paused",
    )
    .binary_sensor(
        attribute_name=AminaControlCluster.AttributeDefs.ev_status.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        device_class=BinarySensorDeviceClass.HEAT,
        attribute_converter=lambda value: EvStatus.Derated in EvStatus(value),
        unique_id_suffix="derated",
        translation_key="derated",
        fallback_name="Thermal derating",
    )
    # Alarms
    .sensor(
        attribute_name=AminaControlCluster.AttributeDefs.alarms.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_converter=alarms_text,
        reporting_config=ReportingConfig(
            min_interval=0, max_interval=900, reportable_change=1
        ),
        unique_id_suffix="alarms_text",
        translation_key="alarms",
        fallback_name="Alarms",
    )
    .binary_sensor(
        attribute_name=AminaControlCluster.AttributeDefs.alarms.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_converter=bool,
        unique_id_suffix="alarm_active",
        translation_key="alarm_active",
        fallback_name="Alarm active",
    )
    # Energy counters
    .sensor(
        attribute_name=AminaControlCluster.AttributeDefs.total_active_energy.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        divisor=1000,
        suggested_display_precision=2,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        attribute_initialized_from_cache=False,
        translation_key="total_active_energy",
        fallback_name="Total energy",
    )
    .sensor(
        attribute_name=AminaControlCluster.AttributeDefs.last_session_energy.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        divisor=1000,
        suggested_display_precision=2,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        attribute_initialized_from_cache=False,
        translation_key="last_session_energy",
        fallback_name="Last session energy",
    )
    # Phase and offline configuration
    .switch(
        attribute_name=AminaControlCluster.AttributeDefs.single_phase.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        translation_key="single_phase",
        fallback_name="Force single-phase charging",
    )
    .switch(
        attribute_name=AminaControlCluster.AttributeDefs.enable_offline.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        translation_key="enable_offline",
        fallback_name="Enable offline mode",
    )
    .switch(
        attribute_name=AminaControlCluster.AttributeDefs.offline_single_phase.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        translation_key="offline_single_phase",
        fallback_name="Offline single-phase charging",
    )
    .number(
        attribute_name=AminaControlCluster.AttributeDefs.offline_current.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        min_value=MIN_CHARGE_CURRENT,
        max_value=MAX_CHARGE_CURRENT,
        step=1,
        unit=UnitOfElectricCurrent.AMPERE,
        device_class=NumberDeviceClass.CURRENT,
        translation_key="offline_current",
        fallback_name="Offline current limit",
    )
    .number(
        attribute_name=AminaControlCluster.AttributeDefs.time_to_offline.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        min_value=0,
        max_value=3600,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="time_to_offline",
        fallback_name="Time to offline",
    )
    .add_to_registry()
)
