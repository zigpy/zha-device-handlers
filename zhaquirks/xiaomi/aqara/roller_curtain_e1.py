"""Aqara Roller Shade Driver E1 device."""
from __future__ import annotations

from typing import Any

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Alarms,
    AnalogOutput,
    Basic,
    DeviceTemperature,
    GreenPowerProxy,
    Groups,
    Identify,
    MultistateOutput,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster

from zhaquirks import Bus, CustomCluster, LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import LUMI, BasicCluster, XiaomiCluster, XiaomiCustomDevice

PRESENT_VALUE = 0x0055
CURRENT_POSITION_LIFT_PERCENTAGE = 0x0008
GO_TO_LIFT_PERCENTAGE = 0x0005
DOWN_CLOSE = 0x0001
UP_OPEN = 0x0000
STOP = 0x0002


class XiaomiAqaraRollerE1(XiaomiCluster, ManufacturerSpecificCluster):
    """Xiaomi mfg cluster implementation specific for E1 Roller."""

    cluster_id = 0xFCC0

    attributes = XiaomiCluster.attributes.copy()
    attributes.update(
        {
            0x0400: ("reverse_direction", t.Bool, True),
            0x0402: ("positions_stored", t.Bool, True),
            0x0407: ("store_position", t.uint8_t, True),
            0x0408: ("speed", t.uint8_t, True),
            0x0409: ("charging", t.uint8_t, True),
            0x00F7: ("aqara_attributes", t.LVBytes, True),
        }
    )


class AnalogOutputRollerE1(CustomCluster, AnalogOutput):
    """Analog output cluster, only used to relay current_value to WindowCovering."""

    cluster_id = AnalogOutput.cluster_id

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        super().__init__(*args, **kwargs)

        self._update_attribute(0x0041, float(0x064))  # max_present_value
        self._update_attribute(0x0045, 0.0)  # min_present_value
        self._update_attribute(0x0051, 0)  # out_of_service
        self._update_attribute(0x006A, 1.0)  # resolution
        self._update_attribute(0x006F, 0x00)  # status_flags

    def _update_attribute(self, attrid: int, value: Any) -> None:

        super()._update_attribute(attrid, value)

        if attrid == PRESENT_VALUE:
            self.endpoint.window_covering._update_attribute(
                CURRENT_POSITION_LIFT_PERCENTAGE, (100 - value)
            )


class WindowCoveringRollerE1(CustomCluster, WindowCovering):
    """Window covering cluster to receive commands that are sent to the AnalogOutput's present_value to move the motor."""

    cluster_id = WindowCovering.cluster_id

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        super().__init__(*args, **kwargs)

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args: Any,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tries: int = 1,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ) -> Any:
        """Overwrite the commands to make it work for both firmware 1425 and 1427.

        We either overwrite analog_output's current_value or multistate_output's current
        value to make the roller work.
        """
        if command_id == UP_OPEN:
            (res,) = await self.endpoint.multistate_output.write_attributes(
                {"present_value": 1}
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)
        if command_id == DOWN_CLOSE:
            (res,) = await self.endpoint.multistate_output.write_attributes(
                {"present_value": 0}
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)
        if command_id == GO_TO_LIFT_PERCENTAGE:
            (res,) = await self.endpoint.analog_output.write_attributes(
                {"present_value": (100 - args[0])}
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)
        if command_id == STOP:
            (res,) = await self.endpoint.multistate_output.write_attributes(
                {"present_value": 2}
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)


class MultistateOutputRollerE1(CustomCluster, MultistateOutput):
    """Multistate Output cluster which overwrites present_value.

    Otherwise, it gives errors of wrong datatype when using it in the commands.
    """

    attributes = MultistateOutput.attributes.copy()
    attributes.update(
        {
            0x0055: ("present_value", t.uint16_t),
        }
    )


class PowerConfigurationRollerE1(PowerConfiguration, LocalDataCluster):
    """Xiaomi power configuration cluster implementation."""

    BATTERY_PERCENTAGE_REMAINING = 0x0021

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.power_bus_percentage.add_listener(self)

    def update_battery_percentage(self, value: int) -> None:
        """Doubles the battery percentage to the Zigbee spec's expected 200% maximum."""
        super()._update_attribute(
            self.BATTERY_PERCENTAGE_REMAINING,
            (value * 2),
        )


class RollerE1AQ(XiaomiCustomDevice):
    """Aqara Roller Shade Driver E1 device."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        self.power_bus_percentage: Bus = Bus()  # type: ignore
        super().__init__(*args, **kwargs)  # type: ignore

    signature = {
        MODELS_INFO: [(LUMI, "lumi.curtain.acn002")],
        ENDPOINTS: {
            # <SizePrefixedSimpleDescriptor endpoint=1 profile=260 device_type=256
            # device_version=1
            # input_clusters=[0, 2, 3, 4, 5, 6, 9, 64704, 13, 19, 258]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Alarms.cluster_id,
                    AnalogOutput.cluster_id,
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    XiaomiAqaraRollerE1.cluster_id,
                    MultistateOutput.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            },
            # <SizePrefixedSimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0,
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Alarms.cluster_id,
                    AnalogOutputRollerE1,
                    BasicCluster,
                    DeviceTemperature.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    XiaomiAqaraRollerE1,
                    MultistateOutputRollerE1,
                    Scenes.cluster_id,
                    WindowCoveringRollerE1,
                    PowerConfigurationRollerE1,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }


class RollerE1AQ_2(RollerE1AQ):
    """Aqara Roller Shade Driver E1 (version 2) device."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.curtain.acn002")],
        ENDPOINTS: {
            # <SizePrefixedSimpleDescriptor endpoint=1 profile=260 device_type=256
            # device_version=1
            # input_clusters=[0, 2, 3, 4, 5, 6, 9, 13, 19, 258]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Alarms.cluster_id,
                    AnalogOutput.cluster_id,
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    MultistateOutput.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            },
            # <SizePrefixedSimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0,
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }
