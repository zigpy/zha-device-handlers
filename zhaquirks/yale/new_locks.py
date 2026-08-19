"""Device handler for Yale."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import ClusterType, QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
import zigpy.types as t
from zigpy.zcl.clusters.closures import DoorLock, OperationEvent
from zigpy.zcl.clusters.general import Ota, PowerConfiguration
from zigpy.zcl.foundation import ZCLCommandDef


class YaleCluster(CustomCluster):
    """Proprietary Yale cluster (0x100F)."""

    cluster_id = 0x100F
    name = "Yale Proprietary Cluster"
    ep_attribute = "yale_cluster"


class YaleOperationEventSource(t.enum8):
    """Yale's proprietary values for the operation_event_notification 'source' byte.

    The ZCL spec only defines 0-3 and 0xFF for this field (Keypad/RF/Manual/RFID/
    Indeterminate), but Yale's YDM60/YMC420 firmware uses a 16-value combined
    method+action code in this same byte position. Values validated against
    zigbee-herdsman-converters' ymc_action converter (src/devices/yale.ts),
    confirmed against 4 production units over 10 days
    (see Koenkk/zigbee2mqtt#32103).
    """

    PasswordUnlock = 0x00
    Unlock = 0x01
    AutoLock = 0x02
    RFIDUnlock = 0x03
    FingerprintUnlock = 0x04
    UnlockFailureInvalidPinOrId = 0x05
    UnlockFailureInvalidSchedule = 0x06
    OneTouchLock = 0x07
    KeyLock = 0x08
    KeyUnlock = 0x09
    ScheduleAutoLock = 0x0A
    ScheduleLock = 0x0B
    ScheduleUnlock = 0x0C
    ManualLock = 0x0D
    ManualUnlock = 0x0E
    NonAccessUserOperationalEvent = 0x0F


class FixedDoorLock(CustomCluster, DoorLock):
    """DoorLock cluster with fixes/extensions for Yale's firmware quirks.

    1. ZHA's lock platform checks ``result[0] is not Status.SUCCESS``, but
       ``DefaultResponse`` fields are ``(command_id, status)`` in that order, so
       ``result[0]`` is actually the ``command_id``. This makes every successful
       lock/unlock get logged as an error. Re-order the returned tuple so
       index 0 holds the real status, without changing the Zigbee command sent.
    2. Yale repurposes the standard ``operation_event_notification`` "source"
       byte with its own 16-value method+action code (see
       ``YaleOperationEventSource``). Overriding the schema here makes ZHA
       (and its default Logbook entries) decode it correctly instead of
       showing ``undefined_0xNN``.
    """

    async def lock_door(self, *args, **kwargs):
        """Lock the door, fixing the (command_id, status) ordering bug."""
        result = await self.command(
            self.ServerCommandDefs.lock_door.id, *args, **kwargs
        )
        return (result.status, result.command_id)

    async def unlock_door(self, *args, **kwargs):
        """Unlock the door, fixing the (command_id, status) ordering bug."""
        result = await self.command(
            self.ServerCommandDefs.unlock_door.id, *args, **kwargs
        )
        return (result.status, result.command_id)

    class ClientCommandDefs(DoorLock.ClientCommandDefs):
        """Override operation_event_notification to decode Yale's source byte."""

        operation_event_notification: Final = ZCLCommandDef(
            id=0x20,
            schema={
                "operation_event_source": YaleOperationEventSource,
                "operation_event_code": OperationEvent,
                "user_id": t.uint16_t,
                "pin": t.CharacterString,
                "local_time": t.LocalTime,
                "data?": t.CharacterString,
            },
        )


(
    QuirkBuilder("Yale", "YDM60")
    .also_applies_to("Yale", "YMC 420 D")
    .also_applies_to("Yale", "YMC420")
    .replaces(FixedDoorLock, cluster_type=ClusterType.Server)
    .replaces(FixedDoorLock, cluster_type=ClusterType.Client)
    .replaces(YaleCluster, cluster_type=ClusterType.Server)
    .replaces(YaleCluster, cluster_type=ClusterType.Client)
    .adds(PowerConfiguration.cluster_id, cluster_type=ClusterType.Server)
    .adds(Ota.cluster_id, cluster_type=ClusterType.Client)
    .number(
        DoorLock.AttributeDefs.auto_relock_time.name,
        DoorLock.cluster_id,
        min_value=0,
        max_value=3600,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="auto_relock_time",
        fallback_name="Auto relock time",
    )
    .number(
        DoorLock.AttributeDefs.sound_volume.name,
        DoorLock.cluster_id,
        min_value=0,
        max_value=2,
        step=1,
        translation_key="sound_volume",
        fallback_name="Sound volume",
    )
    .number(
        DoorLock.AttributeDefs.wrong_code_entry_limit.name,
        DoorLock.cluster_id,
        min_value=1,
        max_value=10,
        step=1,
        translation_key="wrong_code_entry_limit",
        fallback_name="Wrong code entry limit",
    )
    .switch(
        DoorLock.AttributeDefs.enable_one_touch_locking.name,
        DoorLock.cluster_id,
        translation_key="enable_one_touch_locking",
        fallback_name="One touch locking",
    )
    .add_to_registry()
)
