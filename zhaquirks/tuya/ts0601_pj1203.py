"""Tuya PJ-1203 Single Channel Clamp Energy Meter.

This quirk supports the Tuya PJ-1203 single channel clamp power meter.
The device reports voltage, current, power, and total energy. Apparent power
and power factor are calculated from these values.

Energy tracking: The device's native energy counter (DP 101) resets on reconnects.
This quirk provides an additional calculated energy value that integrates power
over time, providing a more reliable cumulative energy measurement.

Reset handling: The metering cluster tracks device counter resets and maintains
a cumulative offset. On quirk reload/restart, it attempts to restore the offset
from ZHA's attribute cache to maintain continuity.

Manufacturer IDs: _TZE204_cjbofhxw, _TZE284_cjbofhxw
Model: TS0601

Datapoints:
- DP 18: Current (mA)
- DP 19: Power (W * 10)
- DP 20: Voltage (V * 10)
- DP 101: Total Energy (Wh)
"""

import datetime
import logging
import time

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import NoManufacturerCluster, TuyaLocalCluster
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster

_LOGGER = logging.getLogger(__name__)


class TuyaElectricalMeasurementPJ1203(TuyaLocalCluster, ElectricalMeasurement):
    """ElectricalMeasurement cluster for PJ-1203 with calculated apparent power and power factor.

    Also integrates power over time to calculate cumulative energy consumption.
    """

    cluster_id = ElectricalMeasurement.cluster_id

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
        ElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
    }

    # Maximum gap between power readings to consider for integration (seconds)
    # If gap is larger, we skip integration to avoid counting offline time
    MAX_INTEGRATION_GAP = 300  # 5 minutes

    def __init__(self, *args, **kwargs):
        """Initialize the cluster with energy integration state."""
        super().__init__(*args, **kwargs)
        self._last_power_time: float | None = None
        self._last_power_value: int | None = None
        self._integrated_energy_wh: float = 0.0

    def _update_attribute(self, attrid, value):
        """Update attribute and calculate derived values."""
        super()._update_attribute(attrid, value)

        # Get current cached values
        rms_voltage = self._attr_cache.get(self.AttributeDefs.rms_voltage.id)
        rms_current = self._attr_cache.get(self.AttributeDefs.rms_current.id)
        active_power = self._attr_cache.get(self.AttributeDefs.active_power.id)

        # Calculate apparent power and power factor when we have the necessary values
        if rms_voltage is not None and rms_current is not None:
            # Calculate apparent power: V * A
            # voltage is in dV (tenths), current is in mA
            # Result in VA (same scale as active_power in W)
            apparent_power = round((rms_voltage * rms_current) / 10000)
            super()._update_attribute(
                self.AttributeDefs.apparent_power.id, apparent_power
            )

            # Calculate power factor if we have active power and apparent power
            if active_power is not None and apparent_power > 0:
                # Power factor as percentage (0-100)
                power_factor = round((abs(active_power) * 100) / apparent_power)
                power_factor = min(power_factor, 100)
                super()._update_attribute(
                    self.AttributeDefs.power_factor.id, power_factor
                )
            elif apparent_power == 0:
                # No apparent power means power factor is undefined, set to 0
                super()._update_attribute(self.AttributeDefs.power_factor.id, 0)

        # Integrate power over time when active_power is updated
        if attrid == self.AttributeDefs.active_power.id and value is not None:
            self._integrate_power(value)

    def _integrate_power(self, power_watts: int) -> None:
        """Integrate power over time to calculate energy consumption.

        Uses trapezoidal integration for better accuracy: takes average of
        previous and current power readings multiplied by time delta.

        Args:
            power_watts: Current power reading in watts

        """
        current_time = time.monotonic()

        if self._last_power_time is not None and self._last_power_value is not None:
            time_delta = current_time - self._last_power_time

            # Only integrate if the gap is reasonable
            if 0 < time_delta <= self.MAX_INTEGRATION_GAP:
                # Trapezoidal integration: average power * time
                avg_power = (self._last_power_value + power_watts) / 2
                # Convert: W * seconds -> Wh (divide by 3600)
                energy_wh = (avg_power * time_delta) / 3600
                self._integrated_energy_wh += energy_wh

                # Update the metering cluster with integrated energy (in Wh)
                metering = self.endpoint.smartenergy_metering
                if hasattr(metering, "update_integrated_energy"):
                    metering.update_integrated_energy(round(self._integrated_energy_wh))

        self._last_power_time = current_time
        self._last_power_value = power_watts

    def get_integrated_energy_wh(self) -> float:
        """Return the current integrated energy value in Wh."""
        return self._integrated_energy_wh

    def reset_integrated_energy(self) -> None:
        """Reset the integrated energy counter."""
        self._integrated_energy_wh = 0.0
        self._last_power_time = None
        self._last_power_value = None

    async def read_attributes(
        self, attributes, allow_cache=False, only_cache=False, manufacturer=None
    ):
        """Read attributes ZCL foundation command.

        Returns (success_dict, failure_dict) matching the zigpy Cluster API.
        """
        success = {}
        failure = {}
        for attr in attributes:
            if isinstance(attr, str):
                attr_id = self.attributes_by_name[attr].id
            else:
                attr_id = attr

            # Check constant attributes first
            if attr_id in self._CONSTANT_ATTRIBUTES:
                success[attr_id] = self._CONSTANT_ATTRIBUTES[attr_id]
            elif attr_id in self._attr_cache:
                success[attr_id] = self._attr_cache[attr_id]
            else:
                failure[attr_id] = foundation.Status.UNSUPPORTED_ATTRIBUTE

        return (success, failure)


class TuyaMeteringPJ1203(TuyaLocalCluster, Metering):
    """Metering cluster for PJ-1203 to report total energy consumption.

    This cluster tracks energy in two ways:
    1. Device's native counter (DP 101) - resets on reconnects
    2. Integrated energy from power readings - more reliable cumulative value

    When the device's counter resets (value decreases), we compensate by
    tracking the offset to maintain a continuous cumulative reading.
    """

    cluster_id = Metering.cluster_id

    POWER_WATT = 0x0000

    # Mark instantaneous_demand as unsupported since this device only reports total energy
    set_unsupported_attributes = {Metering.AttributeDefs.instantaneous_demand.id}

    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.unit_of_measure.id: POWER_WATT,
        Metering.AttributeDefs.multiplier.id: 1,
        Metering.AttributeDefs.divisor.id: 1000,  # Device reports in Wh, convert to kWh
        Metering.AttributeDefs.summation_formatting.id: 0b0_0100_011,  # 4 digits after decimal
    }

    def __init__(self, *args, **kwargs):
        """Initialize the cluster with energy tracking state."""
        super().__init__(*args, **kwargs)
        self._last_device_energy: int | None = None
        self._energy_offset: int = 0  # Offset to add when device counter resets
        self._integrated_energy_wh: int = 0
        self._initialized_from_cache: bool = False  # Track if we've restored from cache

    def _update_attribute(self, attrid, value):
        """Update attribute and handle device energy counter resets.

        On first update after initialization, attempts to restore the energy
        offset from ZHA's attribute cache to maintain continuity across
        quirk reloads/restarts.
        """
        if attrid == Metering.AttributeDefs.current_summ_delivered.id:
            # On first update, try to restore offset from cached value
            if not self._initialized_from_cache:
                self._initialized_from_cache = True
                cached_value = self._attr_cache.get(attrid)
                if cached_value is not None and value < cached_value:
                    # Device value is lower than cached - restore offset to maintain continuity
                    self._energy_offset = cached_value
                    _LOGGER.debug(
                        "PJ1203: Restored energy offset from cache. "
                        "Cached: %s Wh, Device: %s Wh, Offset set to: %s Wh",
                        cached_value,
                        value,
                        self._energy_offset,
                    )
                elif cached_value is not None:
                    _LOGGER.debug(
                        "PJ1203: Cache value (%s Wh) <= device value (%s Wh), "
                        "no offset restoration needed",
                        cached_value,
                        value,
                    )
                else:
                    _LOGGER.debug(
                        "PJ1203: No cached value available for offset restoration"
                    )

            # Track device energy and detect resets during normal operation
            if (
                self._last_device_energy is not None
                and value < self._last_device_energy
            ):
                # Device counter reset detected - add previous value to offset
                self._energy_offset += self._last_device_energy
                _LOGGER.debug(
                    "PJ1203: Device counter reset detected. "
                    "Previous: %s Wh, New: %s Wh, Offset now: %s Wh",
                    self._last_device_energy,
                    value,
                    self._energy_offset,
                )

            self._last_device_energy = value

            # Report the compensated value (device value + offset)
            compensated_value = value + self._energy_offset
            super()._update_attribute(attrid, compensated_value)
        else:
            super()._update_attribute(attrid, value)

    def update_integrated_energy(self, energy_wh: int) -> None:
        """Update the integrated energy value from power readings.

        This provides an alternative energy measurement that doesn't rely
        on the device's resetting counter.

        Args:
            energy_wh: Integrated energy in Wh

        """
        self._integrated_energy_wh = energy_wh

    def get_integrated_energy_wh(self) -> int:
        """Return the integrated energy value in Wh."""
        return self._integrated_energy_wh

    def get_compensated_energy_wh(self) -> int:
        """Return the compensated device energy (with reset handling) in Wh."""
        if self._last_device_energy is not None:
            return self._last_device_energy + self._energy_offset
        return self._energy_offset

    async def read_attributes(
        self, attributes, allow_cache=False, only_cache=False, manufacturer=None
    ):
        """Read attributes ZCL foundation command.

        Returns (success_dict, failure_dict) matching the zigpy Cluster API.
        """
        success = {}
        failure = {}
        for attr in attributes:
            if isinstance(attr, str):
                attr_id = self.attributes_by_name[attr].id
            else:
                attr_id = attr

            # Check constant attributes first
            if attr_id in self._CONSTANT_ATTRIBUTES:
                success[attr_id] = self._CONSTANT_ATTRIBUTES[attr_id]
            elif attr_id in self._attr_cache:
                success[attr_id] = self._attr_cache[attr_id]
            else:
                failure[attr_id] = foundation.Status.UNSUPPORTED_ATTRIBUTE

        return (success, failure)


class TuyaPJ1203ManufCluster(NoManufacturerCluster, TuyaMCUCluster):
    """Manufacturer cluster for PJ-1203 single channel energy meter."""

    set_time_offset = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        18: DPToAttributeMapping(
            TuyaElectricalMeasurementPJ1203.ep_attribute,
            "rms_current",
        ),
        19: DPToAttributeMapping(
            TuyaElectricalMeasurementPJ1203.ep_attribute,
            "active_power",
            converter=lambda x: x // 10,
        ),
        20: DPToAttributeMapping(
            TuyaElectricalMeasurementPJ1203.ep_attribute,
            "rms_voltage",
        ),
        101: DPToAttributeMapping(
            TuyaMeteringPJ1203.ep_attribute,
            "current_summ_delivered",
        ),
    }

    data_point_handlers = {
        18: "_dp_2_attr_update",
        19: "_dp_2_attr_update",
        20: "_dp_2_attr_update",
        101: "_dp_2_attr_update",
    }


class TuyaPJ1203PowerMeter(CustomDevice):
    """Tuya PJ-1203 single channel clamp energy meter."""

    signature = {
        MODELS_INFO: [
            ("_TZE204_cjbofhxw", "TS0601"),
            ("_TZE284_cjbofhxw", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    TuyaMCUCluster.cluster_id,  # 0xef00
                    0xED00,  # 60672
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaPJ1203ManufCluster,
                    TuyaElectricalMeasurementPJ1203,
                    TuyaMeteringPJ1203,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
