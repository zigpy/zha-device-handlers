"""NodOn Roller Shutter Relay Switch."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

NODON = "NodOn"


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


(
    QuirkBuilder(NODON, "SIN-4-RS-20")
    .applies_to(NODON, "SIN-4-RS-20_PRO")
    .replaces(NodOnWindowCovering)
    .number(
        attribute_name=NodOnWindowCovering.AttributeDefs.calibration_vertical_run_time_up.name,
        cluster_id=NodOnWindowCovering.cluster_id,
        min_value=0,
        max_value=65535,
        step=10,
        unit=UnitOfTime.MILLISECONDS,
        device_class=NumberDeviceClass.DURATION,
        initially_disabled=True,
        translation_key="calibration_vertical_run_time_up",
        fallback_name="Calibration vertical run time up",
    )
    .number(
        attribute_name=NodOnWindowCovering.AttributeDefs.calibration_vertical_run_time_down.name,
        cluster_id=NodOnWindowCovering.cluster_id,
        min_value=0,
        max_value=65535,
        step=10,
        unit=UnitOfTime.MILLISECONDS,
        device_class=NumberDeviceClass.DURATION,
        initially_disabled=True,
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
        initially_disabled=True,
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
        initially_disabled=True,
        translation_key="calibration_rotation_run_time_down",
        fallback_name="Calibration rotation run time down",
    )
    .add_to_registry()
)
