"""ZHA support for xyzroe/DIYRuZ DIY_Zintercom firmware.

The firmware advertises its custom reporting cluster as an output cluster and
omits Power Configuration from its simple descriptor. Add their server sides
without discarding Basic or the OnOff client used for incoming-call events.

Protocol reference: xyzroe/Zintercom, commit
5b2db2f803adb25d47cef93e337922eb1e34eefe, Source/zcl_app_data.c.
"""

import asyncio
import time
from typing import Any, Final

from zigpy.exceptions import ZigbeeException
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff, PowerConfiguration
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class ZintercomState(t.enum8):
    """Reported state of the intercom electronics, not a door-position sensor."""

    Idle = 0
    Ring = 1
    Talk = 2
    Open = 3
    Drop = 4


class ZintercomMode(t.enum8):
    """Automatic handling of an incoming call."""

    Never = 0
    Once = 1
    Always = 2
    Drop = 3


class DIYZintercomDoorLockCluster(CustomCluster):
    """The firmware's custom attributes share the DoorLock cluster ID."""

    cluster_id = 0x0101
    ep_attribute = "zintercom"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize wake-read bookkeeping."""
        self._battery_read_pending = False
        self._battery_last_attempt: float | None = None
        self._battery_last_success: float | None = None
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid: int | ZCLAttributeDef, value: Any) -> None:
        """Refresh battery only after an Idle update, never during opening."""
        super()._update_attribute(attrid, value)
        attribute_id = attrid if isinstance(attrid, int) else attrid.id
        # An Idle update is received both after a call and in periodic reports.
        # The radio has just been awake. Do not compete with Once during Ring.
        if attribute_id == self.AttributeDefs.state.id and value == ZintercomState.Idle:
            self._refresh_battery_when_awake()

    def _refresh_battery_when_awake(self) -> None:
        """Read battery measurements when an Idle report indicates a wake window."""
        power = self.endpoint.in_clusters.get(PowerConfiguration.cluster_id)
        if power is None or self._battery_read_pending:
            return
        now = time.monotonic()
        if (
            self._battery_last_attempt is not None
            and now - self._battery_last_attempt < 300
        ):
            return
        percentage = power.get("battery_percentage_remaining")
        if (
            percentage is not None
            and percentage != 0xFF
            and self._battery_last_success is not None
            and now - self._battery_last_success < 21600
        ):
            return
        self._battery_last_attempt = now
        self._battery_read_pending = True
        self.create_catching_task(self._read_awake_battery(power))

    async def _read_awake_battery(self, power: PowerConfiguration) -> None:
        """Refresh real measurements without writing any intercom attributes."""
        try:
            # RingEnd updates the measurement in the same firmware task.
            await asyncio.sleep(0.05)
            success, _ = await power.read_attributes(
                ["battery_voltage", "battery_percentage_remaining"],
                allow_cache=False,
            )
            percentage = success.get("battery_percentage_remaining")
            if percentage is not None and 0 <= percentage <= 200:
                self._battery_last_success = time.monotonic()
        except (ZigbeeException, TimeoutError):
            # A sleepy device may already be asleep again. Retry on a later
            # natural Idle report, subject to the cooldown; never wake/reset it.
            self.debug("Battery refresh missed the wake window")
        finally:
            self._battery_read_pending = False

    class AttributeDefs(BaseAttributeDefs):
        """Use the exact ZCL types declared by the firmware."""

        state: Final = ZCLAttributeDef(
            id=0x0050,
            type=ZintercomState,
            access="rp",
            manufacturer_code=None,
        )
        mode: Final = ZCLAttributeDef(
            id=0x0051,
            type=ZintercomMode,
            access="rwp",
            manufacturer_code=None,
        )
        sound: Final = ZCLAttributeDef(
            id=0x0052,
            type=t.Bool,
            access="rwp",
            manufacturer_code=None,
        )
        time_ring: Final = ZCLAttributeDef(
            id=0x0053,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=None,
        )
        time_talk: Final = ZCLAttributeDef(
            id=0x0054,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=None,
        )
        time_open: Final = ZCLAttributeDef(
            id=0x0055,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=None,
        )
        time_report: Final = ZCLAttributeDef(
            id=0x0056,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=None,
        )
        time_bell: Final = ZCLAttributeDef(
            id=0x0057,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=None,
        )


class DIYZintercomPowerConfigurationCluster(CustomCluster, PowerConfiguration):
    """Treat the firmware's uninitialised battery measurements as unknown."""

    def get(self, key: str | int, default: Any = None) -> Any:
        """Normalize unknown measurements, including values restored from cache."""
        # Quirk replacement restores the old attribute cache directly, bypassing
        # _update_attribute. Normalise on read so both restored and fresh values
        # use the same unknown-value semantics without changing wire data.
        value = super().get(key, default)
        if (
            self.find_attribute(key).id
            in (
                PowerConfiguration.AttributeDefs.battery_voltage.id,
                PowerConfiguration.AttributeDefs.battery_percentage_remaining.id,
            )
            and value == 0xFF
        ):
            return None
        return value


CALL_REPORTING = ReportingConfig(min_interval=0, max_interval=3600, reportable_change=0)

builder = (
    QuirkBuilder("xyzroe", "DIY_Zintercom")
    .also_applies_to("DIYRuZ", "DIY_Zintercom")
    .replaces(DIYZintercomDoorLockCluster)
    .replaces(DIYZintercomPowerConfigurationCluster)
    # Preserve the old binary sensor's unique ID, but describe what it measures:
    # the firmware sends On for an active call and Off when the call ends.
    .change_entity_metadata(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        function=lambda entity: entity.PLATFORM.value == "binary_sensor",
        new_translation_key="call_active",
        new_device_class=BinarySensorDeviceClass.SOUND,
        new_fallback_name="Call active",
    )
    .enum(
        "state",
        ZintercomState,
        DIYZintercomDoorLockCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        attribute_initialized_from_cache=False,
        reporting_config=CALL_REPORTING,
        translation_key="state",
        fallback_name="Call state",
    )
    .binary_sensor(
        "state",
        DIYZintercomDoorLockCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.SOUND,
        attribute_initialized_from_cache=False,
        attribute_converter=lambda value: value == ZintercomState.Ring,
        reporting_config=CALL_REPORTING,
        unique_id_suffix="ringing",
        translation_key="ringing",
        fallback_name="Incoming call",
    )
    .binary_sensor(
        "state",
        DIYZintercomDoorLockCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        attribute_initialized_from_cache=False,
        attribute_converter=lambda value: value == ZintercomState.Open,
        reporting_config=CALL_REPORTING,
        unique_id_suffix="opening_signal",
        translation_key="opening_signal",
        fallback_name="Opening signal",
    )
    .enum(
        "mode",
        ZintercomMode,
        DIYZintercomDoorLockCluster.cluster_id,
        attribute_initialized_from_cache=False,
        reporting_config=CALL_REPORTING,
        translation_key="mode",
        fallback_name="Mode",
    )
    .switch(
        "sound",
        DIYZintercomDoorLockCluster.cluster_id,
        attribute_initialized_from_cache=False,
        reporting_config=CALL_REPORTING,
        translation_key="sound",
        fallback_name="Handset sound",
    )
)

# Timers are uint8 on the wire. The four second-based timers are multiplied by
# 1000 before widening to uint32 in the CC2530 firmware (16-bit int). Keep writes
# within 32 seconds to avoid overflowing that intermediate calculation.
for attribute, name in (
    ("time_ring", "Delay before answering"),
    ("time_talk", "Delay before opening"),
    ("time_open", "Opening signal duration"),
    ("time_bell", "Call end timeout"),
):
    builder.number(
        attribute,
        DIYZintercomDoorLockCluster.cluster_id,
        min_value=1,
        max_value=32,
        step=1,
        unit=UnitOfTime.SECONDS,
        attribute_initialized_from_cache=False,
        translation_key=attribute,
        fallback_name=name,
    )

builder.number(
    "time_report",
    DIYZintercomDoorLockCluster.cluster_id,
    min_value=1,
    max_value=255,
    step=1,
    unit=UnitOfTime.MINUTES,
    attribute_initialized_from_cache=False,
    translation_key="time_report",
    fallback_name="Reporting interval",
)

ZINTERCOM_QUIRK = builder.add_to_registry()
