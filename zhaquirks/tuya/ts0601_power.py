"""Tuya Power Meter."""

import asyncio

import zigpy.types as t
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks.builder import (
    PERCENTAGE,
    BinarySensorDeviceClass,
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_QUERY_DATA, TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster


def dp_to_power(data: bytes) -> int:
    """Convert DP data to power value."""
    # From https://github.com/Koenkk/zigbee2mqtt/issues/18603#issuecomment-2277697295
    power = int(data)
    if power > 0x0FFFFFFF:
        power = (0x1999999C - power) * -1
    return power


def multi_dp_to_power(data: bytes) -> int:
    """Convert DP data to power value."""
    # Support negative power readings
    # From https://github.com/Koenkk/zigbee2mqtt/issues/18603#issuecomment-2277697295
    power = data[7] | (data[6] << 8)
    if power > 0x7FFF:
        power = (0x999A - power) * -1
    return power


def multi_dp_to_current(data: bytes) -> int:
    """Convert DP data to current value."""
    return data[4] | (data[3] << 8)


def multi_dp_to_voltage(data: bytes) -> int:
    """Convert DP data to voltage value."""
    return data[1] | (data[0] << 8)


class Tuya3PhaseElectricalMeasurement(ElectricalMeasurement, TuyaLocalCluster):
    """Tuya Electrical Measurement cluster."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
    }


(
    TuyaQuirkBuilder("_TZE200_nslr42tt", "TS0601")
    .tuya_temperature(dp_id=133, scale=10)
    .tuya_sensor(
        dp_id=134,
        attribute_name="device_status",
        type=t.int32s,
        fallback_name="Device status",
        translation_key="device_status",
    )
    .tuya_dp(
        dp_id=132,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="ac_frequency",
    )
    # Energy
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy",
        type=t.int32s,
        divisor=100,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Total energy",
    )
    .tuya_sensor(
        dp_id=101,
        attribute_name="energy_ph_a",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_a",
        fallback_name="Energy phase A",
    )
    .tuya_sensor(
        dp_id=111,
        attribute_name="energy_ph_b",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_b",
        fallback_name="Energy phase B",
    )
    .tuya_sensor(
        dp_id=121,
        attribute_name="energy_ph_c",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_c",
        fallback_name="Energy phase C",
    )
    .tuya_sensor(
        dp_id=9,
        attribute_name="power",
        type=t.int32s,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        fallback_name="Total power",
        converter=dp_to_power,
    )
    .tuya_sensor(
        dp_id=131,
        attribute_name="current",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        unit=UnitOfElectricCurrent.AMPERE,
        fallback_name="Total current",
    )
    .tuya_dp_multi(
        dp_id=6,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="active_power",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_current",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp_multi(
        dp_id=7,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="active_power_ph_b",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage_ph_b",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_current_ph_b",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp_multi(
        dp_id=8,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="active_power_ph_c",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage_ph_c",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_current_ph_c",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp(
        dp_id=102,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor",
    )
    .tuya_dp(
        dp_id=112,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_b",
    )
    .tuya_dp(
        dp_id=122,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_c",
    )
    .adds(Tuya3PhaseElectricalMeasurement)
    .removes(LevelControl.cluster_id)
    .removes(OnOff.cluster_id)
    .skip_configuration()
    .add_to_registry()
)

(
    TuyaQuirkBuilder("_TZE200_dikb3dp6", "TS0601")
    .applies_to("_TZE204_dikb3dp6", "TS0601")
    .applies_to("_TZE284_dikb3dp6", "TS0601")
    .applies_to("_TZE284_wbhaespm", "TS0601")  # reported in #4277
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy",
        type=t.int32s,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Total energy",
    )
    .tuya_sensor(
        dp_id=23,
        attribute_name="energy_produced",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced",
        fallback_name="Energy produced",
    )
    .tuya_dp(
        dp_id=29,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="total_active_power",
    )
    .tuya_dp(
        dp_id=32,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="ac_frequency",
        converter=lambda x: x / 100,
    )
    .tuya_sensor(
        dp_id=50,
        attribute_name="power_factor",
        type=t.uint8_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER_FACTOR,
        unit=PERCENTAGE,
        translation_key="total_power_factor",
        fallback_name="Total power factor",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="update_frequency",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=5,
        max_value=3600,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="update_frequency",
        fallback_name="Update frequency",
    )
    # Phase A
    .tuya_dp(
        dp_id=103,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage",
    )
    .tuya_dp(
        dp_id=104,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_current",
    )
    .tuya_dp(
        dp_id=105,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="active_power",
    )
    .tuya_dp(
        dp_id=108,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor",
    )
    .tuya_sensor(
        dp_id=109,
        attribute_name="energy_consumed_ph_a",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_a",
        fallback_name="Energy phase A",
    )
    .tuya_sensor(
        dp_id=110,
        attribute_name="energy_produced_ph_a",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced_ph_a",
        fallback_name="Energy produced phase A",
    )
    # Phase B
    .tuya_dp(
        dp_id=112,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage_ph_b",
    )
    .tuya_dp(
        dp_id=113,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_current_ph_b",
    )
    .tuya_dp(
        dp_id=114,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="active_power_ph_b",
    )
    .tuya_dp(
        dp_id=117,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_b",
    )
    .tuya_sensor(
        dp_id=118,
        attribute_name="energy_consumed_ph_b",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_b",
        fallback_name="Energy phase B",
    )
    .tuya_sensor(
        dp_id=119,
        attribute_name="energy_produced_ph_b",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced_ph_b",
        fallback_name="Energy produced phase B",
    )
    # Phase C
    .tuya_dp(
        dp_id=121,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage_ph_c",
    )
    .tuya_dp(
        dp_id=122,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_current_ph_c",
    )
    .tuya_dp(
        dp_id=123,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="active_power_ph_c",
    )
    .tuya_dp(
        dp_id=126,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_c",
    )
    .tuya_sensor(
        dp_id=127,
        attribute_name="energy_consumed_ph_c",
        divisor=100,
        type=t.uint32_t,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_c",
        fallback_name="Energy phase C",
    )
    .tuya_sensor(
        dp_id=128,
        attribute_name="energy_produced_ph_c",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced_ph_c",
        fallback_name="Energy produced phase C",
    )
    .adds(Tuya3PhaseElectricalMeasurement)
    .skip_configuration()
    .add_to_registry()
)

(
    TuyaQuirkBuilder("_TZE284_a14rjslz", "TS0601")
    # Metering
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy_consumed",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Energy",
    )
    .tuya_sensor(
        dp_id=23,
        attribute_name="energy_produced",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced",
        fallback_name="Energy produced",
    )
    # ElectricalMeasurement
    .tuya_dp(
        dp_id=29,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="total_active_power",
    )
    .tuya_dp(
        dp_id=30,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="total_reactive_power",
    )
    .tuya_dp_multi(
        dp_id=6,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="active_power",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_current",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp_multi(
        dp_id=7,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="active_power_ph_b",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage_ph_b",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_current_ph_b",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp_multi(
        dp_id=8,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="active_power_ph_c",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage_ph_c",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_current_ph_c",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp(
        dp_id=50,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor",
    )
    .adds(Tuya3PhaseElectricalMeasurement)
    .skip_configuration()
    .add_to_registry()
)


# Moes ZM6LT1 single-phase energy meter with CT clamp.
# DP 6 packs phase data into an 18 byte buffer (confirmed from device capture):
#   [0:2]   constant header
#   [2:4]   voltage, V * 10 (16-bit)
#   [4:7]   current, mA (24-bit)
#   [7:10]  active power, W (24-bit)
#   [10:13] reactive power, var (24-bit)
#   [13:16] apparent power, VA (24-bit)
#   [16]    power factor, %
#   [17]    padding
def zm6lt1_dp6_to_voltage(data: bytes) -> int:
    """Extract voltage (V * 10) from the packed phase datapoint."""
    return (data[2] << 8) | data[3]


def zm6lt1_dp6_to_current(data: bytes) -> int:
    """Extract current (mA, 24-bit) from the packed phase datapoint."""
    return (data[4] << 16) | (data[5] << 8) | data[6]


def zm6lt1_dp6_to_power(data: bytes) -> int:
    """Extract active power (W, 24-bit) from the packed phase datapoint."""
    return (data[7] << 16) | (data[8] << 8) | data[9]


def zm6lt1_dp6_to_reactive_power(data: bytes) -> int:
    """Extract reactive power (var, 24-bit) from the packed phase datapoint."""
    return (data[10] << 16) | (data[11] << 8) | data[12]


def zm6lt1_dp6_to_apparent_power(data: bytes) -> int:
    """Extract apparent power (VA, 24-bit) from the packed phase datapoint."""
    return (data[13] << 16) | (data[14] << 8) | data[15]


def zm6lt1_dp6_to_power_factor(data: bytes) -> int:
    """Extract power factor (%) from the packed phase datapoint."""
    return data[16]


class ZM6LT1ElectricalMeasurement(ElectricalMeasurement, TuyaLocalCluster):
    """Electrical measurement cluster fed by Tuya datapoints."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_frequency_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 100,
    }


class ZM6LT1ManufCluster(TuyaMCUCluster):
    """Tuya MCU cluster that periodically queries the meter for datapoints.

    The ZM6LT1 does not report DP 6 (voltage/current/power) on its own, so a
    Tuya data-query command is sent every 60 seconds, matching the polling
    interval Zigbee2MQTT uses for this device.
    """

    POLL_INTERVAL = 60

    # one poller per device, survives cluster re-instantiation
    _pollers: dict[t.EUI64, asyncio.Task] = {}

    def __init__(self, *args, **kwargs):
        """Init and start the polling task."""
        super().__init__(*args, **kwargs)
        self._poll_task = None
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return  # no event loop (e.g. import-time tooling); skip polling

        ieee = self.endpoint.device.ieee
        prev = ZM6LT1ManufCluster._pollers.pop(ieee, None)
        if prev is not None and not prev.done():
            prev.cancel()
        self._poll_task = self.create_catching_task(self._poll_loop())
        ZM6LT1ManufCluster._pollers[ieee] = self._poll_task

    async def _poll_loop(self):
        while True:
            await asyncio.sleep(self.POLL_INTERVAL)
            try:
                # fire-and-forget: the meter answers with DP reports
                await self.command(TUYA_QUERY_DATA, expect_reply=False)
            except asyncio.CancelledError:
                raise
            except Exception as ex:  # noqa: BLE001 - keep polling on failure
                self.debug("ZM6LT1 data query failed: %r", ex)


(
    TuyaQuirkBuilder("_TZE284_2fnssffc", "TS0601")  # Moes ZM6LT1
    .tuya_enchantment(read_attr_spell=True, data_query_spell=True)
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Total energy",
    )
    .tuya_sensor(
        dp_id=2,
        attribute_name="reverse_energy",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="reverse_energy",
        fallback_name="Total reverse energy",
    )
    .tuya_dp_multi(
        dp_id=6,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=ZM6LT1ElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage",
                converter=zm6lt1_dp6_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=ZM6LT1ElectricalMeasurement.ep_attribute,
                attribute_name="rms_current",
                converter=zm6lt1_dp6_to_current,
            ),
            DPToAttributeMapping(
                ep_attribute=ZM6LT1ElectricalMeasurement.ep_attribute,
                attribute_name="active_power",
                converter=zm6lt1_dp6_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=ZM6LT1ElectricalMeasurement.ep_attribute,
                attribute_name="reactive_power",
                converter=zm6lt1_dp6_to_reactive_power,
            ),
            DPToAttributeMapping(
                ep_attribute=ZM6LT1ElectricalMeasurement.ep_attribute,
                attribute_name="apparent_power",
                converter=zm6lt1_dp6_to_apparent_power,
            ),
            DPToAttributeMapping(
                ep_attribute=ZM6LT1ElectricalMeasurement.ep_attribute,
                attribute_name="power_factor",
                converter=zm6lt1_dp6_to_power_factor,
            ),
        ],
    )
    .tuya_sensor(
        dp_id=10,
        attribute_name="fault",
        type=t.uint32_t,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="fault",
        fallback_name="Fault",
    )
    .tuya_switch(
        dp_id=20,
        attribute_name="clear_event",
        entity_type=EntityType.CONFIG,
        translation_key="clear_event",
        fallback_name="Clear event",
    )
    .tuya_binary_sensor(
        dp_id=44,
        attribute_name="online_state",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="online_state",
        fallback_name="Online state",
    )
    .tuya_dp(
        dp_id=49,
        ep_attribute=ZM6LT1ElectricalMeasurement.ep_attribute,
        attribute_name="ac_frequency",
    )
    .tuya_sensor(
        dp_id=51,
        attribute_name="active_energy",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="active_energy",
        fallback_name="Total active energy",
    )
    .tuya_number(
        dp_id=101,
        attribute_name="countdown_1",
        type=t.uint16_t,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=2000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="countdown",
        fallback_name="Countdown",
    )
    .tuya_switch(
        dp_id=104,
        attribute_name="device_restart",
        entity_type=EntityType.CONFIG,
        translation_key="device_restart",
        fallback_name="Device restart",
    )
    .adds(ZM6LT1ElectricalMeasurement)
    .skip_configuration()
    .add_to_registry(replacement_cluster=ZM6LT1ManufCluster)
)
