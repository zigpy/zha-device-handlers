"""MOES ZC301 pull-cord curtain motor quirk for _TZ3210_hs01bacp / TS030F."""

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering

from zhaquirks.builder import EntityPlatform, EntityType, SensorStateClass
from zhaquirks.tuya import TUYA_SEND_DATA, TuyaCommand
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster, TuyaWindowCovering


class MoesWindowCovering(TuyaWindowCovering):
    """Window covering that uses the standard ZCL commands for open/close/stop."""

    async def command(self, command_id, *args, **kwargs):
        """Send standard ZCL Window Covering commands instead of Tuya datapoints.

        This firmware implements the standard ZCL WindowCovering cluster, so
        open/close/stop and go-to-position are sent as ordinary ZCL commands.
        Tuya datapoints are still used for position reports and calibration.
        """
        return await WindowCovering.command(
            self,
            command_id,
            *args,
            **kwargs,
        )


class MoesCoverMCUCluster(TuyaMCUCluster):
    """Accept the device-specific Tuya datapoint report command 0x05."""

    class ClientCommandDefs(TuyaMCUCluster.ClientCommandDefs):
        """Tuya MCU client commands plus the 0x05 datapoint report command."""

        moes_data_report = foundation.ZCLCommandDef(
            id=0x05,
            schema={"data": TuyaCommand},
            manufacturer_code=None,
        )

    def handle_moes_data_report(self, command):
        """Process command 0x05 through the normal Tuya datapoint handler."""
        return self.handle_get_data(command)


READ_ONLY = foundation.ZCLAttributeAccess.Read


class MoesMotorCalibration(t.enum8):
    """DP5 motor calibration values."""

    None_ = 0x00
    Up_Start = 0x01
    Down_Start = 0x02
    Completed = 0x03


class MoesWorkState(t.enum8):
    """DP7 work state."""

    Stanby = 0x00
    Opening = 0x01
    Closing = 0x02


class MoesSituationSet(t.enum8):
    """DP11 percentage meaning."""

    Fully_Open = 0x00
    Fully_Close = 0x01


class MoesChargeState(t.enum8):
    """DP101 charge state."""

    Uncharged = 0x00
    Charging = 0x01
    Charged = 0x02


class MoesFault(t.enum8):
    """DP12 fault state."""

    None_ = 0x00
    Motor_Fault = 0x01


(
    TuyaQuirkBuilder("_TZ3210_hs01bacp", "TS030F")
    .replaces_endpoint(
        1,
        device_type=zha.DeviceType.WINDOW_COVERING_DEVICE,
    )
    .tuya_cover(
        control_dp=1,
        position_state_dp=3,
        position_control_dp=2,
        invert=False,
        cover_cfg=MoesWindowCovering,
    )
    .tuya_dp_attribute(
        dp_id=5,
        attribute_name="motor_calibration",
        type=t.enum8,
        access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write,
    )
    .write_attr_button(
        attribute_name="motor_calibration",
        attribute_value=MoesMotorCalibration.Up_Start,
        cluster_id=TuyaMCUCluster.cluster_id,
        unique_id_suffix="calibration_up_start",
        translation_key="calibrate_up",
        fallback_name="Start upward calibration",
    )
    .write_attr_button(
        attribute_name="motor_calibration",
        attribute_value=MoesMotorCalibration.Down_Start,
        cluster_id=TuyaMCUCluster.cluster_id,
        unique_id_suffix="calibration_down_start",
        translation_key="calibrate_down",
        fallback_name="Start downward calibration",
    )
    .write_attr_button(
        attribute_name="motor_calibration",
        attribute_value=MoesMotorCalibration.Completed,
        cluster_id=TuyaMCUCluster.cluster_id,
        unique_id_suffix="calibration_finish",
        translation_key="finish_calibration",
        fallback_name="Finish calibration",
    )
    .command_button(
        command_name="stop",
        cluster_id=WindowCovering.cluster_id,
        unique_id_suffix="mark_calibrated",
        translation_key="mark_calibrated",
        fallback_name="Stop and save current limit",
    )
    .tuya_enum(
        dp_id=7,
        attribute_name="work_state",
        enum_class=MoesWorkState,
        access=READ_ONLY,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="work_state",
        fallback_name="Work state",
    )
    .tuya_sensor(
        dp_id=10,
        attribute_name="time_total",
        type=t.uint32_t,
        unit="ms",
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="time_total",
        fallback_name="Full travel time",
    )
    .tuya_enum(
        dp_id=11,
        attribute_name="situation_set",
        enum_class=MoesSituationSet,
        translation_key="situation_set",
        fallback_name="Percentage meaning",
    )
    .tuya_enum(
        dp_id=12,
        attribute_name="fault",
        enum_class=MoesFault,
        access=READ_ONLY,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="fault",
        fallback_name="Fault",
    )
    .tuya_battery(
        dp_id=13,
    )
    .tuya_enum(
        dp_id=101,
        attribute_name="charge_state",
        enum_class=MoesChargeState,
        access=READ_ONLY,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="charge_state",
        fallback_name="Charge state",
    )
    .tuya_switch(
        dp_id=107,
        attribute_name="curtain_close_direction",
        translation_key="curtain_close_direction",
        fallback_name="Closing direction",
    )
    .tuya_sensor(
        dp_id=108,
        attribute_name="total_meters",
        type=t.uint32_t,
        state_class=SensorStateClass.TOTAL_INCREASING,
        translation_key="total_meters",
        fallback_name="Total metres travelled",
    )
    .tuya_switch(
        dp_id=155,
        attribute_name="charge_led_switch",
        translation_key="charge_led_switch",
        fallback_name="Charge LED",
    )
    .tuya_enchantment()
    .skip_configuration()
    .add_to_registry(
        replacement_cluster=MoesCoverMCUCluster,
        mcu_write_command=TUYA_SEND_DATA,
    )
)
