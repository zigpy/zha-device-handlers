"""Aqara Roller Shade Driver E1 device."""

from __future__ import annotations

from typing import Any

from zigpy import types as t
from zigpy.profiles import zgp, zha
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
    Scenes,
    Time,
)

from zhaquirks import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCluster,
    XiaomiCustomDevice,
    XiaomiPowerConfigurationPercent,
)


class XiaomiAqaraRollerE1(XiaomiAqaraE1Cluster):
    """Xiaomi mfg cluster implementation specific for E1 Roller."""

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

    _CONSTANT_ATTRIBUTES = {
        AnalogOutput.AttributeDefs.description.id: "Current position",
        AnalogOutput.AttributeDefs.max_present_value.id: 100.0,
        AnalogOutput.AttributeDefs.min_present_value.id: 0.0,
        AnalogOutput.AttributeDefs.out_of_service.id: 0,
        AnalogOutput.AttributeDefs.resolution.id: 1.0,
        AnalogOutput.AttributeDefs.status_flags.id: 0x00,
    }

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)

        if attrid == self.AttributeDefs.present_value.id:
            self.endpoint.window_covering.update_attribute(
                WindowCovering.AttributeDefs.current_position_lift_percentage.id,
                (100 - value),
            )


class WindowCoveringRollerE1(CustomCluster, WindowCovering):
    """Window covering cluster to receive commands that are sent to the AnalogOutput's present_value to move the motor."""

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args: Any,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ) -> Any:
        """Overwrite the commands to make it work for both firmware 1425 and 1427.

        We either overwrite analog_output's current_value or multistate_output's current
        value to make the roller work.
        """
        if command_id == WindowCovering.ServerCommandDefs.up_open.id:
            (res,) = await self.endpoint.multistate_output.write_attributes(
                {"present_value": 1}
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)
        if command_id == WindowCovering.ServerCommandDefs.down_close.id:
            (res,) = await self.endpoint.multistate_output.write_attributes(
                {"present_value": 0}
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)
        if command_id == WindowCovering.ServerCommandDefs.go_to_lift_percentage.id:
            (res,) = await self.endpoint.analog_output.write_attributes(
                {"present_value": (100 - args[0])}
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)
        if command_id == WindowCovering.ServerCommandDefs.stop.id:
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
            MultistateOutput.AttributeDefs.present_value.id: (
                "present_value",
                t.uint16_t,
            ),
        }
    )


class RollerE1AQ(XiaomiCustomDevice):
    """Aqara Roller Shade Driver E1 device."""

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
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
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
                    XiaomiPowerConfigurationPercent,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
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
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }


class RollerE1AQ_3(RollerE1AQ):
    """Aqara Roller Shade Driver E1 (version 3) device."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.curtain.acn002")],
        ENDPOINTS: {
            # <SizePrefixedSimpleDescriptor endpoint=1 profile=260 device_type=514
            # device_version=1
            # input_clusters=[0, 2, 3, 4, 5, 6, 9, 13, 19, 258]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
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
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }
