"""Aqara Curtain Driver E1 device."""

from __future__ import annotations

from typing import Any, Final

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zdo.types import LogicalType, NodeDescriptor

from zhaquirks import CustomCluster
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    LocalIlluminanceMeasurementCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDeviceV2,
    XiaomiPowerConfigurationPercent,
)


class XiaomiAqaraDriverE1(XiaomiAqaraE1Cluster):
    """Xiaomi Aqara Curtain Driver E1 cluster."""

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        hand_open: Final = ZCLAttributeDef(
            id=0x0401, type=t.Bool, is_manufacturer_specific=True
        )
        positions_stored: Final = ZCLAttributeDef(
            id=0x0402, type=t.Bool, is_manufacturer_specific=True
        )
        store_position: Final = ZCLAttributeDef(
            id=0x0407, type=t.uint8_t, is_manufacturer_specific=True
        )
        hooks_lock: Final = ZCLAttributeDef(
            id=0x0427, type=t.uint8_t, is_manufacturer_specific=True
        )
        hooks_state: Final = ZCLAttributeDef(
            id=0x0428, type=t.uint8_t, is_manufacturer_specific=True
        )
        light_level: Final = ZCLAttributeDef(
            id=0x0429, type=t.uint8_t, is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.light_level.id:
            # Light level value seems like it can be 0, 1, or 2.
            # Multiply by 50 to map those values to later show: 1 lx, 50 lx, 100 lx.
            self.endpoint.illuminance.update_attribute(
                IlluminanceMeasurement.AttributeDefs.measured_value.id,
                value * 50,
            )
        super()._update_attribute(attrid, value)


class WindowCoveringE1(CustomCluster, WindowCovering):
    """Xiaomi Window Covering cluster that maps open/close to lift percentage."""

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
            args = (0,)
        elif command_id == WindowCovering.ServerCommandDefs.down_close.id:
            command_id = WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
            args = (100,)

        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )


(
    QuirkBuilder(LUMI, "lumi.curtain.agl001")
    .device_class(XiaomiCustomDeviceV2)
    .replaces_endpoint(1, device_type=zha.DeviceType.WINDOW_COVERING_DEVICE)
    .replaces(BasicCluster, endpoint_id=1)
    .replaces(XiaomiPowerConfigurationPercent, endpoint_id=1)
    .replaces(WindowCoveringE1, endpoint_id=1)
    .adds(LocalIlluminanceMeasurementCluster, endpoint_id=1)
    .replaces(XiaomiAqaraDriverE1, endpoint_id=1)
    .removes(XiaomiAqaraDriverE1, cluster_type=ClusterType.Client, endpoint_id=1)
    .node_descriptor(
        NodeDescriptor(
            logical_type=LogicalType.EndDevice,
            complex_descriptor_available=0,
            user_descriptor_available=0,
            reserved=0,
            aps_flags=0,
            frequency_band=NodeDescriptor.FrequencyBand.Freq2400MHz,
            mac_capability_flags=NodeDescriptor.MACCapabilityFlags.AllocateAddress,  # removes `MainsPowered`
            manufacturer_code=4447,
            maximum_buffer_size=127,
            maximum_incoming_transfer_size=100,
            server_mask=11264,
            maximum_outgoing_transfer_size=100,
            descriptor_capability_field=NodeDescriptor.DescriptorCapability.NONE,
        )
    )
    .add_to_registry()
)
