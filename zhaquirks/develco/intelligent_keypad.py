"""Intelligent keypad."""

from typing import Any, Final, Union

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityType, QuirkBuilder
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t
from zigpy.types import Addressing
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasAce, IasWd, IasZone
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import (
    ARGS,
    CLUSTER_ID,
    COMMAND,
    ENDPOINT_ID,
    LONG_PRESS,
    ZHA_SEND_EVENT,
)

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
            manufacturer_code=MANUFACTURER_CODE,
        )
        auto_disarm: Final = ZCLAttributeDef(
            id=0x8004,
            type=t.Bool,
            access="w",
            manufacturer_code=MANUFACTURER_CODE,
        )
        auto_arm_disarm: Final = ZCLAttributeDef(
            id=0x8003,
            type=t.enum8,
            access="w",
            manufacturer_code=MANUFACTURER_CODE,
        )
        pin_length: Final = ZCLAttributeDef(
            id=0x8006,
            type=t.uint8_t,
            access="w",
            manufacturer_code=MANUFACTURER_CODE,
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
        self._cached_panel_status = self.PanelStatus.Panel_Disarmed
        self._cached_seconds = 0
        self._cached_audible = self.AudibleNotification.Default_Sound
        self._cached_alarm = self.AlarmStatus.No_Alarm
        self._have_cache = False
        self._suppress_panel_updates = False

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Any,
        *,
        dst_addressing: Union[Addressing.Group, Addressing.IEEE, Addressing.NWK]
        | None = None,
    ):
        """Intercept SOS presses before ZHA's IAS logic reacts."""
        if hdr.command_id == self.ServerCommandDefs.emergency.id:
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

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Translate mode writes into manufacturer-specific commands."""
        incoming_manufacturer = kwargs.pop("manufacturer", None)
        special_manufacturer = (
            incoming_manufacturer
            if incoming_manufacturer is not None
            else MANUFACTURER_CODE
        )
        attributes_copy = dict(attributes)
        auto_arm_mode = None
        auto_disarm = None
        auto_arm_disarm = None
        pin_length = None

        if self.AttributeDefs.auto_arm_mode.id in attributes_copy:
            auto_arm_mode = attributes_copy.pop(self.AttributeDefs.auto_arm_mode.id)
        elif self.AttributeDefs.auto_arm_mode.name in attributes_copy:
            auto_arm_mode = attributes_copy.pop(self.AttributeDefs.auto_arm_mode.name)

        if self.AttributeDefs.auto_disarm.id in attributes_copy:
            auto_disarm = attributes_copy.pop(self.AttributeDefs.auto_disarm.id)
        elif self.AttributeDefs.auto_disarm.name in attributes_copy:
            auto_disarm = attributes_copy.pop(self.AttributeDefs.auto_disarm.name)

        if self.AttributeDefs.auto_arm_disarm.id in attributes_copy:
            auto_arm_disarm = attributes_copy.pop(self.AttributeDefs.auto_arm_disarm.id)
        elif self.AttributeDefs.auto_arm_disarm.name in attributes_copy:
            auto_arm_disarm = attributes_copy.pop(
                self.AttributeDefs.auto_arm_disarm.name
            )

        if self.AttributeDefs.pin_length.id in attributes_copy:
            pin_length = attributes_copy.pop(self.AttributeDefs.pin_length.id)
        elif self.AttributeDefs.pin_length.name in attributes_copy:
            pin_length = attributes_copy.pop(self.AttributeDefs.pin_length.name)

        attributes_to_write: dict[str, Any] = {}
        pending_cache_updates: dict[int, Any] = {}
        if auto_arm_mode is not None:
            attributes_to_write[self.AttributeDefs.auto_arm_mode.name] = auto_arm_mode
            pending_cache_updates[self.AttributeDefs.auto_arm_mode.id] = auto_arm_mode
        if auto_disarm is not None:
            attributes_to_write[self.AttributeDefs.auto_disarm.name] = auto_disarm
            pending_cache_updates[self.AttributeDefs.auto_disarm.id] = auto_disarm
        if auto_arm_disarm is not None:
            attributes_to_write[self.AttributeDefs.auto_arm_disarm.name] = (
                auto_arm_disarm
            )
            pending_cache_updates[self.AttributeDefs.auto_arm_disarm.id] = (
                auto_arm_disarm
            )
        if pin_length is not None:
            attributes_to_write[self.AttributeDefs.pin_length.name] = pin_length
            pending_cache_updates[self.AttributeDefs.pin_length.id] = pin_length

        results: list[list[foundation.WriteAttributesStatusRecord]] = []
        if attributes_to_write:
            write_results = await super().write_attributes(
                attributes_to_write,
                manufacturer=special_manufacturer,
                **kwargs,
            )
            results.extend(write_results)
            if self._writes_succeeded(write_results):
                for attr_id, value in pending_cache_updates.items():
                    self._update_attribute(attr_id, value)

        if attributes_copy:
            generic_kwargs = dict(kwargs)
            if incoming_manufacturer is not None:
                generic_kwargs["manufacturer"] = incoming_manufacturer
            results.extend(
                await super().write_attributes(attributes_copy, **generic_kwargs)
            )

        if results:
            return results

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    @staticmethod
    def _writes_succeeded(
        write_results: list[list[foundation.WriteAttributesStatusRecord]],
    ) -> bool:
        for status_list in write_results:
            for status in status_list:
                if status.status != foundation.Status.SUCCESS:
                    return False
        return True


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
        function=lambda entity: (
            entity.translation_key
            in (
                "default_siren_tone",
                "default_siren_level",
                "default_strobe_level",
                "default_strobe",
            )
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
    .device_automation_triggers(
        {
            (LONG_PRESS, "SOS button"): {
                ENDPOINT_ID: 44,
                CLUSTER_ID: int(IasAce.cluster_id),
                COMMAND: IasAce.ServerCommandDefs.emergency.name,
            },
        }
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
        min_value=4,
        max_value=10,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="pin_length",
        fallback_name="PIN length",
    )
    .add_to_registry()
)
