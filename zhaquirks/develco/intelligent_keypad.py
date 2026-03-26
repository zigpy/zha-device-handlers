"""Intelligent keypad."""

import asyncio
from datetime import UTC, datetime
from typing import Any, Final, Optional, Union

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityType, QuirkBuilder, SensorDeviceClass
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t
from zigpy.types import Addressing
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasAce, IasWd, IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.const import (
    ARGS,
    CLUSTER_ID,
    COMMAND,
    ENDPOINT_ID,
    LONG_PRESS,
    ZHA_SEND_EVENT,
)
from zhaquirks import LocalDataCluster

MANUFACTURER_CODE = 0x1015


class FrientKeypadIasAce(CustomCluster, IasAce):
    """Patch panel status replies so keypad LEDs stay in sync when armed remotely."""

    _FAILURE_NOTIFICATIONS = {
        IasAce.ArmNotification.Invalid_Arm_Disarm_Code,
        IasAce.ArmNotification.Not_Ready_To_Arm,
        IasAce.ArmNotification.Already_Disarmed,
    }

    class AttributeDefs(IasAce.AttributeDefs):
        """Manufacturer-specific IAS ACE attributes for keypad configuration."""

        auto_arm_mode: Final = ZCLAttributeDef(
            id=0x8005,
            type=t.enum8,
            access="w",
            manufacturer_code=0x1015,
        )
        auto_disarm: Final = ZCLAttributeDef(
            id=0x8004,
            type=t.Bool,
            access="w",
            manufacturer_code=0x1015,
        )
        auto_arm_disarm: Final = ZCLAttributeDef(
            id=0x8003,
            type=t.enum8,
            access="w",
            manufacturer_code=0x1015,
        )
        pin_length: Final = ZCLAttributeDef(
            id=0x8006,
            type=t.uint8_t,
            access="w",
            manufacturer_code=0x1015,
        )

    class AutoArmMode(t.enum8):
        """Keypad auto-arm mode values."""

        No_Auto_Arm = 0x00
        Auto_Arm_in_Away_Mode = 0x01
        Auto_Arm_in_Night_Mode = 0x02
        Auto_Arm_in_Home_Mode = 0x03

    class AutoArmDisarm(t.enum8):
        """Keypad auto arm/disarm modes."""

        Disabled = 0x00
        Auto_Arm_Disarm_Using_Rfid = 0x01
        Auto_Arm_Disarm_Using_Pin = 0x02

    def __init__(self, *args, **kwargs):
        """Init cache with sensible defaults."""
        super().__init__(*args, **kwargs)
        if self.ep_attribute:
            self.endpoint._cluster_attr[self.ep_attribute] = self
        self._cached_panel_status = self.PanelStatus.Panel_Disarmed
        self._cached_seconds = 0
        self._cached_audible = self.AudibleNotification.Default_Sound
        self._cached_alarm = self.AlarmStatus.No_Alarm
        self._have_cache = False
        self._suppress_panel_updates = False
        self._emergency_reset_handle: Optional[asyncio.TimerHandle] = None
        self._update_attribute(
            self.AttributeDefs.auto_arm_mode.id, self.AutoArmMode.No_Auto_Arm
        )
        self._update_attribute(self.AttributeDefs.auto_disarm.id, False)
        self._update_attribute(
            self.AttributeDefs.auto_arm_disarm.id, self.AutoArmDisarm.Disabled
        )
        self._update_attribute(self.AttributeDefs.pin_length.id, 4)

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Any,
        *,
        dst_addressing: Optional[
            Union[Addressing.Group, Addressing.IEEE, Addressing.NWK]
        ] = None,
    ):
        """Intercept SOS presses before ZHA's IAS logic reacts."""
        if hdr.command_id == self.ServerCommandDefs.arm.id:
            self._store_last_code(args)
            event_args = {
                COMMAND: self.ServerCommandDefs.arm.name,
                CLUSTER_ID: int(self.cluster_id),
                ENDPOINT_ID: self.endpoint.endpoint_id,
                ARGS: args,
            }
            self.listener_event(
                ZHA_SEND_EVENT,
                self.ServerCommandDefs.arm.name,
                event_args,
            )

        if hdr.command_id == self.ServerCommandDefs.emergency.id:
            self._track_emergency_trigger()
            event_args = {
                COMMAND: self.ServerCommandDefs.emergency.name,
                CLUSTER_ID: int(self.cluster_id),
                ENDPOINT_ID: self.endpoint.endpoint_id,
                ARGS: args,
            }
            self.listener_event(
                ZHA_SEND_EVENT,
                self.ServerCommandDefs.emergency.name,
                event_args,
            )
            if not hdr.frame_control.disable_default_response:
                self.send_default_rsp(hdr, foundation.Status.SUCCESS)
            return

        return super().handle_cluster_request(
            hdr,
            args,
            dst_addressing=dst_addressing,
        )

    def _track_emergency_trigger(self) -> None:
        """Update emergency attributes and schedule an auto-reset."""
        emergency_cluster = getattr(self.endpoint, "frient_emergency", None)
        if emergency_cluster is None:
            return

        emergency_cluster._update_attribute(
            emergency_cluster.AttributeDefs.emergency.id,
            True,
        )
        emergency_cluster._update_attribute(
            emergency_cluster.AttributeDefs.last_emergency_triggered.id,
            datetime.now(UTC).isoformat(),
        )

        if self._emergency_reset_handle is not None:
            self._emergency_reset_handle.cancel()

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        self._emergency_reset_handle = loop.call_later(
            10,
            self._reset_emergency_flag,
        )

    def _reset_emergency_flag(self) -> None:
        """Clear the emergency flag after the timeout."""
        emergency_cluster = getattr(self.endpoint, "frient_emergency", None)
        if emergency_cluster is None:
            return

        emergency_cluster._update_attribute(
            emergency_cluster.AttributeDefs.emergency.id,
            False,
        )

    def _remember_panel_state(
        self,
        panel_status: IasAce.PanelStatus,
        seconds_remaining: int,
        audible_notification: IasAce.AudibleNotification,
        alarm_status: IasAce.AlarmStatus,
    ) -> None:
        """Persist the most recent state we intentionally pushed to the keypad."""
        self._cached_panel_status = panel_status
        self._cached_seconds = seconds_remaining
        self._cached_audible = audible_notification
        self._cached_alarm = alarm_status
        self._have_cache = True

    def _should_ignore_state(self, panel_status: IasAce.PanelStatus) -> bool:
        """Return True if pending failure means we need to keep LEDs unchanged."""
        if not self._suppress_panel_updates:
            return False

        if panel_status == self._cached_panel_status:
            # Controller is repeating the state we already have, so no harm.
            return False

        return True

    async def panel_status_changed(
        self,
        panel_status: IasAce.PanelStatus,
        seconds_remaining: int,
        audible_notification: IasAce.AudibleNotification,
        alarm_status: IasAce.AlarmStatus,
        **kwargs,
    ):
        """Track every state we broadcast so cached responses stay authoritative."""
        if self._should_ignore_state(panel_status):
            return await super().client_command(
                self.ClientCommandDefs.panel_status_changed.id,
                self._cached_panel_status,
                self._cached_seconds,
                self._cached_audible,
                self._cached_alarm,
                **kwargs,
            )

        self._suppress_panel_updates = False
        self._remember_panel_state(
            panel_status,
            seconds_remaining,
            audible_notification,
            alarm_status,
        )
        return await super().client_command(
            self.ClientCommandDefs.panel_status_changed.id,
            panel_status,
            seconds_remaining,
            audible_notification,
            alarm_status,
            **kwargs,
        )

    async def panel_status_response(
        self,
        panel_status: IasAce.PanelStatus,
        seconds_remaining: int,
        audible_notification: IasAce.AudibleNotification,
        alarm_status: IasAce.AlarmStatus,
        **kwargs,
    ):
        """Ensure responses mirror the last pushed panel status instead of stale data."""
        if not self._have_cache:
            self._remember_panel_state(
                panel_status,
                seconds_remaining,
                audible_notification,
                alarm_status,
            )

        return await super().client_command(
            self.ClientCommandDefs.panel_status_response.id,
            self._cached_panel_status,
            self._cached_seconds,
            self._cached_audible,
            self._cached_alarm,
            **kwargs,
        )

    async def arm_response(
        self,
        arm_notification: IasAce.ArmNotification,
        **kwargs,
    ):
        """Toggle suppression flag when HA rejects keypad-initiated arm/disarm."""
        self._suppress_panel_updates = arm_notification in self._FAILURE_NOTIFICATIONS
        return await super().client_command(
            self.ClientCommandDefs.arm_response.id,
            arm_notification,
            **kwargs,
        )

    def _store_last_code(self, args: Any) -> None:
        """Cache the last arm/disarm code (RFID tag) sent by the keypad."""
        if not args:
            return

        tag = None
        if isinstance(args, (list, tuple)) and len(args) > 1:
            tag = args[1]
        elif isinstance(args, dict):
            tag = args.get("arm_disarm_code")
        elif hasattr(args, "arm_disarm_code"):
            tag = getattr(args, "arm_disarm_code")

        if not tag:
            return

        if isinstance(tag, bytes):
            tag = tag.decode(errors="ignore")
        else:
            tag = str(tag)

        last_code_cluster = getattr(self.endpoint, "frient_last_code", None)
        if last_code_cluster is not None:
            last_code_cluster._update_attribute(
                last_code_cluster.AttributeDefs.last_code.id,
                tag,
            )

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Translate mode writes into manufacturer-specific commands."""
        auto_arm_mode = None
        auto_disarm = None
        auto_arm_disarm = None
        pin_length = None

        if self.AttributeDefs.auto_arm_mode.id in attributes:
            auto_arm_mode = attributes.pop(self.AttributeDefs.auto_arm_mode.id)
        elif self.AttributeDefs.auto_arm_mode.name in attributes:
            auto_arm_mode = attributes.pop(self.AttributeDefs.auto_arm_mode.name)

        if self.AttributeDefs.auto_disarm.id in attributes:
            auto_disarm = attributes.pop(self.AttributeDefs.auto_disarm.id)
        elif self.AttributeDefs.auto_disarm.name in attributes:
            auto_disarm = attributes.pop(self.AttributeDefs.auto_disarm.name)

        if self.AttributeDefs.auto_arm_disarm.id in attributes:
            auto_arm_disarm = attributes.pop(self.AttributeDefs.auto_arm_disarm.id)
        elif self.AttributeDefs.auto_arm_disarm.name in attributes:
            auto_arm_disarm = attributes.pop(self.AttributeDefs.auto_arm_disarm.name)

        if self.AttributeDefs.pin_length.id in attributes:
            pin_length = attributes.pop(self.AttributeDefs.pin_length.id)
        elif self.AttributeDefs.pin_length.name in attributes:
            pin_length = attributes.pop(self.AttributeDefs.pin_length.name)

        attributes_to_write: dict[str, Any] = {}
        if auto_arm_mode is not None:
            self._update_attribute(self.AttributeDefs.auto_arm_mode.id, auto_arm_mode)
            attributes_to_write[self.AttributeDefs.auto_arm_mode.name] = auto_arm_mode
        if auto_disarm is not None:
            self._update_attribute(self.AttributeDefs.auto_disarm.id, auto_disarm)
            attributes_to_write[self.AttributeDefs.auto_disarm.name] = auto_disarm
        if auto_arm_disarm is not None:
            self._update_attribute(
                self.AttributeDefs.auto_arm_disarm.id, auto_arm_disarm
            )
            attributes_to_write[self.AttributeDefs.auto_arm_disarm.name] = (
                auto_arm_disarm
            )
        if pin_length is not None:
            self._update_attribute(self.AttributeDefs.pin_length.id, pin_length)
            attributes_to_write[self.AttributeDefs.pin_length.name] = pin_length

        if attributes_to_write:
            await super().write_attributes(
                attributes_to_write,
                manufacturer=MANUFACTURER_CODE,
            )

        if attributes:
            return await super().write_attributes(attributes, **kwargs)

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


class FrientKeypadLastCodeCluster(LocalDataCluster):
    """Virtual cluster to expose the last code as a sensor-friendly attribute."""

    cluster_id = 0xFC4D
    ep_attribute = "frient_last_code"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute that holds the most recent code sent by the keypad."""

        last_code: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.CharacterString,
            access="r",
            is_manufacturer_specific=True,
        )


class FrientKeypadEmergencyCluster(LocalDataCluster):
    """Virtual cluster to expose emergency state and timestamps."""

    cluster_id = 0xFC4E
    ep_attribute = "frient_emergency"

    class AttributeDefs(BaseAttributeDefs):
        """Attributes that track emergency events."""

        emergency: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.Bool,
            access="r",
            is_manufacturer_specific=True,
        )
        last_emergency_triggered: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.CharacterString,
            access="r",
            is_manufacturer_specific=True,
        )

    def __init__(self, *args, **kwargs):
        """Seed attributes so entities start with a defined value."""
        super().__init__(*args, **kwargs)
        self._update_attribute(self.AttributeDefs.emergency.id, False)
        self._update_attribute(self.AttributeDefs.last_emergency_triggered.id, "")


def parse_emergency_timestamp(value: str | datetime | None) -> datetime | None:
    """Convert stored ISO strings into timezone-aware datetimes for HA."""
    if not value:
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


(
    QuirkBuilder("frient A/S", "KEPZB-110")
    .applies_to("Develco Products A/S", "KEPZB-110")
    .applies_to("frient A/S", "KEPZB-112")
    .applies_to("Develco Products A/S", "KEPZB-112")
    .applies_to("frient A/S", "KEPZB-120")
    .applies_to("Develco Products A/S", "KEPZB-120")
    .applies_to("frient A/S", "KEPZB-122")
    .applies_to("Develco Products A/S", "KEPZB-122")
    .replaces(
        FrientKeypadIasAce,
        endpoint_id=44,
        cluster_id=IasAce.cluster_id,
        cluster_type=ClusterType.Client,
    )
    .adds(
        FrientKeypadLastCodeCluster,
        cluster_type=ClusterType.Server,
        endpoint_id=44,
    )
    .adds(
        FrientKeypadEmergencyCluster,
        cluster_type=ClusterType.Server,
        endpoint_id=44,
    )
    .prevent_default_entity_creation(endpoint_id=44, cluster_id=BinaryInput.cluster_id)
    # Hide the default `ias_zone` entity
    .prevent_default_entity_creation(
        endpoint_id=44,
        cluster_id=IasZone.cluster_id,
        function=lambda entity: entity.translation_key == "ias_zone",
    )
    .prevent_default_entity_creation(
        endpoint_id=44,
        cluster_id=IasWd.cluster_id,
        function=lambda entity: entity.translation_key
        in (
            "default_siren_tone",
            "default_siren_level",
            "default_strobe_level",
            "default_strobe",
        ),
    )
    .binary_sensor(
        endpoint_id=44,
        cluster_id=IasZone.cluster_id,
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
        unique_id_suffix="tamper",
        fallback_name="Tamper",
    )
    .binary_sensor(
        endpoint_id=44,
        cluster_id=FrientKeypadEmergencyCluster.cluster_id,
        cluster_type=ClusterType.Server,
        attribute_name=FrientKeypadEmergencyCluster.AttributeDefs.emergency.name,
        fallback_name="Emergency",
        translation_key="emergency",
        unique_id_suffix="emergency",
    )
    .device_automation_triggers(
        {
            (LONG_PRESS, "SOS button"): {
                ENDPOINT_ID: 44,
                CLUSTER_ID: int(IasAce.cluster_id),
                COMMAND: IasAce.ServerCommandDefs.emergency.name,
            },
        }
    )
    .sensor(
        endpoint_id=44,
        cluster_id=FrientKeypadLastCodeCluster.cluster_id,
        cluster_type=ClusterType.Server,
        attribute_name=FrientKeypadLastCodeCluster.AttributeDefs.last_code.name,
        fallback_name="Last code",
        translation_key="last_code",
        unique_id_suffix="last_code",
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
    )
    .sensor(
        endpoint_id=44,
        cluster_id=FrientKeypadEmergencyCluster.cluster_id,
        cluster_type=ClusterType.Server,
        attribute_name=FrientKeypadEmergencyCluster.AttributeDefs.last_emergency_triggered.name,
        attribute_converter=parse_emergency_timestamp,
        fallback_name="Last emergency triggered",
        translation_key="last_emergency_triggered",
        device_class=SensorDeviceClass.TIMESTAMP,
        unique_id_suffix="last_emergency_triggered",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .enum(
        attribute_name=FrientKeypadIasAce.AttributeDefs.auto_arm_mode.name,
        enum_class=FrientKeypadIasAce.AutoArmMode,
        cluster_id=IasAce.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=44,
        entity_type=EntityType.CONFIG,
        translation_key="auto_arm_mode",
        fallback_name="Auto arm mode",
    )
    .switch(
        attribute_name=FrientKeypadIasAce.AttributeDefs.auto_disarm.name,
        cluster_id=IasAce.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=44,
        entity_type=EntityType.CONFIG,
        translation_key="auto_disarm",
        fallback_name="Auto disarm",
    )
    .enum(
        attribute_name=FrientKeypadIasAce.AttributeDefs.auto_arm_disarm.name,
        enum_class=FrientKeypadIasAce.AutoArmDisarm,
        cluster_id=IasAce.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=44,
        entity_type=EntityType.CONFIG,
        translation_key="auto_arm_disarm",
        fallback_name="Auto arm/disarm",
    )
    .number(
        attribute_name=FrientKeypadIasAce.AttributeDefs.pin_length.name,
        cluster_id=IasAce.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=44,
        min_value=0,
        max_value=10,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="pin_length",
        fallback_name="PIN length",
    )
    .add_to_registry()
)
