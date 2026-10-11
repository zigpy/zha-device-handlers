"""Device handler for the Bosch outdoor siren, RBSH-OS-ZB-EU (BSIR-EZ).

The siren has the standard IAS WD cluster, but it sounds its alarm through a Bosch
manufacturer specific command and applies the alarm mode, volume, delays and durations
that are stored on the device. So the siren entity is a basic siren (on and off) that
sends that command, and the stored settings are entities of their own.

Zone status bits (Bosch specific):
- Alarm_1: alarm from the external trigger input
- Alarm_2: power outage (only with an AC or DC supply)
- Tamper: the device is tampered with

The device wants a manufacturer specific acknowledgement for the tamper and power outage
bits. ZHA's own IAS zone sensor would treat the external trigger and the power outage as
one alarm, so it is replaced by one binary sensor per bit.
"""

from typing import Any, Final

from zha.quirks import SIREN_BASIC
from zigpy import types as t
from zigpy.exceptions import ZigbeeException
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasWd, IasZone, WarningMode, WarningType
from zigpy.zcl.foundation import ZCLAttributeDef, ZCLCommandDef

from zhaquirks.bosch import BOSCH
from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricPotential,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster

MODEL = "RBSH-OS-ZB-EU"
BOSCH_MANUFACTURER_CODE = 0x1209

# Data of the alarm_control command: start the alarm with the stored settings, or stop it
ALARM_TRIGGER = 0x07
ALARM_STOP = 0x00

# Data of the acknowledgement command, by the zone status bit it confirms
ACK_TAMPER = 0x02
ACK_POWER_OUTAGE = 0x04


# The values below are plain uint8 attributes on the wire. The device refuses a write
# with an enum8 data type (INVALID_DATA_TYPE), so the enums only name the values.
class BoschAlarmMode(t.enum8):
    """What the device does when an alarm is triggered."""

    Only_light = 0x00
    Only_siren = 0x01
    Siren_and_light = 0x02


class BoschSirenVolume(t.enum8):
    """Volume of the siren."""

    Reduced = 0x01
    Medium = 0x02
    Loud = 0x03


class BoschDeviceState(t.enum8):
    """What the siren and the light are doing right now."""

    Idle = 0x00
    Siren_active_external = 0x05
    Light_active_external = 0x06
    Siren_and_light_active_external = 0x07
    Siren_active = 0x09
    Light_active = 0x0A
    Siren_and_light_active = 0x0B


class BoschPrimaryPowerSource(t.enum8):
    """Power source that the device is set to use, the battery is always the backup."""

    Solar_panel = 0x00
    AC_power_supply = 0x01
    DC_power_supply = 0x02


class BoschCurrentPowerSource(t.enum8):
    """Power source that the device is running on."""

    Battery = 0x00
    Solar_panel = 0x01
    AC_power = 0x02
    DC_power = 0x03


class BoschSirenPowerConfiguration(CustomCluster, PowerConfiguration):
    """Power configuration cluster with the Bosch power source attributes."""

    class AttributeDefs(PowerConfiguration.AttributeDefs):
        """Manufacturer specific attributes."""

        # Tenths of a volt
        solar_panel_voltage: Final = ZCLAttributeDef(
            id=0xA000,
            type=t.uint16_t,
            access="rp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        primary_power_source: Final = ZCLAttributeDef(
            id=0xA002,
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )


class BoschSirenIasZone(CustomCluster, IasZone):
    """IAS Zone cluster that acknowledges the Bosch zone status bits."""

    class AttributeDefs(IasZone.AttributeDefs):
        """Manufacturer specific attributes."""

        current_power_source: Final = ZCLAttributeDef(
            id=0xA001,
            type=t.uint8_t,
            access="rp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

    class ServerCommandDefs(IasZone.ServerCommandDefs):
        """Manufacturer specific commands."""

        acknowledge_status_change: Final = ZCLCommandDef(
            id=0xF3,
            schema={"data": t.uint8_t},
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Any,
        *,
        dst_addressing: Any = None,
    ) -> None:
        """Acknowledge the tamper and power outage bits of a status change."""
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

        if hdr.command_id != IasZone.ClientCommandDefs.status_change_notification.id:
            return

        zone_status = IasZone.ZoneStatus(args.zone_status)

        if zone_status & IasZone.ZoneStatus.Tamper:
            self.create_catching_task(self._acknowledge(ACK_TAMPER))
        if zone_status & IasZone.ZoneStatus.Alarm_2:
            self.create_catching_task(self._acknowledge(ACK_POWER_OUTAGE))

    async def _acknowledge(self, data: int) -> None:
        """Confirm a zone status bit to the device."""
        try:
            await self.acknowledge_status_change(data=data)
        except (ZigbeeException, TimeoutError) as err:
            self.warning("Acknowledging zone status 0x%02X failed: %s", data, err)


class BoschSirenIasWd(CustomCluster, IasWd):
    """IAS WD cluster with the Bosch alarm settings and the alarm command."""

    class AttributeDefs(IasWd.AttributeDefs):
        """Manufacturer specific attributes."""

        # Minutes
        siren_duration: Final = ZCLAttributeDef(
            id=0xA000,
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        alarm_mode: Final = ZCLAttributeDef(
            id=0xA001,
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        siren_volume: Final = ZCLAttributeDef(
            id=0xA002,
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        # Seconds
        siren_delay: Final = ZCLAttributeDef(
            id=0xA003,
            type=t.uint16_t,
            access="rwp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        # Seconds
        light_delay: Final = ZCLAttributeDef(
            id=0xA004,
            type=t.uint16_t,
            access="rwp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        # Minutes
        light_duration: Final = ZCLAttributeDef(
            id=0xA005,
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        device_state: Final = ZCLAttributeDef(
            id=0xA006,
            type=t.uint8_t,
            access="rp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

    class ServerCommandDefs(IasWd.ServerCommandDefs):
        """Manufacturer specific commands."""

        alarm_control: Final = ZCLCommandDef(
            id=0xF0,
            schema={"data": t.uint8_t},
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

    async def start_warning(
        self, warning: WarningType, warning_duration: int, **kwargs: Any
    ) -> None:
        """Trigger the alarm with the stored settings, or stop it.

        The tone, level, strobe and duration that ZHA sends have no meaning here, the
        device uses its own settings and delays.
        """
        data = ALARM_STOP if warning.mode == WarningMode.Stop else ALARM_TRIGGER
        result = await self.alarm_control(data=data)
        status = getattr(result, "status", foundation.Status.SUCCESS)
        if status != foundation.Status.SUCCESS:
            raise ZigbeeException(f"The device refused the alarm command: {status}")

    async def squawk(self, *args: Any, **kwargs: Any) -> None:
        """Refuse to squawk, the device cannot."""
        raise ZigbeeException("The outdoor siren does not support squawking")


def zone_status_flag(flag: int):
    """Return a converter that reads one flag of the zone status."""

    def convert(value: int) -> bool:
        return bool(IasZone.ZoneStatus(value) & flag)

    return convert


# The device sends changes of these by itself once reporting is configured
STATE_REPORTING = ReportingConfig(
    min_interval=0, max_interval=3600, reportable_change=1
)

(
    QuirkBuilder(BOSCH, MODEL)
    .friendly_name(model="BSIR-EZ", manufacturer=BOSCH)
    .replaces(BoschSirenPowerConfiguration)
    .replaces(BoschSirenIasZone)
    .replaces(BoschSirenIasWd)
    # Basic siren: turn on and off, no tones, volume or strobe options. ZHA's default
    # tone, level and strobe selects only exist for sirens without this feature
    .exposes_feature(SIREN_BASIC)
    # Replaced by one binary sensor per zone status bit below. The function filter
    # keeps the rule from matching those new sensors as well
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=IasZone.cluster_id,
        function=lambda entity: entity.__class__.__name__ == "IASZone",
    )
    # The siren entity only shows "on" for the duration that the caller passes, so an
    # alarm that it does not show, such as one from the external trigger input, can
    # only be stopped with this button
    .command_button(
        command_name=BoschSirenIasWd.ServerCommandDefs.alarm_control.name,
        cluster_id=IasWd.cluster_id,
        command_kwargs={"data": ALARM_STOP},
        entity_type=EntityType.CONFIG,
        unique_id_suffix="stop_alarm",
        translation_key="stop_alarm",
        fallback_name="Stop alarm",
    )
    .enum(
        attribute_name=BoschSirenIasWd.AttributeDefs.alarm_mode.name,
        enum_class=BoschAlarmMode,
        cluster_id=IasWd.cluster_id,
        entity_type=EntityType.CONFIG,
        attribute_initialized_from_cache=False,
        translation_key="alarm_mode",
        fallback_name="Alarm mode",
    )
    .enum(
        attribute_name=BoschSirenIasWd.AttributeDefs.siren_volume.name,
        enum_class=BoschSirenVolume,
        cluster_id=IasWd.cluster_id,
        entity_type=EntityType.CONFIG,
        attribute_initialized_from_cache=False,
        translation_key="siren_volume",
        fallback_name="Siren volume",
    )
    .number(
        attribute_name=BoschSirenIasWd.AttributeDefs.siren_duration.name,
        cluster_id=IasWd.cluster_id,
        min_value=1,
        max_value=15,
        step=1,
        unit=UnitOfTime.MINUTES,
        entity_type=EntityType.CONFIG,
        attribute_initialized_from_cache=False,
        translation_key="siren_duration",
        fallback_name="Siren duration",
    )
    .number(
        attribute_name=BoschSirenIasWd.AttributeDefs.light_duration.name,
        cluster_id=IasWd.cluster_id,
        min_value=1,
        max_value=15,
        step=1,
        unit=UnitOfTime.MINUTES,
        entity_type=EntityType.CONFIG,
        attribute_initialized_from_cache=False,
        translation_key="light_duration",
        fallback_name="Light duration",
    )
    .number(
        attribute_name=BoschSirenIasWd.AttributeDefs.siren_delay.name,
        cluster_id=IasWd.cluster_id,
        min_value=0,
        max_value=180,
        step=1,
        unit=UnitOfTime.SECONDS,
        entity_type=EntityType.CONFIG,
        attribute_initialized_from_cache=False,
        translation_key="siren_delay",
        fallback_name="Siren delay",
    )
    .number(
        attribute_name=BoschSirenIasWd.AttributeDefs.light_delay.name,
        cluster_id=IasWd.cluster_id,
        min_value=0,
        max_value=180,
        step=1,
        unit=UnitOfTime.SECONDS,
        entity_type=EntityType.CONFIG,
        attribute_initialized_from_cache=False,
        translation_key="light_delay",
        fallback_name="Light delay",
    )
    .enum(
        attribute_name=BoschSirenPowerConfiguration.AttributeDefs.primary_power_source.name,
        enum_class=BoschPrimaryPowerSource,
        cluster_id=PowerConfiguration.cluster_id,
        entity_type=EntityType.CONFIG,
        attribute_initialized_from_cache=False,
        reporting_config=STATE_REPORTING,
        translation_key="primary_power_source",
        fallback_name="Primary power source",
    )
    .enum(
        attribute_name=BoschSirenIasWd.AttributeDefs.device_state.name,
        enum_class=BoschDeviceState,
        cluster_id=IasWd.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        reporting_config=STATE_REPORTING,
        translation_key="device_state",
        fallback_name="Device state",
    )
    .enum(
        attribute_name=BoschSirenIasZone.AttributeDefs.current_power_source.name,
        enum_class=BoschCurrentPowerSource,
        cluster_id=IasZone.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        reporting_config=STATE_REPORTING,
        translation_key="current_power_source",
        fallback_name="Current power source",
    )
    .sensor(
        attribute_name=BoschSirenPowerConfiguration.AttributeDefs.solar_panel_voltage.name,
        cluster_id=PowerConfiguration.cluster_id,
        divisor=10,
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        reporting_config=ReportingConfig(
            min_interval=300, max_interval=3600, reportable_change=1
        ),
        translation_key="solar_panel_voltage",
        fallback_name="Solar panel voltage",
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        attribute_converter=zone_status_flag(IasZone.ZoneStatus.Alarm_1),
        entity_type=EntityType.STANDARD,
        unique_id_suffix="external_trigger",
        translation_key="external_trigger",
        fallback_name="External trigger",
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=zone_status_flag(IasZone.ZoneStatus.Tamper),
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix="tamper",
        translation_key="tamper",
        fallback_name="Tamper",
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        attribute_converter=zone_status_flag(IasZone.ZoneStatus.Alarm_2),
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix="power_outage",
        translation_key="power_outage",
        fallback_name="Power outage",
    )
    .add_to_registry()
)
