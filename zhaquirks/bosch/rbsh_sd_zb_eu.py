"""Device handler for Bosch RBSH-SD-ZB-EU smoke detector (BSD-2)."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType
import zigpy.types as t
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import ZCLCommandDef

from zhaquirks.bosch import BOSCH

# Alarm timer - 4 minutes, as per Bosch default
_ALARM_TIMEOUT_ACTIVE = 0xF0


class BoschAlarmMode(t.enum8):
    """Alarm mode values for the alarmControl command. Each has a different tone."""

    Smoke = 0x00
    Burglar = 0x01


class BoschSmokeDetectorIasZone(CustomCluster, IasZone):
    """Bosch BSD-II IasZone cluster with manufacturer-specific alarm control command.

    Command 0x80 (alarmControl): alarmMode ENUM8 + alarmTimeout UINT8.
    alarmMode: 0x00 = smoke, 0x01 = burglar.
    alarmTimeout: seconds to sound; 0x00 = stop immediately.
    """

    class ServerCommandDefs(IasZone.ServerCommandDefs):
        """Bosch smoke detector manufacturer specific server commands."""

        alarm_control: Final = ZCLCommandDef(
            id=0x80,
            schema={"alarm_mode": BoschAlarmMode, "alarm_timeout": t.uint8_t},
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder(BOSCH, "RBSH-SD-ZB-EU")
    .replaces(BoschSmokeDetectorIasZone)
    # --- Smoke alarm control ---
    .command_button(
        BoschSmokeDetectorIasZone.ServerCommandDefs.alarm_control.name,
        BoschSmokeDetectorIasZone.cluster_id,
        command_kwargs={
            "alarm_mode": BoschAlarmMode.Smoke,
            "alarm_timeout": _ALARM_TIMEOUT_ACTIVE,
        },
        entity_type=EntityType.CONFIG,
        translation_key="trigger_smoke_alarm",
        fallback_name="Trigger smoke alarm",
        unique_id_suffix="trigger_smoke_alarm",
    )
    .command_button(
        BoschSmokeDetectorIasZone.ServerCommandDefs.alarm_control.name,
        BoschSmokeDetectorIasZone.cluster_id,
        command_kwargs={"alarm_mode": BoschAlarmMode.Smoke, "alarm_timeout": 0x00},
        entity_type=EntityType.CONFIG,
        translation_key="stop_smoke_alarm",
        fallback_name="Stop smoke alarm",
        unique_id_suffix="stop_smoke_alarm",
    )
    # --- Burglar alarm control ---
    .command_button(
        BoschSmokeDetectorIasZone.ServerCommandDefs.alarm_control.name,
        BoschSmokeDetectorIasZone.cluster_id,
        command_kwargs={
            "alarm_mode": BoschAlarmMode.Burglar,
            "alarm_timeout": _ALARM_TIMEOUT_ACTIVE,
        },
        entity_type=EntityType.CONFIG,
        translation_key="trigger_burglar_alarm",
        fallback_name="Trigger burglar alarm",
        unique_id_suffix="trigger_burglar_alarm",
    )
    .command_button(
        BoschSmokeDetectorIasZone.ServerCommandDefs.alarm_control.name,
        BoschSmokeDetectorIasZone.cluster_id,
        command_kwargs={"alarm_mode": BoschAlarmMode.Burglar, "alarm_timeout": 0x00},
        entity_type=EntityType.CONFIG,
        translation_key="stop_burglar_alarm",
        fallback_name="Stop burglar alarm",
        unique_id_suffix="stop_burglar_alarm",
    )
    # --- Zone status feedback binary sensors ---
    # Bit 1: smoke alarm has been manually triggered
    .binary_sensor(
        IasZone.AttributeDefs.zone_status.name,
        BoschSmokeDetectorIasZone.cluster_id,
        attribute_converter=lambda value: bool(value & (1 << 1)),
        translation_key="manual_smoke_alarm",
        fallback_name="Manual smoke alarm",
        unique_id_suffix="manual_smoke_alarm",
    )
    # Bit 7: burgular alarm has been manually triggered
    .binary_sensor(
        IasZone.AttributeDefs.zone_status.name,
        BoschSmokeDetectorIasZone.cluster_id,
        attribute_converter=lambda value: bool(value & (1 << 7)),
        translation_key="manual_burglar_alarm",
        fallback_name="Manual burglar alarm",
        unique_id_suffix="manual_burglar_alarm",
    )
    # Bit 11: smoke alarm has been locally silenced (10 min timeout)
    .binary_sensor(
        IasZone.AttributeDefs.zone_status.name,
        BoschSmokeDetectorIasZone.cluster_id,
        attribute_converter=lambda value: bool(value & (1 << 11)),
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="smoke_alarm_silenced",
        fallback_name="Smoke alarm silenced",
        unique_id_suffix="smoke_alarm_silenced",
    )
    # Bit 8: local button held for more than 3s (test/silence)
    .binary_sensor(
        IasZone.AttributeDefs.zone_status.name,
        BoschSmokeDetectorIasZone.cluster_id,
        attribute_converter=lambda value: bool(value & (1 << 8)),
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="button_pushed",
        fallback_name="Button pushed",
        unique_id_suffix="button_pushed",
    )
    .add_to_registry()
)
