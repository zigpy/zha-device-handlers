"""Device handler for Bosch Light/shutter control unit II."""

from typing import Final

from zigpy import types as t
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import CustomCluster
from zhaquirks.bosch import BOSCH


class BoschDeviceMode(t.enum8):
    """Device mode enum."""

    Disabled = 0x00
    Cover = 0x01
    Light = 0x04


class BoschSwitchType(t.enum8):
    """Switch type enum."""

    Button = 0x01
    Button_key_change = 0x02
    Rocker_switch = 0x03
    Rocker_switch_key_change = 0x04


class BoschMotorState(t.enum8):
    """Motor state enum."""

    Stopped = 0x00
    Opening = 0x01
    Closing = 0x02


class BoschLightShutterControlII(CustomCluster):
    """Custom cluster for Bosch BMCT-SLZ device control."""

    cluster_id: Final[t.uint16_t] = 0xFCA0

    class AttributeDefs(BaseAttributeDefs):
        """Manufacturer specific attributes."""

        device_mode = ZCLAttributeDef(
            id=0x0000,
            type=BoschDeviceMode,
            access="rwp",
            is_manufacturer_specific=True,
        )

        switch_type = ZCLAttributeDef(
            id=0x0001,
            type=BoschSwitchType,
            access="rwp",
            is_manufacturer_specific=True,
        )

        calibration_opening_time = ZCLAttributeDef(
            id=0x0002,
            type=t.uint32_t,
            access="rwp",
            is_manufacturer_specific=True,
        )

        calibration_closing_time = ZCLAttributeDef(
            id=0x0003,
            type=t.uint32_t,
            access="rwp",
            is_manufacturer_specific=True,
        )

        calibration_button_hold_time = ZCLAttributeDef(
            id=0x0005,
            type=t.uint8_t,
            access="rwp",
            is_manufacturer_specific=True,
        )

        child_lock = ZCLAttributeDef(
            id=0x0008,
            type=t.Bool,
            access="rwp",
            is_manufacturer_specific=True,
        )

        calibration_motor_start_delay = ZCLAttributeDef(
            id=0x000F,
            type=t.uint8_t,
            access="rwp",
            is_manufacturer_specific=True,
        )

        motor_state = ZCLAttributeDef(
            id=0x0013,
            type=BoschMotorState,
            access="rp",
            is_manufacturer_specific=True,
        )


class BoschWindowCovering(CustomCluster, WindowCovering):
    """Custom Bosch window covering cluster.

    The Bosch reported type of Shutter only enables tilt commands (per the Zigbee cluster spec).
    This is overridden to Tilt_blind_tilt_and_lift because the device is a generic relay.
    """

    _CONSTANT_ATTRIBUTES = {
        WindowCovering.AttributeDefs.window_covering_type.id: WindowCovering.WindowCoveringType.Tilt_blind_tilt_and_lift,
    }


(
    QuirkBuilder(BOSCH, "RBSH-MMS-ZB-EU")
    .friendly_name(manufacturer=BOSCH, model="BMCT-SLZ")
    .replace_cluster_occurrences(BoschLightShutterControlII)
    .replaces(BoschWindowCovering)
    .sensor(
        BoschLightShutterControlII.AttributeDefs.motor_state.name,
        BoschLightShutterControlII.cluster_id,
        translation_key="motor_state",
        fallback_name="Motor state",
    )
    .enum(
        BoschLightShutterControlII.AttributeDefs.device_mode.name,
        BoschDeviceMode,
        BoschLightShutterControlII.cluster_id,
        translation_key="device_mode",
        fallback_name="Device mode",
    )
    .enum(
        BoschLightShutterControlII.AttributeDefs.switch_type.name,
        BoschSwitchType,
        BoschLightShutterControlII.cluster_id,
        translation_key="switch_type",
        fallback_name="Switch type",
    )
    .number(
        BoschLightShutterControlII.AttributeDefs.calibration_closing_time.name,
        BoschLightShutterControlII.cluster_id,
        min_value=1,
        max_value=90,
        step=0.1,
        unit=UnitOfTime.SECONDS,
        mode="box",
        multiplier=0.1,
        translation_key="closing_duration",
        fallback_name="Closing duration",
    )
    .number(
        BoschLightShutterControlII.AttributeDefs.calibration_opening_time.name,
        BoschLightShutterControlII.cluster_id,
        min_value=1,
        max_value=90,
        step=0.1,
        unit=UnitOfTime.SECONDS,
        mode="box",
        multiplier=0.1,
        translation_key="opening_duration",
        fallback_name="Opening duration",
    )
    .number(
        BoschLightShutterControlII.AttributeDefs.calibration_button_hold_time.name,
        BoschLightShutterControlII.cluster_id,
        min_value=0.1,
        max_value=2,
        step=0.1,
        unit=UnitOfTime.SECONDS,
        mode="box",
        multiplier=0.1,
        translation_key="long_press_duration",
        fallback_name="Long press duration",
    )
    .number(
        BoschLightShutterControlII.AttributeDefs.calibration_motor_start_delay.name,
        BoschLightShutterControlII.cluster_id,
        min_value=0,
        max_value=20,
        step=0.1,
        unit=UnitOfTime.SECONDS,
        mode="box",
        multiplier=0.1,
        translation_key="motor_start_delay",
        fallback_name="Motor start delay",
    )
    .switch(
        BoschLightShutterControlII.AttributeDefs.child_lock.name,
        BoschLightShutterControlII.cluster_id,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .switch(
        BoschLightShutterControlII.AttributeDefs.child_lock.name,
        BoschLightShutterControlII.cluster_id,
        endpoint_id=2,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .switch(
        BoschLightShutterControlII.AttributeDefs.child_lock.name,
        BoschLightShutterControlII.cluster_id,
        endpoint_id=3,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .add_to_registry()
)
