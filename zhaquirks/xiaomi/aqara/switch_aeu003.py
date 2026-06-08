"""Aqara H2 Shutter device."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic, Identify

from zhaquirks.const import BUTTON_3, BUTTON_4, COMMAND, COMMAND_SINGLE
from zhaquirks.xiaomi import (
    AQARA,
    AnalogInputCluster,
    ElectricalMeasurementCluster,
    MeteringCluster,
)
from zhaquirks.xiaomi.aqara.opple_remote import COMMAND_3_SINGLE, COMMAND_4_SINGLE
from zhaquirks.xiaomi.aqara.opple_switch import MultistateInputCluster


class InvertedWindowCoveringCluster(CustomCluster, WindowCovering):
    """WindowCovering cluster that corrects the Aqara H2 position convention.

    The Aqara H2 shutter switch uses Home Assistant convention throughout
    (0 = closed, 100 = open), while ZHA expects Zigbee spec convention
    (0 = open, 100 = closed) and applies a 100-x inversion on both reads
    and writes.  Without correction this produces a double inversion in
    both directions.  This cluster pre-inverts values in both directions
    so the two inversions cancel out:

    - Incoming attribute reports (_update_attribute): device→cluster value
      is inverted before ZHA reads it.
    - Outgoing go_to_lift_percentage commands (request): ZHA-inverted value
      is re-inverted before it is sent to the device.
    """

    CURRENT_POSITION_LIFT_PERCENTAGE = (
        WindowCovering.AttributeDefs.current_position_lift_percentage.id
    )
    GO_TO_LIFT_PERCENTAGE_CMD = (
        WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
    )

    # -- Incoming: fix reported position ------------------------------------

    def _update_attribute(self, attrid, value):
        if attrid == self.CURRENT_POSITION_LIFT_PERCENTAGE and value is not None:
            value = 100 - value
        super()._update_attribute(attrid, value)

    # -- Outgoing: fix commanded position -----------------------------------

    async def request(self, general, command_id, schema, *args, **kwargs):
        """Extend WindowCovering.request to override Go to lift percentage commands."""
        if not general and command_id == self.GO_TO_LIFT_PERCENTAGE_CMD and args:
            args = (100 - args[0],) + args[1:]
        return await super().request(general, command_id, schema, *args, **kwargs)


(
    QuirkBuilder(AQARA, "lumi.switch.aeu003")
    .adds_endpoint(1, zha.DeviceType.ON_OFF_SWITCH)
    .adds_endpoint(2, zha.DeviceType.ON_OFF_SWITCH)
    .adds_endpoint(3, zha.DeviceType.ON_OFF_SWITCH)
    .adds_endpoint(4, zha.DeviceType.ON_OFF_SWITCH)
    .adds_endpoint(21, zha.DeviceType.ON_OFF_SWITCH)
    .adds(Basic, endpoint_id=1)
    .adds(Identify, endpoint_id=1)
    .replaces(InvertedWindowCoveringCluster, endpoint_id=1)
    .replaces(MultistateInputCluster, endpoint_id=3)
    .replaces(MultistateInputCluster, endpoint_id=4)
    .replaces(ElectricalMeasurementCluster, endpoint_id=1)
    .replaces(MeteringCluster, endpoint_id=1)
    .replaces(AnalogInputCluster, endpoint_id=21)
    .device_automation_triggers(
        {
            (COMMAND_SINGLE, BUTTON_3): {COMMAND: COMMAND_3_SINGLE},
            (COMMAND_SINGLE, BUTTON_4): {COMMAND: COMMAND_4_SINGLE},
        }
    )
    .add_to_registry()
)
