"""NodOn Roller Shutter Relay Switch."""

import zigpy.types as t
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.builder import EntityType, NumberDeviceClass, QuirkBuilder, UnitOfTime
from zhaquirks.clusters import CustomCluster

NODON = "NodOn"


class NodOnSwitchType(t.enum8):
    """Type of the switch wired to the device."""

    Bistable = 0x00
    Monostable = 0x01
    AutoDetect = 0x02


class NodOnWindowCovering(WindowCovering, CustomCluster):
    """NodOn custom WindowCovering cluster."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # IDs 0x0001-0x0004 redefined below
        window_covering_type = (
            WindowCovering.AttributeDefs.window_covering_type
        )  # 0x0000
        number_of_actuations_lift = (
            WindowCovering.AttributeDefs.number_of_actuations_lift
        )  # 0x0005
        number_of_actuations_tilt = (
            WindowCovering.AttributeDefs.number_of_actuations_tilt
        )  # 0x0006
        config_status = WindowCovering.AttributeDefs.config_status  # 0x0007
        current_position_lift_percentage = (
            WindowCovering.AttributeDefs.current_position_lift_percentage
        )  # 0x0008
        current_position_tilt_percentage = (
            WindowCovering.AttributeDefs.current_position_tilt_percentage
        )  # 0x0009
        installed_open_limit_lift = (
            WindowCovering.AttributeDefs.installed_open_limit_lift
        )  # 0x0010
        installed_closed_limit_lift = (
            WindowCovering.AttributeDefs.installed_closed_limit_lift
        )  # 0x0011
        installed_open_limit_tilt = (
            WindowCovering.AttributeDefs.installed_open_limit_tilt
        )  # 0x0012
        installed_closed_limit_tilt = (
            WindowCovering.AttributeDefs.installed_closed_limit_tilt
        )  # 0x0013
        velocity_lift = WindowCovering.AttributeDefs.velocity_lift  # 0x0014
        acceleration_time_lift = (
            WindowCovering.AttributeDefs.acceleration_time_lift
        )  # 0x0015
        deceleration_time_lift = (
            WindowCovering.AttributeDefs.deceleration_time_lift
        )  # 0x0016
        window_covering_mode = (
            WindowCovering.AttributeDefs.window_covering_mode
        )  # 0x0017
        intermediate_setpoints_lift = (
            WindowCovering.AttributeDefs.intermediate_setpoints_lift
        )  # 0x0018
        intermediate_setpoints_tilt = (
            WindowCovering.AttributeDefs.intermediate_setpoints_tilt
        )  # 0x0019

        # porting https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/src/devices/nodon.ts#L16

        # Set vertical run time up of the roller shutter.
        calibration_vertical_run_time_up = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )

        # Set vertical run time down of the roller shutter.
        calibration_vertical_run_time_down = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )

        # Set rotation run time up of the roller shutter.
        calibration_rotation_run_time_up = ZCLAttributeDef(
            id=0x0003,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )

        # Set rotation run time down of the roller shutter.
        calibration_rotation_run_time_down = ZCLAttributeDef(
            id=0x0004,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )

        # Type of the switch wired to the device.
        switch_type = ZCLAttributeDef(
            id=0x1001,
            type=NodOnSwitchType,
            access="rw",
            is_manufacturer_specific=True,
        )

        # Recompute the run times on each full run, overwriting the manual values.
        calibration_auto_adjust = ZCLAttributeDef(
            id=0x1002,
            type=t.Bool,
            access="rw",
            is_manufacturer_specific=True,
        )


class NodOnCalibrationCluster(LocalDataCluster):
    """Virtual cluster to start a calibration from a button.

    Writing window_covering_mode from an entity would overwrite the other bits
    (motor direction reversed, LED feedback), so only the calibration bit is set.
    """

    cluster_id = 0xFBFD
    name = "NodOn Calibration"
    ep_attribute = "nodon_calibration"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # Start a full calibration run (up, down, up), the device clears the bit when done.
        start_calibration = ZCLAttributeDef(id=0x0000, type=t.Bool)

    async def _start_calibration(self):
        """Set the calibration bit of window_covering_mode on the device."""
        window_covering = self.endpoint.window_covering
        mode_attr = WindowCovering.AttributeDefs.window_covering_mode
        await window_covering.read_attributes([mode_attr.id])
        mode = WindowCovering.WindowCoveringMode(window_covering.get(mode_attr.id) or 0)
        mode |= WindowCovering.WindowCoveringMode.Run_in_calibration_mode
        return await window_covering.write_attributes({mode_attr.id: mode})

    async def write_attributes(self, attributes, manufacturer=None, **kwargs):
        """Translate the start_calibration write into a window_covering_mode write."""
        for attr in attributes:
            if self.find_attribute(attr) == self.AttributeDefs.start_calibration:
                return await self._start_calibration()
        return await super().write_attributes(attributes, manufacturer, **kwargs)


(
    QuirkBuilder(NODON, "SIN-4-RS-20")
    .applies_to(NODON, "SIN-4-RS-20_PRO")
    .replaces(NodOnWindowCovering)
    .number(
        attribute_name=NodOnWindowCovering.AttributeDefs.calibration_vertical_run_time_up.name,
        cluster_id=NodOnWindowCovering.cluster_id,
        min_value=0,
        max_value=655350,
        step=10,
        multiplier=10,
        unit=UnitOfTime.MILLISECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="calibration_vertical_run_time_up",
        fallback_name="Calibration vertical run time up",
    )
    .number(
        attribute_name=NodOnWindowCovering.AttributeDefs.calibration_vertical_run_time_down.name,
        cluster_id=NodOnWindowCovering.cluster_id,
        min_value=0,
        max_value=655350,
        step=10,
        multiplier=10,
        unit=UnitOfTime.MILLISECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="calibration_vertical_run_time_down",
        fallback_name="Calibration vertical run time down",
    )
    .number(
        attribute_name=NodOnWindowCovering.AttributeDefs.calibration_rotation_run_time_up.name,
        cluster_id=NodOnWindowCovering.cluster_id,
        min_value=0,
        max_value=65535,
        step=10,
        unit=UnitOfTime.MILLISECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="calibration_rotation_run_time_up",
        fallback_name="Calibration rotation run time up",
    )
    .number(
        attribute_name=NodOnWindowCovering.AttributeDefs.calibration_rotation_run_time_down.name,
        cluster_id=NodOnWindowCovering.cluster_id,
        min_value=0,
        max_value=65535,
        step=10,
        unit=UnitOfTime.MILLISECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="calibration_rotation_run_time_down",
        fallback_name="Calibration rotation run time down",
    )
    .enum(
        attribute_name=NodOnWindowCovering.AttributeDefs.switch_type.name,
        enum_class=NodOnSwitchType,
        cluster_id=NodOnWindowCovering.cluster_id,
        translation_key="switch_type",
        fallback_name="Switch type",
    )
    .switch(
        attribute_name=NodOnWindowCovering.AttributeDefs.calibration_auto_adjust.name,
        cluster_id=NodOnWindowCovering.cluster_id,
        translation_key="calibration_auto_adjust",
        fallback_name="Calibration auto adjust",
    )
    .adds(NodOnCalibrationCluster)
    .write_attr_button(
        attribute_name=NodOnCalibrationCluster.AttributeDefs.start_calibration.name,
        attribute_value=True,
        cluster_id=NodOnCalibrationCluster.cluster_id,
        translation_key="run_auto_calibration",
        fallback_name="Run auto-calibration",
    )
    .command_button(
        command_name=Basic.ServerCommandDefs.reset_fact_default.name,
        cluster_id=Basic.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="factory_reset",
        fallback_name="Factory reset",
    )
    .add_to_registry()
)
