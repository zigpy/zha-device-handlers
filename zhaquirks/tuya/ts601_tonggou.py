"""Device handler for Tonggou TO-Q-SA1 Power Meter."""

import logging

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2.homeassistant import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.tuya.builder import TuyaQuirkBuilder

_LOGGER = logging.getLogger(__name__)


class TonggouPowerMeterCluster(CustomCluster):
    """Custom cluster for Tonggou power meter with composite DP 6 data."""

    cluster_id = 0xFC00  # Manufacturer-specific cluster ID
    ep_attribute = "tonggou_power_meter"

    class AttributeDefs(BaseAttributeDefs):
        """Define custom attributes for voltage, current, and power extracted from DP 6."""

        voltage = ZCLAttributeDef(
            id=0x8001,
            type=t.Single,
            access="r",
        )
        current = ZCLAttributeDef(
            id=0x8002,
            type=t.Single,
            access="r",
        )
        power = ZCLAttributeDef(
            id=0x8003,
            type=t.Single,
            access="r",
        )

    def _update_attribute(self, attrid, value):
        """Parse composite voltage/current/power data from DP 6."""
        # When DP 6 sends composite data, parse and extract values
        try:
            # Convert value to bytes (handles LVBytes, bytes, str, etc.)
            if isinstance(value, bytes):
                buf = value
            else:
                buf = bytes(value)

            if len(buf) >= 8:
                # Extract voltage: bytes[0:2] as big-endian, divide by 10
                voltage = ((buf[0] << 8) | buf[1]) / 10
                # Extract current: bytes[3:5] as big-endian, divide by 1000
                current = ((buf[3] << 8) | buf[4]) / 1000
                # Extract power: bytes[6:8] as big-endian
                power = (buf[6] << 8) | buf[7]

                _LOGGER.warning(
                    "DP6 parsed - Voltage: %.1f V, Current: %.3f A, Power: %d W",
                    voltage,
                    current,
                    power,
                )

                # Update our custom attributes
                super()._update_attribute(0x8001, voltage)
                super()._update_attribute(0x8002, current)
                super()._update_attribute(0x8003, power)
                return
        except Exception as e:
            _LOGGER.warning(
                "Failed to parse composite DP 6 data: %s (value type: %s)",
                e,
                type(value).__name__,
            )

        super()._update_attribute(attrid, value)


(
    TuyaQuirkBuilder("_TZE284_pglpvdar", "TS0601")
    .applies_to("_TZE284_4hdbt6rn", "TS0601")
    .replaces(TonggouPowerMeterCluster)
    # Register DP 6 for the custom cluster to handle
    .tuya_dp(
        dp_id=6,
        ep_attribute=TonggouPowerMeterCluster.ep_attribute,
        attribute_name="voltage",
        converter=lambda x: x,  # Raw value, parsing done in cluster's _update_attribute
    )
    # Energy sensor (total forward energy in kWh)
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy",
        type=t.uint32_t,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        divisor=100,
        translation_key="energy",
        fallback_name="Energy",
    )
    # Voltage sensor from composite DP 6
    .sensor(
        attribute_name="voltage",
        cluster_id=TonggouPowerMeterCluster.cluster_id,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        translation_key="voltage",
        fallback_name="Voltage",
    )
    # Current sensor from composite DP 6
    .sensor(
        attribute_name="current",
        cluster_id=TonggouPowerMeterCluster.cluster_id,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricCurrent.AMPERE,
        translation_key="current",
        fallback_name="Current",
    )
    # Power sensor from composite DP 6
    .sensor(
        attribute_name="power",
        cluster_id=TonggouPowerMeterCluster.cluster_id,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.WATT,
        translation_key="power",
        fallback_name="Power",
    )
    # Temperature sensor (DP 131)
    .tuya_sensor(
        dp_id=131,
        attribute_name="temperature",
        type=t.uint16_t,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        divisor=10,
        translation_key="temperature",
        fallback_name="Temperature",
    )
    # AC Frequency sensor
    .tuya_sensor(
        dp_id=32,
        attribute_name="ac_frequency",
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfFrequency.HERTZ,
        divisor=100,
        translation_key="ac_frequency",
        fallback_name="AC frequency",
    )
    # Power factor sensor
    .tuya_sensor(
        dp_id=50,
        attribute_name="power_factor",
        type=t.uint8_t,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="power_factor",
        fallback_name="Power factor",
    )
    .skip_configuration()
    .add_to_registry()
)
