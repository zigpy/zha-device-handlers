"""Tuya Din RCBO Circuit Breaker."""
from typing import Any, Dict, Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    DeviceTemperature,
    Groups,
    Ota,
    Scenes,
    Time,
)
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
from zhaquirks.tuya import (
    TUYA_MCU_COMMAND,
    AttributeWithMask,
    BigEndianInt16,
    PowerOnState,
)
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaAttributesCluster,
    TuyaClusterData,
    TuyaDPType,
    TuyaMCUCluster,
    TuyaOnOff,
)
from zhaquirks.xbee.types import (
    uint_t as uint_t_be,  # Temporary workaround until zigpy/zigpy#1124 is merged
)

TUYA_DP_STATE = 1
TUYA_DP_COUNTDOWN_TIMER = 9
TUYA_DP_FAULT_CODE = 26
TUYA_DP_RELAY_STATUS = 27  # power recovery behaviour
TUYA_DP_CHILD_LOCK = 29
TUYA_DP_VOLTAGE = 101
TUYA_DP_CURRENT = 102
TUYA_DP_ACTIVE_POWER = 103
TUYA_DP_LEAKAGE_CURRENT = 104
TUYA_DP_TEMPERATURE = 105
TUYA_DP_REMAINING_ENERGY = 106
TUYA_DP_RECHARGE_ENERGY = 107
TUYA_DP_COST_PARAMETERS = 108
TUYA_DP_LEAKAGE_PARAMETERS = 109
TUYA_DP_VOLTAGE_THRESHOLD = 110
TUYA_DP_CURRENT_THRESHOLD = 111
TUYA_DP_TEMPERATURE_THRESHOLD = 112
TUYA_DP_TOTAL_ACTIVE_POWER = 113
TUYA_DP_EQUIPMENT_NUMBER_AND_TYPE = 114
TUYA_DP_CLEAR_ENERGY = 115
TUYA_DP_LOCKING = 116  # test button pressed
TUYA_DP_TOTAL_REVERSE_ACTIVE_POWER = 117
TUYA_DP_HISTORICAL_VOLTAGE = 118
TUYA_DP_HISTORICAL_CURRENT = 119


class FaultCode(t.enum8):
    """Fault Code enum."""

    CLEAR = 0x00
    OVERVOLTAGE = 0x01
    UNDERVOLTAGE = 0x02
    OVERCURRENT = 0x04
    OVERTEMPERATURE = 0x08
    OVERLEAKAGECURRENT = 0x0A
    TRIPTEST = 0x10
    SAFETYLOCK = 0x80


class SelfTest(t.enum8):
    """Self test enum."""

    CLEAR = 0x00
    TEST = 0x01


class Locking(t.enum8):
    """Locking enum."""

    CLEAR = 0x00
    TRIP = 0x01


class CostParameters(t.Struct):
    """Tuya cost parameters."""

    cost_parameters: BigEndianInt16
    cost_parameters_enabled: t.Bool


class LeakageParameters(t.Struct):
    """Tuya leakage parameters."""

    self_test_auto_days: t.uint8_t
    self_test_auto_hours: t.uint8_t
    self_test_auto: t.Bool
    over_leakage_current_threshold: BigEndianInt16
    over_leakage_current_trip: t.Bool
    over_leakage_current_alarm: t.Bool
    self_test: SelfTest


class VoltageParameters(t.Struct):
    """Tuya voltage parameters."""

    over_voltage_threshold: BigEndianInt16
    over_voltage_trip: t.Bool
    over_voltage_alarm: t.Bool
    under_voltage_threshold: BigEndianInt16
    under_voltage_trip: t.Bool
    under_voltage_alarm: t.Bool


class uint24_t_be(
    uint_t_be
):  # TODO: Replace with zigpy big endian type once zigpy/zigpy#1124 is merged
    """Unsigned int 24 bit big-endian type."""

    _size = 3


class CurrentParameters(t.Struct):
    """Tuya current parameters."""

    over_current_threshold: uint24_t_be
    over_current_trip: t.Bool
    over_current_alarm: t.Bool


class TemperatureSetting(t.Struct):
    """Tuya temperature parameters."""

    over_temperature_threshold: t.int8s
    over_temperature_trip: t.Bool
    over_temperature_alarm: t.Bool


class TuyaRCBOBasic(CustomCluster, Basic):
    """Provide Tuya Basic Cluster with custom attributes."""

    attributes = Basic.attributes.copy()
    attributes.update(
        {
            0xFFE2: ("tuya_FFE2", t.uint8_t),
            0xFFE4: ("tuya_FFE4", t.uint8_t),
        }
    )


class TuyaRCBOOnOff(TuyaOnOff, TuyaAttributesCluster):
    """Custom class for on off switch."""

    attributes = TuyaOnOff.attributes.copy()
    attributes.update(
        {
            0x8000: ("child_lock", t.Bool),
            0x8002: ("power_on_state", PowerOnState),
            0xF090: ("countdown_timer", t.uint32_t),
            0xF740: ("trip", Locking),
        }
    )

    server_commands = TuyaOnOff.server_commands.copy()
    server_commands.update(
        {
            0x74: foundation.ZCLCommandDef("clear_locking", {}, False),
        }
    )

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default Cluster command."""

        # clear_locking
        if command_id == 0x74:
            self.debug(
                "Sending Tuya Cluster Command... Cluster Command is %x, Arguments are %s",
                command_id,
                args,
            )

            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_attr="trip",
                attr_value=True,
                expect_reply=expect_reply,
                manufacturer=manufacturer,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

        return await super().command(command_id, args, manufacturer, expect_reply, tsn)


class TuyaRCBOElectricalMeasurement(ElectricalMeasurement, TuyaAttributesCluster):
    """Custom class for power, voltage and current measurement."""

    AC_VOLTAGE_MULTIPLIER = 0x0600
    AC_VOLTAGE_DIVISOR = 0x0601
    AC_CURRENT_MULTIPLIER = 0x0602
    AC_CURRENT_DIVISOR = 0x0603
    AC_POWER_MULTIPLIER = 0x0604
    AC_POWER_DIVISOR = 0x0605

    _CONSTANT_ATTRIBUTES = {
        AC_VOLTAGE_MULTIPLIER: 1,
        AC_VOLTAGE_DIVISOR: 10,
        AC_CURRENT_MULTIPLIER: 1,
        AC_CURRENT_DIVISOR: 1000,
        AC_POWER_MULTIPLIER: 1,
        AC_POWER_DIVISOR: 10,
    }

    attributes = ElectricalMeasurement.attributes.copy()
    attributes.update(
        {
            0x0802: ("ac_current_overload", t.uint24_t),
            0xF1A0: ("alarm", FaultCode),
            0xF680: ("leakage_current", t.uint32_t),
            0xF6D0: ("self_test_auto_days", t.uint8_t),
            0xF6D1: ("self_test_auto_hours", t.uint8_t),
            0xF6D2: ("self_test_auto", t.Bool),
            0xF6D3: ("over_leakage_current_threshold", t.uint16_t),
            0xF6D5: ("over_leakage_current_trip", t.Bool),
            0xF6D6: ("over_leakage_current_alarm", t.Bool),
            0xF6D7: ("self_test", SelfTest),
            0xF6E3: ("over_voltage_trip", t.Bool),
            0xF6E7: ("under_voltage_trip", t.Bool),
            0xF6F3: ("over_current_trip", t.Bool),
            0xF760: ("rms_historical_voltage", t.uint16_t),
            0xF770: ("rms_historical_current", t.uint16_t),
        }
    )

    def update_attribute(self, attr_name: str, value: Any) -> None:
        """Calculate active current and power factor."""

        super().update_attribute(attr_name, value)

        if attr_name == "rms_current":
            rms_voltage = self.get("rms_voltage")
            if rms_voltage:
                apparent_power = value * rms_voltage / 1000
                super().update_attribute("apparent_power", int(apparent_power))

        if attr_name == "active_power":
            apparent_power = self.get("apparent_power")
            if apparent_power:
                power_factor = value / apparent_power * 1000
                if power_factor > 1000:
                    power_factor = 1000
                super().update_attribute("power_factor", int(power_factor))


class TuyaRCBODeviceTemperature(DeviceTemperature, TuyaAttributesCluster):
    """Tuya device temperature."""

    attributes = DeviceTemperature.attributes.copy()
    attributes.update(
        {
            0xFF10: ("over_temp_trip", t.Bool),
        }
    )


class TuyaRCBOMetering(Metering, TuyaAttributesCluster):
    """Custom class for total energy measurement."""

    UNIT_OF_MEASURE = 0x0300
    MULTIPLIER = 0x0301
    DIVISOR = 0x0302
    POWER_WATT = 0x0000

    _CONSTANT_ATTRIBUTES = {UNIT_OF_MEASURE: POWER_WATT, MULTIPLIER: 1, DIVISOR: 100}

    attributes = Metering.attributes.copy()
    attributes.update(
        {
            0xF6A0: ("remaining_energy", t.uint32_t),
            0xF6C0: ("cost_parameters", t.uint16_t),
            0xF6C1: ("cost_parameters_enabled", t.Bool),
            0xF720: ("meter_number", t.LimitedCharString(20)),
        }
    )

    server_commands = Metering.server_commands.copy()
    server_commands.update(
        {
            0x73: foundation.ZCLCommandDef("clear_device_data", {}, False),
        }
    )

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default Cluster command."""

        self.debug(
            "Sending Tuya Cluster Command... Cluster Command is %x, Arguments are %s",
            command_id,
            args,
        )

        # clear_device_data
        if command_id == 0x73:
            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_attr="clear_device_data",
                attr_value=True,
                expect_reply=expect_reply,
                manufacturer=manufacturer,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

        self.warning("Unsupported command_id: %s", command_id)
        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND)


class TuyaRCBOManufCluster(TuyaMCUCluster):
    """Tuya with power measurement data points."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        TUYA_DP_STATE: DPToAttributeMapping(
            TuyaRCBOOnOff.ep_attribute,
            "on_off",
            TuyaDPType.BOOL,
        ),
        TUYA_DP_COUNTDOWN_TIMER: DPToAttributeMapping(
            TuyaRCBOOnOff.ep_attribute,
            "countdown_timer",
            TuyaDPType.VALUE,
        ),
        TUYA_DP_FAULT_CODE: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            "alarm",
            TuyaDPType.ENUM,
            lambda x: FaultCode(x),
        ),
        TUYA_DP_RELAY_STATUS: DPToAttributeMapping(
            TuyaRCBOOnOff.ep_attribute,
            "power_on_state",
            TuyaDPType.ENUM,
            lambda x: PowerOnState(x),
        ),
        TUYA_DP_CHILD_LOCK: DPToAttributeMapping(
            TuyaRCBOOnOff.ep_attribute,
            "child_lock",
            TuyaDPType.BOOL,
        ),
        TUYA_DP_VOLTAGE: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            "rms_voltage",
            TuyaDPType.RAW,
            lambda x: x[1] | x[0] << 8,
        ),
        TUYA_DP_CURRENT: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            "rms_current",
            TuyaDPType.RAW,
            lambda x: x[2] | x[1] << 8,
        ),
        TUYA_DP_ACTIVE_POWER: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            "active_power",
            TuyaDPType.RAW,
            lambda x: x[2] | x[1] << 8,
        ),
        TUYA_DP_LEAKAGE_CURRENT: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            "leakage_current",
            TuyaDPType.VALUE,
        ),
        TUYA_DP_TEMPERATURE: DPToAttributeMapping(
            TuyaRCBODeviceTemperature.ep_attribute,
            "current_temperature",
            TuyaDPType.VALUE,
            lambda x: x * 100,
        ),
        TUYA_DP_REMAINING_ENERGY: DPToAttributeMapping(
            TuyaRCBOMetering.ep_attribute,
            "remaining_energy",
            TuyaDPType.VALUE,
        ),
        TUYA_DP_COST_PARAMETERS: DPToAttributeMapping(
            TuyaRCBOMetering.ep_attribute,
            ("cost_parameters", "cost_parameters_enabled"),
            TuyaDPType.RAW,
            lambda x: (x[1] | x[0] << 8, x[2]),
            lambda *fields: CostParameters(*fields),
        ),
        TUYA_DP_LEAKAGE_PARAMETERS: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            (
                "self_test_auto_days",
                "self_test_auto_hours",
                "self_test_auto",
                "over_leakage_current_threshold",
                "over_leakage_current_trip",
                "over_leakage_current_alarm",
                "self_test",
            ),
            TuyaDPType.RAW,
            lambda x: (x[0], x[1], x[2], x[4] | x[3] << 8, x[5], x[6], SelfTest(x[7])),
            lambda *fields: LeakageParameters(*fields),
        ),
        TUYA_DP_VOLTAGE_THRESHOLD: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            (
                "rms_extreme_over_voltage",
                "over_voltage_trip",
                "ac_alarms_mask",
                "rms_extreme_under_voltage",
                "under_voltage_trip",
            ),
            TuyaDPType.RAW,
            lambda x: (
                x[1] | x[0] << 8,
                x[2],
                AttributeWithMask(x[3] << 6 | x[7] << 7, 1 << 6 | 1 << 7),
                x[5] | x[4] << 8,
                x[6],
            ),
            lambda rms_extreme_over_voltage, over_voltage_trip, ac_alarms_mask, rms_extreme_under_voltage, under_voltage_trip: VoltageParameters(
                rms_extreme_over_voltage,
                over_voltage_trip,
                bool(ac_alarms_mask & 0x40),
                rms_extreme_under_voltage,
                under_voltage_trip,
                bool(ac_alarms_mask & 0x80),
            ),
        ),
        TUYA_DP_CURRENT_THRESHOLD: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            ("ac_current_overload", "over_current_trip", "ac_alarms_mask"),
            TuyaDPType.RAW,
            lambda x: (
                (x[2] | x[1] << 8 | x[0] << 16),
                x[3],
                AttributeWithMask(x[4] << 1, 1 << 1),
            ),
            lambda ac_current_overload, over_current_trip, ac_alarms_mask: CurrentParameters(
                ac_current_overload, over_current_trip, bool(ac_alarms_mask & 0x02)
            ),
        ),
        TUYA_DP_TEMPERATURE_THRESHOLD: DPToAttributeMapping(
            TuyaRCBODeviceTemperature.ep_attribute,
            ("high_temp_thres", "over_temp_trip", "dev_temp_alarm_mask"),
            TuyaDPType.RAW,
            lambda x: (x[0] if x[0] <= 127 else x[0] - 256, x[1], x[2] << 1),
            lambda x, y, z: TemperatureSetting(x, y, bool(z & 0x02)),
        ),
        TUYA_DP_TOTAL_ACTIVE_POWER: DPToAttributeMapping(
            TuyaRCBOMetering.ep_attribute,
            "current_summ_delivered",
            TuyaDPType.VALUE,
        ),
        TUYA_DP_EQUIPMENT_NUMBER_AND_TYPE: DPToAttributeMapping(
            TuyaRCBOMetering.ep_attribute,
            "meter_number",
            TuyaDPType.STRING,
            lambda x: x.rstrip(),
        ),
        TUYA_DP_CLEAR_ENERGY: DPToAttributeMapping(
            TuyaRCBOMetering.ep_attribute, "clear_device_data", TuyaDPType.BOOL
        ),
        TUYA_DP_LOCKING: DPToAttributeMapping(
            TuyaRCBOOnOff.ep_attribute, "trip", TuyaDPType.BOOL, lambda x: Locking(x)
        ),
        TUYA_DP_TOTAL_REVERSE_ACTIVE_POWER: DPToAttributeMapping(
            TuyaRCBOMetering.ep_attribute,
            "current_summ_received",
            TuyaDPType.VALUE,
        ),
        TUYA_DP_HISTORICAL_VOLTAGE: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            "rms_historical_voltage",
            TuyaDPType.RAW,
            lambda x: x[1] | x[0] << 8,
        ),
        TUYA_DP_HISTORICAL_CURRENT: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            "rms_historical_current",
            TuyaDPType.RAW,
            lambda x: x[2] | x[1] << 8,
        ),
    }

    data_point_handlers: Dict[int, str] = {
        TUYA_DP_STATE: "_dp_2_attr_update",
        TUYA_DP_COUNTDOWN_TIMER: "_dp_2_attr_update",
        TUYA_DP_FAULT_CODE: "_dp_2_attr_update",
        TUYA_DP_RELAY_STATUS: "_dp_2_attr_update",
        TUYA_DP_CHILD_LOCK: "_dp_2_attr_update",
        TUYA_DP_VOLTAGE: "_dp_2_attr_update",
        TUYA_DP_CURRENT: "_dp_2_attr_update",
        TUYA_DP_ACTIVE_POWER: "_dp_2_attr_update",
        TUYA_DP_LEAKAGE_CURRENT: "_dp_2_attr_update",
        TUYA_DP_TEMPERATURE: "_dp_2_attr_update",
        TUYA_DP_REMAINING_ENERGY: "_dp_2_attr_update",
        TUYA_DP_COST_PARAMETERS: "_dp_2_attr_update",
        TUYA_DP_LEAKAGE_PARAMETERS: "_dp_2_attr_update",
        TUYA_DP_VOLTAGE_THRESHOLD: "_dp_2_attr_update",
        TUYA_DP_CURRENT_THRESHOLD: "_dp_2_attr_update",
        TUYA_DP_TEMPERATURE_THRESHOLD: "_dp_2_attr_update",
        TUYA_DP_TOTAL_ACTIVE_POWER: "_dp_2_attr_update",
        TUYA_DP_EQUIPMENT_NUMBER_AND_TYPE: "_dp_2_attr_update",
        TUYA_DP_LOCKING: "_dp_2_attr_update",
        TUYA_DP_TOTAL_REVERSE_ACTIVE_POWER: "_dp_2_attr_update",
        TUYA_DP_HISTORICAL_VOLTAGE: "_dp_2_attr_update",
        TUYA_DP_HISTORICAL_CURRENT: "_dp_2_attr_update",
    }


class TuyaCircuitBreaker(CustomDevice):
    """Tuya RCBO with power meter device."""

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # device_version=1
        # input_clusters=[0x0000, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x000a, 0x0019]
        MODELS_INFO: [
            ("_TZE200_hkdl5fmv", "TS0601"),
        ],
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
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    TuyaRCBOBasic,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaRCBOOnOff,
                    TuyaRCBOElectricalMeasurement,
                    TuyaRCBODeviceTemperature,
                    TuyaRCBOMetering,
                    TuyaRCBOManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
