"""Tuya Energy Meter."""

import zigpy.types as t
from typing import Dict
from zigpy.profiles import zgp, zha
from zigpy.zcl.clusters.general import Basic, GreenPowerProxy, Groups, Ota, Scenes, Time
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    NoManufacturerCluster,
    TuyaLocalCluster,
    TuyaZBElectricalMeasurement,
    TuyaZBMeteringClusterWithUnit,
)
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    EnchantedDevice,
    TuyaMCUCluster,
)

AC_FREQUENCY_COEF = 0x027A
CURRENT_SUMM_DELIVERED_COEF = 0x0277
CURRENT_SUMM_DELIVERED_COEF_B = 0x027D
CURRENT_SUMM_RECEIVED_COEF = 0x027F
CURRENT_SUMM_RECEIVED_COEF_B = 0x0280
INSTANTANEOUS_DEMAND = 0x0265
INSTANTANEOUS_DEMAND_B = 0x0269
INSTANTANEOUS_DEMAND_COEF = 0x0276
INSTANTANEOUS_DEMAND_COEF_B = 0x027C
INSTANTANEOUS_DEMAND_TOTAL = 0x0273
POWER_FLOW = 0x0266
POWER_FLOW_B = 0x0268
RMS_CURRENT_COEF = 0x0275
RMS_CURRENT_COEF_B = 0x027B
RMS_VOLTAGE_COEF = 0x0274
UPDATE_PERIOD = 0x0281

METER_CONFIGURATION = 0x5000
SUPPRESS_NEGATIVE = 0x5001
SUPPRESS_NEGATIVE_B = 0x5002


class MeterConfiguration(t.enum8):
    """Enums for different Energy Meter configurations."""

    a = 0x00
    a_plus_b = 0x01
    a_minus_b = 0x02
    grid = 0x03
    production = 0x04
    grid_plus_production = 0x05
    demand_minus_grid = 0x06
    demand_minus_production = 0x07


class PowerFlow(t.enum8):
    """Indicates power flow direction."""

    forward = 0x00
    reverse = 0x01


class PowerCalculation:
    """For calculating power in different meter configurations."""

    @staticmethod
    def a_plus_b(a, b):
        return a + b

    @staticmethod
    def a_minus_b(a, b):
        return a - b

    @staticmethod
    def power_flow_preempt_a_plus_b(a, b, c, flow: PowerFlow):
        return PowerFlow.forward if flow == PowerFlow.reverse and a > b - c else flow

    POWER_C_METHODS = {
        MeterConfiguration.a_plus_b: a_plus_b,
        MeterConfiguration.a_minus_b: a_minus_b,
        MeterConfiguration.grid_plus_production: a_plus_b,
        MeterConfiguration.demand_minus_grid: a_minus_b,
        MeterConfiguration.demand_minus_production: a_minus_b,
    }

    POWER_FLOW_PREEMPT_METHODS = {
        MeterConfiguration.grid_plus_production: power_flow_preempt_a_plus_b,
    }

    @classmethod
    def power_c(cls, meter_configuration, a, b):
        method = cls.POWER_C_METHODS.get(meter_configuration)
        if method:
            return method(a, b)
        return None

    @classmethod
    def power_flow_preempt(cls, meter_configuration, a, b, c, flow):
        method = cls.POWER_FLOW_PREEMPT_METHODS.get(meter_configuration)
        if method:
            return method(a, b, c, flow)
        return flow


class TuyaPowerPhase:
    """Extracts values from Tuya power phase datapoints."""

    @staticmethod
    def variant_1(value):
        voltage = value[14] | value[13] << 8
        current = value[12] | value[11] << 8
        return voltage, current

    @staticmethod
    def variant_2(value):
        voltage = value[1] | value[0] << 8
        current = value[4] | value[3] << 8
        power = value[7] | value[6] << 8
        return voltage, current, power * 100

    @staticmethod
    def variant_3(value):
        voltage = (value[0] << 8) | value[1]
        current = (value[2] << 16) | (value[3] << 8) | value[4]
        power = (value[5] << 16) | (value[6] << 8) | value[7]
        return voltage, current, power * 100


class TuyaEnergyMeterCluster(TuyaLocalCluster):
    """Parent class for Tuya Energy Meter reporting clusters."""

    def attr_present(self, attr_names: str | tuple):
        if not isinstance(attr_names, tuple):
            attr_names = (attr_names,)
        return all(
            attr
            in self.endpoint.device.endpoints[1].tuya_manufacturer.reporting_attributes
            for attr in tuple(
                (self.ep_attribute, attr_name, self.endpoint.endpoint_id)
                for attr_name in attr_names
            )
        )

    @property
    def clamp_id(self):
        map = {2: "b", 3: "c"}
        return map.get(self.endpoint.endpoint_id, None)

    def mcu_attr(self, attr_name: str, default=None):
        try:
            value = self.endpoint.device.endpoints[1].tuya_manufacturer.get(
                attr_name, default
            )
        except Exception:
            value = default
        return value

    def suppress_negative(self, value: int):
        if value < 0 and self.mcu_attr(
            f"suppress_negative{'_' + self.clamp_id if self.clamp_id else ''}"
        ):
            value = 0
        return value

    def value_with_power_flow(self, value: int):
        power_flow = self.mcu_attr(
            f"power_flow{'_' + self.clamp_id if self.clamp_id else ''}"
        )
        if power_flow in (PowerFlow.forward, PowerFlow.reverse):
            value = value * (-1 if power_flow else 1)
        return value


class TuyaElectricalMeasurement(
    TuyaEnergyMeterCluster,
    TuyaZBElectricalMeasurement,
):
    """Tuya ElectricalMeasurement cluster for Energy Meter devices."""

    AC_FREQUENCY_DIVISOR = 0x0401
    AC_FREQUENCY_MULTIPLIER = 0x0400
    AC_POWER_DIVISOR = 0x0605
    AC_POWER_MULTIPLIER = 0x0604
    AC_VOLTAGE_DIVISOR = 0x0601
    AC_VOLTAGE_MULTIPLIER = 0x0600

    _CONSTANT_ATTRIBUTES = {
        **TuyaZBElectricalMeasurement._CONSTANT_ATTRIBUTES,
        AC_FREQUENCY_DIVISOR: 100,
        AC_FREQUENCY_MULTIPLIER: 1,
        AC_POWER_DIVISOR: 100,
        AC_POWER_MULTIPLIER: 1,
        AC_VOLTAGE_DIVISOR: 10,
        AC_VOLTAGE_MULTIPLIER: 1,
    }

    _MEASUREMENT_TYPES = {
        "active_power": 0b000001001,
        "active_power_ph_b": 0b000010001,
        "active_power_ph_c": 0b000100001,
        "reactive_power": 0b000001010,
        "reactive_power_ph_b": 0b000010010,
        "reactive_power_ph_c": 0b000100010,
        "apparent_power": 0b000001100,
        "apparent_power_ph_b": 0b000010100,
        "apparent_power_ph_c": 0b000100100,
    }

    def update_measurement_type(self, attr_name=None):
        measurement_type = 0b000000000
        for measurement, mask in self._MEASUREMENT_TYPES.items():
            if measurement == attr_name or self.get(measurement) is not None:
                measurement_type |= mask
        super().update_attribute("measurement_type", measurement_type)

    def active_power_from_apparent_power_and_power_factor(self, value):
        power_factor = self.get("power_factor")
        if power_factor is None:
            return
        power_factor *= 0.01
        active_power = value * power_factor
        self.update_attribute("active_power", round(active_power))

    def apparent_power_from_rms_current_and_rms_voltage(self, value):
        rms_voltage = self.get("rms_voltage") or self.endpoint.device.endpoints[
            1
        ].electrical_measurement.get("rms_voltage")
        if rms_voltage is None:
            return
        ac_current_divisor = self.get("ac_current_divisor", 1)
        ac_current_multiplier = self.get("ac_current_multiplier", 1)
        ac_power_divisor = self.get("ac_power_divisor", 1)
        ac_power_multiplier = self.get("ac_power_multiplier", 1)
        ac_voltage_divisor = self.get("ac_voltage_divisor", 1)
        ac_voltage_multiplier = self.get("ac_voltage_multiplier", 1)

        current = value / ac_current_divisor * ac_current_multiplier
        voltage = rms_voltage / ac_voltage_divisor * ac_voltage_multiplier
        apparent_power = (current * voltage) * ac_power_divisor / ac_power_multiplier
        self.update_attribute("apparent_power", round(apparent_power))

    def reactive_power_from_apparent_power_and_power_factor(self, value):
        power_factor = self.get("power_factor")
        if power_factor is None:
            return
        power_factor *= 0.01
        reactive_power = (value**2 * (1 - power_factor**2)) ** 0.5
        self.update_attribute("reactive_power", round(reactive_power))

    def reactive_power_from_apparent_power_and_active_power(self, value):
        apparent_power = self.get("apparent_power")
        if apparent_power is None or apparent_power < abs(value):
            return
        reactive_power = (apparent_power**2 - value**2) ** 0.5
        self.update_attribute("reactive_power", round(reactive_power))

    def update_attribute(self, attr_name: str, value) -> None:
        if attr_name in self._MEASUREMENT_TYPES:
            self.update_measurement_type(attr_name)
        if attr_name in ("active_power", "reactive_power"):
            value = self.value_with_power_flow(value)
            value = self.suppress_negative(value)

        super().update_attribute(attr_name, value)

        if attr_name == "active_power" and not self.attr_present("reactive_power"):
            self.reactive_power_from_apparent_power_and_active_power(value)
        if attr_name == "apparent_power" and not self.attr_present("reactive_power"):
            self.reactive_power_from_apparent_power_and_power_factor(value)
        if attr_name == "apparent_power" and not self.attr_present("active_power"):
            self.active_power_from_apparent_power_and_power_factor(value)
        if attr_name == "rms_current" and not self.attr_present("apparent_power"):
            self.apparent_power_from_rms_current_and_rms_voltage(value)


class TuyaMetering(
    TuyaEnergyMeterCluster,
    TuyaZBMeteringClusterWithUnit,
):
    """Tuya Metering cluster for Energy Meter devices."""

    STATUS = 0x0200
    MULTIPLIER = 0x0301
    DIVISOR = 0x0302
    SUMMATION_FORMATTING = 0x0303
    DEMAND_FORMATTING = 0x0304

    _CONSTANT_ATTRIBUTES = {
        **TuyaZBMeteringClusterWithUnit._CONSTANT_ATTRIBUTES,
        STATUS: 0x00,
        MULTIPLIER: 1,
        DIVISOR: 10000,
        SUMMATION_FORMATTING: 0b01111010,
        DEMAND_FORMATTING: 0b01111010,
    }

    _METER_DEVICE_TYPES = {
        (1, MeterConfiguration.production): 11,
        (2, MeterConfiguration.demand_minus_production): 11,
        (2, MeterConfiguration.grid_plus_production): 11,
        (3, MeterConfiguration.demand_minus_grid): 11,
    }

    def update_metering_device_type(self):
        metering_device_type = self._METER_DEVICE_TYPES.get(
            (self.endpoint.endpoint_id, self.mcu_attr("meter_configuration")), 0
        )
        super().update_attribute("metering_device_type", metering_device_type)

    def update_attribute(self, attr_name: str, value) -> None:
        if attr_name != "metering_device_type":
            self.update_metering_device_type()
        if attr_name in ("instantaneous_demand"):
            value = self.value_with_power_flow(value)
            value = self.suppress_negative(value)
        super().update_attribute(attr_name, value)


class TuyaEnergyMeterManufCluster(NoManufacturerCluster, TuyaMCUCluster):
    """Manufactuter cluster for Tuya Energy Meter devices."""

    LOCAL_ATTRIBUTES = (METER_CONFIGURATION, SUPPRESS_NEGATIVE, SUPPRESS_NEGATIVE_B)
    LOCAL_DEFAULTS = {METER_CONFIGURATION: 0}

    _attributes = {
        AC_FREQUENCY_COEF: ("ac_frequency_coefficient", t.uint32_t_be, True),
        CURRENT_SUMM_DELIVERED_COEF: (
            "current_summ_delivered_coefficient",
            t.uint32_t_be,
            True,
        ),
        CURRENT_SUMM_DELIVERED_COEF_B: (
            "current_summ_delivered_coefficient_b",
            t.uint32_t_be,
            True,
        ),
        CURRENT_SUMM_RECEIVED_COEF: (
            "current_summ_received_coefficient",
            t.uint32_t_be,
            True,
        ),
        CURRENT_SUMM_RECEIVED_COEF_B: (
            "current_summ_received_coefficient_b",
            t.uint32_t_be,
            True,
        ),
        INSTANTANEOUS_DEMAND: ("instantaneous_demand", t.uint32_t_be, True),
        INSTANTANEOUS_DEMAND_B: ("instantaneous_demand_b", t.uint32_t_be, True),
        INSTANTANEOUS_DEMAND_COEF: (
            "instantaneous_demand_coefficient",
            t.uint32_t_be,
            True,
        ),
        INSTANTANEOUS_DEMAND_COEF_B: (
            "instantaneous_demand_coefficient_b",
            t.uint32_t_be,
            True,
        ),
        INSTANTANEOUS_DEMAND_TOTAL: ("instantaneous_demand_total", t.int32s_be, True),
        POWER_FLOW: ("power_flow", PowerFlow, True),
        POWER_FLOW_B: ("power_flow_b", PowerFlow, True),
        RMS_CURRENT_COEF: ("rms_current_coefficient", t.uint32_t_be, True),
        RMS_CURRENT_COEF_B: ("rms_current_coefficient_b", t.uint32_t_be, True),
        RMS_VOLTAGE_COEF: ("rms_voltage_coefficient", t.uint32_t_be, True),
        UPDATE_PERIOD: ("update_period", t.uint32_t_be, True),
    }

    attributes = {
        **TuyaMCUCluster.attributes,
        METER_CONFIGURATION: (
            "meter_configuration",
            MeterConfiguration,
            True,
        ),
    }

    def __init__(self, *args, **kwargs):
        """Init defaults for local attributes."""
        super().__init__(*args, **kwargs)
        # if self.get("meter_configuration") is None:
        #    self.update_attribute("meter_configuration", MeterConfiguration.a)

    def __init_subclass__(cls) -> None:
        """Initializes device specific configuration"""

        attr_name_to_id = {}
        for attr_id, attr in cls._attributes.items():
            attr_name_to_id[attr[0] if isinstance(attr, tuple) else attr.name] = attr_id

        cls.attributes = {**cls.attributes}
        cls.reporting_attributes = []
        for dp, dp_map in cls.dp_to_attribute.items():
            attr_names = (
                dp_map.attribute_name
                if isinstance(dp_map.attribute_name, tuple)
                else (dp_map.attribute_name,)
            )
            for attr_name in attr_names:
                # Setup MCU attributes for device datapoints
                if dp_map.ep_attribute == TuyaMCUCluster.ep_attribute:
                    attr_id = attr_name_to_id.get(attr_name)
                    if attr_id is not None:
                        cls.attributes[attr_id] = cls._attributes[attr_id]

                # Attributes available in reporting clusters
                elif attr_name not in cls.reporting_attributes:
                    cls.reporting_attributes.append(
                        (dp_map.ep_attribute, attr_name, dp_map.endpoint_id or 1)
                    )
        super().__init_subclass__()

    async def write_attributes(self, attributes, manufacturer=None):
        """Handle writes to local configuration attributes."""

        local_attributes = {}
        for attr_id in set(self.LOCAL_ATTRIBUTES).intersection(set(attributes)):
            local_attributes[attr_id] = self.attributes[attr_id].type(
                attributes.pop(attr_id)
            )
        await TuyaLocalCluster.write_attributes(self, local_attributes, manufacturer)
        return await super().write_attributes(attributes, manufacturer=manufacturer)


class TuyaEnergyMeterManufCluster1Clamp(TuyaEnergyMeterManufCluster):
    """Tuya Energy Meter manufacturer cluster."""

    TUYA_DP_CURRENT_SUMM_DELIVERED = 101
    TUYA_DP_INSTANTANEOUS_DEMAND = 19
    TUYA_DP_RMS_CURRENT = 18
    TUYA_DP_RMS_VOLTAGE = 20

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        TUYA_DP_CURRENT_SUMM_DELIVERED: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "current_summ_delivered",
            converter=lambda x: x * 10,
        ),
        TUYA_DP_INSTANTANEOUS_DEMAND: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "instantaneous_demand",
        ),
        TUYA_DP_RMS_CURRENT: DPToAttributeMapping(
            TuyaElectricalMeasurement.ep_attribute,
            "rms_current",
        ),
        TUYA_DP_RMS_VOLTAGE: DPToAttributeMapping(
            TuyaElectricalMeasurement.ep_attribute,
            "rms_voltage",
        ),
    }

    data_point_handlers = {
        TUYA_DP_CURRENT_SUMM_DELIVERED: "_dp_2_attr_update",
        TUYA_DP_INSTANTANEOUS_DEMAND: "_dp_2_attr_update",
        TUYA_DP_RMS_CURRENT: "_dp_2_attr_update",
        TUYA_DP_RMS_VOLTAGE: "_dp_2_attr_update",
    }


class TuyaEnergyMeterManufClusterB1Clamp(TuyaEnergyMeterManufCluster):
    """Tuya Energy Meter bidirectional manufacturer cluster."""

    TUYA_DP_CURRENT_SUMM_DELIVERED = 1
    TUYA_DP_CURRENT_SUMM_RECEIVED = 2
    TUYA_DP_INSTANTANEOUS_DEMAND = 101
    TUYA_DP_POWER_FLOW = 102
    TUYA_DP_POWER_PHASE = 6

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        TUYA_DP_CURRENT_SUMM_DELIVERED: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "current_summ_delivered",
            converter=lambda x: x * 100,
        ),
        TUYA_DP_CURRENT_SUMM_RECEIVED: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "current_summ_received",
            converter=lambda x: x * 100,
        ),
        TUYA_DP_INSTANTANEOUS_DEMAND: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "instantaneous_demand",
            converter=lambda x: x * 10,
        ),
        TUYA_DP_POWER_FLOW: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "power_flow",
            converter=lambda x: PowerFlow(x),
        ),
        TUYA_DP_POWER_PHASE: DPToAttributeMapping(
            TuyaElectricalMeasurement.ep_attribute,
            ("rms_voltage", "rms_current", "active_power"),
            converter=lambda x: TuyaPowerPhase.variant_3(x),
        ),
    }

    data_point_handlers = {
        TUYA_DP_CURRENT_SUMM_DELIVERED: "_dp_2_attr_update",
        TUYA_DP_CURRENT_SUMM_RECEIVED: "_dp_2_attr_update",
        TUYA_DP_INSTANTANEOUS_DEMAND: "_dp_2_attr_update",
        TUYA_DP_POWER_FLOW: "_dp_2_attr_update",
        TUYA_DP_POWER_PHASE: "_dp_2_attr_update",
    }


class TuyaEnergyMeterManufClusterB2Clamp(TuyaEnergyMeterManufCluster):
    """Tuya Energy Meter bidirectional 2 clamp manufacturer cluster."""

    TUYA_DP_AC_FREQUENCY = 111
    TUYA_DP_AC_FREQUENCY_COEF = 122
    TUYA_DP_CURRENT_SUMM_DELIVERED = 106
    TUYA_DP_CURRENT_SUMM_DELIVERED_COEF = 119
    TUYA_DP_CURRENT_SUMM_DELIVERED_B = 108
    TUYA_DP_CURRENT_SUMM_DELIVERED_COEF_B = 125
    TUYA_DP_CURRENT_SUMM_RECEIVED = 107
    TUYA_DP_CURRENT_SUMM_RECEIVED_COEF = 127
    TUYA_DP_CURRENT_SUMM_RECEIVED_B = 109
    TUYA_DP_CURRENT_SUMM_RECEIVED_COEF_B = 128
    TUYA_DP_INSTANTANEOUS_DEMAND = 101
    TUYA_DP_INSTANTANEOUS_DEMAND_B = 105
    TUYA_DP_INSTANTANEOUS_DEMAND_COEF = 118
    TUYA_DP_INSTANTANEOUS_DEMAND_COEF_B = 124
    TUYA_DP_INSTANTANEOUS_DEMAND_TOTAL = 115
    TUYA_DP_POWER_FACTOR = 110
    TUYA_DP_POWER_FACTOR_B = 121
    TUYA_DP_POWER_FLOW = 102
    TUYA_DP_POWER_FLOW_B = 104
    TUYA_DP_UPDATE_PERIOD = 129
    TUYA_DP_RMS_CURRENT = 113
    TUYA_DP_RMS_CURRENT_COEF = 117
    TUYA_DP_RMS_CURRENT_B = 114
    TUYA_DP_RMS_CURRENT_COEF_B = 123
    TUYA_DP_RMS_VOLTAGE = 112
    TUYA_DP_RMS_VOLTAGE_COEF = 116

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        TUYA_DP_AC_FREQUENCY: DPToAttributeMapping(
            TuyaElectricalMeasurement.ep_attribute,
            "ac_frequency",
        ),
        TUYA_DP_AC_FREQUENCY_COEF: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "ac_frequency_coefficient",
        ),
        TUYA_DP_CURRENT_SUMM_DELIVERED: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "current_summ_delivered",
            converter=lambda x: x * 100,
        ),
        TUYA_DP_CURRENT_SUMM_DELIVERED_B: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "current_summ_delivered",
            endpoint_id=2,
            converter=lambda x: x * 100,
        ),
        TUYA_DP_CURRENT_SUMM_DELIVERED_COEF: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "current_summ_delivered_coefficient",
        ),
        TUYA_DP_CURRENT_SUMM_DELIVERED_COEF_B: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "current_summ_delivered_coefficient_b",
        ),
        TUYA_DP_CURRENT_SUMM_RECEIVED: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "current_summ_received",
            converter=lambda x: x * 100,
        ),
        TUYA_DP_CURRENT_SUMM_RECEIVED_B: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "current_summ_received",
            endpoint_id=2,
            converter=lambda x: x * 100,
        ),
        TUYA_DP_CURRENT_SUMM_RECEIVED_COEF: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "current_summ_received_coefficient",
        ),
        TUYA_DP_CURRENT_SUMM_RECEIVED_COEF_B: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "current_summ_received_coefficient_b",
        ),
        TUYA_DP_INSTANTANEOUS_DEMAND: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "instantaneous_demand",
        ),
        TUYA_DP_INSTANTANEOUS_DEMAND_B: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "instantaneous_demand_b",
        ),
        TUYA_DP_INSTANTANEOUS_DEMAND_COEF: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "instantaneous_demand_coefficient",
        ),
        TUYA_DP_INSTANTANEOUS_DEMAND_COEF_B: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "instantaneous_demand_coefficient_b",
        ),
        TUYA_DP_INSTANTANEOUS_DEMAND_TOTAL: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "instantaneous_demand_total",
        ),
        TUYA_DP_POWER_FACTOR: DPToAttributeMapping(
            TuyaElectricalMeasurement.ep_attribute,
            "power_factor",
        ),
        TUYA_DP_POWER_FACTOR_B: DPToAttributeMapping(
            TuyaElectricalMeasurement.ep_attribute,
            "power_factor",
            endpoint_id=2,
        ),
        TUYA_DP_POWER_FLOW: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "power_flow",
            converter=lambda x: PowerFlow(x),
        ),
        TUYA_DP_POWER_FLOW_B: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "power_flow_b",
            converter=lambda x: PowerFlow(x),
        ),
        TUYA_DP_RMS_CURRENT: DPToAttributeMapping(
            TuyaElectricalMeasurement.ep_attribute,
            "rms_current",
        ),
        TUYA_DP_RMS_CURRENT_B: DPToAttributeMapping(
            TuyaElectricalMeasurement.ep_attribute,
            "rms_current",
            endpoint_id=2,
        ),
        TUYA_DP_RMS_CURRENT_COEF: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "rms_current_coefficient",
        ),
        TUYA_DP_RMS_CURRENT_COEF_B: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "rms_current_coefficient_b",
        ),
        TUYA_DP_RMS_VOLTAGE: DPToAttributeMapping(
            TuyaElectricalMeasurement.ep_attribute,
            "rms_voltage",
        ),
        TUYA_DP_RMS_VOLTAGE_COEF: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "rms_voltage_coefficient",
        ),
        TUYA_DP_UPDATE_PERIOD: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "update_period",
        ),
    }

    data_point_handlers = {
        TUYA_DP_AC_FREQUENCY: "_dp_2_attr_update",
        TUYA_DP_AC_FREQUENCY_COEF: "_dp_2_attr_update",
        TUYA_DP_CURRENT_SUMM_DELIVERED: "_dp_2_attr_update",
        TUYA_DP_CURRENT_SUMM_DELIVERED_COEF: "_dp_2_attr_update",
        TUYA_DP_CURRENT_SUMM_DELIVERED_B: "_dp_2_attr_update",
        TUYA_DP_CURRENT_SUMM_DELIVERED_COEF_B: "_dp_2_attr_update",
        TUYA_DP_CURRENT_SUMM_RECEIVED: "_dp_2_attr_update",
        TUYA_DP_CURRENT_SUMM_RECEIVED_COEF: "_dp_2_attr_update",
        TUYA_DP_CURRENT_SUMM_RECEIVED_B: "_dp_2_attr_update",
        TUYA_DP_CURRENT_SUMM_RECEIVED_COEF_B: "_dp_2_attr_update",
        TUYA_DP_INSTANTANEOUS_DEMAND: "_dp_2_attr_update",
        TUYA_DP_INSTANTANEOUS_DEMAND_B: "_dp_2_attr_update",
        TUYA_DP_INSTANTANEOUS_DEMAND_COEF: "_dp_2_attr_update",
        TUYA_DP_INSTANTANEOUS_DEMAND_COEF_B: "_dp_2_attr_update",
        TUYA_DP_INSTANTANEOUS_DEMAND_TOTAL: "_dp_2_attr_update",
        TUYA_DP_POWER_FACTOR: "_dp_2_attr_update",
        TUYA_DP_POWER_FACTOR_B: "_dp_2_attr_update",
        TUYA_DP_POWER_FLOW: "_dp_2_attr_update",
        TUYA_DP_POWER_FLOW_B: "_dp_2_attr_update",
        TUYA_DP_RMS_CURRENT: "_dp_2_attr_update",
        TUYA_DP_RMS_CURRENT_COEF: "_dp_2_attr_update",
        TUYA_DP_RMS_CURRENT_B: "_dp_2_attr_update",
        TUYA_DP_RMS_CURRENT_COEF_B: "_dp_2_attr_update",
        TUYA_DP_RMS_VOLTAGE: "_dp_2_attr_update",
        TUYA_DP_RMS_VOLTAGE_COEF: "_dp_2_attr_update",
        TUYA_DP_UPDATE_PERIOD: "_dp_2_attr_update",
    }

    attributes = {
        **TuyaEnergyMeterManufCluster.attributes,
        SUPPRESS_NEGATIVE: ("suppress_negative", t.Bool, True),
        SUPPRESS_NEGATIVE_B: ("suppress_negative_b", t.Bool, True),
    }

    def get_cluster(
        self,
        endpoint_id: int,
        ep_attribute: str,
    ):
        return getattr(self.endpoint.device.endpoints[endpoint_id], ep_attribute)

    def update_multi_clamp_metering_clusters(self):
        """Orchestrate updates to reporting clusters."""

        metering_a = self.get_cluster(1, TuyaMetering.ep_attribute)
        metering_b = self.get_cluster(2, TuyaMetering.ep_attribute)
        metering_c = self.get_cluster(3, TuyaMetering.ep_attribute)

        instantaneous_demand = self.get("instantaneous_demand")
        instantaneous_demand_b = self.get("instantaneous_demand_b")
        instantaneous_demand_c = getattr(self, "instantaneous_demand_c", 0)

        meter_configuration = self.get(
            "meter_configuration", MeterConfiguration.a_plus_b
        )

        self.update_attribute(
            "power_flow",
            PowerCalculation.power_flow_preempt(
                meter_configuration,
                instantaneous_demand,
                instantaneous_demand_b,
                instantaneous_demand_c,
                self.get("power_flow"),
            ),
        )
        self.update_attribute(
            "power_flow_b",
            PowerCalculation.power_flow_preempt(
                meter_configuration,
                instantaneous_demand_b,
                instantaneous_demand,
                instantaneous_demand_c,
                self.get("power_flow_b"),
            ),
        )

        metering_a.update_attribute("instantaneous_demand", instantaneous_demand)
        metering_b.update_attribute("instantaneous_demand", instantaneous_demand_b)

        current_summ_delivered_c = PowerCalculation.power_c(
            meter_configuration,
            metering_a.get("current_summ_delivered"),
            metering_b.get("current_summ_delivered"),
        )
        current_summ_received_c = PowerCalculation.power_c(
            meter_configuration,
            metering_a.get("current_summ_received"),
            metering_b.get("current_summ_received"),
        )
        self.instantaneous_demand_c = PowerCalculation.power_c(
            meter_configuration,
            metering_a.get("instantaneous_demand"),
            metering_b.get("instantaneous_demand"),
        )

        metering_c.update_attribute(
            "current_summ_delivered",
            current_summ_delivered_c,
        )
        metering_c.update_attribute(
            "current_summ_received",
            current_summ_received_c,
        )
        metering_c.update_attribute(
            "instantaneous_demand",
            self.instantaneous_demand_c,
        )

    def update_attribute(self, attr_name: str, value) -> None:
        super().update_attribute(attr_name, value)
        if attr_name == "instantaneous_demand_b":
            self.update_multi_clamp_metering_clusters()


class TuyaEnergyMeter1Clamp(EnchantedDevice):
    """Tuya PJ-MGW1203 1 Clamp Energy Meter."""

    signature = {
        MODELS_INFO: [("_TZE204_cjbofhxw", "TS0601")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=51
            # device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaMCUCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # input_clusters=[]
                # output_clusters=[33]
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
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
                    TuyaEnergyMeterManufCluster1Clamp,
                    TuyaElectricalMeasurement,
                    TuyaMetering,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaEnergyMeterB1Clamp(EnchantedDevice):
    """Tuya PJ-1203A Bidirectional 1 Clamp Energy Meter."""

    signature = {
        MODELS_INFO: [("_TZE204_ac0fhfiq", "TS0601")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=51
            # device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaMCUCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # input_clusters=[]
                # output_clusters=[33]
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
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
                    TuyaEnergyMeterManufClusterB1Clamp,
                    TuyaElectricalMeasurement,
                    TuyaMetering,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaEnergyMeterB2Clamp(EnchantedDevice):
    """Tuya PJ-1203A Bidirectional 2 Clamp Energy Meter."""

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4417
        #                       maximum_buffer_size=66 maximum_incoming_transfer_size=66 server_mask=10752
        #                       maximum_outgoing_transfer_size=66 descriptor_capability_field=0>",
        # device_version=1
        # input_clusters=[0x0000, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x000a, 0x0019]
        MODELS_INFO: [("_TZE204_81yrt3lo", "TS0601"), ("_TZE200_rks0sgb7", "TS0601")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=51
            # device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaMCUCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # input_clusters=[]
                # output_clusters=[33]
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
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
                    TuyaEnergyMeterManufClusterB2Clamp,
                    TuyaElectricalMeasurement,
                    TuyaMetering,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [
                    TuyaElectricalMeasurement,
                    TuyaMetering,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [
                    TuyaMetering,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }
