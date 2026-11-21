"""MOES JKD-513COM-Z combined smoke and carbon monoxide detector."""

from time import monotonic
from typing import Any

from zigpy.exceptions import ZigbeeException
import zigpy.types as t
from zigpy.typing import AddressingMode
from zigpy.zcl import foundation

from zhaquirks.builder import BinarySensorDeviceClass, EntityPlatform, EntityType
from zhaquirks.tuya import (
    TUYA_ACTIVE_STATUS_RPT,
    TUYA_CLUSTER_ID,
    TUYA_GET_DATA,
    TUYA_QUERY_DATA,
    TUYA_SET_DATA_RESPONSE,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster

_QUERY_RESPONSE_WINDOW = 20.0


class SmokeState(t.enum8):
    """Smoke detection state."""

    Alarm = 0
    Normal = 1
    Detecting = 2
    Unknown = 3


class COState(t.enum8):
    """Carbon monoxide detection state."""

    Alarm = 0
    Normal = 1
    Unknown = 255  # Local initial value, not a documented wire value.


class CheckingResult(t.enum8):
    """Self-test result reported by the detector."""

    Checking = 0
    Check_success = 1
    Check_failure = 2
    Others = 3


class BatteryState(t.enum8):
    """Battery level category; the device does not report a percentage."""

    Low = 0
    High = 1
    Unknown = 255  # Local initial value.


_KNOWN_STATES = {
    "smoke_state": (SmokeState.Alarm, SmokeState.Normal, SmokeState.Detecting),
    "co_state": (COState.Alarm, COState.Normal),
    "battery_state": (BatteryState.Low, BatteryState.High),
}


def alarm_state(value: int) -> bool | None:
    """Only explicit normal clears an alarm; other states remain unknown."""
    return {0: True, 1: False}.get(int(value))


class MoesSmokeCOCluster(TuyaMCUCluster):
    """Request initial states and keep missing reports unknown."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Track the initial and follow-up queries for this device."""
        super().__init__(*args, **kwargs)
        # None marks a pending query, including one scheduled by a report.
        self._followup_allowed_at: float | None = 0.0
        self._followup_sent = False

    async def apply_custom_configuration(self, *args: Any, **kwargs: Any) -> None:
        """Request Tuya datapoints during ZHA device configuration."""
        await super().apply_custom_configuration(*args, **kwargs)
        if self._followup_allowed_at is None:
            return
        self._followup_sent = False
        self._followup_allowed_at = None
        await self._query_status()

    async def _query_status(self) -> None:
        """Request status and allow configuration to finish on delivery failure."""
        response_window = _QUERY_RESPONSE_WINDOW
        try:
            await self.command(TUYA_QUERY_DATA)
        except (TimeoutError, ZigbeeException) as exc:
            self.debug("Tuya status query failed: %s", exc)
            response_window = 0.0
        finally:
            self._followup_allowed_at = monotonic() + response_window

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: AddressingMode | None = None,
    ) -> None:
        """Query remaining states once after a later Tuya report."""
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)
        if (
            hdr.direction != foundation.Direction.Server_to_Client
            or hdr.command_id
            not in (TUYA_GET_DATA, TUYA_SET_DATA_RESPONSE, TUYA_ACTIVE_STATUS_RPT)
            or self._followup_sent
            or self._followup_allowed_at is None
            # Query replies can use the same commands as unsolicited reports.
            or monotonic() < self._followup_allowed_at
            or not args[0].datapoints
        ):
            return

        if all(self.get(name) in states for name, states in _KNOWN_STATES.items()):
            return

        self._followup_sent = True
        self._followup_allowed_at = None
        self.create_catching_task(self._query_status())

    def get(self, key, default=None):
        """Keep unreported alarm and battery states unknown."""
        value = super().get(key, default)
        if value is not None:
            return value
        # ZHA's generic binary sensor otherwise treats a missing value as False.
        # Use a local sentinel without injecting a normal reading into the cache.
        defaults = {"smoke_state": 3, "co_state": 255, "battery_state": 255}
        if isinstance(key, int) and key in self.attributes:
            key = self.attributes[key].name
        return defaults.get(key, value)


builder = TuyaQuirkBuilder("_TZE284_aoah6bv8", "TS0601").friendly_name(
    model="JKD-513COM-Z", manufacturer="MOES"
)
for dp, name, enum, label, category in (
    (1, "smoke_state", SmokeState, "Smoke state", EntityType.STANDARD),
    (9, "checking_result", CheckingResult, "Self test result", EntityType.DIAGNOSTIC),
    (14, "battery_state", BatteryState, "Battery state", EntityType.DIAGNOSTIC),
    (18, "co_state", COState, "CO state", EntityType.STANDARD),
):
    builder.tuya_enum(
        dp_id=dp,
        attribute_name=name,
        enum_class=enum,
        access=foundation.ZCLAttributeAccess.Read
        | foundation.ZCLAttributeAccess.Report,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=category,
        translation_key=name,
        fallback_name=label,
    )

for name, device_class, label, category in (
    ("smoke_state", BinarySensorDeviceClass.SMOKE, "Smoke alarm", EntityType.STANDARD),
    ("co_state", BinarySensorDeviceClass.CO, "CO alarm", EntityType.STANDARD),
    (
        "battery_state",
        BinarySensorDeviceClass.BATTERY,
        "Battery low",
        EntityType.DIAGNOSTIC,
    ),
):
    builder.binary_sensor(
        attribute_name=name,
        cluster_id=TUYA_CLUSTER_ID,
        attribute_converter=alarm_state,
        device_class=device_class,
        entity_type=category,
        unique_id_suffix=name + "_alarm",
        translation_key=name + "_alarm",
        fallback_name=label,
    )

# Preserve the entire bitmap: multiple fault flags may be active at once.
builder.tuya_sensor(
    dp_id=11,
    attribute_name="fault_bitmap",
    type=t.bitmap32,
    entity_type=EntityType.DIAGNOSTIC,
    translation_key="fault_bitmap",
    fallback_name="Fault bitmap",
)
builder.tuya_switch(
    dp_id=16,
    attribute_name="muffling",
    translation_key="muffling",
    fallback_name="Silence alarm",
)
QUIRK = builder.skip_configuration().add_to_registry(
    replacement_cluster=MoesSmokeCOCluster
)
