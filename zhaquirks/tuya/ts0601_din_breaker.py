"""Tuya TS0601 _TZE204_fhvdgeuh DIN-rail breaker with power monitoring.

Zigbee2MQTT model TS0601_din_4 (Tuya "Din rail switch with power monitoring and
threshold settings"). Datapoints taken from zigbee-herdsman-converters (tuya.ts,
TS0601_din_4 and the RMDZB-1PNL63 threshold layout) and from
zigpy/zha-device-handlers issues #3140 / #3850.

DP map
  1   energy            kWh / 100                      (sensor energy)
  6   phase A raw       V(2 bytes)/10, A(3 bytes)/1000, W(3 bytes) (voltage/current/active_power)
  9   faults bitmap                                    (sensor fault, text)
  15  leakage current   mA                             (sensor leakage_current)
  16  relay             bool                           (switch, OnOff cluster)
  17  alarm set 1 raw   [type, enable, hi, lo] * n, type 4 = leakage (mA), 5 = high temperature (C)
  18  alarm set 2 raw   type 1 = over current (0.1 A), 3 = over voltage (V), 4 = under voltage (V)
  102 reclosing allowed times                          (number reclosing_allowed_times)
  103 temperature       C                              (sensor temperature)
  104 reclosing enable  bool                           (switch reclosing_enable)
  105 countdown timer   s                              (number timer, disabled by default)
  107 reclose recover   s                              (number reclose_recover_seconds)
  127 status            0 standby / 1 active           (sensor status, text)
  134 power-on state    0 off / 1 on / 2 last state    (select relay_status_for_power_on)
"""

from __future__ import annotations

from typing import Any

import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.tuya import PowerOnState, TuyaDatapointData
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster

TUYA_CLUSTER_ID = TuyaMCUCluster.cluster_id
MCU = TuyaMCUCluster.ep_attribute

DP_ENERGY = 1
DP_PHASE_A = 6
DP_FAULTS = 9
DP_LEAKAGE = 15
DP_RELAY = 16
DP_ALARM_SET_1 = 17
DP_ALARM_SET_2 = 18
DP_RECLOSING_TRIES = 102
DP_TEMPERATURE = 103
DP_RECLOSING_ENABLE = 104
DP_TIMER = 105
DP_RECLOSE_RECOVER = 107
DP_STATUS = 127
DP_POWER_ON_STATE = 134

# Threshold entries: dp -> ordered list of (type id, threshold attribute, breaker attribute).
# The order defines the position of every 4-byte entry in the raw payload.
THRESHOLDS: dict[int, list[tuple[int, str, str]]] = {
    DP_ALARM_SET_1: [
        (4, "leakage_threshold", "leakage_breaker"),
        (5, "high_temperature_threshold", "high_temperature_breaker"),
    ],
    DP_ALARM_SET_2: [
        (1, "over_current_threshold", "over_current_breaker"),
        (3, "over_voltage_threshold", "over_voltage_breaker"),
        (4, "under_voltage_threshold", "under_voltage_breaker"),
    ],
}

# Zigbee2MQTT circuitBreakerFaultList, bit 0 first.
FAULT_NAMES = [
    "short_circuit",
    "surge",
    "overload",
    "leakage_current",
    "temperature",
    "fire",
    "high_power",
    "self_test",
    "over_current",
    "unbalance",
    "over_voltage",
    "under_voltage",
    "power_loss",
    "magnetism",
    "low_voltage",
    "delay_fault",
]

NEGATIVE_POWER_OFFSET = 0x99999A
NEGATIVE_POWER_THRESHOLD = 0x800000
TWOS_COMPLEMENT_MODULUS = 0x1000000


def _raw(data: Any) -> bytes:
    """Return the raw bytes of a datapoint payload."""
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    return bytes(data.serialize()) if hasattr(data, "serialize") else bytes(data)


def phase_voltage(data: Any) -> int:
    """Phase A voltage in 0.1 V."""
    b = _raw(data)
    return (b[0] << 8) | b[1] if len(b) >= 2 else 0


def phase_current(data: Any) -> int:
    """Phase A current in mA (3 bytes, see z2m phaseVariant2WithPhase)."""
    b = _raw(data)
    if len(b) >= 8:
        return (b[2] << 16) | (b[3] << 8) | b[4]
    if len(b) >= 5:
        return (b[3] << 8) | b[4]
    return 0


def phase_power(data: Any) -> int:
    """Phase A active power in W (3 bytes, negative values as in z2m)."""
    b = _raw(data)
    if len(b) >= 8:
        power = (b[5] << 16) | (b[6] << 8) | b[7]
    elif len(b) >= 7:
        return (b[5] << 8) | b[6]
    else:
        return 0
    if power >= NEGATIVE_POWER_THRESHOLD:
        if power <= NEGATIVE_POWER_OFFSET:
            power = power - NEGATIVE_POWER_OFFSET
        else:
            power = power - TWOS_COMPLEMENT_MODULUS
    return power


def faults_bitmap(value: Any) -> int:
    """Normalize the DP 9 bitmap to an int.

    Tuya sends bitmaps big-endian while zhaquirks deserializes the BITMAP payload
    little-endian, so multi-byte values arrive byte-swapped and are swapped back here.
    """
    width = {t.bitmap8: 1, t.bitmap16: 2, t.bitmap32: 4}.get(type(value))
    if width:
        return int.from_bytes(int(value).to_bytes(width, "little"), "big")
    try:
        return int(value)
    except (TypeError, ValueError):
        raw = _raw(value)
        return int.from_bytes(raw, "big") if raw else 0


def _to_int(value: Any) -> int | None:
    """Best-effort int conversion; None for text that is not a number.

    The zigpy attribute cache may still hold values written by an older quirk version
    (e.g. the text "active"), and an exception here would abort the whole ZHA start-up.
    """
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        return int.from_bytes(bytes(value), "big") if value else 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def faults_to_text(value: Any) -> str:
    """Convert the (normalized) fault bitmap to a readable text (ZHA side, also for cached values)."""
    bits = _to_int(value)
    if bits is None:
        return str(value)  # already text (cached by a previous quirk version)
    names = [name for i, name in enumerate(FAULT_NAMES) if bits & (1 << i)]
    extra = bits >> len(FAULT_NAMES)
    if extra:
        names.append(f"unknown_0x{extra:x}")
    return ", ".join(names) if names else "ok"


def status_to_text(value: Any) -> str:
    """DP 127: 0 standby, 1 active (text values from an older cache are passed through)."""
    v = _to_int(value)
    if v is None:
        return str(value)
    return {0: "standby", 1: "active"}.get(v, f"unknown_{v}")


def _encode_thresholds(dp: int, *values: Any) -> t.Bytes:
    """Build the raw payload for an alarm-set DP from (threshold, breaker) pairs."""
    payload = bytearray()
    specs = THRESHOLDS[dp]
    for i, (type_id, _thr, _brk) in enumerate(specs):
        threshold = values[2 * i] if 2 * i < len(values) else None
        breaker = values[2 * i + 1] if 2 * i + 1 < len(values) else None
        if threshold is None or breaker is None:
            payload += bytes(4)  # unknown entry: type 0, ignored by the device
            continue
        threshold = max(0, min(0xFFFF, int(threshold)))
        payload += bytes([type_id, 1 if breaker else 0]) + threshold.to_bytes(2, "big")
    return t.Bytes(bytes(payload))


def encode_alarm_set_1(*values: Any) -> t.Bytes:
    """DP 17 attribute -> raw converter (args in THRESHOLDS order)."""
    return _encode_thresholds(DP_ALARM_SET_1, *values)


def encode_alarm_set_2(*values: Any) -> t.Bytes:
    """DP 18 attribute -> raw converter (args in THRESHOLDS order)."""
    return _encode_thresholds(DP_ALARM_SET_2, *values)


class SmartMeterManufCluster(TuyaMCUCluster):
    """Tuya MCU cluster with a raw handler for the alarm-set datapoints."""

    def _threshold_dp_update(self, datapoint: TuyaDatapointData) -> None:
        """Parse [type, enable, hi, lo] entries and update only the present ones."""
        raw = _raw(datapoint.data.payload)
        specs = {type_id: (thr, brk) for type_id, thr, brk in THRESHOLDS[datapoint.dp]}
        for i in range(0, len(raw) - 3, 4):
            type_id = raw[i]
            if type_id not in specs:
                continue
            thr_attr, brk_attr = specs[type_id]
            self.update_attribute(brk_attr, bool(raw[i + 1]))
            self.update_attribute(thr_attr, (raw[i + 2] << 8) | raw[i + 3])


_RW = foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write
_RO = foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report

builder = (
    TuyaQuirkBuilder("_TZE204_fhvdgeuh", "TS0601")
    .tuya_enchantment(read_attr_spell=True, data_query_spell=True)
    # relay
    .tuya_onoff(dp_id=DP_RELAY)
    # total energy
    .tuya_sensor(
        dp_id=DP_ENERGY,
        attribute_name="energy",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Energy",
    )
    # phase A: voltage / current / power packed in one raw DP
    .tuya_attribute(dp_id=0xA0, attribute_name="voltage", type=t.uint16_t, access=_RO)
    .tuya_attribute(dp_id=0xA1, attribute_name="current", type=t.uint32_t, access=_RO)
    .tuya_attribute(
        dp_id=0xA2, attribute_name="active_power", type=t.int32s, access=_RO
    )
    .tuya_dp_multi(
        dp_id=DP_PHASE_A,
        attribute_mapping=[
            DPToAttributeMapping(MCU, "voltage", converter=phase_voltage),
            DPToAttributeMapping(MCU, "current", converter=phase_current),
            DPToAttributeMapping(MCU, "active_power", converter=phase_power),
        ],
    )
    .sensor(
        attribute_name="voltage",
        cluster_id=TUYA_CLUSTER_ID,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        unit=UnitOfElectricPotential.VOLT,
        fallback_name="Voltage",
    )
    .sensor(
        attribute_name="current",
        cluster_id=TUYA_CLUSTER_ID,
        divisor=1000,
        suggested_display_precision=3,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        unit=UnitOfElectricCurrent.AMPERE,
        fallback_name="Current",
    )
    .sensor(
        attribute_name="active_power",
        cluster_id=TUYA_CLUSTER_ID,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        fallback_name="Power",
    )
    # faults / status: raw ints stored in the attribute (survive the zigpy attribute cache),
    # converted to text on the ZHA side
    .tuya_dp_attribute(
        dp_id=DP_FAULTS,
        attribute_name="fault",
        type=t.uint32_t,
        converter=faults_bitmap,
        access=_RO,
    )
    .sensor(
        attribute_name="fault",
        cluster_id=TUYA_CLUSTER_ID,
        attribute_converter=faults_to_text,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="fault",
        fallback_name="Fault",
    )
    .tuya_dp_attribute(
        dp_id=DP_STATUS,
        attribute_name="status",
        type=t.uint8_t,
        converter=int,
        access=_RO,
    )
    .sensor(
        attribute_name="status",
        cluster_id=TUYA_CLUSTER_ID,
        attribute_converter=status_to_text,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="status",
        fallback_name="Status",
    )
    # temperature / leakage
    .tuya_sensor(
        dp_id=DP_TEMPERATURE,
        attribute_name="temperature",
        type=t.int16s,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Temperature",
    )
    .tuya_sensor(
        dp_id=DP_LEAKAGE,
        attribute_name="leakage_current",
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        unit=UnitOfElectricCurrent.MILLIAMPERE,
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Leakage",
    )
    # auto reclosing
    .tuya_number(
        dp_id=DP_RECLOSING_TRIES,
        attribute_name="reclosing_allowed_times",
        type=t.uint8_t,
        min_value=0,
        max_value=30,
        step=1,
        translation_key="reclosing_allowed_times",
        fallback_name="Reclosing tries",
    )
    .tuya_switch(
        dp_id=DP_RECLOSING_ENABLE,
        attribute_name="reclosing_enable",
        translation_key="reclosing_enable",
        fallback_name="Reclosing enable",
    )
    .tuya_number(
        dp_id=DP_RECLOSE_RECOVER,
        attribute_name="reclose_recover_seconds",
        type=t.uint16_t,
        min_value=0,
        max_value=600,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="reclose_recover_seconds",
        fallback_name="Reclose recover",
    )
    # countdown timer (writing it switches the relay after N seconds) - off by default
    .tuya_number(
        dp_id=DP_TIMER,
        attribute_name="timer",
        type=t.uint32_t,
        min_value=0,
        max_value=86400,
        step=1,
        unit=UnitOfTime.SECONDS,
        initially_disabled=True,
        translation_key="timer",
        fallback_name="Timer",
    )
    # power-on behaviour
    .tuya_enum(
        dp_id=DP_POWER_ON_STATE,
        attribute_name="relay_status_for_power_on",
        enum_class=PowerOnState,
        translation_key="relay_status_for_power_on",
        fallback_name="Power on state",
    )
)

# Protection thresholds: several attributes share one raw DP, so the attributes are declared
# with pseudo datapoint ids (only the ZCL attribute id is derived from it) and the real DP is
# mapped once with a custom raw handler and an attributes -> raw converter.
_THRESHOLD_META = {
    "leakage_threshold": {
        "min_value": 10,
        "max_value": 100,
        "unit": UnitOfElectricCurrent.MILLIAMPERE,
        "name": "Leakage threshold",
    },
    "high_temperature_threshold": {
        "min_value": 40,
        "max_value": 100,
        "unit": UnitOfTemperature.CELSIUS,
        "name": "High temperature threshold",
    },
    "over_current_threshold": {
        "min_value": 1,
        "max_value": 63,
        "step": 0.1,
        "multiplier": 0.1,
        "unit": UnitOfElectricCurrent.AMPERE,
        "name": "Over current threshold",
    },
    "over_voltage_threshold": {
        "min_value": 250,
        "max_value": 300,
        "unit": UnitOfElectricPotential.VOLT,
        "name": "Over voltage threshold",
    },
    "under_voltage_threshold": {
        "min_value": 150,
        "max_value": 200,
        "unit": UnitOfElectricPotential.VOLT,
        "name": "Under voltage threshold",
    },
}
_BREAKER_NAMES = {
    "leakage_breaker": "Leakage breaker",
    "high_temperature_breaker": "High temperature breaker",
    "over_current_breaker": "Over current breaker",
    "over_voltage_breaker": "Over voltage breaker",
    "under_voltage_breaker": "Under voltage breaker",
}

_pseudo_dp = 0xB0
for _dp, _specs in THRESHOLDS.items():
    _mappings: list[DPToAttributeMapping] = []
    for _type_id, _thr, _brk in _specs:
        meta = _THRESHOLD_META[_thr]
        builder.tuya_attribute(
            dp_id=_pseudo_dp, attribute_name=_thr, type=t.uint16_t, access=_RW
        )
        _pseudo_dp += 1
        builder.tuya_attribute(
            dp_id=_pseudo_dp, attribute_name=_brk, type=t.Bool, access=_RW
        )
        _pseudo_dp += 1
        builder.number(
            attribute_name=_thr,
            cluster_id=TUYA_CLUSTER_ID,
            min_value=meta["min_value"],
            max_value=meta["max_value"],
            step=meta.get("step", 1),
            multiplier=meta.get("multiplier"),
            unit=meta["unit"],
            entity_type=EntityType.CONFIG,
            translation_key=_thr,
            fallback_name=meta["name"],
        )
        builder.switch(
            attribute_name=_brk,
            cluster_id=TUYA_CLUSTER_ID,
            entity_type=EntityType.CONFIG,
            translation_key=_brk,
            fallback_name=_BREAKER_NAMES[_brk],
        )
        _mappings.append(DPToAttributeMapping(MCU, _thr))
        _mappings.append(DPToAttributeMapping(MCU, _brk))
    builder.tuya_dp_multi(
        dp_id=_dp,
        attribute_mapping=_mappings,
        dp_handler="_threshold_dp_update",
        dp_converter=encode_alarm_set_1
        if _dp == DP_ALARM_SET_1
        else encode_alarm_set_2,
    )

builder.skip_configuration().add_to_registry(replacement_cluster=SmartMeterManufCluster)
