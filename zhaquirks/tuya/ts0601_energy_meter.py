"""Tuya Energy Meter."""

from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple, Type, Union

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, GreenPowerProxy, Groups, Ota, Scenes, Time
from zigpy.zcl.foundation import ZCLAttributeDef

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

# from zigpy.zcl.clusters.homeautomation import MeasurementType


# Manufacturer cluster identifiers for device signatures
EARU_MANUFACTURER_CLUSTER_ID = 0xFF66

# Offset of 512 (0x200) for transating DP ID to Attribute ID
# Attribute IDs don't need to match every device's specific values
DP_ATTR_OFFSET = 512

# Power direction acttributes
POWER_FLOW = 102 + DP_ATTR_OFFSET  # PowerFlow (0: forward, 1: reverse)
POWER_FLOW_B = 104 + DP_ATTR_OFFSET  # PowerFlow (0: forward, 1: reverse)

# Calibration attributes
AC_FREQUENCY_COEF = 122 + DP_ATTR_OFFSET  # uint32_t_be
CURRENT_SUMM_DELIVERED_COEF = 119 + DP_ATTR_OFFSET  # uint32_t_be
CURRENT_SUMM_DELIVERED_COEF_B = 125 + DP_ATTR_OFFSET  # uint32_t_be
CURRENT_SUMM_RECEIVED_COEF = 127 + DP_ATTR_OFFSET  # uint32_t_be
CURRENT_SUMM_RECEIVED_COEF_B = 128 + DP_ATTR_OFFSET  # uint32_t_be
INSTANTANEOUS_DEMAND_COEF = 118 + DP_ATTR_OFFSET  # uint32_t_be
INSTANTANEOUS_DEMAND_COEF_B = 124 + DP_ATTR_OFFSET  # uint32_t_be
RMS_CURRENT_COEF = 117 + DP_ATTR_OFFSET  # uint32_t_be
RMS_CURRENT_COEF_B = 123 + DP_ATTR_OFFSET  # uint32_t_be
RMS_VOLTAGE_COEF = 116 + DP_ATTR_OFFSET  # uint32_t_be

# Device configuration attributes
UPDATE_PERIOD = 129 + DP_ATTR_OFFSET  # uint32_t_be (3-60 seconds supported)

# Local configuration attributes
CHANNEL_CONFIGURATION = 0x5000
SUPPRESS_REVERSE_FLOW = 0x5010
SUPPRESS_REVERSE_FLOW_B = 0x5011
POWER_FLOW_PREEMPT = 0x5020

# Suffix for device attributes which need power flow direction applied
UNSIGNED_POWER_ATTR_SUFFIX = "_attr_unsigned"

# Default Tuya MCU cluster endpoint_id
TUYA_MCU_ENDPOINT_ID = 1


def is_type_uint(attr_type: Type) -> bool:
    """True if the specified attribute type is an unsigned integer."""
    return issubclass(attr_type, t.uint_t)


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
    """Enums for for all energy meter configurations."""

    NONE = 0x00
    A_PLUS_B = 0x01
    A_MINUS_B = 0x02
    GRID_PLUS_PRODUCTION = 0x03
    CONSUMPTION_MINUS_PRODUCTION = 0x04


class ChannelConfiguration_1CH(t.enum8):
    """Enums for 1 channel energy meter configuration."""

    NONE = ChannelConfiguration.NONE
    DEFAULT = NONE


class ChannelConfiguration_1CHB(t.enum8):
    """Enums for 1 channel bidirectional energy meter configuration."""

    NONE = ChannelConfiguration.NONE
    DEFAULT = NONE


class ChannelConfiguration_2CH(t.enum8):
    """Enums for 2 channel energy meter configuration."""

    A_PLUS_B = ChannelConfiguration.A_PLUS_B
    A_MINUS_B = ChannelConfiguration.A_MINUS_B
    CONSUMPTION_MINUS_PRODUCTION = ChannelConfiguration.CONSUMPTION_MINUS_PRODUCTION
    DEFAULT = CONSUMPTION_MINUS_PRODUCTION


class ChannelConfiguration_2CHB(t.enum8):
    """Enums for 2 channel bidirectional energy meter configuration."""

    A_PLUS_B = ChannelConfiguration.A_PLUS_B
    A_MINUS_B = ChannelConfiguration.A_MINUS_B
    GRID_PLUS_PRODUCTION = ChannelConfiguration.GRID_PLUS_PRODUCTION
    CONSUMPTION_MINUS_PRODUCTION = ChannelConfiguration.CONSUMPTION_MINUS_PRODUCTION
    DEFAULT = GRID_PLUS_PRODUCTION


class MeasurementType(
    t.bitmap32
):  # Would like to import this from zigpy.zcl.clusters.homeautomation, but its offset is currently incorrect
    """Defines the measurement type bits for the ElectricalMeasurement cluster."""

    Active_measurement_AC = 1 << 0
    Reactive_measurement_AC = 1 << 1
    Apparent_measurement_AC = 1 << 2
    Phase_A_measurement = 1 << 3
    Phase_B_measurement = 1 << 4
    Phase_C_measurement = 1 << 5
    DC_measurement = 1 << 6
    Harmonics_measurement = 1 << 7
    Power_quality_measurement = 1 << 8


class Metering:
    """Functions for use with the ZCL Metering cluster."""

    @staticmethod
    def format(
        int_digits: int, dec_digits: int, suppress_leading_zeros: bool = True
    ) -> int:
        """Returns the formatter value for summation and demand Metering attributes."""
        assert 0 <= int_digits <= 7, "int_digits must be within range of 0 to 7."
        assert 0 <= dec_digits <= 7, "dec_digits must be within range of 0 to 7."
        return (suppress_leading_zeros << 6) | (int_digits << 3) | dec_digits


class PowerFlow(t.enum1):
    """Indicates power flow direction."""

    FORWARD = 0x0
    REVERSE = 0x1

    @classmethod
    def align_value(cls, value: int, power_flow=None) -> int:
        """Aligns the value with the power_flow direction."""
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
    def variant_1(value) -> Tuple[t.uint_t, t.uint_t]:
        voltage = value[14] | value[13] << 8
        current = value[12] | value[11] << 8
        return voltage, current

    @staticmethod
    def variant_2(value) -> Tuple[t.uint_t, t.uint_t, int]:
        voltage = value[1] | value[0] << 8
        current = value[4] | value[3] << 8
        power = value[7] | value[6] << 8
        return voltage, current, power * 10

    @staticmethod
    def variant_3(value) -> Tuple[t.uint_t, t.uint_t, int]:
        voltage = (value[0] << 8) | value[1]
        current = (value[2] << 16) | (value[3] << 8) | value[4]
        power = (value[5] << 16) | (value[6] << 8) | value[7]
        return voltage, current, power * 10


class PowerCalculation:
    """Methods for calculating power values."""

    @staticmethod
    def active_power_from_apparent_power_power_factor_and_power_flow(
        apparent_power: Optional[t.uint_t],
        power_factor: Optional[t.int_t],
        power_flow: Optional[PowerFlow] = None,
    ) -> Optional[t.int_t]:
        if apparent_power is None or power_factor is None:
            return
        power_factor *= 0.01
        return round(apparent_power * abs(power_factor) * (-1 if power_flow else 1))

    @staticmethod
    def apparent_power_from_active_power_and_power_factor(
        active_power: Optional[t.int_t], power_factor: Optional[t.int_t]
    ) -> Optional[t.uint_t]:
        if active_power is None or power_factor is None:
            return
        power_factor *= 0.01
        return round(abs(active_power) / abs(power_factor))

    @staticmethod
    def apparent_power_from_rms_current_and_rms_voltage(
        rms_current: Optional[t.uint_t],
        rms_voltage: Optional[t.uint_t],
        ac_current_divisor: int = 1,
        ac_current_multiplier: int = 1,
        ac_voltage_divisor: int = 1,
        ac_voltage_multiplier: int = 1,
        ac_power_divisor: int = 1,
        ac_power_multiplier: int = 1,
    ) -> Optional[t.uint_t]:
        if rms_current is None or rms_voltage is None:
            return
        return round(
            (rms_current * ac_current_multiplier / ac_current_divisor)
            * (rms_voltage * ac_voltage_multiplier / ac_voltage_divisor)
            * ac_power_divisor
            / ac_power_multiplier
        )

    @staticmethod
    def reactive_power_from_apparent_power_and_power_factor(
        apparent_power: Optional[t.uint_t], power_factor: Optional[t.int_t]
    ) -> Optional[t.int_t]:
        if apparent_power is None or power_factor is None:
            return
        power_factor *= 0.01
        return round(
            (apparent_power * (1 - power_factor**2) ** 0.5)
            * (-1 if power_factor < 0 else 1)
        )


class LocalClusterAttributes:
    """Methods for handling local configuration attributes on device."""

    _ATTRIBUTE_DEFAULTS: Dict[int, Any] = {}
    _LOCAL_ATTRIBUTES: Tuple[int] = ()

    def _attr_default(
        self, attrid: Union[str, int], default: Optional[Any] = None
    ) -> Optional[Any]:
        """Returns an attribute's default value."""
        attr_def = self.find_attribute(attrid)
        return self._ATTRIBUTE_DEFAULTS.get(
            attr_def.id, getattr(attr_def.type, "DEFAULT", default)
        )

    def _format_attr_value(self, attrid: Union[str, int], value: Any) -> Optional[Any]:
        """Used to format the input the input value with the attribute's type."""
        try:
            attr_def = self.find_attribute(attrid)
            value = attr_def.type(value)
            return value
        except KeyError:
            self.error("%s is not a valid attribute id", attrid)
        except ValueError as e:
            self.error(
                "Failed to convert attribute %s from %s (%s) to type %s: %s",
                attr_def.id,
                value,
                type(value),
                attr_def.type,
                e,
            )
        return

    def get(self, key: Union[int, str], default: Optional[Any] = None) -> Optional[Any]:
        """Get cached attribute value and fall back to its device/type default if defined."""
        value = super().get(key, default)
        if value is None:
            value = self._attr_default(key, default)
        return value

    async def read_attributes(self, attributes, *args, **kwargs):
        """Handle reads to local configuration attributes."""
        success, failure = await super().read_attributes(attributes, *args, **kwargs)
        for attrid in set(self._LOCAL_ATTRIBUTES).intersection(set(attributes)):
            if attrid not in success:
                default = self._attr_default(attrid)
                if default is None:
                    continue
                success[attrid] = default
                failure.pop(attrid, None)
            if success[attrid] not in (None, ""):
                success[attrid] = self.attributes[attrid].type(success[attrid])
        return success, failure

    async def write_attributes(self, attributes, *args, **kwargs):
        """Handle writes to local configuration attributes."""
        local_attributes = {}
        for attrid in set(self._LOCAL_ATTRIBUTES).intersection(set(attributes)):
            value = attributes.pop(attrid)
            if value in (None, ""):
                local_attributes[attrid] = None
                continue
            value = self._format_attr_value(attrid, value)
            if value is not None:
                local_attributes[attrid] = value
        await TuyaLocalCluster.write_attributes(self, local_attributes, *args, **kwargs)
        return await super().write_attributes(attributes, *args, **kwargs)


class TuyaEnergyMeterManufCluster(
    LocalClusterAttributes, NoManufacturerCluster, TuyaMCUCluster
):
    """Manufactuter cluster for Tuya energy meter devices."""

    _CHANNEL_CONFIGURATION_ATTRIBUTES: Dict[Type, Tuple[int]] = {
        ChannelConfiguration_1CHB: (SUPPRESS_REVERSE_FLOW,),
        ChannelConfiguration_2CHB: (
            POWER_FLOW_PREEMPT,
            SUPPRESS_REVERSE_FLOW,
            SUPPRESS_REVERSE_FLOW_B,
        ),
    }

    _LOCAL_ATTRIBUTES: Tuple[int] = (
        CHANNEL_CONFIGURATION,
        POWER_FLOW_PREEMPT,
        SUPPRESS_REVERSE_FLOW,
        SUPPRESS_REVERSE_FLOW_B,
    )

    attributes: Dict[int, ZCLAttributeDef] = {
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
        SUPPRESS_REVERSE_FLOW: ("suppress_reverse_flow", t.Bool, True),
        SUPPRESS_REVERSE_FLOW_B: ("suppress_reverse_flow_ch_b", t.Bool, True),
    }

    def get_optional(
        self, key: Union[int, str], default: Optional[Any] = None
    ) -> Optional[Any]:
        """Returns the provided default value or None if an attribute is undefined."""
        try:
            return self.get(key, default)
        except KeyError:
            return default

    def __init_subclass__(cls, configuration_type: Type) -> None:
        """Init cluster subclass."""
        cls.attributes = {**TuyaMCUCluster.attributes}
        cls._populate_mapped_attributes_lookup(cls)
        cls._setup_channel_config_attributes(cls, configuration_type)
        cls._setup_device_attributes(cls)
        super().__init_subclass__()

    def _populate_mapped_attributes_lookup(cls) -> None:
        """Stores a tuple for each cluster attribute mapped from MCU data points."""
        cls.mapped_attributes: Tuple[Tuple[str, str, int]] = tuple(
            (dp_map.ep_attribute, attr_name, dp_map.endpoint_id or TUYA_MCU_ENDPOINT_ID)
            for dp_map in cls.dp_to_attribute.values()
            for attr_name in (
                dp_map.attribute_name
                if isinstance(dp_map.attribute_name, tuple)
                else (dp_map.attribute_name,)
            )
        )

    def _setup_channel_config_attributes(cls, configuration_type: Type) -> None:
        """Setup local attributes for the device channel configuration type."""
        config_type_attr = TuyaEnergyMeterManufCluster.attributes[CHANNEL_CONFIGURATION]
        cls.attributes[CHANNEL_CONFIGURATION] = (
            config_type_attr.name,
            configuration_type,
            config_type_attr.is_manufacturer_specific,
        )
        config_attr = cls._CHANNEL_CONFIGURATION_ATTRIBUTES.get(configuration_type, ())
        for attrid in config_attr:
            cls.attributes[attrid] = TuyaEnergyMeterManufCluster.attributes[attrid]

    def _setup_device_attributes(cls) -> None:
        """Setup manufacturer cluster attributes for mapped device data points."""
        attr_name_to_id: Dict[str, int] = {
            attr[0] if isinstance(attr, tuple) else attr.name: attrid
            for attrid, attr in TuyaEnergyMeterManufCluster.attributes.items()
        }
        for ep_attribute, attr_name, endpoint_id in cls.mapped_attributes:
            if ep_attribute != cls.ep_attribute:
                continue
            assert (
                endpoint_id == 1
            ), "Check endpoint_id of TuyaEnergyMeterManufCluster dp_to_attribute."
            attrid = attr_name_to_id.get(attr_name)
            if attrid is not None:
                cls.attributes[attrid] = TuyaEnergyMeterManufCluster.attributes[attrid]


class EnergyMeterChannel:
    """Methods and properties for energy meter channel clusters."""

    _ENDPOINT_TO_CHANNEL: Dict[Tuple[Type, int], Channel] = {
        (ChannelConfiguration_1CH, 1): Channel.A,
        (ChannelConfiguration_1CHB, 1): Channel.A,
        (ChannelConfiguration_2CH, 1): Channel.A,
        (ChannelConfiguration_2CH, 2): Channel.B,
        (ChannelConfiguration_2CH, 3): Channel.AB,
        (ChannelConfiguration_2CHB, 1): Channel.A,
        (ChannelConfiguration_2CHB, 2): Channel.B,
        (ChannelConfiguration_2CHB, 3): Channel.AB,
    }

    _EXTENSIVE_ATTRIBUTES: Tuple[str] = ()
    _INTENSIVE_ATTRIBUTES: Tuple[str] = ()
    _CUMULATIVE_FORWARD_ATTRIBUTES: Tuple[str] = ()
    _CUMULATIVE_REVERSE_ATTRIBUTES: Tuple[str] = ()
    _INVERSE_ATTRIBUTES: Dict[str, str] = {}

    def __init__(self, *args, **kwargs):
        """Init."""
        self._CHANNEL_TO_ENDPOINT: Dict[Tuple[Type, Channel], int] = {
            (k[0], v): k[1] for k, v in self._ENDPOINT_TO_CHANNEL.items()
        }
        self._INVERSE_ATTRIBUTES.update(
            {v: k for k, v in dict(self._INVERSE_ATTRIBUTES).items()}
        )
        self._CUMULATIVE_ATTRIBUTES = (
            self._CUMULATIVE_FORWARD_ATTRIBUTES + self._CUMULATIVE_REVERSE_ATTRIBUTES
        )
        super().__init__(*args, **kwargs)

    @property
    def channel(self) -> Optional[str]:
        """Returns the cluster's channel."""
        return self._ENDPOINT_TO_CHANNEL.get(
            (self.channel_configuration_type, self.endpoint.endpoint_id), None
        )

    @property
    def channel_configuration(self) -> Optional[ChannelConfiguration]:
        """Returns the device's current channel configuration."""
        return self.manufacturer_cluster.get("channel_configuration")

    @property
    def channel_configuration_type(self) -> Type:
        """Returns the device's channel configuration type."""
        return self.manufacturer_cluster.AttributeDefs.channel_configuration.type

    @property
    def manufacturer_cluster(self) -> TuyaEnergyMeterManufCluster:
        """Returns the device's manufacturer cluster."""
        return getattr(
            self.endpoint.device.endpoints[TUYA_MCU_ENDPOINT_ID],
            TuyaEnergyMeterManufCluster.ep_attribute,
        )

    def attr_present(
        self,
        *attr_names: str,
        ep_attribute: Optional[str] = None,
        endpoint_id: Optional[int] = None,
    ) -> bool:
        """Returns True if any of the specified attributes are provided by the device."""
        ep_attribute = ep_attribute or self.ep_attribute
        endpoint_id = endpoint_id or self.endpoint.endpoint_id
        return any(
            attr in self.manufacturer_cluster.mapped_attributes
            for attr in tuple(
                (ep_attribute, attr_name, endpoint_id) for attr_name in attr_names
            )
        )

    def attr_type(self, attr_name: str) -> Type:
        """Returns the type of the specified attribute."""
        return getattr(self.AttributeDefs, attr_name).type

    def get_cluster(
        self,
        channel_or_endpoint_id: Union[Channel, int],
        ep_attribute: Optional[str] = None,
    ):
        """Returns the device cluster for the given channel or endpoint."""
        if channel_or_endpoint_id in Channel:
            channel_or_endpoint_id = self._CHANNEL_TO_ENDPOINT.get(
                (self.channel_configuration_type, channel_or_endpoint_id), None
            )
        assert channel_or_endpoint_id is not None, "Invalid channel_or_endpoint_id."
        return getattr(
            self.endpoint.device.endpoints[channel_or_endpoint_id],
            ep_attribute or self.ep_attribute,
        )

    def update_calculated_attribute(self, attr_name: str, calculated_value) -> None:
        """Updates the specified attribute if the calculated value is valid."""
        if calculated_value is None:
            return
        self.update_attribute(attr_name, calculated_value)


class EnergyMeterPowerFlow(EnergyMeterChannel):
    """Methods and properties for handling power flow on Tuya energy meter devices."""

    @property
    def power_flow(self) -> Optional[PowerFlow]:
        """Returns the channel's current power flow direction."""
        return self.manufacturer_cluster.get_optional(
            Channel.attr_with_channel("power_flow", self.channel)
        )

    @power_flow.setter
    def power_flow(self, value: PowerFlow) -> None:
        """Updates the channel's power flow direction."""
        self.manufacturer_cluster.update_attribute(
            Channel.attr_with_channel("power_flow", self.channel), value
        )

    @property
    def suppress_reverse_flow(self) -> bool:
        """Returns True if suppress_reverse_flow is enabled for the channel."""
        return self.manufacturer_cluster.get_optional(
            Channel.attr_with_channel("suppress_reverse_flow", self.channel), False
        )

    def _align_unsigned_attribute_with_power_flow(
        self, attr_name: str, value
    ) -> Tuple[str, Any]:
        """Attributes marked as unsigned are aligned with the current power flow direction."""
        if attr_name.endswith(UNSIGNED_POWER_ATTR_SUFFIX):
            attr_name = attr_name.removesuffix(UNSIGNED_POWER_ATTR_SUFFIX)
            value = PowerFlow.align_value(value, self.power_flow)
        return attr_name, value

    def _suppress_reverse_power_flow(self, attr_name: str, value) -> Optional[Any]:
        """Returns 0 if suppress_reverse_flow is enabled for the channel and power flow is reverse."""
        if self.suppress_reverse_flow and (
            attr_name in self._EXTENSIVE_ATTRIBUTES
            and self.power_flow == PowerFlow.REVERSE
            or attr_name in self._CUMULATIVE_REVERSE_ATTRIBUTES
        ):
            value = 0
        return value

    def power_flow_handler(self, attr_name: str, value) -> Tuple[str, Any]:
        """Orchestrates processing of directional attributes."""
        attr_name, value = self._align_unsigned_attribute_with_power_flow(
            attr_name, value
        )
        value = self._suppress_reverse_power_flow(attr_name, value)
        return attr_name, value


class PowerFlowPreemptConfiguration:
    """Contains the parameters for preempting power_flow direction."""

    def __init__(
        self,
        source_channels: tuple = (),
        trigger_channel: Optional[Channel] = None,
        preempt_method: Optional[Callable] = None,
    ) -> None:
        self.source_channels = source_channels
        self.trigger_channel = trigger_channel
        self.preempt_method = preempt_method


class PowerFlowPreempt(EnergyMeterPowerFlow, EnergyMeterChannel):
    """Logic for preempting delayed power flow direction change on 2 channel devices."""

    HOLD = "hold"
    PREEMPT = "preempt"
    RELEASE = "release"

    @property
    def power_flow_preempt(self) -> bool:
        """Returns True if power_flow_preempt is enabled for the device."""
        return self.manufacturer_cluster.get_optional("power_flow_preempt", False)

    def __init__(self, *args, **kwargs):
        """Init."""
        self._preempt_values: Dict[str, Optional[int]] = {}
        super().__init__(*args, **kwargs)

    def _preempt_grid_plus_production(self, attr_name: str) -> None:
        """Power flow preempt method for grid_plus_production configured devices."""
        cluster_a = self.get_cluster(Channel.A)
        cluster_b = self.get_cluster(Channel.B)
        value_a = cluster_a._get_preempt_value(attr_name)
        value_b = cluster_b._get_preempt_value(attr_name)
        if None in (value_a, value_b):
            return
        cluster_a.power_flow = (
            PowerFlow.FORWARD
            if cluster_a.power_flow == PowerFlow.REVERSE and abs(value_a) > abs(value_b)
            else cluster_a.power_flow
        )
        cluster_b.power_flow = (
            PowerFlow.FORWARD
            if cluster_b.power_flow == PowerFlow.REVERSE and abs(value_b) > abs(value_a)
            else cluster_b.power_flow
        )

    _PREEMPT_CONFIGURATION: Dict[
        ChannelConfiguration, PowerFlowPreemptConfiguration
    ] = {
        ChannelConfiguration.GRID_PLUS_PRODUCTION: PowerFlowPreemptConfiguration(
            (Channel.A, Channel.B),
            Channel.B,
            _preempt_grid_plus_production,
        ),
    }

    def _preempt_action(
        self, attr_name: str, value: int, trigger_channel: Channel
    ) -> str:
        """Returns the action for the power flow preempt handler."""
        if self.channel == trigger_channel:
            return self.PREEMPT
        if self._get_preempt_value(attr_name) != value:
            return self.HOLD
        return self.RELEASE

    def _get_preempt_value(self, attr_name: str) -> Optional[int]:
        """Retrieves the value which was held for consideration in the preempt method."""
        return self._preempt_values.get(attr_name, None)

    def _store_preempt_value(self, attr_name: str, value: Optional[int]) -> None:
        """Stores the value for consideration in the preempt method."""
        self._preempt_values[attr_name] = value

    def _release_preempt_values(
        self, attr_name: str, source_channels: Tuple[Channel], trigger_channel: Channel
    ) -> None:
        """Releases held values to update the cluster attributes following the preempt method."""
        for channel in source_channels:
            cluster = self.get_cluster(channel)
            if channel != trigger_channel:
                value = cluster._get_preempt_value(attr_name)
                if value is not None:
                    cluster.update_attribute(attr_name, value)
            cluster._store_preempt_value(attr_name, None)

    def power_flow_preempt_handler(self, attr_name: str, value) -> Optional[str]:
        """Compensates for delay in reported power flow direction."""

        if (
            not self.power_flow_preempt
            or attr_name.removesuffix(UNSIGNED_POWER_ATTR_SUFFIX)
            not in self._EXTENSIVE_ATTRIBUTES
            or not self.attr_present(attr_name)
        ):
            return

        config = self._PREEMPT_CONFIGURATION.get(
            self.channel_configuration, PowerFlowPreemptConfiguration()
        )
        if not config.preempt_method or self.channel not in config.source_channels:
            return

        action = self._preempt_action(attr_name, value, config.trigger_channel)
        if action != self.RELEASE:
            self._store_preempt_value(attr_name, value)
        if action != self.PREEMPT:
            return action
        config.preempt_method(self, attr_name)
        self._release_preempt_values(
            attr_name, config.source_channels, config.trigger_channel
        )
        return action


class VirtualChannelConfiguration:
    """Contains the parameters for updating a virtual channel."""

    def __init__(
        self,
        virtual_channel: Optional[Channel] = None,
        source_channels: tuple = (),
        trigger_channel: Optional[Channel] = None,
        discrete_method: Optional[Callable] = None,
        cumulative_method: Optional[Callable] = None,
    ) -> None:
        self.virtual_channel = virtual_channel
        self.source_channels = source_channels
        self.trigger_channel = trigger_channel
        self.discrete_method = discrete_method
        self.cumulative_method = cumulative_method


class VirtualChannel(EnergyMeterPowerFlow, EnergyMeterChannel):
    """Methods and properties for updating virtual energy meter channel attributes."""

    @property
    def virtual_channel(self) -> Optional[Channel]:
        """Returns the virtual channel for the current configuration."""
        return self._VIRTUAL_CHANNEL_CONFIGURATION.get(
            self.channel_configuration,
            VirtualChannelConfiguration(),
        ).virtual_channel

    def __init__(self, *args, **kwargs):
        """Init."""
        self._virtual_channel_stored_values: Dict[str, Dict[str, int]] = {}
        super().__init__(*args, **kwargs)

    def _a_plus_b(self, attr_name: str) -> Optional[int]:
        """Method for calculating virtual channel values in a_plus_b configuration types."""

        cluster_a = self.get_cluster(Channel.A)
        cluster_b = self.get_cluster(Channel.B)
        value_a = cluster_a.get(attr_name)
        value_b = cluster_b.get(attr_name)

        if None in (value_a, value_b):
            return
        if attr_name in self._EXTENSIVE_ATTRIBUTES and is_type_uint(
            self.attr_type(attr_name)
        ):
            value_a = PowerFlow.align_value(value_a, cluster_a.power_flow)
            value_b = PowerFlow.align_value(value_b, cluster_b.power_flow)

        return value_a + value_b

    def _a_minus_b(self, attr_name: str) -> Optional[int]:
        """Method for calculating virtual channel values in a_minus_b configuration types."""

        cluster_a = self.get_cluster(Channel.A)
        cluster_b = self.get_cluster(Channel.B)
        value_a = cluster_a.get(attr_name)
        value_b = cluster_b.get(attr_name)

        if None in (value_a, value_b):
            return
        if attr_name in self._EXTENSIVE_ATTRIBUTES and is_type_uint(
            self.attr_type(attr_name)
        ):
            value_a = PowerFlow.align_value(value_a, cluster_a.power_flow)
            value_b = PowerFlow.align_value(value_b, cluster_b.power_flow)

        return value_a - value_b

    def _cumulative_grid_plus_production(self, attr_name: str) -> Optional[t.uint_t]:
        """Method for calculating cumulative virtual channel values in grid_plus_production configuration."""

        if attr_name in self._CUMULATIVE_REVERSE_ATTRIBUTES:
            return 0
        inv_attr_name = self._INVERSE_ATTRIBUTES.get(attr_name, None)
        assert (
            inv_attr_name is not None
        ), "An inverse attribute must be defined for cumulative values."

        cluster_a = self.get_cluster(Channel.A)
        cluster_b = self.get_cluster(Channel.B)
        value_a = cluster_a.get(attr_name)
        value_a_inv = cluster_a.get(inv_attr_name)
        value_b = cluster_b.get(attr_name)
        value_b_inv = cluster_b.get(inv_attr_name)

        if None in (value_a, value_a_inv, value_b, value_b_inv):
            return
        return (value_a + value_b) - (value_a_inv + value_b_inv)

    def _cumulative_consumption_minus_production(
        self, attr_name: str
    ) -> Optional[t.uint_t]:
        """Method for calculating cumulative virtual channel values in consumption_minus_production configuration."""

        inv_attr_name = self._INVERSE_ATTRIBUTES.get(attr_name, None)
        assert (
            inv_attr_name is not None
        ), "An inverse attribute must be defined for cumulative values."

        cluster_a = self.get_cluster(Channel.A)
        cluster_b = self.get_cluster(Channel.B)
        cluster_ab = self.get_cluster(Channel.AB)
        value_a = cluster_a.get(attr_name)
        value_a_inv = cluster_a.get(inv_attr_name)
        value_b = cluster_b.get(attr_name)
        value_b_inv = cluster_b.get(inv_attr_name)
        value_ab = cluster_ab.get(attr_name, 0)

        value_a_prev = cluster_a._get_previous_value(attr_name)
        value_a_inv_prev = cluster_a._get_previous_value(inv_attr_name, attr_name)
        value_b_prev = cluster_a._get_previous_value(attr_name)
        value_b_inv_prev = cluster_b._get_previous_value(inv_attr_name, attr_name)

        cluster_a._store_current_value(attr_name)
        cluster_a._store_current_value(inv_attr_name, attr_name)
        cluster_b._store_current_value(attr_name)
        cluster_b._store_current_value(inv_attr_name, attr_name)

        if None in (value_a, value_a_inv, value_b, value_b_inv):
            return

        delta = (value_a - value_a_prev) - (value_b - value_b_prev)
        delta_inv = (value_a_inv - value_a_inv_prev) - (value_b_inv - value_b_inv_prev)

        return (
            value_ab + (delta if delta > 0 else 0) - (delta_inv if delta_inv < 0 else 0)
        )

    _VIRTUAL_CHANNEL_CONFIGURATION: Dict[
        ChannelConfiguration, VirtualChannelConfiguration
    ] = {
        ChannelConfiguration.A_PLUS_B: VirtualChannelConfiguration(
            Channel.AB,
            (Channel.A, Channel.B),
            Channel.B,
            _a_plus_b,
            _a_plus_b,
        ),
        ChannelConfiguration.A_MINUS_B: VirtualChannelConfiguration(
            Channel.AB,
            (Channel.A, Channel.B),
            Channel.B,
            _a_minus_b,
            _a_minus_b,
        ),
        ChannelConfiguration.GRID_PLUS_PRODUCTION: VirtualChannelConfiguration(
            Channel.AB,
            (Channel.A, Channel.B),
            Channel.B,
            _a_plus_b,
            _cumulative_grid_plus_production,
        ),
        ChannelConfiguration.CONSUMPTION_MINUS_PRODUCTION: VirtualChannelConfiguration(
            Channel.AB,
            (Channel.A, Channel.B),
            Channel.B,
            _a_minus_b,
            _cumulative_consumption_minus_production,
        ),
    }

    def _get_previous_value(
        self, attr_name: str, child_key: Optional[str] = None
    ) -> Optional[int]:
        """Returns the stored value of the attribute."""
        child_key = child_key if child_key else attr_name
        if attr_name in self._virtual_channel_stored_values:
            return self._virtual_channel_stored_values[attr_name].get(
                child_key, self._virtual_channel_stored_values[attr_name][attr_name]
            )
        else:
            return self.get(attr_name)

    def _store_current_value(
        self, attr_name: str, child_key: Optional[str] = None
    ) -> None:
        """Stores the current value of the attribute."""
        child_key = child_key if child_key else attr_name
        value = self.get(attr_name)
        if attr_name in self._virtual_channel_stored_values:
            self._virtual_channel_stored_values[attr_name][child_key] = value
        else:
            self._virtual_channel_stored_values[attr_name] = {child_key: value}

    def virtual_channel_initial_values(self, attr_name: str, value):
        """Retains the initial attribute value for use in delta calculations."""
        if (
            attr_name in self._CUMULATIVE_ATTRIBUTES
            and ChannelConfiguration.CONSUMPTION_MINUS_PRODUCTION
            in self.channel_configuration_type
            and attr_name not in self._virtual_channel_stored_values
        ):
            self._store_current_value(attr_name)

    def virtual_channel_handler(self, attr_name: str) -> None:
        """Handles updates to a virtual energy meter channel."""

        config = self._VIRTUAL_CHANNEL_CONFIGURATION.get(
            self.channel_configuration,
            VirtualChannelConfiguration(),
        )

        if (
            self.channel not in config.source_channels
            or self.channel != config.trigger_channel
            and attr_name not in self._CUMULATIVE_ATTRIBUTES
        ):
            return

        method = None
        if attr_name in self._EXTENSIVE_ATTRIBUTES:
            method = config.discrete_method
        elif attr_name in self._CUMULATIVE_ATTRIBUTES:
            method = config.cumulative_method
        if not method:
            return

        virtual_value = method(self, attr_name)
        if virtual_value is None:
            return
        virtual_cluster = self.get_cluster(config.virtual_channel)
        virtual_cluster.update_attribute(attr_name, virtual_value)


class TuyaElectricalMeasurement(
    VirtualChannel,
    PowerFlowPreempt,
    EnergyMeterPowerFlow,
    EnergyMeterChannel,
    TuyaLocalCluster,
    TuyaZBElectricalMeasurement,
):
    """ElectricalMeasurement cluster for Tuya energy meter devices."""

    _CONSTANT_ATTRIBUTES: Dict[int, Any] = {
        **TuyaZBElectricalMeasurement._CONSTANT_ATTRIBUTES,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 100,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_frequency_multiplier.id: 1,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 10,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
    }

    _ATTRIBUTE_MEASUREMENT_TYPES: Dict[str, MeasurementType] = {
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

    _EXTENSIVE_ATTRIBUTES: Tuple[str] = (
        "active_power",
        "apparent_power",
        "reactive_power",
        "rms_current",
    )
    _INTENSIVE_ATTRIBUTES: Tuple[str] = ("rms_voltage",)

    def calculated_attributes(self, attr_name: str, value) -> None:
        """Calculates attributes that are not reported by the device."""

        if (
            self.channel == self.virtual_channel
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
                    or self.get_cluster(Channel.A).get("rms_voltage"),
                    self.get("ac_current_divisor", 1),
                    self.get("ac_current_multiplier", 1),
                    self.get("ac_voltage_divisor", 1),
                    self.get("ac_voltage_multiplier", 1),
                    self.get("ac_power_divisor", 1),
                    self.get("ac_power_multiplier", 1),
                ),
            )

    def update_attribute(self, attr_name: str, value) -> None:
        """Updates the cluster attribute."""
        if self.power_flow_preempt_handler(attr_name, value) == PowerFlowPreempt.HOLD:
            return
        attr_name, value = self.power_flow_handler(attr_name, value)
        self.update_measurement_type(attr_name)
        self.calculated_attributes(attr_name, value)
        self.virtual_channel_initial_values(attr_name, value)
        super().update_attribute(attr_name, value)
        self.virtual_channel_handler(attr_name)

    def update_measurement_type(self, attr_name: str) -> None:
        """Derives the measurement type from reported attributes."""
        if attr_name not in self._ATTRIBUTE_MEASUREMENT_TYPES:
            return
        measurement_type = 0
        for measurement, mask in self._ATTRIBUTE_MEASUREMENT_TYPES.items():
            if measurement == attr_name or self.get(measurement) is not None:
                measurement_type |= mask
        super().update_attribute("measurement_type", measurement_type)


class TuyaMetering(
    VirtualChannel,
    PowerFlowPreempt,
    EnergyMeterPowerFlow,
    EnergyMeterChannel,
    TuyaLocalCluster,
    TuyaZBMeteringClusterWithUnit,
):
    """Metering cluster for Tuya energy meter devices."""

    _CONSTANT_ATTRIBUTES: Dict[int, Any] = {
        **TuyaZBMeteringClusterWithUnit._CONSTANT_ATTRIBUTES,
        TuyaZBMeteringClusterWithUnit.AttributeDefs.status.id: 0x00,
        TuyaZBMeteringClusterWithUnit.AttributeDefs.multiplier.id: 1,
        TuyaZBMeteringClusterWithUnit.AttributeDefs.divisor.id: 10000,  # 1 decimal place after conversion from kW to W
        TuyaZBMeteringClusterWithUnit.AttributeDefs.summation_formatting.id: Metering.format(
            7, 2, True
        ),
        TuyaZBMeteringClusterWithUnit.AttributeDefs.demand_formatting.id: Metering.format(
            7, 1, True
        ),
    }

    _EXTENSIVE_ATTRIBUTES: Tuple[str] = ("instantaneous_demand",)
    _CUMULATIVE_FORWARD_ATTRIBUTES: Tuple[str] = ("current_summ_delivered",)
    _CUMULATIVE_REVERSE_ATTRIBUTES: Tuple[str] = ("current_summ_received",)
    _INVERSE_ATTRIBUTES: Dict[str, str] = {
        "current_summ_delivered": "current_summ_received",
    }

    def update_attribute(self, attr_name: str, value) -> None:
        """Updates the cluster attribute."""
        if self.power_flow_preempt_handler(attr_name, value) == PowerFlowPreempt.HOLD:
            return
        attr_name, value = self.power_flow_handler(attr_name, value)
        self.virtual_channel_initial_values(attr_name, value)
        super().update_attribute(attr_name, value)
        self.virtual_channel_handler(attr_name)


class TuyaEnergyMeterManufCluster_1CH(
    TuyaEnergyMeterManufCluster, configuration_type=ChannelConfiguration_1CH
):
    """Tuya 1 channel energy meter manufacturer cluster."""

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
    """Tuya 1 channel bidirectional energy meter manufacturer cluster."""

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
            TuyaEnergyMeterManufCluster.ep_attribute,
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


class TuyaEnergyMeterManufCluster_2CHB_MatSeePlus(
    TuyaEnergyMeterManufCluster, configuration_type=ChannelConfiguration_2CHB
):
    """MatSee Plus Tuya 2 channel bidirectional energy meter manufacturer cluster."""

    _ATTRIBUTE_DEFAULTS: Dict[int, Any] = {
        POWER_FLOW_PREEMPT: True,
    }

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
            TuyaEnergyMeterManufCluster.ep_attribute,
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
            TuyaEnergyMeterManufCluster.ep_attribute,
            "current_summ_delivered_coefficient",
        ),
        TUYA_DP_CURRENT_SUMM_DELIVERED_COEF_B: DPToAttributeMapping(
            TuyaEnergyMeterManufCluster.ep_attribute,
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
            TuyaEnergyMeterManufCluster.ep_attribute,
            "current_summ_received_coefficient",
        ),
        TUYA_DP_CURRENT_SUMM_RECEIVED_COEF_B: DPToAttributeMapping(
            TuyaEnergyMeterManufCluster.ep_attribute,
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
            TuyaEnergyMeterManufCluster.ep_attribute,
            "instantaneous_demand_coefficient",
        ),
        TUYA_DP_INSTANTANEOUS_DEMAND_COEF_B: DPToAttributeMapping(
            TuyaEnergyMeterManufCluster.ep_attribute,
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
            TuyaEnergyMeterManufCluster.ep_attribute,
            "power_flow",
            converter=lambda x: PowerFlow(x),
        ),
        TUYA_DP_POWER_FLOW_B: DPToAttributeMapping(
            TuyaEnergyMeterManufCluster.ep_attribute,
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
            TuyaEnergyMeterManufCluster.ep_attribute,
            "rms_current_coefficient",
        ),
        TUYA_DP_RMS_CURRENT_COEF_B: DPToAttributeMapping(
            TuyaEnergyMeterManufCluster.ep_attribute,
            "rms_current_coefficient_ch_b",
        ),
        TUYA_DP_RMS_VOLTAGE: DPToAttributeMapping(
            TuyaElectricalMeasurement.ep_attribute,
            "rms_voltage",
        ),
        TUYA_DP_RMS_VOLTAGE_COEF: DPToAttributeMapping(
            TuyaEnergyMeterManufCluster.ep_attribute,
            "rms_voltage_coefficient",
        ),
        TUYA_DP_UPDATE_PERIOD: DPToAttributeMapping(
            TuyaEnergyMeterManufCluster.ep_attribute,
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
    """EARU Tuya 2 channel bidirectional energy meter manufacturer cluster."""

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
            TuyaEnergyMeterManufCluster.ep_attribute,
            "power_flow",
            converter=lambda x: PowerFlow(x),
        ),
        TUYA_DP_POWER_FLOW_B: DPToAttributeMapping(
            TuyaEnergyMeterManufCluster.ep_attribute,
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
            TuyaEnergyMeterManufCluster.ep_attribute,
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


class TuyaEnergyMeter_1CH(CustomDevice):
    """Tuya PJ-MGW1203 1 channel energy meter."""

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


class TuyaEnergyMeter_1CHB(CustomDevice):
    """Tuya bidirectional 1 channel energy meter with Zigbee Green Power."""

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


class TuyaEnergyMeter_2CHB_EARU(CustomDevice):
    """EARU Tuya PC311-Z-TY bidirectional 2 channel energy meter."""

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


class TuyaEnergyMeter_2CHB_MatSeePlus(CustomDevice):
    """MatSee Plus Tuya PJ-1203A 2 channel bidirectional energy meter with Zigbee Green Power."""

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
                    TuyaEnergyMeterManufCluster_2CHB_MatSeePlus,
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
