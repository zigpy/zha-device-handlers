"""Aqara Curtain Driver B1 device."""
from __future__ import annotations

import logging
from typing import Any

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    AnalogOutput,
    Basic,
    Groups,
    Identify,
    MultistateOutput,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import LUMI, XiaomiCustomDevice

_LOGGER = logging.getLogger(__name__)


class AnalogOutputB1(CustomCluster, AnalogOutput):
    """Analog output cluster, used to relay current_value to WindowCovering."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        _LOGGER.debug("AnalogOutputB1 Cluster init")
        super().__init__(*args, **kwargs)
        self._update_attribute(
            self.attributes_by_name["max_present_value"].id, 100.0
        )  # max_present_value
        self._update_attribute(
            self.attributes_by_name["min_present_value"].id, 0.0
        )  # min_present_value

    def _update_attribute(self, attrid: int, value: Any) -> None:
        _LOGGER.debug("AnalogOutput update attribute %04x to %s... ", attrid, value)
        super()._update_attribute(attrid, value)
        if attrid == self.attributes_by_name["present_value"].id:
            self.endpoint.window_covering._update_attribute(  # pylint: disable=protected-access
                WindowCovering.attributes_by_name[
                    "current_position_lift_percentage"
                ].id,
                (100 - value),
            )
            self.endpoint.on_off._update_attribute(  # pylint: disable=protected-access
                OnOff.attributes_by_name["on_off"].id, value > 0
            )


class WindowCoveringB1(CustomCluster, WindowCovering):
    """Window covering cluster, used to cause commands to update the AnalogOutput present_value."""

    stop_called = bool(False)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        _LOGGER.debug("WindowCoveringB1 Cluster init")
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid: int, value: Any) -> None:
        _LOGGER.debug(
            "WindowCovering update attribute %04x to %s and stop_called is %s",
            attrid,
            value,
            self.stop_called,
        )
        if self.stop_called:
            _LOGGER.debug("Recently stopped, updating AnalogOutput value")
            self.stop_called = bool(False)
            self.endpoint.analog_output._update_attribute(  # pylint: disable=protected-access
                AnalogOutput.attributes_by_name["present_value"].id, value
            )
        super()._update_attribute(attrid, value)

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args: Any,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ) -> Any:
        """Overwrite the commands.

        Overwrite analog_output's current_value
        value to make the curtain work as expected.
        """
        _LOGGER.debug("WindowCovering command %04x", command_id)
        if command_id == self.commands_by_name["up_open"].id:
            (res,) = await self.endpoint.analog_output.write_attributes(
                {"present_value": 100}
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)
        if command_id == self.commands_by_name["down_close"].id:
            (res,) = await self.endpoint.analog_output.write_attributes(
                {"present_value": 0}
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)
        if command_id == self.commands_by_name["go_to_lift_percentage"].id:
            _LOGGER.debug("go_to_lift_percentage %d", args[0])
            (res,) = await self.endpoint.analog_output.write_attributes(
                {"present_value": (100 - args[0])}
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)
        if command_id == self.commands_by_name["stop"].id:
            self.stop_called = bool(True)
            return await super().command(
                command_id,
                *args,
                manufacturer=manufacturer,
                expect_reply=expect_reply,
                tsn=tsn,
                **kwargs,
            )


class OnOffB1(CustomCluster, OnOff):
    """On Off Cluster, used to update state based on AnalogOutput"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        _LOGGER.debug("OnOffB1 Cluster init")
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid: int, value: Any) -> None:
        _LOGGER.debug("OnOff update attribute %04x to %s", attrid, value)
        super()._update_attribute(attrid, value)


class CurtainB1(XiaomiCustomDevice):
    """Aqara Curtain Driver B1 device."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        super().__init__(*args, **kwargs)  # type: ignore
        _LOGGER.info("CurtainB1 custom quirk loaded for model ZNCLDJ11LM")

    signature = {
        MODELS_INFO: [(LUMI, "lumi.curtain")],
        ENDPOINTS: {
            # <SizePrefixedSimpleDescriptor endpoint=1 profile=260 device_type=514
            # device_version=1
            # input_clusters=["0x0000", "0x0001", "0x0003", "0x0004", "0x0005", "0x0006", "0x000a", "0x000d", "0x0013", "0x0102", "0x0406"]
            # output_clusters=["0x0001", "0x0006", "0x000a", "0x000d", "0x0013", "0x0019", "0x0102", "0x0406"]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Time.cluster_id,
                    AnalogOutput.cluster_id,
                    MultistateOutput.cluster_id,
                    WindowCovering.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    PowerConfiguration.cluster_id,
                    OnOff.cluster_id,
                    Time.cluster_id,
                    AnalogOutput.cluster_id,
                    MultistateOutput.cluster_id,
                    Ota.cluster_id,
                    WindowCovering.cluster_id,
                    OccupancySensing.cluster_id,
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
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    OnOffB1,
                    AnalogOutputB1,
                    WindowCoveringB1,
                ],
                OUTPUT_CLUSTERS: [
                    OnOffB1,
                    Time.cluster_id,
                    AnalogOutputB1,
                    Ota.cluster_id,
                    WindowCoveringB1,
                ],
            },
        },
    }
