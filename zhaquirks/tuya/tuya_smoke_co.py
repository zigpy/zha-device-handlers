"""MOES JKD-513COM-Z combined smoke and carbon monoxide detector."""

import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import BinarySensorDeviceClass, EntityPlatform, EntityType
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster


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


def alarm_state(value: int) -> bool | None:
    """Only explicit normal clears an alarm; other states remain unknown."""
    return {0: True, 1: False}.get(int(value))


class MoesSmokeCOCluster(TuyaMCUCluster):
    """Initialize unreported alarm attributes to unknown, not normal."""

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
