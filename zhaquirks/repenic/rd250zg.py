"""Repenic RD-250ZG Dimmer."""

import asyncio
from datetime import datetime
import logging
import time
from typing import Any

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff, Time

from zhaquirks import EventableCluster, NoReplyMixin
from zhaquirks.const import (
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_TRIPLE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    TRIPLE_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
)

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.WARNING)
# Add console handler for debugging
if not _LOGGER.handlers:
    _console_handler = logging.StreamHandler()
    _console_handler.setLevel(logging.WARNING)
    _console_handler.setFormatter(
        logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    )
    _LOGGER.addHandler(_console_handler)


class RepenicTimeCluster(CustomCluster, Time):
    """Custom Time Cluster that syncs time when application is ready."""

    def __init__(self, *args, **kwargs):
        """Initialize cluster and schedule time sync."""
        super().__init__(*args, **kwargs)
        # Schedule time sync after application is ready
        # asyncio.get_event_loop().call_soon(
        #     lambda: asyncio.ensure_future(self._sync_time_when_ready())
        # )

    async def _sync_time_when_ready(self):
        """Wait for application controller to be ready, then sync time."""
        # Wait for application controller to be running (up to 60 seconds)
        for _ in range(120):
            try:
                app = self.endpoint.device.application
                if app.state == "running":
                    break
            except AttributeError:
                pass
            await asyncio.sleep(0.5)

        await self._sync_time()

    async def _sync_time(self):
        """Sync local time and timezone to device."""
        local_time = datetime.now().astimezone()
        utc_offset = local_time.utcoffset()
        timezone_offset = int(utc_offset.total_seconds()) if utc_offset else 0

        # Local Unix timestamp (same as JS: Date.now() / 1000 + (-offset * 60))
        local_unix_time = int(time.time()) + timezone_offset

        time_data = {
            "time": local_unix_time,
            "time_zone": timezone_offset,
        }
        _LOGGER.warning(
            "Syncing time to device: local_unix_time=%s, timezone_offset=%s",
            local_unix_time,
            timezone_offset,
        )
        await self.write_attributes(time_data, manufacturer=None)

    def deserialize(self, data: bytes) -> tuple[foundation.ZCLHeader, ...]:
        """Deserialize data."""
        result = super().deserialize(data)
        _LOGGER.warning("RepenicTimeCluster: raw_bytes=%r", data)
        _LOGGER.warning("RepenicTimeCluster: deserialized=%r", result)
        asyncio.get_event_loop().call_soon(
            lambda: asyncio.ensure_future(self._sync_time_when_ready())
        )
        return result


class PressType(t.enum8):
    """Press type enum."""

    triple_click = 0x010
    long_press = 0x02
    release = 0x04
    double_click = 0x08


class RepenicPressureCluster(EventableCluster):
    """Private cluster 0xE004 for pressure events."""

    cluster_id = 0xE004
    name = "Repenic Pressure"
    ep_attribute = "repenic_pressure"

    def handle_cluster_request(self, hdr, args, *, dst_addressing=None):
        """Handle cluster request."""
        _LOGGER.debug(
            "RepenicPressureCluster cluster request: command_id=0x%02x args=%r",
            hdr.command_id,
            args,
        )
        if hdr.command_id == 0x00 and len(args) > 1:
            press_value = args[1]
            press_command = None
            if press_value == int(PressType.double_click):
                press_command = COMMAND_DOUBLE
            elif press_value == int(PressType.triple_click):
                press_command = COMMAND_TRIPLE
            elif press_value == int(PressType.long_press):
                press_command = COMMAND_HOLD
            elif press_value == int(PressType.release):
                press_command = COMMAND_RELEASE

            if press_command is not None:
                self.listener_event(ZHA_SEND_EVENT, press_command, {VALUE: press_value})
        return super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


class OnOffState(t.enum8):
    """On off state enum."""

    Off = 0
    On = 1


class Hour(t.enum8):
    """Hour enum - 24 hour format."""

    hour_00 = 0x00
    hour_01 = 0x01
    hour_02 = 0x02
    hour_03 = 0x03
    hour_04 = 0x04
    hour_05 = 0x05
    hour_06 = 0x06
    hour_07 = 0x07
    hour_08 = 0x08
    hour_09 = 0x09
    hour_10 = 0x0A
    hour_11 = 0x0B
    hour_12 = 0x0C
    hour_13 = 0x0D
    hour_14 = 0x0E
    hour_15 = 0x0F
    hour_16 = 0x10
    hour_17 = 0x11
    hour_18 = 0x12
    hour_19 = 0x13
    hour_20 = 0x14
    hour_21 = 0x15
    hour_22 = 0x16
    hour_23 = 0x17


class Minute(t.enum8):
    """Minute enum."""

    minute_00 = 0x00
    minute_01 = 0x01
    minute_02 = 0x02
    minute_03 = 0x03
    minute_04 = 0x04
    minute_05 = 0x05
    minute_06 = 0x06
    minute_07 = 0x07
    minute_08 = 0x08
    minute_09 = 0x09
    minute_10 = 0x0A
    minute_11 = 0x0B
    minute_12 = 0x0C
    minute_13 = 0x0D
    minute_14 = 0x0E
    minute_15 = 0x0F
    minute_16 = 0x10
    minute_17 = 0x11
    minute_18 = 0x12
    minute_19 = 0x13
    minute_20 = 0x14
    minute_21 = 0x15
    minute_22 = 0x16
    minute_23 = 0x17
    minute_24 = 0x18
    minute_25 = 0x19
    minute_26 = 0x1A
    minute_27 = 0x1B
    minute_28 = 0x1C
    minute_29 = 0x1D
    minute_30 = 0x1E
    minute_31 = 0x1F
    minute_32 = 0x20
    minute_33 = 0x21
    minute_34 = 0x22
    minute_35 = 0x23
    minute_36 = 0x24
    minute_37 = 0x25
    minute_38 = 0x26
    minute_39 = 0x27
    minute_40 = 0x28
    minute_41 = 0x29
    minute_42 = 0x2A
    minute_43 = 0x2B
    minute_44 = 0x2C
    minute_45 = 0x2D
    minute_46 = 0x2E
    minute_47 = 0x2F
    minute_48 = 0x30
    minute_49 = 0x31
    minute_50 = 0x32
    minute_51 = 0x33
    minute_52 = 0x34
    minute_53 = 0x35
    minute_54 = 0x36
    minute_55 = 0x37
    minute_56 = 0x38
    minute_57 = 0x39
    minute_58 = 0x3A
    minute_59 = 0x3B


class SleepCountdown(t.enum8):
    """Sleep countdown enum - duration in minutes."""

    minutes_10 = 0x0A
    minutes_20 = 0x14
    minutes_30 = 0x1E


class WakeupCountdown(t.enum8):
    """Wakeup countdown enum - duration in minutes."""

    minutes_10 = 0x0A
    minutes_20 = 0x14
    minutes_30 = 0x1E


class RepenicSceneModeCluster(CustomCluster):
    """Private cluster 0xE003 for scene mode."""

    cluster_id = 0xE003
    name = "Repenic Scene Mode"
    ep_attribute = "repenic_scene_mode"
    attributes = {
        0x0000: ("sleep_pattern", t.CharacterString, False),
        0x0001: ("wake_up_pattern", t.CharacterString, False),
        0x0002: ("night_pattern", t.CharacterString, False),
        0x0003: ("scene_mode", OnOffState, False),
        0xA001: ("sleep_on_off", OnOffState, True),
        0xA002: ("sleep_hour", Hour, True),
        0xA003: ("sleep_minute", Minute, True),
        0xA004: ("sleep_countdown", SleepCountdown, True),
        0xA005: ("wakeup_on_off", OnOffState, True),
        0xA006: ("wakeup_hour", Hour, True),
        0xA007: ("wakeup_minute", Minute, True),
        0xA008: ("wakeup_brightness", t.uint8_t, True),
        0xA009: ("wakeup_countdown", WakeupCountdown, True),
        0xA00A: ("night_on_off", OnOffState, True),
        0xA00B: ("night_hour", Hour, True),
        0xA00C: ("night_minute", Minute, True),
        0xA00D: ("night_end_hour", Hour, True),
        0xA00E: ("night_end_minute", Minute, True),
        0xA00F: ("night_brightness", t.uint8_t, True),
    }
    server_commands = {
        0x00: foundation.ZCLCommandDef(
            "set_pattern",
            {"pattern": t.Bytes},
            is_manufacturer_specific=False,
        ),
        0x01: foundation.ZCLCommandDef(
            "set_wakeup_pattern",
            {"pattern": t.Bytes},
            is_manufacturer_specific=False,
        ),
        0x02: foundation.ZCLCommandDef(
            "set_night_pattern",
            {"pattern": t.Bytes},
            is_manufacturer_specific=False,
        ),
    }

    def __init__(self, *args, **kwargs):
        """Initialize cluster."""
        super().__init__(*args, **kwargs)
        self._attr_cache["sleep_on_off"] = 0
        self._attr_cache["sleep_hour"] = 10
        self._attr_cache["sleep_minute"] = 0
        self._attr_cache["sleep_countdown"] = 30
        self._attr_cache["wakeup_on_off"] = 0
        self._attr_cache["wakeup_hour"] = 10
        self._attr_cache["wakeup_minute"] = 0
        self._attr_cache["wakeup_brightness"] = 100
        self._attr_cache["wakeup_countdown"] = 30
        self._attr_cache["night_on_off"] = 0
        self._attr_cache["night_hour"] = 0
        self._attr_cache["night_minute"] = 0
        self._attr_cache["night_end_hour"] = 6
        self._attr_cache["night_end_minute"] = 0
        self._attr_cache["night_brightness"] = 10

    async def apply_custom_configuration(self, *args, **kwargs):
        """Apply custom configuration to read sleep-related attributes."""
        await self.read_attributes([0x0000])
        await self.read_attributes([0x0001])
        await self.read_attributes([0x0002])

    def deserialize(self, data: bytes) -> tuple[foundation.ZCLHeader, ...]:
        """Deserialize ZCL frame and parse sleep_pattern, wake_up_pattern and night_pattern data."""
        _LOGGER.warning("deserialize: raw_bytes=%r", data)
        result = super().deserialize(data)
        _LOGGER.warning("deserialize: result=%r", result)

        # Parse sleep_pattern (attrid=0) directly from raw bytes
        # Format: frame_control(1) + tsn(1) + cmd_id(1) + attrid(2) + status(1) + type(1) + len(1) + data
        try:
            if len(data) >= 8 and data[2] == 0x01:  # command_id = Read_Attributes_rsp
                attrid = data[3] | (data[4] << 8)
                if attrid == 0x0000:
                    status = data[5]
                    if status == 0:  # SUCCESS
                        data_type = data[6]
                        if data_type == 0x42:  # CharacterString type
                            # sleep_pattern format: [sleep_on_off, sleep_hour, sleep_minute, 0, sleep_countdown, 0]
                            sleep_data = data[8:14]  # length fixed to 6
                            sleep_on_off = sleep_data[0] if len(sleep_data) > 0 else 0
                            sleep_hour = sleep_data[1] if len(sleep_data) > 1 else 10
                            sleep_minute = sleep_data[2] if len(sleep_data) > 2 else 0
                            sleep_countdown = (
                                sleep_data[4] if len(sleep_data) > 4 else 30
                            )

                            self._attr_cache["sleep_on_off"] = OnOffState(sleep_on_off)
                            self._attr_cache["sleep_hour"] = Hour(sleep_hour)
                            self._attr_cache["sleep_minute"] = Minute(sleep_minute)
                            self._attr_cache["sleep_countdown"] = SleepCountdown(
                                sleep_countdown
                            )

                            _LOGGER.warning(
                                "Parsed sleep_pattern from raw bytes: on_off=%s, hour=%s, minute=%s, countdown=%s",
                                sleep_on_off,
                                sleep_hour,
                                sleep_minute,
                                sleep_countdown,
                            )
                elif attrid == 0x0001:
                    status = data[5]
                    if status == 0:  # SUCCESS
                        data_type = data[6]
                        if data_type == 0x42:  # CharacterString type
                            # wake_up_pattern format: [wakeup_on_off, wakeup_hour, wakeup_minute, wakeup_brightness, wakeup_countdown, 0]
                            wakeup_data = data[8:14]  # length fixed to 6
                            wakeup_on_off = (
                                wakeup_data[0] if len(wakeup_data) > 0 else 0
                            )
                            wakeup_hour = wakeup_data[1] if len(wakeup_data) > 1 else 10
                            wakeup_minute = (
                                wakeup_data[2] if len(wakeup_data) > 2 else 0
                            )
                            wakeup_brightness = (
                                wakeup_data[3] if len(wakeup_data) > 3 else 100
                            )
                            wakeup_countdown = (
                                wakeup_data[4] if len(wakeup_data) > 4 else 30
                            )

                            self._attr_cache["wakeup_on_off"] = OnOffState(
                                wakeup_on_off
                            )
                            self._attr_cache["wakeup_hour"] = Hour(wakeup_hour)
                            self._attr_cache["wakeup_minute"] = Minute(wakeup_minute)
                            self._attr_cache["wakeup_brightness"] = int(
                                wakeup_brightness / 2.54
                            )
                            self._attr_cache["wakeup_countdown"] = WakeupCountdown(
                                wakeup_countdown
                            )

                            _LOGGER.warning(
                                "Parsed wake_up_pattern from raw bytes: on_off=%s, hour=%s, minute=%s, brightness=%s, countdown=%s",
                                wakeup_on_off,
                                wakeup_hour,
                                wakeup_minute,
                                wakeup_brightness,
                                wakeup_countdown,
                            )
                elif attrid == 0x0002:
                    status = data[5]
                    if status == 0:  # SUCCESS
                        data_type = data[6]
                        if data_type == 0x42:  # CharacterString type
                            # night_pattern format: [night_on_off, night_hour, night_minute, night_brightness, night_end_hour, night_end_minute]
                            night_data = data[8:14]  # length fixed to 6
                            night_on_off = night_data[0] if len(night_data) > 0 else 0
                            night_hour = night_data[1] if len(night_data) > 1 else 0
                            night_minute = night_data[2] if len(night_data) > 2 else 0
                            night_brightness = (
                                night_data[3] if len(night_data) > 3 else 10
                            )
                            night_end_hour = night_data[4] if len(night_data) > 4 else 6
                            night_end_minute = (
                                night_data[5] if len(night_data) > 5 else 0
                            )

                            self._attr_cache["night_on_off"] = OnOffState(night_on_off)
                            self._attr_cache["night_hour"] = Hour(night_hour)
                            self._attr_cache["night_minute"] = Minute(night_minute)
                            self._attr_cache["night_brightness"] = int(
                                night_brightness / 2.54
                            )
                            self._attr_cache["night_end_hour"] = Hour(night_end_hour)
                            self._attr_cache["night_end_minute"] = Minute(
                                night_end_minute
                            )

                            _LOGGER.warning(
                                "Parsed night_pattern from raw bytes: on_off=%s, hour=%s, minute=%s, brightness=%s, end_hour=%s, end_minute=%s",
                                night_on_off,
                                night_hour,
                                night_minute,
                                night_brightness,
                                night_end_hour,
                                night_end_minute,
                            )
        except Exception as ex:
            _LOGGER.warning("Failed to parse pattern from raw bytes: %s", ex)

        return result

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Handle sleep and wakeup attribute changes."""
        _LOGGER.warning("Writing attributes: %s", attributes)
        # Define sleep attribute mapping (name -> ID)
        sleep_attr_map = {
            "sleep_on_off": 0xA001,
            "sleep_hour": 0xA002,
            "sleep_minute": 0xA003,
            "sleep_countdown": 0xA004,
        }
        # Define wakeup attribute mapping (name -> ID)
        wakeup_attr_map = {
            "wakeup_on_off": 0xA005,
            "wakeup_hour": 0xA006,
            "wakeup_minute": 0xA007,
            "wakeup_brightness": 0xA008,
            "wakeup_countdown": 0xA009,
        }
        # Define night attribute mapping (name -> ID)
        night_attr_map = {
            "night_on_off": 0xA00A,
            "night_hour": 0xA00B,
            "night_minute": 0xA00C,
            "night_end_hour": 0xA00D,
            "night_end_minute": 0xA00E,
            "night_brightness": 0xA00F,
        }
        await self.sync_time()
        # Check if any sleep attribute is being written (by name or by ID)
        attr_keys = set(attributes.keys())
        sleep_attrs = set(sleep_attr_map.keys())
        sleep_attr_ids = set(sleep_attr_map.values())
        if not sleep_attrs.isdisjoint(attr_keys) or not sleep_attr_ids.isdisjoint(
            attr_keys
        ):
            # Update with new values if provided (support both name and ID)
            for attr_name, attr_id in sleep_attr_map.items():
                if attr_name in attributes:
                    self._attr_cache[attr_name] = attributes[attr_name]
                elif attr_id in attributes:
                    self._attr_cache[attr_name] = attributes[attr_id]
            # Get current values for all sleep attributes
            sleep_on_off = self._attr_cache.get("sleep_on_off", 0)
            sleep_hour = self._attr_cache.get("sleep_hour", 10)
            sleep_minute = self._attr_cache.get("sleep_minute", 0)
            sleep_countdown = self._attr_cache.get("sleep_countdown", 30)
            _LOGGER.warning(
                "Setting sleep pattern: on_off=%s, hour=%s, minute=%s, countdown=%s",
                sleep_on_off,
                sleep_hour,
                sleep_minute,
                sleep_countdown,
            )

            # Send command: [sleep_on_off, sleep_hour, sleep_minute, 0, sleep_countdown, 0]
            await self.set_pattern(
                pattern=bytes(
                    [sleep_on_off, sleep_hour, sleep_minute, 0, sleep_countdown, 0]
                )
            )
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

        # Check if any wakeup attribute is being written (by name or by ID)
        wakeup_attrs = set(wakeup_attr_map.keys())
        wakeup_attr_ids = set(wakeup_attr_map.values())
        if not wakeup_attrs.isdisjoint(attr_keys) or not wakeup_attr_ids.isdisjoint(
            attr_keys
        ):
            # Update with new values if provided (support both name and ID)
            for attr_name, attr_id in wakeup_attr_map.items():
                if attr_name in attributes:
                    self._attr_cache[attr_name] = attributes[attr_name]
                elif attr_id in attributes:
                    self._attr_cache[attr_name] = attributes[attr_id]
            # Get current values for all wakeup attributes
            wakeup_on_off = self._attr_cache.get("wakeup_on_off", 0)
            wakeup_hour = self._attr_cache.get("wakeup_hour", 10)
            wakeup_minute = self._attr_cache.get("wakeup_minute", 0)
            wakeup_brightness = self._attr_cache.get("wakeup_brightness", 100)
            wakeup_countdown = self._attr_cache.get("wakeup_countdown", 30)
            _LOGGER.warning(
                "Setting wakeup pattern: on_off=%s, hour=%s, minute=%s, brightness=%s, countdown=%s",
                wakeup_on_off,
                wakeup_hour,
                wakeup_minute,
                wakeup_brightness,
                wakeup_countdown,
            )

            # Send command: [wakeup_on_off, wakeup_hour, wakeup_minute, int(wakeup_brightness * 2.54), wakeup_countdown, 0]
            await self.set_wakeup_pattern(
                pattern=bytes(
                    [
                        wakeup_on_off,
                        wakeup_hour,
                        wakeup_minute,
                        int(wakeup_brightness * 2.54),
                        wakeup_countdown,
                        0,
                    ]
                )
            )
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

        # Check if any night attribute is being written (by name or by ID)
        night_attrs = set(night_attr_map.keys())
        night_attr_ids = set(night_attr_map.values())
        if not night_attrs.isdisjoint(attr_keys) or not night_attr_ids.isdisjoint(
            attr_keys
        ):
            # Update with new values if provided (support both name and ID)
            for attr_name, attr_id in night_attr_map.items():
                if attr_name in attributes:
                    self._attr_cache[attr_name] = attributes[attr_name]
                elif attr_id in attributes:
                    self._attr_cache[attr_name] = attributes[attr_id]
            # Get current values for all night attributes
            night_on_off = self._attr_cache.get("night_on_off", 0)
            night_hour = self._attr_cache.get("night_hour", 0)
            night_minute = self._attr_cache.get("night_minute", 0)
            night_end_hour = self._attr_cache.get("night_end_hour", 6)
            night_end_minute = self._attr_cache.get("night_end_minute", 0)
            night_brightness = self._attr_cache.get("night_brightness", 10)
            _LOGGER.warning(
                "Setting night pattern: on_off=%s, hour=%s, minute=%s, end_hour=%s, end_minute=%s, brightness=%s",
                night_on_off,
                night_hour,
                night_minute,
                night_end_hour,
                night_end_minute,
                night_brightness,
            )

            # Send command: [night_on_off, night_hour, night_minute, int(night_brightness * 2.54), night_end_hour, night_end_minute]
            await self.set_night_pattern(
                pattern=bytes(
                    [
                        night_on_off,
                        night_hour,
                        night_minute,
                        int(night_brightness * 2.54),
                        night_end_hour,
                        night_end_minute,
                    ]
                )
            )
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

        return await super().write_attributes(
            attributes,
            manufacturer=manufacturer,
            **kwargs,
        )

    async def sync_time(self):
        """Sync local time and timezone to device."""
        local_time = datetime.now().astimezone()
        utc_offset = local_time.utcoffset()
        timezone_offset = int(utc_offset.total_seconds()) if utc_offset else 0

        # Local Unix timestamp (same as JS: Date.now() / 1000 + (-offset * 60))
        local_unix_time = int(time.time()) + timezone_offset

        time_data = {
            "time": local_unix_time,
            "time_zone": timezone_offset,
        }
        _LOGGER.warning(
            "Syncing time to device: local_unix_time=%s, timezone_offset=%s",
            local_unix_time,
            timezone_offset,
        )
        # Get Time cluster (cluster_id=0x000A) from endpoint and write attributes to it
        time_cluster = getattr(self.endpoint, "time", None)
        if time_cluster:
            await time_cluster.write_attributes(time_data, manufacturer=None)
        else:
            _LOGGER.warning("Time cluster not found on endpoint")


class DimmingMode(t.enum8):
    """Dimming mode enum."""

    Trailing_edge = 0
    Leading_edge = 1


class RepenicOnOff(NoReplyMixin, CustomCluster, OnOff):
    """Repenic On Off Cluster with optimistic state updates."""

    void_input_commands = {cmd.id for cmd in OnOff.commands_by_name.values()}

    def __init__(self, *args, **kwargs):
        """Initialize cluster."""
        super().__init__(*args, **kwargs)
        asyncio.get_event_loop().call_soon(
            lambda: asyncio.ensure_future(self._read_onoff_when_ready())
        )

    async def _read_onoff_when_ready(self):
        """Wait for application controller to be ready, then read onoff."""
        # Wait for application controller to be running (up to 60 seconds)
        for _ in range(120):
            try:
                app = self.endpoint.device.application
                if app.state == "running":
                    break
            except AttributeError:
                pass
            await asyncio.sleep(0.5)

        await self.read_attributes([0x000])


class RepenicLevelControl(NoReplyMixin, CustomCluster, LevelControl):
    """Repenic LevelControl Cluster."""

    void_input_commands = {cmd.id for cmd in LevelControl.commands_by_name.values()}
    attributes = LevelControl.attributes.copy()
    attributes.update(
        {
            0xA000: ("min_brightness", t.uint8_t, False),
            0xA003: ("max_brightness", t.uint8_t, False),
            0xA004: ("boost", t.uint8_t, False),
            0xB000: ("dimming_mode", DimmingMode, False),
            0x14: ("default_move_rate", t.uint8_t, False),
        }
    )

    def _update_attribute(self, attrid, value):
        """Update attribute and log device report."""
        _LOGGER.warning(
            "RepenicLevelControl received report: attrid=0x%04X, value=%s",
            attrid,
            value,
        )
        super()._update_attribute(attrid, value)


(
    QuirkBuilder("Repenic Ltd.", "RD-250ZG")
    .replaces(RepenicLevelControl)
    .replaces(RepenicSceneModeCluster)
    .replaces(RepenicPressureCluster)
    .replaces(RepenicOnOff)
    .replaces(RepenicTimeCluster)
    .number(
        attribute_name="min_brightness",
        cluster_id=RepenicLevelControl.cluster_id,
        min_value=0,
        max_value=99,
        step=1,
        attribute_initialized_from_cache=True,
        translation_key="min_brightness",
        fallback_name="Minimum brightness",
    )
    .number(
        attribute_name="max_brightness",
        cluster_id=RepenicLevelControl.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        attribute_initialized_from_cache=True,
        translation_key="max_brightness",
        fallback_name="Maximum brightness",
    )
    .switch(
        attribute_name="boost",
        cluster_id=RepenicLevelControl.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="boost",
        fallback_name="Boost",
    )
    .enum(
        attribute_name="dimming_mode",
        enum_class=DimmingMode,
        cluster_id=RepenicLevelControl.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="dimming_mode",
        fallback_name="Dimming mode",
    )
    .number(
        attribute_name="default_move_rate",
        cluster_id=RepenicLevelControl.cluster_id,
        min_value=1,
        max_value=10,
        step=1,
        attribute_initialized_from_cache=True,
        translation_key="default_move_rate",
        fallback_name="Default move rate",
    )
    .enum(
        attribute_name="scene_mode",
        enum_class=OnOffState,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="scene_mode",
        fallback_name="Scene mode",
    )
    .enum(
        attribute_name="sleep_on_off",
        enum_class=OnOffState,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="sleep_on_off",
        fallback_name="Sleep On/Off",
    )
    .enum(
        attribute_name="sleep_hour",
        enum_class=Hour,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="sleep_hour",
        fallback_name="Sleep Hour",
    )
    .enum(
        attribute_name="sleep_minute",
        enum_class=Minute,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="sleep_minute",
        fallback_name="Sleep Minute",
    )
    .enum(
        attribute_name="sleep_countdown",
        enum_class=SleepCountdown,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="sleep_countdown",
        fallback_name="Sleep Countdown",
    )
    .enum(
        attribute_name="wakeup_on_off",
        enum_class=OnOffState,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="wakeup_on_off",
        fallback_name="Wakeup On/Off",
    )
    .enum(
        attribute_name="wakeup_hour",
        enum_class=Hour,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="wakeup_hour",
        fallback_name="Wakeup Hour",
    )
    .enum(
        attribute_name="wakeup_minute",
        enum_class=Minute,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="wakeup_minute",
        fallback_name="Wakeup Minute",
    )
    .number(
        attribute_name="wakeup_brightness",
        cluster_id=RepenicSceneModeCluster.cluster_id,
        min_value=1,
        max_value=100,
        step=1,
        attribute_initialized_from_cache=True,
        translation_key="wakeup_brightness",
        fallback_name="Wakeup Brightness",
    )
    .enum(
        attribute_name="wakeup_countdown",
        enum_class=WakeupCountdown,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="wakeup_countdown",
        fallback_name="Wakeup Countdown",
    )
    .enum(
        attribute_name="night_on_off",
        enum_class=OnOffState,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="night_on_off",
        fallback_name="Night On/Off",
    )
    .enum(
        attribute_name="night_hour",
        enum_class=Hour,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="night_hour",
        fallback_name="Night Hour",
    )
    .enum(
        attribute_name="night_minute",
        enum_class=Minute,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="night_minute",
        fallback_name="Night Minute",
    )
    .enum(
        attribute_name="night_end_hour",
        enum_class=Hour,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="night_end_hour",
        fallback_name="Night End Hour",
    )
    .enum(
        attribute_name="night_end_minute",
        enum_class=Minute,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="night_end_minute",
        fallback_name="Night End Minute",
    )
    .number(
        attribute_name="night_brightness",
        cluster_id=RepenicSceneModeCluster.cluster_id,
        min_value=1,
        max_value=100,
        step=1,
        attribute_initialized_from_cache=True,
        translation_key="night_brightness",
        fallback_name="Night Brightness",
    )
    .device_automation_triggers(
        {
            (DOUBLE_PRESS, BUTTON): {
                COMMAND: COMMAND_DOUBLE,
                CLUSTER_ID: RepenicPressureCluster.cluster_id,
                ENDPOINT_ID: 1,
            },
            (TRIPLE_PRESS, BUTTON): {
                COMMAND: COMMAND_TRIPLE,
                CLUSTER_ID: RepenicPressureCluster.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, BUTTON): {
                COMMAND: COMMAND_HOLD,
                CLUSTER_ID: RepenicPressureCluster.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_RELEASE, BUTTON): {
                COMMAND: COMMAND_RELEASE,
                CLUSTER_ID: RepenicPressureCluster.cluster_id,
                ENDPOINT_ID: 1,
            },
        }
    )
    .add_to_registry()
)
