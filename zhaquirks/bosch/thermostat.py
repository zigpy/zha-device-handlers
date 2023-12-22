"""Device handler for Bosch thermostats."""
from typing import Final

import zigpy.types as t

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Groups, Ota, PollControl, Time
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import PowerConfigurationCluster
from zhaquirks.bosch import BOSCH
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

MANUFACTURER_ID = 0x1209

SCREEN_ORIENTATION = 0x400b
DISPLAY_MODE = 0x4039
SCREEN_TIMEOUT = 0x403a
SCREEN_BRIGHTNESS = 0x403b

WINDOW_OPEN = 0x4042
BOOST = 0x4043
SYSTEM_MODE = 0x4007
VALVE_POSITION = 0x4020
REMOTE_TEMPERATURE = 0x4040


class ScreenOrientation(t.uint8_t):
    Normal = 0x00
    Flipped = 0x01


class DisplayMode(t.enum8):
    Target = 0x00
    Measured = 0x01


class ScreenTimeout(t.enum8):
    pass


class ScreenBrightness(t.enum8):
    pass


class WindowOpen(t.enum8):
    Closed = 0x00
    Open = 0x01


class SystemMode(t.enum8):
    Auto = 0x00
    Heat = 0x01
    Off = 0x05


class BoschHvacUserInterface(UserInterface):
    """Bosch HVAC User Interface cluster"""

    ScreenOrientation: Final = ScreenOrientation
    DisplayMode: Final = DisplayMode
    ScreenTimeout: Final = ScreenTimeout
    ScreenBrightness: Final = ScreenBrightness

    class AttributeDefs(UserInterface.AttributeDefs):
        screen_orientation: Final = ZCLAttributeDef(
            id=SCREEN_ORIENTATION,
            type=ScreenOrientation,
            access="rw",
            is_manufacturer_specific=True
        )
        display_mode: Final = ZCLAttributeDef(
            id=DISPLAY_MODE,
            type=DisplayMode,
            access="rw",
            is_manufacturer_specific=True
        )
        screen_timeout: Final = ZCLAttributeDef(
            id=SCREEN_TIMEOUT,
            type=ScreenTimeout,
            access="rw",
            is_manufacturer_specific=True
        )
        screen_brightness: Final = ZCLAttributeDef(
            id=SCREEN_BRIGHTNESS,
            type=ScreenBrightness,
            access="rw",
            is_manufacturer_specific=True
        )


class BoschThermostat(Thermostat):
    """Bosch Thermostat cluster"""

    WindowOpen: Final = WindowOpen

    class AttributeDefs(Thermostat.AttributeDefs):
        window_open: Final = ZCLAttributeDef(
            id=WINDOW_OPEN,
            type=WindowOpen,
            access="rw",
            is_manufacturer_specific=True,
        )


class RBSHTRV0ZBEU(CustomDevice):
    """Custom device representing Bosch Radiator Thermostat II."""

    manufacturer_id_override = MANUFACTURER_ID

    signature = {
        MODELS_INFO: [(BOSCH, "RBSH-TRV0-ZB-EU")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    PollControl.cluster_id,
                    Thermostat.cluster_id,
                    UserInterface.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    PollControl.cluster_id,
                    BoschThermostat,
                    BoschHvacUserInterface,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id
                ],
            }
        }
    }
