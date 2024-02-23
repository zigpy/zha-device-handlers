"""Tuya Energy Meter."""

from enum import Enum
from typing import Dict, Union

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, GreenPowerProxy, Groups, Ota, Scenes, Time
from zigpy.zcl.clusters.homeautomation import MeasurementType

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
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster

# Manufacturer cluster identifiers for device signatures
EARU_MANUFACTURER_CLUSTER_ID = 0xFF66

# Offset of 512 (0x200) for transating DP ID to Attribute ID
# Attribute IDs don't need to match every device's specific values
DP_ATTR_OFFSET = 512

# Power direction acttributes
POWER_FLOW = 102 + DP_ATTR_OFFSET  # PowerFlow (0: forward, 1: reverse)
POWER_FLOW_B = 104 + DP_ATTR_OFFSET  # PowerFlow (0: forward, 1: reverse)

# Calibration attributes
CURRENT_SUMM_DELIVERED_COEF = 119 + DP_ATTR_OFFSET  # uint32_t_be
CURRENT_SUMM_DELIVERED_COEF_B = 125 + DP_ATTR_OFFSET  # uint32_t_be
CURRENT_SUMM_RECEIVED_COEF = 127 + DP_ATTR_OFFSET  # uint32_t_be
CURRENT_SUMM_RECEIVED_COEF_B = 128 + DP_ATTR_OFFSET  # uint32_t_be
INSTANTANEOUS_DEMAND_COEF = 118 + DP_ATTR_OFFSET  # uint32_t_be
INSTANTANEOUS_DEMAND_COEF_B = 124 + DP_ATTR_OFFSET  # uint32_t_be
AC_FREQUENCY_COEF = 122 + DP_ATTR_OFFSET  # uint32_t_be
RMS_CURRENT_COEF = 117 + DP_ATTR_OFFSET  # uint32_t_be
RMS_CURRENT_COEF_B = 123 + DP_ATTR_OFFSET  # uint32_t_be
RMS_VOLTAGE_COEF = 116 + DP_ATTR_OFFSET  # uint32_t_be

# Device configuration attributes
UPDATE_PERIOD = 129 + DP_ATTR_OFFSET  # uint32_t_be (3-60 seconds supported)

# Local configuration attributes
CHANNEL_CONFIGURATION = 0x5000
SUPPRESS_NEGATIVE = 0x5010
SUPPRESS_NEGATIVE_B = 0x5011
POWER_FLOW_PREEMPT = 0x5020

# Suffix for device attributes which need power flow direction applied
UNSIGNED_POWER_ATTR_SUFFIX = "_attr_unsigned"


class Channel(str, Enum):
    """Meter channels."""

    A = "a"
    B = "b"
    AB = "ab"

    @classmethod
    def attr_with_channel(cls, attr_name: str, channel=None) -> str:
        """Returns the attr_name with channel suffix."""
        assert channel is None or channel in cls, "Invalid channel."
        if channel and channel != cls.A:
            attr_name = attr_name + "_ch_" + channel
        return attr_name


class ChannelConfiguration(t.enum8):
    """Enums for for all Energy Meter configurations."""

    SINGLE = 0x00
    A_PLUS_B = 0x01
    A_MINUS_B = 0x02


class ChannelConfiguration_1CH(t.enum8):
    """Single channel Energy Meter configuration."""

    SINGLE = ChannelConfiguration.SINGLE
    DEFAULT = SINGLE


class ChannelConfiguration_1CHB(t.enum8):
    """Single channel bidirectional Energy Meter configuration."""

    SINGLE = ChannelConfiguration.SINGLE
    DEFAULT = SINGLE


class ChannelConfiguration_2CH(t.enum8):
    """Dual channel Energy Meter configuration."""

    A_PLUS_B = ChannelConfiguration.A_PLUS_B
    A_MINUS_B = ChannelConfiguration.A_MINUS_B
    DEFAULT = A_MINUS_B  # Consumption minus production


class ChannelConfiguration_2CHB(t.enum8):
    """Dual channel bidirectional Energy Meter configuration."""

    A_PLUS_B = ChannelConfiguration.A_PLUS_B
    A_MINUS_B = ChannelConfiguration.A_MINUS_B
    DEFAULT = A_PLUS_B  # Grid plus production


class PowerFlow(t.enum1):
    """Indicates power flow direction."""

    FORWARD = 0x0
    REVERSE = 0x1

    @classmethod
    def align_value(cls, value: int, power_flow=None):
        if (
            power_flow == cls.REVERSE
            and value > 0
            or power_flow == cls.FORWARD
            and value < 0
        ):
            value = -value
        return value


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
        return voltage, current, power * 10

    @staticmethod
    def variant_3(value):
        voltage = (value[0] << 8) | value[1]
        current = (value[2] << 16) | (value[3] << 8) | value[4]
        power = (value[5] << 16) | (value[6] << 8) | value[7]
        return voltage, current, power * 10


class PowerCalculation:
    """Methods for calculating power values."""

    @staticmethod
    def active_power_from_apparent_power_power_factor_and_power_flow(
        apparent_power, power_factor, power_flow=None
    ):
        if apparent_power is None or power_factor is None:
            return
        power_factor *= 0.01
        return apparent_power * abs(power_factor) * (-1 if power_flow else 1)

    @staticmethod
    def apparent_power_from_active_power_and_power_factor(active_power, power_factor):
        if active_power is None or power_factor is None:
            return
        power_factor *= 0.01
        return abs(active_power) / abs(power_factor)

    @staticmethod
    def apparent_power_from_rms_current_and_rms_voltage(
        rms_current,
        rms_voltage,
        ac_current_divisor: int = 1,
        ac_current_multiplier: int = 1,
        ac_voltage_divisor: int = 1,
        ac_voltage_multiplier: int = 1,
        ac_power_divisor: int = 1,
        ac_power_multiplier: int = 1,
    ):
        if rms_current is None or rms_voltage is None:
            return
        return (
            (rms_current * ac_current_multiplier / ac_current_divisor)
            * (rms_voltage * ac_voltage_multiplier / ac_voltage_divisor)
            * ac_power_divisor
            / ac_power_multiplier
        )

    @staticmethod
    def reactive_power_from_apparent_power_and_power_factor(
        apparent_power, power_factor
    ):
        if apparent_power is None or power_factor is None:
            return
        power_factor *= 0.01
        return (apparent_power * (1 - power_factor**2) ** 0.5) * (
            -1 if power_factor < 0 else 1
        )


class MeterChannelClusterBase:
    """Common methods and properties for energy meter reporting clusters."""

    _DIRECTIONAL_ATTRIBUTES = ()
    _ENDPOINT_TO_CHANNEL = {
        (ChannelConfiguration_2CH, 1): Channel.A,
        (ChannelConfiguration_2CH, 2): Channel.B,
        (ChannelConfiguration_2CH, 3): Channel.AB,
        (ChannelConfiguration_2CHB, 1): Channel.A,
        (ChannelConfiguration_2CHB, 2): Channel.B,
        (ChannelConfiguration_2CHB, 3): Channel.AB,
    }
    _CHANNEL_TO_ENDPOINT = {(k[0], v): k[1] for k, v in _ENDPOINT_TO_CHANNEL.items()}

    @property
    def channel(self) -> Union[str, None]:
        return self._ENDPOINT_TO_CHANNEL.get(
            (self.channel_config_type, self.endpoint.endpoint_id), None
        )

    @property
    def channel_config(self) -> Union[ChannelConfiguration, None]:
        return self.manufacturer_cluster.get_optional("channel_configuration")

    @property
    def channel_config_type(self):
        try:
            return self.manufacturer_cluster.AttributeDefs.channel_configuration.type
        except Exception:
            pass

    @property
    def manufacturer_cluster(self):
        return self.get_cluster(1, TuyaMCUCluster.ep_attribute)

    @property
    def power_flow(self) -> Union[PowerFlow, None]:
        return self.manufacturer_cluster.get_optional(
            Channel.attr_with_channel("power_flow", self.channel)
        )

    @power_flow.setter
    def power_flow(self, value: PowerFlow):
        self.manufacturer_cluster.update_attribute(
            Channel.attr_with_channel("power_flow", self.channel), value
        )

    def attr_present(self, *attr_names) -> bool:
        """Returns True if any of the specified attributes are provided by the device."""
        return any(
            attr in self.manufacturer_cluster.device_reported_attributes
            for attr in tuple(
                (self.ep_attribute, attr_name, self.endpoint.endpoint_id)
                for attr_name in attr_names
            )
        )

    def attr_type(self, attr_name: str):
        """Returns the type of the specified attribute."""
        return getattr(self.AttributeDefs, attr_name).type

    def directional_attribute_handler(self, attr_name: str, value) -> tuple:
        """Orchestrates handling of directional meter attributes."""
        if attr_name.endswith(UNSIGNED_POWER_ATTR_SUFFIX):
            attr_name = attr_name.removesuffix(UNSIGNED_POWER_ATTR_SUFFIX)
            value = PowerFlow.align_value(value, self.power_flow)
        if attr_name in self._DIRECTIONAL_ATTRIBUTES:
            value = self.suppress_negative(value)
        return attr_name, value

    def get_cluster(
        self,
        channel_or_endpoint_id: Union[Channel, int],
        ep_attribute: str,
    ):
        """Returns a specified device cluster."""
        if channel_or_endpoint_id in Channel:
            channel_or_endpoint_id = self._CHANNEL_TO_ENDPOINT.get(
                (self.channel_config_type, channel_or_endpoint_id), None
            )
        assert channel_or_endpoint_id is not None, "Invalid channel_or_endpoint_id."
        return getattr(
            self.endpoint.device.endpoints[channel_or_endpoint_id], ep_attribute
        )

    def suppress_negative(self, value: int) -> int:
        """Negative values are 0 if suppress_negative is enabled."""
        if value < 0 and self.manufacturer_cluster.get_optional(
            Channel.attr_with_channel("suppress_negative", self.channel)
        ):
            value = 0
        return value

    def update_calculated_attribute(self, target_attr: str, value) -> None:
        """Updates a target attribute if the calculated value is valid."""
        if value is None:
            return
        value = round(value)
        self.update_attribute(target_attr, value)


class PowerFlowPreempt:
    """Logic for preempting delayed power flow direction change on dual channel devices."""

    _PF_PREEMPT_HOLD_PREFIX = "power_flow_preempt_hold_"
    _PF_PREEMPT_SOURCE_ATTR = (
        "rms_current",
        "active_power",
        "instantaneous_demand",
        "active_power" + UNSIGNED_POWER_ATTR_SUFFIX,
        "instantaneous_demand" + UNSIGNED_POWER_ATTR_SUFFIX,
    )
    _PF_PREEMPT_SOURCE_CHANNELS = (Channel.A, Channel.B)
    _PF_PREEMPT_TRIGGER_CHANNEL = Channel.B

    power_flow: PowerFlow

    @property
    def power_flow_preempt(self) -> bool:
        return self.manufacturer_cluster.get_optional("power_flow_preempt", False)

    @staticmethod
    def _power_flow_preempt_a_plus_b(a, b, flow: PowerFlow):
        """Compensates for delay in reported direction."""
        return (
            PowerFlow.FORWARD if flow == PowerFlow.REVERSE and abs(a) > abs(b) else flow
        )

    def power_flow_preempt_handler(self, attr_name: str, value):
        if (
            not self.power_flow_preempt
            or self.channel_config != ChannelConfiguration.A_PLUS_B
            or self.channel not in self._PF_PREEMPT_SOURCE_CHANNELS
            or attr_name not in self._PF_PREEMPT_SOURCE_ATTR
        ):
            return

        if self.channel is not self._PF_PREEMPT_TRIGGER_CHANNEL:
            action = None
            if getattr(self, self._PF_PREEMPT_HOLD_PREFIX + attr_name, None) != value:
                setattr(self, self._PF_PREEMPT_HOLD_PREFIX + attr_name, value)
                action = "hold"
            return action

        cluster_a = self.get_cluster(Channel.A, self.ep_attribute)
        value_a = getattr(cluster_a, self._PF_PREEMPT_HOLD_PREFIX + attr_name, None)
        if value_a is None:
            return

        cluster_a.power_flow = self._power_flow_preempt_a_plus_b(
            value_a,
            value,
            cluster_a.power_flow,
        )
        self.power_flow = self._power_flow_preempt_a_plus_b(
            value,
            value_a,
            self.power_flow,
        )

        cluster_a.update_attribute(attr_name, value_a)
        setattr(cluster_a, self._PF_PREEMPT_HOLD_PREFIX + attr_name, None)


class VirtualChannel:
    """Logic for updating the virtual cluster on dual channel devices."""

    @staticmethod
    def _discrete_a_plus_b(a, b):
        return a + b

    @staticmethod
    def _discrete_a_minus_b(a, b):
        return a - b

    @staticmethod
    def _cumulative_a_plus_b(a, b):
        return a + b

    def _cumulative_a_minus_b(a, b):
        return a - b

    _VIRTUAL_CHANNEL = Channel.AB
    _VIRTUAL_CUMULATIVE_ATTRIBUTES = ()
    _VIRTUAL_DISCRETE_ATTRIBUTES = ()
    _VIRTUAL_UPDATE_TRIGGER_CHANNEL = Channel.B

    _VIRTUAL_DISCRETE_METHODS = {
        ChannelConfiguration.A_PLUS_B: _discrete_a_plus_b,
        ChannelConfiguration.A_MINUS_B: _discrete_a_minus_b,
    }

    _VIRTUAL_CUMULATIVE_METHODS = {
        ChannelConfiguration.A_PLUS_B: _cumulative_a_plus_b,
        # ChannelConfiguration.A_MINUS_B: _cumulative_a_minus_b, This needs work
    }

    def update_virtual_cluster(self, attr_name: str) -> None:
        if (
            self.channel_config
            not in (ChannelConfiguration.A_PLUS_B, ChannelConfiguration.A_MINUS_B)
            or self.channel != self._VIRTUAL_UPDATE_TRIGGER_CHANNEL
            or attr_name
            not in self._VIRTUAL_DISCRETE_ATTRIBUTES
            + self._VIRTUAL_CUMULATIVE_ATTRIBUTES
        ):
            return

        cluster_a = self.get_cluster(Channel.A, self.ep_attribute)
        cluster_b = self.get_cluster(Channel.B, self.ep_attribute)
        value_a = cluster_a.get(attr_name)
        value_b = cluster_b.get(attr_name)

        method = None
        if attr_name in self._VIRTUAL_CUMULATIVE_ATTRIBUTES:
            method = self._VIRTUAL_CUMULATIVE_METHODS.get(self.channel_config)
        elif attr_name in self._VIRTUAL_DISCRETE_ATTRIBUTES:
            method = self._VIRTUAL_DISCRETE_METHODS.get(self.channel_config)
            if getattr(self.attr_type(attr_name), "_signed", None) is False:
                value_a = PowerFlow.align_value(value_a, cluster_a.power_flow)
                value_b = PowerFlow.align_value(value_b, cluster_b.power_flow)
        if not method:
            return

        value_ab = method(value_a, value_b)
        if value_ab is None:
            return
        cluster_ab = self.get_cluster(Channel.AB, self.ep_attribute)
        cluster_ab.update_attribute(attr_name, value_ab)


class TuyaElectricalMeasurement(
    PowerFlowPreempt,
    VirtualChannel,
    MeterChannelClusterBase,
    TuyaLocalCluster,
    TuyaZBElectricalMeasurement,
):
    """Tuya ElectricalMeasurement cluster for Energy Meter devices."""

    _CONSTANT_ATTRIBUTES = {
        **TuyaZBElectricalMeasurement._CONSTANT_ATTRIBUTES,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 100,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_frequency_multiplier.id: 1,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 10,  # 1 decimal place
        TuyaZBElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
    }

    _ATTRIBUTE_MEASUREMENT_TYPES = {
        "active_power": MeasurementType.Active_measurement_AC
        | MeasurementType.Phase_A_measurement,
        "active_power_ph_b": MeasurementType.Active_measurement_AC
        | MeasurementType.Phase_B_measurement,
        "active_power_ph_c": MeasurementType.Active_measurement_AC
        | MeasurementType.Phase_C_measurement,
        "reactive_power": MeasurementType.Reactive_measurement_AC
        | MeasurementType.Phase_A_measurement,
        "reactive_power_ph_b": MeasurementType.Reactive_measurement_AC
        | MeasurementType.Phase_B_measurement,
        "reactive_power_ph_c": MeasurementType.Reactive_measurement_AC
        | MeasurementType.Phase_C_measurement,
        "apparent_power": MeasurementType.Apparent_measurement_AC
        | MeasurementType.Phase_A_measurement,
        "apparent_power_ph_b": MeasurementType.Apparent_measurement_AC
        | MeasurementType.Phase_B_measurement,
        "apparent_power_ph_c": MeasurementType.Apparent_measurement_AC
        | MeasurementType.Phase_C_measurement,
    }

    _DIRECTIONAL_ATTRIBUTES = ("active_power",)

    _VIRTUAL_DISCRETE_ATTRIBUTES = (
        "active_power",
        "apparent_power",
        "reactive_power",
        "rms_current",
    )

    def calculated_attributes(self, attr_name: str, value) -> None:
        """Invoked following completion of parent update_attribute."""

        if (
            self.channel == self._VIRTUAL_CHANNEL
        ):  # Attributes are not calculated for the virtual channel.
            return

        if attr_name == "apparent_power" and not self.attr_present("active_power"):
            self.update_calculated_attribute(
                "active_power",
                PowerCalculation.active_power_from_apparent_power_power_factor_and_power_flow(
                    value, self.get("power_factor"), self.power_flow
                ),
            )

        if attr_name == "apparent_power" and not self.attr_present("reactive_power"):
            self.update_calculated_attribute(
                "reactive_power",
                PowerCalculation.reactive_power_from_apparent_power_and_power_factor(
                    value, self.get("power_factor")
                ),
            )

        if attr_name == "active_power" and not self.attr_present(
            "apparent_power", "rms_current"
        ):
            self.update_calculated_attribute(
                "apparent_power",
                PowerCalculation.apparent_power_from_active_power_and_power_factor(
                    value, self.get("power_factor")
                ),
            )

        if attr_name == "rms_current" and not self.attr_present("apparent_power"):
            self.update_calculated_attribute(
                "apparent_power",
                PowerCalculation.apparent_power_from_rms_current_and_rms_voltage(
                    value,
                    self.get("rms_voltage")
                    or self.endpoint.device.endpoints[1].electrical_measurement.get(
                        "rms_voltage"
                    ),
                    self.get("ac_current_divisor", 1),
                    self.get("ac_current_multiplier", 1),
                    self.get("ac_voltage_divisor", 1),
                    self.get("ac_voltage_multiplier", 1),
                    self.get("ac_power_divisor", 1),
                    self.get("ac_power_multiplier", 1),
                ),
            )

    def update_attribute(self, attr_name: str, value) -> None:
        attr_name, value = self.directional_attribute_handler(attr_name, value)
        if self.power_flow_preempt_handler(attr_name, value) == "hold":
            return
        if attr_name in self._ATTRIBUTE_MEASUREMENT_TYPES:
            self.update_measurement_type(attr_name)
        super().update_attribute(attr_name, value)
        self.update_virtual_cluster(attr_name)
        self.calculated_attributes(attr_name, value)

    def update_measurement_type(self, attr_name=None) -> None:
        """Derives the measurement type from reported attributes."""
        measurement_type = sum(
            mask
            for measurement, mask in self._ATTRIBUTE_MEASUREMENT_TYPES.items()
            if measurement == attr_name or self.get(measurement) is not None
        )
        super().update_attribute("measurement_type", measurement_type)


class TuyaMetering(
    PowerFlowPreempt,
    VirtualChannel,
    MeterChannelClusterBase,
    TuyaLocalCluster,
    TuyaZBMeteringClusterWithUnit,
):
    """Tuya Metering cluster for Energy Meter devices."""

    @staticmethod
    def metering_format(
        int_digits: int, dec_digits: int, suppresss_leading_zeroes: bool = True
    ):
        assert 0 <= int_digits <= 7, "int_digits must be between 0 and 7."
        assert 0 <= dec_digits <= 7, "dec_digits must be between 0 and 7."
        return (suppresss_leading_zeroes << 6) | (int_digits << 3) | dec_digits

    _CONSTANT_ATTRIBUTES = {
        **TuyaZBMeteringClusterWithUnit._CONSTANT_ATTRIBUTES,
        TuyaZBMeteringClusterWithUnit.AttributeDefs.status.id: 0x00,
        TuyaZBMeteringClusterWithUnit.AttributeDefs.multiplier.id: 1,
        TuyaZBMeteringClusterWithUnit.AttributeDefs.divisor.id: 10000,  # 1 decimal place after conversion from kW to W
        TuyaZBMeteringClusterWithUnit.AttributeDefs.summation_formatting.id: metering_format(
            7, 2, True
        ),
        TuyaZBMeteringClusterWithUnit.AttributeDefs.demand_formatting.id: metering_format(
            7, 1, True
        ),
    }

    _DIRECTIONAL_ATTRIBUTES = ("instantaneous_demand",)

    _VIRTUAL_CUMULATIVE_ATTRIBUTES = (
        "current_summation_delivered",
        "current_summation_received",
    )
    _VIRTUAL_DISCRETE_ATTRIBUTES = ("instantaneous_demand",)

    def update_attribute(self, attr_name: str, value) -> None:
        attr_name, value = self.directional_attribute_handler(attr_name, value)
        if self.power_flow_preempt_handler(attr_name, value) == "hold":
            return
        super().update_attribute(attr_name, value)
        self.update_virtual_cluster(attr_name)


class TuyaEnergyMeterManufCluster(NoManufacturerCluster, TuyaMCUCluster):
    """Manufactuter cluster for Tuya Energy Meter devices."""

    attributes: Dict[int, tuple] = {
        AC_FREQUENCY_COEF: ("ac_frequency_coefficient", t.uint32_t_be, True),
        CURRENT_SUMM_DELIVERED_COEF: (
            "current_summ_delivered_coefficient",
            t.uint32_t_be,
            True,
        ),
        CURRENT_SUMM_DELIVERED_COEF_B: (
            "current_summ_delivered_coefficient_ch_b",
            t.uint32_t_be,
            True,
        ),
        CURRENT_SUMM_RECEIVED_COEF: (
            "current_summ_received_coefficient",
            t.uint32_t_be,
            True,
        ),
        CURRENT_SUMM_RECEIVED_COEF_B: (
            "current_summ_received_coefficient_ch_b",
            t.uint32_t_be,
            True,
        ),
        INSTANTANEOUS_DEMAND_COEF: (
            "instantaneous_demand_coefficient",
            t.uint32_t_be,
            True,
        ),
        INSTANTANEOUS_DEMAND_COEF_B: (
            "instantaneous_demand_coefficient_ch_b",
            t.uint32_t_be,
            True,
        ),
        POWER_FLOW: ("power_flow", PowerFlow, True),
        POWER_FLOW_B: ("power_flow_ch_b", PowerFlow, True),
        RMS_CURRENT_COEF: ("rms_current_coefficient", t.uint32_t_be, True),
        RMS_CURRENT_COEF_B: (
            "rms_current_coefficient_ch_b",
            t.uint32_t_be,
            True,
        ),
        RMS_VOLTAGE_COEF: ("rms_voltage_coefficient", t.uint32_t_be, True),
        CHANNEL_CONFIGURATION: (
            "channel_configuration",
            ChannelConfiguration,
            True,
        ),
        UPDATE_PERIOD: ("update_period", t.uint32_t_be, True),
        POWER_FLOW_PREEMPT: ("power_flow_preempt", t.Bool, True),
        SUPPRESS_NEGATIVE: ("suppress_negative", t.Bool, True),
        SUPPRESS_NEGATIVE_B: ("suppress_negative_ch_b", t.Bool, True),
    }

    _LOCAL_ATTRIBUTES: Dict[int, tuple] = {
        CHANNEL_CONFIGURATION: (
            ChannelConfiguration_1CH,
            ChannelConfiguration_1CHB,
            ChannelConfiguration_2CH,
            ChannelConfiguration_2CHB,
        ),
        POWER_FLOW_PREEMPT: (ChannelConfiguration_2CHB,),
        SUPPRESS_NEGATIVE: (ChannelConfiguration_1CHB, ChannelConfiguration_2CHB),
        SUPPRESS_NEGATIVE_B: (ChannelConfiguration_2CHB,),
    }

    def __init__(self, *args, **kwargs):
        """Init cluster."""
        super().__init__(*args, **kwargs)
        self._local_attribute_defaults()

    def __init_subclass__(cls, configuration_type=None) -> None:
        """Init cluster subclass."""
        cls.attributes = {**TuyaMCUCluster.attributes}
        cls._device_attribute_setup(cls)
        cls._local_attribute_setup(cls, configuration_type)
        super().__init_subclass__()

    def _device_attribute_setup(cls) -> None:
        """Setup mapped datapoints for the device."""

        # Allows clusters to check whether an attribute is provided natively
        cls.device_reported_attributes = tuple(
            (dp_map.ep_attribute, attr_name, dp_map.endpoint_id or 1)
            for dp_map in cls.dp_to_attribute.values()
            for attr_name in (
                dp_map.attribute_name
                if isinstance(dp_map.attribute_name, tuple)
                else (dp_map.attribute_name,)
            )
        )

        # Setup MCU attributes for mapped device datapoints
        attr_name_to_id = {
            attr[0] if isinstance(attr, tuple) else attr.name: attr_id
            for attr_id, attr in TuyaEnergyMeterManufCluster.attributes.items()
        }
        for ep_attribute, attr_name, _endpoint_id in cls.device_reported_attributes:
            if ep_attribute != TuyaMCUCluster.ep_attribute:
                continue
            attr_id = attr_name_to_id.get(attr_name)
            if attr_id is not None:
                cls.attributes[attr_id] = TuyaEnergyMeterManufCluster.attributes[
                    attr_id
                ]

    def _local_attribute_defaults(self) -> None:
        """Set default initial values for local configuration attributes."""

        defaults = {}
        for attr_id in set(self._LOCAL_ATTRIBUTES).intersection(set(self.attributes)):
            default = getattr(self.attributes[attr_id].type, "DEFAULT", None)
            if default is not None and self.get(self.attributes[attr_id].name) is None:
                defaults[attr_id] = default
        if defaults:
            self.create_catching_task(self.write_attributes(defaults))

    def _local_attribute_setup(cls, configuration_type) -> None:
        """Setup local attributes for the device channel configuration type."""

        if configuration_type is None:
            return
        for attr_id, config_types in cls._LOCAL_ATTRIBUTES.items():
            if configuration_type not in config_types:
                continue
            cls.attributes[attr_id] = TuyaEnergyMeterManufCluster.attributes[attr_id]

        if CHANNEL_CONFIGURATION not in cls.attributes:
            return
        config_attr = cls.attributes[CHANNEL_CONFIGURATION]
        cls.attributes[CHANNEL_CONFIGURATION] = (
            config_attr.name,
            configuration_type,
            config_attr.is_manufacturer_specific,
        )

    def get_optional(self, attr_name, default=None):
        """Returns the default value if an attribute is undefined."""
        try:
            return self.get(attr_name, default)
        except KeyError:
            return default

    async def write_attributes(self, attributes, manufacturer=None):
        """Handle writes to local configuration attributes."""

        local_attributes = {}
        for attr_id in set(self._LOCAL_ATTRIBUTES).intersection(set(attributes)):
            local_attributes[attr_id] = self.attributes[attr_id].type(
                attributes.pop(attr_id)
            )
        await TuyaLocalCluster.write_attributes(self, local_attributes, manufacturer)
        return await super().write_attributes(attributes, manufacturer)


class TuyaEnergyMeterManufCluster_1CH(
    TuyaEnergyMeterManufCluster, configuration_type=ChannelConfiguration_1CH
):
    """Tuya Energy Meter manufacturer cluster."""

    TUYA_DP_CURRENT_SUMM_DELIVERED = 101
    TUYA_DP_INSTANTANEOUS_DEMAND_UINT = 19
    TUYA_DP_RMS_CURRENT = 18
    TUYA_DP_RMS_VOLTAGE = 20

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        TUYA_DP_CURRENT_SUMM_DELIVERED: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "current_summ_delivered",
            converter=lambda x: x * 10,
        ),
        TUYA_DP_INSTANTANEOUS_DEMAND_UINT: DPToAttributeMapping(
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
        TUYA_DP_INSTANTANEOUS_DEMAND_UINT: "_dp_2_attr_update",
        TUYA_DP_RMS_CURRENT: "_dp_2_attr_update",
        TUYA_DP_RMS_VOLTAGE: "_dp_2_attr_update",
    }


class TuyaEnergyMeterManufCluster_1CHB(
    TuyaEnergyMeterManufCluster,
    configuration_type=ChannelConfiguration_1CHB,
):
    """Tuya Energy Meter bidirectional manufacturer cluster."""

    TUYA_DP_CURRENT_SUMM_DELIVERED = 1
    TUYA_DP_CURRENT_SUMM_RECEIVED = 2
    TUYA_DP_INSTANTANEOUS_DEMAND_UINT = 101
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
        TUYA_DP_INSTANTANEOUS_DEMAND_UINT: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "instantaneous_demand" + UNSIGNED_POWER_ATTR_SUFFIX,
            converter=lambda x: x * 10,
        ),
        TUYA_DP_POWER_FLOW: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "power_flow",
            converter=lambda x: PowerFlow(x),
        ),
        TUYA_DP_POWER_PHASE: DPToAttributeMapping(
            TuyaElectricalMeasurement.ep_attribute,
            (
                "rms_voltage",
                "rms_current",
                "active_power" + UNSIGNED_POWER_ATTR_SUFFIX,
            ),
            converter=lambda x: TuyaPowerPhase.variant_3(x),
        ),
    }

    data_point_handlers = {
        TUYA_DP_CURRENT_SUMM_DELIVERED: "_dp_2_attr_update",
        TUYA_DP_CURRENT_SUMM_RECEIVED: "_dp_2_attr_update",
        TUYA_DP_INSTANTANEOUS_DEMAND_UINT: "_dp_2_attr_update",
        TUYA_DP_POWER_FLOW: "_dp_2_attr_update",
        TUYA_DP_POWER_PHASE: "_dp_2_attr_update",
    }


class TuyaEnergyMeterManufCluster_2CHB_MatSee(
    TuyaEnergyMeterManufCluster, configuration_type=ChannelConfiguration_2CHB
):
    """MatSee Plus Tuya Energy Meter bidirectional 2 clamp manufacturer cluster."""

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
    TUYA_DP_INSTANTANEOUS_DEMAND_UINT = 101
    TUYA_DP_INSTANTANEOUS_DEMAND_UINT_B = 105
    TUYA_DP_INSTANTANEOUS_DEMAND_COEF = 118
    TUYA_DP_INSTANTANEOUS_DEMAND_COEF_B = 124
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
            "current_summ_delivered_coefficient_ch_b",
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
            "current_summ_received_coefficient_ch_b",
        ),
        TUYA_DP_INSTANTANEOUS_DEMAND_UINT: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "instantaneous_demand" + UNSIGNED_POWER_ATTR_SUFFIX,
        ),
        TUYA_DP_INSTANTANEOUS_DEMAND_UINT_B: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "instantaneous_demand" + UNSIGNED_POWER_ATTR_SUFFIX,
            endpoint_id=2,
        ),
        TUYA_DP_INSTANTANEOUS_DEMAND_COEF: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "instantaneous_demand_coefficient",
        ),
        TUYA_DP_INSTANTANEOUS_DEMAND_COEF_B: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "instantaneous_demand_coefficient_ch_b",
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
            "power_flow_ch_b",
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
            "rms_current_coefficient_ch_b",
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
        TUYA_DP_INSTANTANEOUS_DEMAND_UINT: "_dp_2_attr_update",
        TUYA_DP_INSTANTANEOUS_DEMAND_UINT_B: "_dp_2_attr_update",
        TUYA_DP_INSTANTANEOUS_DEMAND_COEF: "_dp_2_attr_update",
        TUYA_DP_INSTANTANEOUS_DEMAND_COEF_B: "_dp_2_attr_update",
        TUYA_DP_POWER_FACTOR: "_dp_2_attr_update",
        TUYA_DP_POWER_FACTOR_B: "_dp_2_attr_update",
        TUYA_DP_POWER_FLOW: "_dp_2_attr_update",
        TUYA_DP_POWER_FLOW_B: "_dp_2_attr_update",
        TUYA_DP_RMS_CURRENT: "_dp_2_attr_update",
        TUYA_DP_RMS_CURRENT_B: "_dp_2_attr_update",
        TUYA_DP_RMS_CURRENT_COEF: "_dp_2_attr_update",
        TUYA_DP_RMS_CURRENT_COEF_B: "_dp_2_attr_update",
        TUYA_DP_RMS_VOLTAGE: "_dp_2_attr_update",
        TUYA_DP_RMS_VOLTAGE_COEF: "_dp_2_attr_update",
        TUYA_DP_UPDATE_PERIOD: "_dp_2_attr_update",
    }


class TuyaEnergyMeterManufCluster_2CHB_EARU(
    TuyaEnergyMeterManufCluster, configuration_type=ChannelConfiguration_2CHB
):
    """EARU Tuya Energy Meter bidirectional 2 clamp manufacturer cluster."""

    TUYA_DP_AC_FREQUENCY = 113
    TUYA_DP_CURRENT_SUMM_DELIVERED = 101
    TUYA_DP_CURRENT_SUMM_DELIVERED_B = 103
    TUYA_DP_CURRENT_SUMM_RECEIVED = 102
    TUYA_DP_CURRENT_SUMM_RECEIVED_B = 104
    TUYA_DP_INSTANTANEOUS_DEMAND = 108
    TUYA_DP_INSTANTANEOUS_DEMAND_B = 111
    TUYA_DP_POWER_FACTOR = 109
    TUYA_DP_POWER_FACTOR_B = 112
    TUYA_DP_POWER_FLOW = 114
    TUYA_DP_POWER_FLOW_B = 115
    TUYA_DP_UPDATE_PERIOD = 116
    TUYA_DP_RMS_CURRENT = 107
    TUYA_DP_RMS_CURRENT_B = 110
    TUYA_DP_RMS_VOLTAGE = 106

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        TUYA_DP_AC_FREQUENCY: DPToAttributeMapping(
            TuyaElectricalMeasurement.ep_attribute,
            "ac_frequency",
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
        TUYA_DP_INSTANTANEOUS_DEMAND: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "instantaneous_demand",
        ),
        TUYA_DP_INSTANTANEOUS_DEMAND_B: DPToAttributeMapping(
            TuyaMetering.ep_attribute,
            "instantaneous_demand",
            endpoint_id=2,
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
            "power_flow_ch_b",
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
        TUYA_DP_RMS_VOLTAGE: DPToAttributeMapping(
            TuyaElectricalMeasurement.ep_attribute,
            "rms_voltage",
        ),
        TUYA_DP_UPDATE_PERIOD: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "update_period",
        ),
    }

    data_point_handlers = {
        TUYA_DP_AC_FREQUENCY: "_dp_2_attr_update",
        TUYA_DP_CURRENT_SUMM_DELIVERED: "_dp_2_attr_update",
        TUYA_DP_CURRENT_SUMM_DELIVERED_B: "_dp_2_attr_update",
        TUYA_DP_CURRENT_SUMM_RECEIVED: "_dp_2_attr_update",
        TUYA_DP_CURRENT_SUMM_RECEIVED_B: "_dp_2_attr_update",
        TUYA_DP_INSTANTANEOUS_DEMAND: "_dp_2_attr_update",
        TUYA_DP_INSTANTANEOUS_DEMAND_B: "_dp_2_attr_update",
        TUYA_DP_POWER_FACTOR: "_dp_2_attr_update",
        TUYA_DP_POWER_FACTOR_B: "_dp_2_attr_update",
        TUYA_DP_POWER_FLOW: "_dp_2_attr_update",
        TUYA_DP_POWER_FLOW_B: "_dp_2_attr_update",
        TUYA_DP_RMS_CURRENT: "_dp_2_attr_update",
        TUYA_DP_RMS_CURRENT_B: "_dp_2_attr_update",
        TUYA_DP_RMS_VOLTAGE: "_dp_2_attr_update",
        TUYA_DP_UPDATE_PERIOD: "_dp_2_attr_update",
    }


class TuyaEnergyMeter1Clamp(CustomDevice):
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
                    TuyaEnergyMeterManufCluster_1CH,
                    TuyaElectricalMeasurement,
                    TuyaMetering,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }


class TuyaEnergyMeterB1ClampZGP(CustomDevice):
    """Tuya Bidirectional 1 Clamp Energy Meter with Zigbee Green Power."""

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
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
            242: {
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
                    TuyaEnergyMeterManufCluster_1CHB,
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


class TuyaEnergyMeter1CHB(CustomDevice):
    """Tuya EARU PC311-Z-TY Bidirectional 2 Clamp Energy Meter."""

    signature = {
        MODELS_INFO: [("_TZE200_rks0sgb7", "TS0601")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=51
            # device_version=1
            # input_clusters: [0, 4, 5, 61184, 65382]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaMCUCluster.cluster_id,
                    EARU_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
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
                    TuyaEnergyMeterManufCluster_2CHB_EARU,
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
                    TuyaElectricalMeasurement,
                    TuyaMetering,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class TuyaEnergyMeter1CHBZGP(CustomDevice):
    """Tuya PJ-1203A Bidirectional 2 Clamp Energy Meter with Zigbee Green Power."""

    signature = {
        MODELS_INFO: [("_TZE204_81yrt3lo", "TS0601")],
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
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
            242: {
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
                    TuyaEnergyMeterManufCluster_2CHB_MatSee,
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
                    TuyaElectricalMeasurement,
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
