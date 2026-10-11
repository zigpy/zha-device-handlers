"""Moes Star Ring (ZHT-SR) Zigbee thermostat for electric floor heating (16 A).

TS0601 / _TZE204_lpedvtvr
Model: MOES-ZHT-SR-GB-WH-MS-2236 (module ZT3L)

Sources of the datapoint map: Zigbee2MQTT (moes.ts, ZHT-SR), the Tuya cloud
(product_id lpedvtvr) and zigpy/zha-device-handlers issue #3666.

Temperatures are reported as integers x10 (scale 1), therefore:
  - ZCL attributes (local_temperature, occupied_heating_setpoint) are multiplied
    by 10 to get centidegrees,
  - number entities (limits, protections, eco, deadzone) use multiplier=0.1.

The climate entity uses its own thermostat cluster with absolute limits
5 - 45 degC (the device accepts 5 - 45 degC); the default TuyaThermostatV2
caps the range at 30 degC.

Time: the device uses the 1970 epoch (default of TuyaMCUCluster).

Weekly program: DP 102 - 108 (week_program_13_1 ... 13_7, type Raw, one
datapoint per day, 1 = Monday ... 7 = Sunday). Format (confirmed by writing it
and watching the relay switch at the scheduled minute on a real thermostat):
  [day number] + 4 x [hour, minute, temperature_hi, temperature_lo]
  temperature = 16 bit big endian integer x10 (0x00C8 = 20.0 degC)
The thermostat accepts exactly 4 slots per day (a 5th slot was ignored).
The "Week program 1-7" sensors show the program as text; writing goes through
zha.set_zigbee_cluster_attribute with a hex string, for example
  value: "06060000c80b1e00c80d1e00c8111e00c8"

Notes:
- DP 47: 0 = heating (open), 1 = idle (close).
- DP 114 (screen on time): values 0 - 5 = 10, 20, 30, 40, 50, 60 s.
- DP 101 (calibration): the value may snap back a few seconds after a change
  (firmware behaviour reported in issue #3666).
- Sensor mode "Floor": one user reported that the relay did not react in this
  mode and the display showed a wrong temperature.
"""

from typing import Any

import zigpy.types as t
from zigpy.profiles import zha
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import RunningState, Thermostat

from zhaquirks.builder import PERCENTAGE, EntityType, UnitOfTemperature
from zhaquirks.tuya import (
    TUYA_CLUSTER_ID,
    TuyaCommand,
    TuyaData,
    TuyaDatapointData,
    TuyaDPType,
)
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_trv import TuyaThermostatV2


class MoesThermostat(TuyaThermostatV2):
    """Thermostat with a 5 - 45 degC range (instead of 5 - 30 degC)."""

    _CONSTANT_ATTRIBUTES = {
        **TuyaThermostatV2._CONSTANT_ATTRIBUTES,
        Thermostat.AttributeDefs.abs_min_heat_setpoint_limit.id: 500,
        Thermostat.AttributeDefs.abs_max_heat_setpoint_limit.id: 4500,
    }


WEEK_PROGRAM_DPS = {f"week_program_{day + 1}": 102 + day for day in range(7)}


def _decode_program(raw: Any) -> str:
    """Convert the program bytes to readable text.

    Format: [day number] + slots of 4 bytes [hour, minute, temp_hi, temp_lo],
    temperature is x10. Result e.g. "06:00 20.0 | 11:30 20.0 | 13:30 20.0".
    """
    data = bytes(raw)
    parts = []
    for i in range(1, len(data) - 3, 4):
        temp = int.from_bytes(data[i + 2 : i + 4], "big") / 10
        parts.append(f"{data[i]:02d}:{data[i + 1]:02d} {temp:.1f}")
    return " | ".join(parts)


def _to_bytes(value: Any) -> bytes:
    """Program value as bytes: hex text ("0606..."), bytes or a list of ints."""
    if isinstance(value, str):
        cleaned = value.strip().lower().removeprefix("0x")
        for sep in (" ", ":", "-", ","):
            cleaned = cleaned.replace(sep, "")
        return bytes.fromhex(cleaned)
    return bytes(value)


class MoesTuyaMCUCluster(TuyaMCUCluster):
    """Tuya MCU cluster that can write the raw weekly program bytes.

    The standard TuyaMCUCluster can only write numbers (TuyaClusterData has an
    int attr_value), so the program bytes are sent directly as a Raw datapoint.
    """

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Write normal attributes as usual and the weekly program as a Raw DP."""
        raw_writes: dict[str, bytes] = {}
        others: dict[str | int | foundation.ZCLAttributeDef, Any] = {}

        for attr, value in attributes.items():
            if isinstance(attr, foundation.ZCLAttributeDef):
                name = attr.name
            elif isinstance(attr, int):
                attr_def = self.attributes.get(attr)
                name = attr_def.name if attr_def else None
            else:
                name = attr
            if name in WEEK_PROGRAM_DPS:
                raw_writes[name] = _to_bytes(value)
            else:
                others[attr] = value

        results: list[list[foundation.WriteAttributesStatusRecord]] = []
        if others:
            results = await super().write_attributes(
                others, manufacturer=manufacturer, **kwargs
            )

        for name, data in raw_writes.items():
            tuya_data = TuyaData()
            tuya_data.dp_type = TuyaDPType.RAW
            tuya_data.function = t.uint8_t(0)
            tuya_data.raw = data
            command = TuyaCommand(
                status=0,
                tsn=self.endpoint.device.application.get_sequence(),
                datapoints=[TuyaDatapointData(WEEK_PROGRAM_DPS[name], tuya_data)],
            )
            self.debug("week program write %s: %s", name, data.hex())
            await self.command(
                self.mcu_write_command,
                command,
                expect_reply=False,
                manufacturer=manufacturer,
            )
            self.update_attribute(name, _decode_program(data))
            results.append(
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            )

        return results


class Preset(t.enum8):
    """DP 2 - thermostat mode."""

    Manual = 0x00
    Temporary_manual = 0x01
    Program = 0x02
    Eco = 0x03


class SensorMode(t.enum8):
    """DP 32 - which sensor is used."""

    Internal = 0x00  # IN - internal sensor, no floor protection
    Internal_with_floor_protection = 0x01  # AL - internal sensor + external as protection
    External = 0x02  # OU - external (floor) sensor


class ScreenTime(t.enum8):
    """DP 114 - how long the screen stays on."""

    S10 = 0x00
    S20 = 0x01
    S30 = 0x02
    S40 = 0x03
    S50 = 0x04
    S60 = 0x05


builder = (
    TuyaQuirkBuilder("_TZE204_lpedvtvr", "TS0601")
    # The default device type is SMART_PLUG, change it back to THERMOSTAT.
    .replaces_endpoint(1, device_type=zha.DeviceType.THERMOSTAT)
    # ---- DP 1 (switch) -> ZCL system_mode ----
    .tuya_dp(
        dp_id=1,
        ep_attribute=MoesThermostat.ep_attribute,
        attribute_name=MoesThermostat.AttributeDefs.system_mode.name,
        converter=lambda x: (
            Thermostat.SystemMode.Heat if x else Thermostat.SystemMode.Off
        ),
        dp_converter=lambda x: x == Thermostat.SystemMode.Heat,
    )
    # ---- DP 2 (preset) ----
    .tuya_enum(
        dp_id=2,
        attribute_name="preset",
        enum_class=Preset,
        entity_type=EntityType.STANDARD,
        translation_key="thermostat_program_mode",
        fallback_name="Mode",
    )
    # ---- DP 16 (temp_current) -> ZCL local_temperature ----
    .tuya_dp(
        dp_id=16,
        ep_attribute=MoesThermostat.ep_attribute,
        attribute_name=MoesThermostat.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    # ---- DP 18 (lower_temp) - minimum settable temperature ----
    .tuya_number(
        dp_id=18,
        attribute_name="min_temperature_limit",
        type=t.uint16_t,
        min_value=5,
        max_value=15,
        step=1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="min_temperature_limit",
        fallback_name="Minimum temperature limit",
    )
    # ---- DP 28 (factory_reset) - WARNING ----
    .tuya_switch(
        dp_id=28,
        attribute_name="factory_reset",
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="factory_reset",
        fallback_name="Factory reset",
    )
    # ---- DP 32 (sensor_mode) ----
    .tuya_enum(
        dp_id=32,
        attribute_name="sensor_mode",
        enum_class=SensorMode,
        translation_key="sensor_mode",
        fallback_name="Sensor mode",
    )
    # ---- DP 34 (upper_temp) - maximum settable temperature ----
    .tuya_number(
        dp_id=34,
        attribute_name="max_temperature_limit",
        type=t.uint16_t,
        min_value=35,
        max_value=45,
        step=1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="max_temperature_limit",
        fallback_name="Maximum temperature limit",
    )
    # ---- DP 39 (child_lock) ----
    .tuya_switch(
        dp_id=39,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    # ---- DP 47 (valve_state) -> ZCL running_state (0 = heat, 1 = idle) ----
    .tuya_dp(
        dp_id=47,
        ep_attribute=MoesThermostat.ep_attribute,
        attribute_name=MoesThermostat.AttributeDefs.running_state.name,
        converter=lambda x: (
            RunningState.Heat_State_On if x == 0 else RunningState.Idle
        ),
    )
    # ---- DP 48 (backlight) ----
    .tuya_number(
        dp_id=48,
        attribute_name="backlight_brightness",
        type=t.uint8_t,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        translation_key="backlight_brightness",
        fallback_name="Backlight brightness",
    )
    # ---- DP 50 (temp_set) -> ZCL occupied_heating_setpoint ----
    # NOTE: the dp_converter must be given directly to tuya_dp (not inside a
    # DPToAttributeMapping of tuya_dp_multi): TuyaQuirkBuilder ignores
    # per-mapping dp_converters as soon as any builder level dp_converter is
    # set. The setpoint would then be written as 3300 instead of 330.
    .tuya_dp(
        dp_id=50,
        ep_attribute=MoesThermostat.ep_attribute,
        attribute_name=MoesThermostat.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    # ---- DP 101 (temperature calibration) ----
    .tuya_number(
        dp_id=101,
        attribute_name="temperature_calibration",
        type=t.int32s,
        min_value=-10,
        max_value=10,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="temperature_calibration",
        fallback_name="Temperature calibration",
    )
    # ---- DP 109 (floor temperature) ----
    .tuya_sensor(
        dp_id=109,
        attribute_name="floor_temperature",
        type=t.int16s,
        divisor=10,
        unit=UnitOfTemperature.CELSIUS,
        entity_type=EntityType.STANDARD,
        translation_key="floor_temperature",
        fallback_name="Floor temperature",
    )
    # ---- DP 110 (deadzone / hysteresis) ----
    .tuya_number(
        dp_id=110,
        attribute_name="deadzone_temperature",
        type=t.uint16_t,
        min_value=0.5,
        max_value=5,
        step=0.5,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="deadzone_temperature",
        fallback_name="Deadzone temperature",
    )
    # ---- DP 111 (high protect temperature) ----
    .tuya_number(
        dp_id=111,
        attribute_name="high_protect_temperature",
        type=t.uint16_t,
        min_value=10,
        max_value=70,
        step=1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="high_protect_temperature",
        fallback_name="High protect temperature",
    )
    # ---- DP 112 (low protect temperature) ----
    .tuya_number(
        dp_id=112,
        attribute_name="low_protect_temperature",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="low_protect_temperature",
        fallback_name="Low protect temperature",
    )
    # ---- DP 113 (eco temperature) ----
    .tuya_number(
        dp_id=113,
        attribute_name="eco_temperature",
        type=t.uint16_t,
        min_value=10,
        max_value=30,
        step=0.5,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="eco_temperature",
        fallback_name="Eco temperature",
    )
    # ---- DP 114 (screen on time) ----
    .tuya_enum(
        dp_id=114,
        attribute_name="screen_time",
        enum_class=ScreenTime,
        translation_key="screen_time",
        fallback_name="Screen on time",
    )
    # ---- DP 115 (RGB light) ----
    .tuya_switch(
        dp_id=115,
        attribute_name="rgb_light",
        translation_key="rgb_light",
        fallback_name="RGB light",
    )
)

# ---- DP 102 - 108 (weekly program, one datapoint per day) ----
# Format: [day 1-7] + 4 x [hour, minute, temp_hi, temp_lo], temperature x10.
# The sensor shows the program as text, e.g.
#   "06:00 20.0 | 11:30 20.0 | 13:30 20.0 | 17:30 20.0"
# Writing: zha.set_zigbee_cluster_attribute with the program as a hex string,
# e.g. value: "06060000c80b1e00c80d1e00c8111e00c8".
# The thermostat accepts exactly 4 slots per day.
for _day in range(7):
    builder.tuya_dp_attribute(
        dp_id=102 + _day,
        attribute_name=f"week_program_{_day + 1}",
        type=t.CharacterString,
        converter=_decode_program,
        access=(
            foundation.ZCLAttributeAccess.Read
            | foundation.ZCLAttributeAccess.Write
            | foundation.ZCLAttributeAccess.Report
        ),
    )
    builder.sensor(
        attribute_name=f"week_program_{_day + 1}",
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key=f"week_program_{_day + 1}",
        fallback_name=f"Week program {_day + 1}",
    )

(
    builder
    .adds(MoesThermostat)
    .tuya_enchantment(read_attr_spell=True, data_query_spell=True)
    .skip_configuration()
    .add_to_registry(replacement_cluster=MoesTuyaMCUCluster)
)
