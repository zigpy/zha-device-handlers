"""amina S EV charger.

The charger exposes its EV state, alarms and energy counters on the
manufacturer-specific cluster 0xFEE7. Its node descriptor reports the
placeholder manufacturer code 0x1234, so every attribute carries the real
manufacturer code 0x143B explicitly.
"""

from typing import Any, Final

from zigpy import types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfEnergy,
)
from zhaquirks.clusters import CustomCluster

AMINA_MANUFACTURER_CODE: Final = 0x143B
AMINA_ENDPOINT_ID: Final = 10


class EVStatus(t.bitmap16):
    """EV status bits."""

    EV_connected = 0x0001
    Ready_to_charge = 0x0002
    Charging = 0x0004
    Charging_paused = 0x0008
    Derated = 0x8000


class Alarms(t.bitmap16):
    """Alarm bits."""

    Welded_relay = 0x0001
    Wrong_voltage_balance = 0x0002
    RDC_DD_DC_leakage = 0x0004
    RDC_DD_AC_leakage = 0x0008
    High_temperature = 0x0010
    Overvoltage = 0x0020
    Undervoltage = 0x0040
    Overcurrent = 0x0080
    Car_communication_error = 0x0100
    Charger_processing_error = 0x0200
    Critical_overcurrent = 0x0400
    Critical_power_loss = 0x0800


class AminaControlCluster(CustomCluster):
    """amina S manufacturer-specific control cluster."""

    cluster_id: Final = 0xFEE7
    name: Final = "Amina Control"
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
            type=EVStatus,
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
            id=0x0005,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=AMINA_MANUFACTURER_CODE,
        )
        offline_current: Final = ZCLAttributeDef(
            id=0x0006,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=AMINA_MANUFACTURER_CODE,
        )
        offline_single_phase: Final = ZCLAttributeDef(
            id=0x0007,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=AMINA_MANUFACTURER_CODE,
        )
        time_to_offline: Final = ZCLAttributeDef(
            id=0x0008,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=AMINA_MANUFACTURER_CODE,
        )
        enable_offline: Final = ZCLAttributeDef(
            id=0x0009,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=AMINA_MANUFACTURER_CODE,
        )
        # The energy counters are not reportable, see `_update_attribute`
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

    def _update_attribute(self, attrid: Any, value: Any) -> None:
        """Read the energy counters when the EV status changes."""
        previous = self.get(self.AttributeDefs.ev_status.id)
        super()._update_attribute(attrid, value)

        attr_id = getattr(attrid, "id", attrid)
        if attr_id == self.AttributeDefs.ev_status.id and previous != value:
            self.create_catching_task(
                self.read_attributes(
                    [
                        self.AttributeDefs.total_active_energy.id,
                        self.AttributeDefs.last_session_energy.id,
                    ],
                    allow_cache=False,
                )
            )


def ev_status_text(value: Any) -> str:
    """Convert the EV status bits into a readable status."""
    status = EVStatus(int(value))

    if not status & EVStatus.EV_connected:
        return "Not connected"
    if status & EVStatus.Charging:
        return "Charging"
    if status & EVStatus.Charging_paused:
        return "Charging paused"
    if status & EVStatus.Ready_to_charge:
        return "Ready to charge"
    return "Connected"


EV_STATUS_REPORTING: Final = ReportingConfig(
    min_interval=0, max_interval=300, reportable_change=1
)


(
    QuirkBuilder("amina distribution AS", "amina S")
    .replaces(AminaControlCluster, endpoint_id=AMINA_ENDPOINT_ID)
    .binary_sensor(
        attribute_name=AminaControlCluster.AttributeDefs.ev_status.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.PLUG,
        attribute_converter=lambda value: bool(value & EVStatus.EV_connected),
        reporting_config=EV_STATUS_REPORTING,
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
        attribute_converter=lambda value: bool(value & EVStatus.Charging),
        unique_id_suffix="ev_charging",
        translation_key="ev_charging",
        fallback_name="Charging",
    )
    .binary_sensor(
        attribute_name=AminaControlCluster.AttributeDefs.ev_status.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_converter=lambda value: bool(value & EVStatus.Derated),
        unique_id_suffix="derated",
        translation_key="derated",
        fallback_name="Derated",
    )
    .binary_sensor(
        attribute_name=AminaControlCluster.AttributeDefs.alarms.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_converter=lambda value: int(value) != 0,
        reporting_config=EV_STATUS_REPORTING,
        unique_id_suffix="alarm_active",
        translation_key="alarm_active",
        fallback_name="Alarm",
    )
    .sensor(
        attribute_name=AminaControlCluster.AttributeDefs.ev_status.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        attribute_converter=ev_status_text,
        unique_id_suffix="ev_status_text",
        translation_key="ev_status",
        fallback_name="EV status",
    )
    .sensor(
        attribute_name=AminaControlCluster.AttributeDefs.alarms.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_converter=int,
        unique_id_suffix="alarm_bits",
        translation_key="alarm_bits",
        fallback_name="Alarm code",
    )
    .sensor(
        attribute_name=AminaControlCluster.AttributeDefs.total_active_energy.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        divisor=1000,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="total_active_energy",
        fallback_name="Total energy",
    )
    .sensor(
        attribute_name=AminaControlCluster.AttributeDefs.last_session_energy.name,
        cluster_id=AminaControlCluster.cluster_id,
        endpoint_id=AMINA_ENDPOINT_ID,
        divisor=1000,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="last_session_energy",
        fallback_name="Last session energy",
    )
    .add_to_registry()
)
