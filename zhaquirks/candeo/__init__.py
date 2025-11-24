"""Module for Candeo quirks implementations."""

import math
from typing import Final

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import (
    BaseCommandDefs,
    DataTypeId,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.const import ZONE_TYPE

CANDEO = "Candeo"


class CandeoSwitchType(t.enum8):
    """Candeo Switch Type."""

    Momentary = 0x00
    Toggle = 0x01


class CandeoRemoteDirection(t.enum8):
    """Candeo Remote Direction."""

    Right = 0x00
    Left = 0x01


class CandeoIlluminanceMeasurementCluster(IlluminanceMeasurement, CustomCluster):
    """Candeo Illuminance Measurement Cluster."""

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.measured_value.id:
            value = pow(10, ((value - 1) / 10000))
            value = self.lux_calibration(value)
            value = 10000 * math.log10(value) + 1
            value = round(value)
        super()._update_attribute(attrid, value)

    @staticmethod
    def lux_calibration(value):
        """Calibrate lux reading from device."""
        lux_value = 1
        if 0 < value <= 2200:
            lux_value = -7.969192 + (0.0151988 * value)
        elif 2200 < value <= 2500:
            lux_value = -1069.189434 + (0.4950663 * value)
        elif value > 2500:
            lux_value = (78029.21628 - (61.73575 * value)) + (0.01223567 * (value**2))
        lux_value = max(lux_value, 1)
        return lux_value


class CandeoBasicCluster(Basic, CustomCluster):
    """Candeo Basic Cluster."""

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute Definitions."""

        external_switch_type = ZCLAttributeDef(
            id=0x8803,
            type=CandeoSwitchType,
            zcl_type=DataTypeId.uint8,
            access="rw",
            is_manufacturer_specific=True,
        )


class CandeoIasZoneContactCluster(IasZone, CustomCluster):
    """Candeo IasZone Contact Cluster."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Contact_Switch}


class CandeoIasZoneMotionCluster(IasZone, CustomCluster):
    """Candeo IasZone Motion Cluster."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Motion_Sensor}


class CandeoIasZoneWaterCluster(IasZone, CustomCluster):
    """Candeo IasZone Water Cluster."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Water_Sensor}


class CandeoRGBColorCluster(Color, CustomCluster):
    """Candeo RGB Color Cluster."""

    _CONSTANT_ATTRIBUTES = {
        Color.AttributeDefs.color_capabilities.id: Color.ColorCapabilities.XY_attributes,
        Color.AttributeDefs.color_temperature.id: None,
        Color.AttributeDefs.start_up_color_temperature.id: None,
    }


class CandeoCCTColorCluster(Color, CustomCluster):
    """Candeo CCT Color Cluster."""

    _CONSTANT_ATTRIBUTES = {
        Color.AttributeDefs.color_capabilities.id: Color.ColorCapabilities.Color_temperature
    }


class CandeoRGBCCTColorCluster(Color, CustomCluster):
    """Candeo RGBCCT Color Cluster."""

    _CONSTANT_ATTRIBUTES = {
        Color.AttributeDefs.color_capabilities.id: Color.ColorCapabilities.XY_attributes
        + Color.ColorCapabilities.Color_temperature
    }


class CandeoOnOffRemoteCluster(OnOff, CustomCluster):
    """Candeo OnOff Remote Cluster."""

    class ServerCommandDefs(BaseCommandDefs):
        """overwrite ServerCommandDefs."""

        double: Final = ZCLCommandDef(
            id=0x00,
            schema={},
        )
        press: Final = ZCLCommandDef(
            id=0x01,
            schema={},
        )
        hold: Final = ZCLCommandDef(
            id=0x02,
            schema={},
        )
        release: Final = ZCLCommandDef(
            id=0x03,
            schema={},
        )


class CandeoLevelControlRemoteCluster(LevelControl, CustomCluster):
    """Candeo LevelControl Remote Cluster."""

    class ServerCommandDefs(BaseCommandDefs):
        """overwrite ServerCommandDefs."""

        started_rotating: Final = ZCLCommandDef(
            id=0x05,
            schema={"direction": CandeoRemoteDirection},
        )
        continued_rotating: Final = ZCLCommandDef(
            id=0x06,
            schema={"direction": CandeoRemoteDirection},
        )
        stopped_rotating: Final = ZCLCommandDef(
            id=0x03,
            schema={},
        )
