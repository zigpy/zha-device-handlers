"""Module for Legrand devices."""

from typing import Any

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import EffectIdentifier, EffectVariant, Identify
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    DataTypeId,
    GeneralCommand,
    ZCLAttributeDef,
)

from zhaquirks import PowerConfigurationCluster

LEGRAND = "Legrand"
MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC01  # decimal = 64513


class DeviceMode(t.enum16):
    """Device modes for some Legrand devices. To be used in custom cluster.

    Note: some values are taken from the Z2M code.
    """

    Pilot_Off = 0x0001
    Pilot_On = 0x0002
    Switch = 0x0003
    Auto = 0x0004
    Dimmer_Off = 0x0100
    Dimmer_On = 0x0101


class LegrandCluster(CustomCluster):
    """LegrandCluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "LegrandCluster"
    ep_attribute = "legrand_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Cluster attributes."""

        device_mode = ZCLAttributeDef(
            id=0x0000,
            type=DeviceMode,
            zcl_type=DataTypeId.data16,
            is_manufacturer_specific=True,
        )
        led_dark = ZCLAttributeDef(
            id=0x0001, type=t.Bool, is_manufacturer_specific=True
        )
        led_on = ZCLAttributeDef(id=0x0002, type=t.Bool, is_manufacturer_specific=True)


class LegrandIdentify(CustomCluster, Identify):
    """Custom Identify cluster for Legrand devices. Replaces the identify command."""

    async def command(
        self,
        command_id: GeneralCommand | int | t.uint8_t,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Override the command method to customize the identify command."""

        if command_id == Identify.ServerCommandDefs.identify.id:
            # Remove identify command specific arguments
            identify_time = kwargs.pop("identify_time", None)

            await super().command(
                command_id=Identify.ServerCommandDefs.trigger_effect.id,
                effect_id=EffectIdentifier.Blink,
                effect_variant=EffectVariant.Default,
                **kwargs,
            )

            # Restore identify command specific arguments
            if identify_time is not None:
                kwargs["identify_time"] = identify_time

        return await super().command(
            command_id,
            *args,
            **kwargs,
        )


class ShutterCalibrationMode(t.enum8):
    """Shutter calibration modes for Legrand devices."""

    Classic = 0x00
    Specific = 0x01
    Up_Down_Stop = 0x02
    Temporal = 0x03
    Venetian = 0x04


class LegrandShutterCluster(CustomCluster, WindowCovering):
    """Custom Shutter cluster for Legrand devices. Adds calibration mode."""

    class AttributeDefs(WindowCovering.AttributeDefs):
        """Cluster attributes."""

        calibration_mode = ZCLAttributeDef(
            id=0xF002,
            type=ShutterCalibrationMode,
            is_manufacturer_specific=True,
        )


class LegrandPowerConfigurationCluster(PowerConfigurationCluster):
    """PowerConfiguration conversor 'V --> %' for Legrand devices."""

    MIN_VOLTS = 2.5
    MAX_VOLTS = 3.0
