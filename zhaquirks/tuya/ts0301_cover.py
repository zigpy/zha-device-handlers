"""Correct inverted lift percentages on selected Tuya TS0301 covers."""

from zigpy.zcl.clusters.closures import WindowCovering

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster


CURRENT_POSITION_LIFT_PERCENTAGE = (
    WindowCovering.AttributeDefs.current_position_lift_percentage.id
)
GO_TO_LIFT_PERCENTAGE = WindowCovering.ServerCommandDefs.go_to_lift_percentage.id


def _invert_lift_percentage(value):
    """Invert valid lift percentages while preserving unknown values."""
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 100:
        return 100 - value
    return value


class ZemismartTS0301WindowCoveringCluster(CustomCluster, WindowCovering):
    """Translate device lift percentages into standard ZCL conventions."""

    def _update_attribute(self, attrid, value):
        if attrid == CURRENT_POSITION_LIFT_PERCENTAGE:
            value = _invert_lift_percentage(value)
        super()._update_attribute(attrid, value)

    async def command(
        self, command_id, *args, manufacturer=None, expect_reply=True, **kwargs
    ):
        """Translate ZCL lift targets to the device's percentage convention."""
        if command_id == GO_TO_LIFT_PERCENTAGE and args:
            args = (_invert_lift_percentage(args[0]), *args[1:])
        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            **kwargs,
        )


(
    QuirkBuilder("_TZE200_cirjrpxe", "TS0301")
    .replaces(ZemismartTS0301WindowCoveringCluster, endpoint_id=1)
    .add_to_registry()
)
