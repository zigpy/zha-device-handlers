"""Quirk for the Tuya TZE204_zxkwaztm thermostat."""

from collections.abc import Callable
from typing import Any, Final

from zigpy.types import t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import RunningState, Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import UnitOfTemperature
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import DPToAttributeMapping
from zhaquirks.tuya.tuya_thermostat import TuyaThermostat

SCHEDULE_ATTRIBUTE_ACCESS = (
    foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write
)


class PresetModeV05(t.enum8):
    """Preset modes used by the TZE204_zxkwaztm thermostat."""

    Auto = 0x00
    Manual = 0x01


class WorkingDayV03(t.enum8):
    """Working-day modes used by the TZE204_zxkwaztm thermostat."""

    Five_Two = 0x00
    Six_One = 0x01
    Seven = 0x02


class TuyaThermostatSchedule(TuyaThermostat):
    """Tuya thermostat cluster with schedule configuration attributes."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Schedule attributes."""

        schedule_slot_1_hour: Final = ZCLAttributeDef(
            id=0xFC00,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_1_minute: Final = ZCLAttributeDef(
            id=0xFC01,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_1_temperature: Final = ZCLAttributeDef(
            id=0xFC02,
            type=t.uint16_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_2_hour: Final = ZCLAttributeDef(
            id=0xFC03,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_2_minute: Final = ZCLAttributeDef(
            id=0xFC04,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_2_temperature: Final = ZCLAttributeDef(
            id=0xFC05,
            type=t.uint16_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_3_hour: Final = ZCLAttributeDef(
            id=0xFC06,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_3_minute: Final = ZCLAttributeDef(
            id=0xFC07,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_3_temperature: Final = ZCLAttributeDef(
            id=0xFC08,
            type=t.uint16_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_4_hour: Final = ZCLAttributeDef(
            id=0xFC09,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_4_minute: Final = ZCLAttributeDef(
            id=0xFC0A,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_4_temperature: Final = ZCLAttributeDef(
            id=0xFC0B,
            type=t.uint16_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_5_hour: Final = ZCLAttributeDef(
            id=0xFC0C,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_5_minute: Final = ZCLAttributeDef(
            id=0xFC0D,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_5_temperature: Final = ZCLAttributeDef(
            id=0xFC0E,
            type=t.uint16_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_6_hour: Final = ZCLAttributeDef(
            id=0xFC0F,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_6_minute: Final = ZCLAttributeDef(
            id=0xFC10,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        schedule_slot_6_temperature: Final = ZCLAttributeDef(
            id=0xFC11,
            type=t.uint16_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        weekend_schedule_slot_1_hour: Final = ZCLAttributeDef(
            id=0xFC12,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        weekend_schedule_slot_1_minute: Final = ZCLAttributeDef(
            id=0xFC13,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        weekend_schedule_slot_1_temperature: Final = ZCLAttributeDef(
            id=0xFC14,
            type=t.uint16_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        weekend_schedule_slot_2_hour: Final = ZCLAttributeDef(
            id=0xFC15,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        weekend_schedule_slot_2_minute: Final = ZCLAttributeDef(
            id=0xFC16,
            type=t.uint8_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )
        weekend_schedule_slot_2_temperature: Final = ZCLAttributeDef(
            id=0xFC17,
            type=t.uint16_t,
            access=SCHEDULE_ATTRIBUTE_ACCESS,
            is_manufacturer_specific=True,
        )


WEEKDAY_SCHEDULE_SLOT_COUNT = 6
WEEKEND_SCHEDULE_SLOT_COUNT = 2
SCHEDULE_SLOT_COUNT = WEEKDAY_SCHEDULE_SLOT_COUNT + WEEKEND_SCHEDULE_SLOT_COUNT
SCHEDULE_SLOT_SIZE = 4
SCHEDULE_PAYLOAD_SIZE = 32


def _schedule_data(value: t.LVBytes) -> bytes:
    """Validate and return the raw schedule payload."""
    data = bytes(value)
    if len(data) != SCHEDULE_PAYLOAD_SIZE:
        raise ValueError(
            f"Expected {SCHEDULE_PAYLOAD_SIZE}-byte schedule, received {len(data)}"
        )
    return data


def _schedule_slot_converter(slot: int, field: int) -> Callable[[Any], int]:
    """Return a converter for one field of a schedule slot."""

    def converter(value: t.LVBytes) -> int:
        data = _schedule_data(value)
        offset = slot * SCHEDULE_SLOT_SIZE
        if field == 0:
            return data[offset]
        if field == 1:
            return data[offset + 1]
        return int.from_bytes(data[offset + 2 : offset + 4], "big")

    return converter


def _schedule_to_dp(*values: Any) -> t.Bytes:
    """Encode six weekday and two weekend schedule slots."""
    if len(values) != SCHEDULE_SLOT_COUNT * 3 or any(value is None for value in values):
        raise ValueError("All schedule values must be available before writing")

    payload = bytearray()
    for offset in range(0, len(values), 3):
        hour, minute, temperature = (
            int(value) for value in values[offset : offset + 3]
        )
        payload.extend((hour, minute))
        payload.extend(temperature.to_bytes(2, "big"))

    if len(payload) != SCHEDULE_PAYLOAD_SIZE:
        raise ValueError(f"Expected {SCHEDULE_PAYLOAD_SIZE}-byte schedule")
    return t.Bytes(payload)


def _schedule_dp_mappings() -> list[DPToAttributeMapping]:
    """Build mappings between schedule DP 67 and thermostat attributes."""
    return [
        DPToAttributeMapping(
            ep_attribute=TuyaThermostatSchedule.ep_attribute,
            attribute_name=f"{_schedule_slot_prefix(slot)}_{field_name}",
            converter=_schedule_slot_converter(slot - 1, field),
        )
        for slot in range(1, SCHEDULE_SLOT_COUNT + 1)
        for field, field_name in enumerate(("hour", "minute", "temperature"))
    ]


def _schedule_slot_prefix(slot: int) -> str:
    """Return the thermostat attribute prefix for a schedule slot."""
    if slot <= WEEKDAY_SCHEDULE_SLOT_COUNT:
        return f"schedule_slot_{slot}"
    return f"weekend_schedule_slot_{slot - WEEKDAY_SCHEDULE_SLOT_COUNT}"


thermostat_zxkwaztm = (
    TuyaQuirkBuilder("_TZE204_zxkwaztm", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.system_mode.name,
        converter=lambda x: {
            True: Thermostat.SystemMode.Heat,
            False: Thermostat.SystemMode.Off,
        }[x],
        dp_converter=lambda x: {
            Thermostat.SystemMode.Heat: True,
            Thermostat.SystemMode.Off: False,
        }[x],
    )
    .tuya_enum(
        dp_id=2,
        attribute_name="preset_mode",
        enum_class=PresetModeV05,
        translation_key="preset_mode",
        fallback_name="Preset mode",
    )
    .tuya_switch(
        dp_id=10,
        attribute_name="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )
    .tuya_dp(
        dp_id=16,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    .tuya_dp(
        dp_id=24,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    .tuya_dp(
        dp_id=36,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.running_state.name,
        # converter=lambda x: RunningState.Heat_State_On if not x else RunningState.Idle,
        converter=lambda x: RunningState.Idle if not x else RunningState.Heat_State_On,
    )
    .tuya_switch(
        dp_id=40,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .tuya_number(
        dp_id=109,
        attribute_name=TuyaThermostat.AttributeDefs.local_temperature_calibration.name,
        type=t.int32s,
        min_value=-9.9,
        max_value=9.9,
        unit=UnitOfTemperature.CELSIUS,
        step=0.1,
        multiplier=0.1,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    .tuya_number(
        dp_id=112,
        attribute_name="regulator_set_point",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=0,
        max_value=100,
        step=1,
        translation_key="regulator_set_point",
        fallback_name="Regulator set point",
    )
    .tuya_enum(
        dp_id=31,
        attribute_name="working_day",
        enum_class=WorkingDayV03,
        translation_key="working_day",
        fallback_name="Working day",
    )
    .tuya_dp_multi(
        dp_id=67,
        attribute_mapping=_schedule_dp_mappings(),
        dp_converter=_schedule_to_dp,
    )
    .tuya_enchantment(read_attr_spell=False, data_query_spell=True)
)

for slot in range(1, SCHEDULE_SLOT_COUNT + 1):
    slot_prefix = _schedule_slot_prefix(slot)
    slot_label = (
        f"Schedule slot {slot}"
        if slot <= WEEKDAY_SCHEDULE_SLOT_COUNT
        else f"Weekend schedule slot {slot - WEEKDAY_SCHEDULE_SLOT_COUNT}"
    )
    for field_name, field_label in (
        ("hour", "Hour"),
        ("minute", "Minute"),
        ("temperature", "Temperature"),
    ):
        attribute_name = f"{slot_prefix}_{field_name}"
        if field_name == "temperature":
            thermostat_zxkwaztm.number(
                attribute_name=attribute_name,
                cluster_id=TuyaThermostatSchedule.cluster_id,
                min_value=0,
                max_value=50,
                step=0.1,
                unit=UnitOfTemperature.CELSIUS,
                multiplier=0.1,
                translation_key=attribute_name,
                fallback_name=f"{slot_label} {field_label}",
            )
        else:
            thermostat_zxkwaztm.number(
                attribute_name=attribute_name,
                cluster_id=TuyaThermostatSchedule.cluster_id,
                min_value=0,
                max_value=23 if field_name == "hour" else 59,
                step=1,
                mode="box",
                translation_key=attribute_name,
                fallback_name=f"{slot_label} {field_label}",
            )

(
    thermostat_zxkwaztm.adds(TuyaThermostatSchedule)
    .skip_configuration()
    .add_to_registry()
)
