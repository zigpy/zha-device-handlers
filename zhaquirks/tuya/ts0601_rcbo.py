"""Tuya Din RCBO Circuit Breaker."""

from typing import Any, Final, Optional, Union

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
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TUYA_MCU_COMMAND, AttributeWithMask, PowerOnState
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaAttributesCluster,
    TuyaClusterData,
    TuyaMCUCluster,
    TuyaOnOff,
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


class CostParameters(t.Struct):
    """Tuya cost parameters."""

    cost_parameters: t.uint16_t_be
    cost_parameters_enabled: t.Bool


class LeakageParameters(t.Struct):
    """Tuya leakage parameters."""

    self_test_auto_days: t.uint8_t
    self_test_auto_hours: t.uint8_t
    self_test_auto: t.Bool
    over_leakage_current_threshold: t.uint16_t_be
    over_leakage_current_trip: t.Bool
    over_leakage_current_alarm: t.Bool
    self_test: SelfTest


class VoltageParameters(t.Struct):
    """Tuya voltage parameters."""

    over_voltage_threshold: t.uint16_t_be
    over_voltage_trip: t.Bool
    over_voltage_alarm: t.Bool
    under_voltage_threshold: t.uint16_t_be
    under_voltage_trip: t.Bool
    under_voltage_alarm: t.Bool


class CurrentParameters(t.Struct):
    """Tuya current parameters."""

    over_current_threshold: t.uint24_t_be
    over_current_trip: t.Bool
    over_current_alarm: t.Bool


class TemperatureSetting(t.Struct):
    """Tuya temperature parameters."""

    over_temperature_threshold: t.int8s
    over_temperature_trip: t.Bool
    over_temperature_alarm: t.Bool


class TuyaRCBOBasic(CustomCluster, Basic):
    """Provide Tuya Basic Cluster with custom attributes."""

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute definitions."""

        tuya_FFE2: Final = ZCLAttributeDef(id=0xFFE2, type=t.uint8_t)  # noqa: N815
        tuya_FFE4: Final = ZCLAttributeDef(id=0xFFE4, type=t.uint8_t)  # noqa: N815


class TuyaRCBOOnOff(TuyaOnOff, TuyaAttributesCluster):
    """Custom class for on off switch."""

    class AttributeDefs(TuyaOnOff.AttributeDefs):
        """Attribute definitions."""

        child_lock: Final = ZCLAttributeDef(id=0x8000, type=t.Bool)
        power_on_state: Final = ZCLAttributeDef(id=0x8002, type=PowerOnState)
        countdown_timer: Final = ZCLAttributeDef(id=0xF090, type=t.uint32_t)
        trip: Final = ZCLAttributeDef(id=0xF740, type=t.Bool)

    class ServerCommandDefs(TuyaOnOff.ServerCommandDefs):
        """Server command definitions."""

        clear_locking = foundation.ZCLCommandDef(
            id=0x74,
            schema={},
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
                cluster_name=self.ep_attribute,
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

    class AttributeDefs(ElectricalMeasurement.AttributeDefs):
        """Attribute definitions."""

        ac_current_overload: Final = ZCLAttributeDef(id=0x0802, type=t.uint24_t)
        alarm: Final = ZCLAttributeDef(id=0xF1A0, type=FaultCode)
        leakage_current: Final = ZCLAttributeDef(id=0xF680, type=t.uint32_t)
        self_test_auto_days: Final = ZCLAttributeDef(id=0xF6D0, type=t.uint8_t)
        self_test_auto_hours: Final = ZCLAttributeDef(id=0xF6D1, type=t.uint8_t)
        self_test_auto: Final = ZCLAttributeDef(id=0xF6D2, type=t.Bool)
        over_leakage_current_threshold: Final = ZCLAttributeDef(
            id=0xF6D3, type=t.uint16_t
        )
        over_leakage_current_trip: Final = ZCLAttributeDef(id=0xF6D5, type=t.Bool)
        over_leakage_current_alarm: Final = ZCLAttributeDef(id=0xF6D6, type=t.Bool)
        self_test: Final = ZCLAttributeDef(id=0xF6D7, type=SelfTest)
        over_voltage_trip: Final = ZCLAttributeDef(id=0xF6E3, type=t.Bool)
        under_voltage_trip: Final = ZCLAttributeDef(id=0xF6E7, type=t.Bool)
        over_current_trip: Final = ZCLAttributeDef(id=0xF6F3, type=t.Bool)
        rms_historical_voltage: Final = ZCLAttributeDef(id=0xF760, type=t.uint16_t)
        rms_historical_current: Final = ZCLAttributeDef(id=0xF770, type=t.uint16_t)

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
                power_factor = value / apparent_power * 100
                power_factor = min(power_factor, 100)
                super().update_attribute("power_factor", round(power_factor))


class TuyaRCBODeviceTemperature(DeviceTemperature, TuyaAttributesCluster):
    """Tuya device temperature."""

    class AttributeDefs(DeviceTemperature.AttributeDefs):
        """Attribute definitions."""

        over_temp_trip: Final = ZCLAttributeDef(id=0xFF10, type=t.Bool)


class TuyaRCBOMetering(Metering, TuyaAttributesCluster):
    """Custom class for total energy measurement."""

    UNIT_OF_MEASURE = 0x0300
    MULTIPLIER = 0x0301
    DIVISOR = 0x0302
    POWER_WATT = 0x0000

    _CONSTANT_ATTRIBUTES = {UNIT_OF_MEASURE: POWER_WATT, MULTIPLIER: 1, DIVISOR: 100}

    class AttributeDefs(Metering.AttributeDefs):
        """Attribute definitions."""

        remaining_energy: Final = ZCLAttributeDef(id=0xF6A0, type=t.uint32_t)
        cost_parameters: Final = ZCLAttributeDef(id=0xF6C0, type=t.uint16_t)
        cost_parameters_enabled: Final = ZCLAttributeDef(id=0xF6C1, type=t.Bool)
        meter_number: Final = ZCLAttributeDef(id=0xF720, type=t.LimitedCharString(20))

    class ServerCommandDefs(Metering.ServerCommandDefs):
        """Server command definitions."""

        clear_device_data = foundation.ZCLCommandDef(
            id=0x73,
            schema={},
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
                cluster_name=self.ep_attribute,
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

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        TUYA_DP_STATE: DPToAttributeMapping(
            TuyaRCBOOnOff.ep_attribute,
            "on_off",
        ),
        TUYA_DP_COUNTDOWN_TIMER: DPToAttributeMapping(
            TuyaRCBOOnOff.ep_attribute,
            "countdown_timer",
        ),
        TUYA_DP_FAULT_CODE: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            "alarm",
            lambda x: FaultCode(x),
        ),
        TUYA_DP_RELAY_STATUS: DPToAttributeMapping(
            TuyaRCBOOnOff.ep_attribute,
            "power_on_state",
            lambda x: PowerOnState(x),
        ),
        TUYA_DP_CHILD_LOCK: DPToAttributeMapping(
            TuyaRCBOOnOff.ep_attribute,
            "child_lock",
        ),
        TUYA_DP_VOLTAGE: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            "rms_voltage",
            lambda x: x[1] | x[0] << 8,
        ),
        TUYA_DP_CURRENT: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            "rms_current",
            lambda x: x[2] | x[1] << 8,
        ),
        TUYA_DP_ACTIVE_POWER: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            "active_power",
            lambda x: x[2] | x[1] << 8,
        ),
        TUYA_DP_LEAKAGE_CURRENT: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            "leakage_current",
        ),
        TUYA_DP_TEMPERATURE: DPToAttributeMapping(
            TuyaRCBODeviceTemperature.ep_attribute,
            "current_temperature",
            lambda x: x * 100,
        ),
        TUYA_DP_REMAINING_ENERGY: DPToAttributeMapping(
            TuyaRCBOMetering.ep_attribute,
            "remaining_energy",
        ),
        TUYA_DP_COST_PARAMETERS: DPToAttributeMapping(
            TuyaRCBOMetering.ep_attribute,
            ("cost_parameters", "cost_parameters_enabled"),
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
            lambda x: (
                x[1] | x[0] << 8,
                x[2],
                AttributeWithMask(x[3] << 6 | x[7] << 7, 1 << 6 | 1 << 7),
                x[5] | x[4] << 8,
                x[6],
            ),
            lambda rms_extreme_over_voltage,
            over_voltage_trip,
            ac_alarms_mask,
            rms_extreme_under_voltage,
            under_voltage_trip: VoltageParameters(
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
            lambda x: (
                (x[2] | x[1] << 8 | x[0] << 16),
                x[3],
                AttributeWithMask(x[4] << 1, 1 << 1),
            ),
            lambda ac_current_overload,
            over_current_trip,
            ac_alarms_mask: CurrentParameters(
                ac_current_overload, over_current_trip, bool(ac_alarms_mask & 0x02)
            ),
        ),
        TUYA_DP_TEMPERATURE_THRESHOLD: DPToAttributeMapping(
            TuyaRCBODeviceTemperature.ep_attribute,
            ("high_temp_thres", "over_temp_trip", "dev_temp_alarm_mask"),
            lambda x: (x[0] if x[0] <= 127 else x[0] - 256, x[1], x[2] << 1),
            lambda x, y, z: TemperatureSetting(x, y, bool(z & 0x02)),
        ),
        TUYA_DP_TOTAL_ACTIVE_POWER: DPToAttributeMapping(
            TuyaRCBOMetering.ep_attribute,
            "current_summ_delivered",
        ),
        TUYA_DP_EQUIPMENT_NUMBER_AND_TYPE: DPToAttributeMapping(
            TuyaRCBOMetering.ep_attribute,
            "meter_number",
            lambda x: x.rstrip(),
        ),
        TUYA_DP_CLEAR_ENERGY: DPToAttributeMapping(
            TuyaRCBOMetering.ep_attribute, "clear_device_data"
        ),
        TUYA_DP_LOCKING: DPToAttributeMapping(TuyaRCBOOnOff.ep_attribute, "trip"),
        TUYA_DP_TOTAL_REVERSE_ACTIVE_POWER: DPToAttributeMapping(
            TuyaRCBOMetering.ep_attribute,
            "current_summ_received",
        ),
        TUYA_DP_HISTORICAL_VOLTAGE: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            "rms_historical_voltage",
            lambda x: x[1] | x[0] << 8,
        ),
        TUYA_DP_HISTORICAL_CURRENT: DPToAttributeMapping(
            TuyaRCBOElectricalMeasurement.ep_attribute,
            "rms_historical_current",
            lambda x: x[2] | x[1] << 8,
        ),
    }

    data_point_handlers: dict[int, str] = {
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
