"""Aqara Curtain Driver E1 device."""
from __future__ import annotations

from typing import Any

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration, Time
from zigpy.zdo.types import NodeDescriptor

from zhaquirks import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import (
    BasicCluster,
    LUMI,
    XiaomiAqaraE1Cluster,
    XiaomiCluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)


class XiaomiAqaraDriverE1(XiaomiAqaraE1Cluster):
    """Xiaomi mfg cluster implementation specific for E1 Driver."""

    attributes = XiaomiCluster.attributes.copy()
    attributes.update(
        {
            0x0402: ("positions_stored", t.Bool, True),
            0x0407: ("store_position", t.uint8_t, True),
        }
    )


class WindowCoveringE1(CustomCluster, WindowCovering):
    """Xiaomi Window Covering cluster that inverts the motor direction if needed."""

    # TODO: commented out for now
    # def _update_attribute(self, attrid, value):
    #     if attrid == WindowCovering.AttributeDefs.current_position_lift_percentage.id:
    #         # TODO: improve this check? remove default? initialize? does the motor save this attr?
    #         # TODO: should we do this in HA? (does it have a way now to invert motor?)
    #         # TODO: should this always be reversed?
    #         if (
    #             self.get(WindowCovering.AttributeDefs.window_covering_mode.id, 0)
    #             & WindowCovering.WindowCoveringMode.Motor_direction_reversed
    #         ):
    #             value = 100 - value
    #     super()._update_attribute(attrid, value)

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args: Any,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ) -> Any:
        """Overwrite the open/close commands to call the lift percentage command instead."""
        if command_id == WindowCovering.ServerCommandDefs.up_open.id:
            command_id = WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
            args = (0,)  # TODO: inverted?
        elif command_id == WindowCovering.ServerCommandDefs.down_close.id:
            command_id = WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
            args = (100,)  # TODO: inverted?
        # elif command_id == WindowCovering.ServerCommandDefs.go_to_lift_percentage.id:
        #     args = (100 - args[0],)  # TODO: needed to invert here? (depending on attr?)

        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )


# TODO: check if cluster works
# TODO: currently duplicated with roller_curtain_e1.py
class PowerConfigurationDriverE1(XiaomiPowerConfiguration):
    """Power cluster which ignores Xiaomi voltage reports."""

    def _update_battery_percentage(self, voltage_mv: int) -> None:
        """Ignore Xiaomi voltage reports, so they're not used to calculate battery percentage."""
        # This device sends battery percentage reports which are handled using a XiaomiCluster and
        # the inherited XiaomiPowerConfiguration cluster.
        # This device might also send Xiaomi battery reports, so we only want to use those for the voltage attribute,
        # but not for the battery percentage. XiaomiPowerConfiguration.battery_reported() still updates the voltage.


class DriverE1(XiaomiCustomDevice):
    """Aqara Curtain Driver E1 device."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.curtain.agl001")],
        ENDPOINTS: {
            # <SizePrefixedSimpleDescriptor endpoint=1 profile=260 device_type=263
            # device_version=1
            # input_clusters=[0, 1, 3, 10, 258, 64704]
            # output_clusters=[3, 10, 25, 64704]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Time.cluster_id,
                    WindowCovering.cluster_id,
                    XiaomiAqaraDriverE1.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                    XiaomiAqaraDriverE1.cluster_id,
                ],
            }
        },
    }
    replacement = {
        # TODO: needed?
        # NODE_DESCRIPTOR: NodeDescriptor(
        #     0x02, 0x40, 0x80, 0x115F, 0x7F, 0x0064, 0x2C00, 0x0064, 0x00
        # ),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    PowerConfigurationDriverE1,
                    Identify.cluster_id,
                    Time.cluster_id,
                    WindowCoveringE1,
                    XiaomiAqaraDriverE1,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                    # XiaomiAqaraDriverE1, # TODO: keep in OUTPUT too?
                ],
            }
        },
    }
