"""Tuya DIN Power Meter Switch ZCR1-40EM."""

from typing import Any, Optional, Union

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, GreenPowerProxy, Groups, Ota, Scenes, Time
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
from zhaquirks.tuya import TUYA_MCU_COMMAND, PowerOnState
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaAttributesCluster,
    TuyaClusterData,
    TuyaMCUCluster,
    TuyaOnOff,
)

TUYA_DP_ENERGY = 1
TUYA_DP_MEASUREMENT = 6
TUYA_DP_STATE = 16
TUYA_DP_RELAY_STATUS = 27


def convert_energy_data(x):
    """Convert raw Tuya energy data."""

    if isinstance(x, (int, float)):
        result = int(x)
        return result

    elif isinstance(x, (bytes, list)) and len(x) >= 4:
        result = int.from_bytes(
            x[:4] if isinstance(x, bytes) else bytes(x[:4]), byteorder="big"
        )
        return result

    return 0


def convert_electrical_measurements(x):
    """Convert raw Tuya electrical measurement data."""
    if not (isinstance(x, (bytes, list)) and len(x) >= 8):
        return 0, 0, 0

    voltage = x[0] << 8 | x[1]
    current = x[3] << 8 | x[4]
    power = x[6] << 8 | x[7]

    return voltage, current, power


class TuyaDinPowerMeterSwitchBasic(CustomCluster, Basic):
    """Tuya DIN Power Meter Switch Basic cluster."""

    attributes = Basic.attributes.copy()
    # noinspection PyTypeChecker
    attributes.update(
        {
            0xFFE2: ("tuya_FFE2", t.uint8_t),
            0xFFE4: ("tuya_FFE4", t.uint8_t),
        }
    )


class TuyaDinPowerMeterSwitchOnOff(TuyaOnOff, TuyaAttributesCluster):
    """Tuya DIN Power Meter Switch OnOff cluster."""

    attributes = TuyaOnOff.attributes.copy()
    # noinspection PyTypeChecker
    attributes.update(
        {
            0x8002: ("power_on_state", PowerOnState),
        }
    )

    server_commands = TuyaOnOff.server_commands.copy()
    # noinspection PyTypeChecker
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
            # noinspection PyUnresolvedReferences
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

        return await super().command(command_id, args, manufacturer, expect_reply, tsn)


class TuyaDinPowerMeterSwitchElectricalMeasurement(
    ElectricalMeasurement, TuyaAttributesCluster
):
    """Tuya DIN Power Meter Switch Electrical Measurement cluster."""

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
        AC_POWER_DIVISOR: 1,
    }

    attributes = ElectricalMeasurement.attributes.copy()

    def update_attribute(self, attr_name: str, value: Any) -> None:
        """Calculate derived attributes."""
        super().update_attribute(attr_name, value)

        if attr_name == "rms_current":
            rms_voltage = self.get("rms_voltage")
            if rms_voltage and rms_voltage > 0:
                apparent_power = value * rms_voltage / 1000
                super().update_attribute("apparent_power", int(apparent_power))

        if attr_name == "active_power":
            apparent_power = self.get("apparent_power")
            if apparent_power and apparent_power > 0:
                power_factor = value / apparent_power * 100
                power_factor = min(power_factor, 100)
                super().update_attribute("power_factor", round(power_factor))


class TuyaDinPowerMeterSwitchMetering(Metering, TuyaAttributesCluster):
    """Tuya DIN Power Meter Switch Metering cluster."""

    attributes = Metering.attributes.copy()

    # noinspection PyTypeChecker
    attributes.update(
        {
            0x0000: ("current_summ_delivered", t.uint48_t),
        }
    )

    _CONSTANT_ATTRIBUTES = {
        0x0300: 0,  # unit_of_measure (0x00 is kWh)
        0x0301: 1,  # multiplier for kWh
        0x0302: 100,  # divisor for kWh
        0x0306: 0x00,  # metering_device_type (Electric Metering)
    }


class TuyaDinPowerMeterSwitchManufCluster(TuyaMCUCluster):
    """Tuya DIN Power Meter Switch manufacturer cluster."""

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        TUYA_DP_STATE: DPToAttributeMapping(
            TuyaDinPowerMeterSwitchOnOff.ep_attribute,
            "on_off",
        ),
        TUYA_DP_ENERGY: DPToAttributeMapping(
            TuyaDinPowerMeterSwitchMetering.ep_attribute,
            "current_summ_delivered",
            converter=convert_energy_data,
        ),
        TUYA_DP_RELAY_STATUS: DPToAttributeMapping(
            TuyaDinPowerMeterSwitchOnOff.ep_attribute,
            "power_on_state",
            converter=lambda x: PowerOnState(x),
        ),
        TUYA_DP_MEASUREMENT: DPToAttributeMapping(
            TuyaDinPowerMeterSwitchElectricalMeasurement.ep_attribute,
            ("rms_voltage", "rms_current", "active_power"),
            converter=convert_electrical_measurements,
        ),
    }

    data_point_handlers: dict[int, str] = {
        TUYA_DP_STATE: "_dp_2_attr_update",
        TUYA_DP_ENERGY: "_dp_2_attr_update",
        TUYA_DP_MEASUREMENT: "_dp_2_attr_update",
        TUYA_DP_RELAY_STATUS: "_dp_2_attr_update",
    }


class TuyaDinPowerMeterSwitch(CustomDevice):
    """Tuya DIN Power Meter Switch device - ZCR1-40EM."""

    signature = {
        # NodeDescriptor: manufacturer_code=4417, max_buffer_size=66, server_mask=10752
        # device_version=1
        # input_clusters=[0x0000, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x000a, 0x0019]
        MODELS_INFO: [
            ("_TZE200_abatw3kj", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=81 device_version=1
            # input_clusters=[4, 5, 61184, 0] -> [Groups, Scenes, TuyaMCU, Basic]
            # output_clusters=[25, 10] -> [OTA, Time]>
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
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97 device_version=0
            # input_clusters=[] output_clusters=[33]>
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
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    TuyaDinPowerMeterSwitchBasic,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaDinPowerMeterSwitchOnOff,
                    TuyaDinPowerMeterSwitchElectricalMeasurement,
                    TuyaDinPowerMeterSwitchMetering,
                    TuyaDinPowerMeterSwitchManufCluster,
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
