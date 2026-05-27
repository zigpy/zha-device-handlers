"""Sonoff SNZB-09P - Zigbee alarm sensor."""

from typing import Any, Union

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType, UnitOfTime
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasWd, IasZone
import zigpy.types as t

SONOFF_CLUSTER_FC11_ID = 0xFC11
SONOFF_MANUFACTURER_CODE = 0x1286

ATTR_SONOFF_POWER_SUPPLY_MODE = 0x0024
ATTR_BATTERY_PERCENTAGE_REMAINING = 0x0021
ATTR_SONOFF_SPLIT = 0x2000
ATTR_SONOFF_ALARM_SOUND_ENABLE = 0x2026
ATTR_SONOFF_ALARM_LIGHT_ENABLE = 0x2022
ATTR_SONOFF_ALARM_SOUND_TYPE = 0x2023
ATTR_SONOFF_ALARM_VOLUME_LEVEL = 0x2024
ATTR_SONOFF_ALARM_DURATION = 0x2025
ATTR_SONOFF_ALARM_ACTIVE = 0x3000

CMD_SOUND_AND_LIGHT_ALARM_SETTINGS = 0x0F
CMD_START_ALARM_NOW = 0xFD
CMD_STOP_ALARM_NOW = 0xFE
CMD_START_SCENE_ALARM = 0xFC
SUBCMD_START_MANUAL_ALARM = 0x00
SUBCMD_STOP_ALARM = 0x01
SUBCMD_START_SCENE_ALARM = 0x02
SUBCMD_ALARM_STATE_REPORT = 0x04

ALARM_STATE_OFF = 0x00
ALARM_STATE_MANUAL = 0x01
ALARM_STATE_SCENE = 0x02
BATTERY_PERCENTAGE_UNKNOWN = 0xFF
BATTERY_PERCENTAGE_FULL = 200


class PowerSupplyMode(t.enum8):
    """Power supply mode enum."""

    OFF = 0x00
    ON = 0x01


class TamperState(t.enum8):
    """Tamper state enum."""

    NORMAL = 0x00
    TRIGGER = 0x01


class AlarmSoundType(t.enum8):
    """Alarm sound type enum."""

    SOUND_0 = 0x00
    SOUND_1 = 0x01
    SOUND_2 = 0x02
    SOUND_3 = 0x03
    SOUND_4 = 0x04
    SOUND_5 = 0x05
    SOUND_6 = 0x06
    SOUND_7 = 0x07
    SOUND_8 = 0x08
    SOUND_9 = 0x09


class AlarmVolumeLevel(t.enum8):
    """Alarm volume level enum."""

    LOW = 0x00
    MEDIUM = 0x01
    HIGH = 0x02
    MAXIMUM = 0x03


class SonoffSNZB09PPowerConfigurationCluster(CustomCluster, PowerConfiguration):
    """Expose battery percentage as unknown while external power is present."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._power_supply_mode = None
        self._raw_battery_percentage = None
        self._allow_battery_percentage_on_external_power = False

    def _update_attribute(self, attrid, value):
        """Cache the raw battery value and publish the masked value."""
        if attrid == ATTR_BATTERY_PERCENTAGE_REMAINING:
            self._raw_battery_percentage = None if value is None else int(value)

            if self._power_supply_mode == PowerSupplyMode.ON:
                self._allow_battery_percentage_on_external_power = (
                    self._raw_battery_percentage == BATTERY_PERCENTAGE_FULL
                )

            value = self._get_display_battery_percentage()

        super()._update_attribute(attrid, value)

    def update_power_supply_mode(self, power_supply_mode) -> None:
        """Refresh the exposed battery value when power mode changes."""
        previous_power_supply_mode = self._power_supply_mode
        self._power_supply_mode = power_supply_mode

        if previous_power_supply_mode != power_supply_mode:
            self._allow_battery_percentage_on_external_power = False

        self._sync_battery_percentage()

    def _sync_battery_percentage(self) -> None:
        """Republish the cached battery percentage with the current mask."""
        if self._raw_battery_percentage is None:
            return

        super()._update_attribute(
            ATTR_BATTERY_PERCENTAGE_REMAINING,
            self._get_display_battery_percentage(),
        )

    def _get_display_battery_percentage(self) -> int | None:
        """Return the battery value that should be visible to ZHA."""
        power_supply_mode = self._power_supply_mode

        if power_supply_mode is None:
            sonoff_cluster = getattr(self.endpoint, "sonoff_manufacturer", None)
            if sonoff_cluster is not None:
                power_supply_mode = sonoff_cluster.get("power_supply_mode")

        if (
            power_supply_mode == PowerSupplyMode.ON
            and not self._allow_battery_percentage_on_external_power
        ):
            return BATTERY_PERCENTAGE_UNKNOWN

        return self._raw_battery_percentage


class SonoffSNZB09PFC11Cluster(CustomCluster):
    """Sonoff manufacturer specific cluster for SNZB-09P."""

    cluster_id = SONOFF_CLUSTER_FC11_ID
    ep_attribute = "sonoff_manufacturer"

    attributes = {
        ATTR_SONOFF_POWER_SUPPLY_MODE: ("power_supply_mode", PowerSupplyMode),
        ATTR_SONOFF_SPLIT: ("tamper_state", TamperState),
        ATTR_SONOFF_ALARM_SOUND_ENABLE: ("alarm_sound_enable", t.Bool),
        ATTR_SONOFF_ALARM_LIGHT_ENABLE: ("alarm_light_enable", t.Bool),
        ATTR_SONOFF_ALARM_SOUND_TYPE: ("alarm_sound_type", AlarmSoundType),
        ATTR_SONOFF_ALARM_VOLUME_LEVEL: (
            "alarm_volume_level",
            AlarmVolumeLevel,
        ),
        ATTR_SONOFF_ALARM_DURATION: ("alarm_duration", t.uint16_t),
        ATTR_SONOFF_ALARM_ACTIVE: ("alarm_active", t.Bool),
    }

    class ServerCommandDefs(foundation.BaseCommandDefs):
        """Server command definitions."""

        sound_and_light_alarm_settings = foundation.ZCLCommandDef(
            id=CMD_SOUND_AND_LIGHT_ALARM_SETTINGS,
            schema={
                "sub_command": t.uint8_t,
                "trigger?": t.uint8_t,
                "voice?": t.Bool,
                "light?": t.Bool,
                "alert_sound?": AlarmSoundType,
                "volume?": AlarmVolumeLevel,
                "duration?": t.uint16_t,
            },
            is_manufacturer_specific=True,
        )

    class ClientCommandDefs(foundation.BaseCommandDefs):
        """Client command definitions."""

        sound_and_light_alarm_settings = foundation.ZCLCommandDef(
            id=CMD_SOUND_AND_LIGHT_ALARM_SETTINGS,
            schema={
                "sub_command": t.uint8_t,
                "trigger?": t.uint8_t,
                "voice?": t.Bool,
                "light?": t.Bool,
                "alert_sound?": AlarmSoundType,
                "volume?": AlarmVolumeLevel,
                "duration?": t.uint16_t,
            },
            is_manufacturer_specific=True,
        )

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._update_attribute(ATTR_SONOFF_ALARM_ACTIVE, t.Bool(False))

    def _update_attribute(self, attrid, value):
        """Forward power supply updates to the battery cluster."""
        super()._update_attribute(attrid, value)

        if attrid == ATTR_SONOFF_POWER_SUPPLY_MODE:
            power_cluster = getattr(self.endpoint, "power", None)
            if isinstance(power_cluster, SonoffSNZB09PPowerConfigurationCluster):
                power_cluster.update_power_supply_mode(value)

    def deserialize(self, data: bytes):
        """Deserialize cluster data and sync alarm switch state from reports."""
        hdr, payload = foundation.ZCLHeader.deserialize(data)

        if (
            hdr.frame_control.frame_type == foundation.FrameType.CLUSTER_COMMAND
            and hdr.command_id == CMD_SOUND_AND_LIGHT_ALARM_SETTINGS
        ):
            payload_bytes = bytes(payload)
            if len(payload_bytes) >= 2 and payload_bytes[0] == SUBCMD_ALARM_STATE_REPORT:
                self._update_alarm_active_from_type(payload_bytes[1])

        return super().deserialize(data)

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Intercept alarm switch writes and map them to start/stop commands."""

        real_attributes = {}
        alarm_switch_state = None

        for attr, value in attributes.items():
            attr_id = attr
            if isinstance(attr, str) and attr in self.attributes_by_name:
                attr_id = self.attributes_by_name[attr].id

            if attr_id == ATTR_SONOFF_ALARM_ACTIVE:
                alarm_switch_state = bool(value)
            else:
                real_attributes[attr] = value

        records: list[foundation.WriteAttributesStatusRecord] = []

        if alarm_switch_state is not None:
            command_arg = (
                SUBCMD_START_MANUAL_ALARM if alarm_switch_state else SUBCMD_STOP_ALARM
            )

            try:
                await self.command(
                    CMD_SOUND_AND_LIGHT_ALARM_SETTINGS,
                    command_arg,
                    manufacturer=manufacturer or SONOFF_MANUFACTURER_CODE,
                )
            except Exception:
                records.append(
                    foundation.WriteAttributesStatusRecord(
                        foundation.Status.FAILURE,
                        ATTR_SONOFF_ALARM_ACTIVE,
                    )
                )
            else:
                self._update_attribute(
                    ATTR_SONOFF_ALARM_ACTIVE,
                    t.Bool(alarm_switch_state),
                )
                records.append(
                    foundation.WriteAttributesStatusRecord(
                        foundation.Status.SUCCESS,
                        ATTR_SONOFF_ALARM_ACTIVE,
                    )
                )

        if real_attributes:
            real_res = await super().write_attributes(real_attributes, manufacturer)
            if isinstance(real_res, list):
                if real_res and isinstance(real_res[0], list):
                    records.extend(real_res[0])
                else:
                    records.extend(real_res)
            elif hasattr(real_res, "status_records"):
                records.extend(real_res.status_records)
            else:
                records.append(real_res)

        return [records]

    def _update_alarm_active_from_type(self, alarm_type: int) -> None:
        """Sync the virtual alarm switch from device reports."""
        self._update_attribute(
            ATTR_SONOFF_ALARM_ACTIVE,
            t.Bool(alarm_type in (ALARM_STATE_MANUAL, ALARM_STATE_SCENE)),
        )


SONOFF_SNZB09P = (
    QuirkBuilder("SONOFF", "SNZB-09P")
    .replaces(SonoffSNZB09PPowerConfigurationCluster)
    .replaces(SonoffSNZB09PFC11Cluster)
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=IasWd.cluster_id,
        function=lambda entity: True,
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=IasZone.cluster_id,
        function=lambda entity: True,
    )
    .switch(
        attribute_name="alarm_sound_enable",
        cluster_id=SonoffSNZB09PFC11Cluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="alarm_sound_enable",
        fallback_name="Alarm Sound Enable",
    )
    .switch(
        attribute_name="alarm_light_enable",
        cluster_id=SonoffSNZB09PFC11Cluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="alarm_light_enable",
        fallback_name="Alarm Light Enable",
    )
    .enum(
        attribute_name="alarm_sound_type",
        enum_class=AlarmSoundType,
        cluster_id=SonoffSNZB09PFC11Cluster.cluster_id,
        entity_type=EntityType.CONFIG,
        entity_platform=EntityPlatform.SELECT,
        translation_key="alarm_sound_type",
        fallback_name="Alarm Sound Type",
    )
    .enum(
        attribute_name="alarm_volume_level",
        enum_class=AlarmVolumeLevel,
        cluster_id=SonoffSNZB09PFC11Cluster.cluster_id,
        entity_type=EntityType.CONFIG,
        entity_platform=EntityPlatform.SELECT,
        translation_key="alarm_volume_level",
        fallback_name="Alarm Volume Level",
    )
    .number(
        attribute_name="alarm_duration",
        cluster_id=SonoffSNZB09PFC11Cluster.cluster_id,
        min_value=1,
        max_value=900,
        step=1,
        unit=UnitOfTime.SECONDS,
        mode="box",
        translation_key="alarm_duration",
        fallback_name="Alarm Duration",
    )
    .switch(
        attribute_name="alarm_active",
        cluster_id=SonoffSNZB09PFC11Cluster.cluster_id,
        entity_type=EntityType.STANDARD,
        translation_key="alarm_active",
        fallback_name="Siren on",
    )
    .binary_sensor(
        attribute_name="power_supply_mode",
        cluster_id=SonoffSNZB09PFC11Cluster.cluster_id,
        attribute_converter=lambda value: value == PowerSupplyMode.ON,
        unique_id_suffix="external_power",
        entity_type=EntityType.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.POWER,
        translation_key="external_power",
        fallback_name="External Power",
    )
    .binary_sensor(
        attribute_name="tamper_state",
        cluster_id=SonoffSNZB09PFC11Cluster.cluster_id,
        attribute_converter=lambda value: value == TamperState.TRIGGER,
        unique_id_suffix="tamper",
        entity_type=EntityType.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.TAMPER,
        translation_key="tamper",
        fallback_name="Tamper",
    )
    .add_to_registry()
)
