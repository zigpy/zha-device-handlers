"""Tuya PJ-1203 Single Channel Clamp Energy Meter.

This quirk supports the Tuya PJ-1203 single channel clamp power meter.
The device reports voltage, current, and power. Apparent power and power
factor are calculated from these values.

Manufacturer IDs: _TZE204_cjbofhxw, _TZE284_cjbofhxw
Model: TS0601

Datapoints:
- DP 18: Current (mA)
- DP 19: Power (W * 10)
- DP 20: Voltage (V * 10)
"""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

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


class TuyaElectricalMeasurementPJ1203(TuyaLocalCluster, ElectricalMeasurement):
    """ElectricalMeasurement cluster for PJ-1203 with calculated apparent power and power factor."""

    cluster_id = ElectricalMeasurement.cluster_id

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
        ElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
    }

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
                super()._update_attribute(
                    self.AttributeDefs.power_factor.id, 0
                )

    async def read_attributes(
        self, attributes, allow_cache=False, only_cache=False, manufacturer=None
    ):
        """Read attributes ZCL foundation command."""
        records = []
        for attr in attributes:
            if isinstance(attr, str):
                attr_id = self.attributes_by_name[attr].id
            else:
                attr_id = attr

            # Check constant attributes first
            if attr_id in self._CONSTANT_ATTRIBUTES:
                records.append(
                    foundation.ReadAttributeRecord(
                        attr_id,
                        foundation.Status.SUCCESS,
                        foundation.TypeValue(
                            type=t.uint16_t, value=self._CONSTANT_ATTRIBUTES[attr_id]
                        ),
                    )
                )
            elif attr_id in self._attr_cache:
                # Determine the correct type for the attribute
                if attr_id == self.AttributeDefs.active_power.id:
                    attr_type = t.int16s
                else:
                    attr_type = t.uint16_t

                records.append(
                    foundation.ReadAttributeRecord(
                        attr_id,
                        foundation.Status.SUCCESS,
                        foundation.TypeValue(
                            type=attr_type, value=self._attr_cache[attr_id]
                        ),
                    )
                )
            else:
                records.append(
                    foundation.ReadAttributeRecord(
                        attr_id,
                        foundation.Status.UNSUPPORTED_ATTRIBUTE,
                        foundation.TypeValue(),
                    )
                )

        return (records,)


class TuyaPJ1203ManufCluster(NoManufacturerCluster, TuyaMCUCluster):
    """Manufacturer cluster for PJ-1203 single channel energy meter."""

    set_time_offset = 1970

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
    }

    data_point_handlers = {
        18: "_dp_2_attr_update",
        19: "_dp_2_attr_update",
        20: "_dp_2_attr_update",
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
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
