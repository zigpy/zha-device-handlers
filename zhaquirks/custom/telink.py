"""Telink TLSR825x based devices with custom firmware.

see https://github.com/pvvx/ZigbeeTLc
"""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature, UnitOfTime
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.hvac import ScheduleProgrammingVisibility, UserInterface
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import CustomCluster


class Display(t.enum8):
    """Turn off the display."""

    Off = 0x01
    On = 0x00


class CustomUserInterfaceCluster(CustomCluster, UserInterface):
    """Custom User Interface Cluster with smiley control."""

    class AttributeDefs(UserInterface.AttributeDefs):
        """Attribute Definitions."""

        # display. 0 - display is off, 1 - display is on
        display = ZCLAttributeDef(
            id=0x0106,
            type=Display,
            access="rw",
            is_manufacturer_specific=True,
        )

        # comfort temperature min: A value in 0.01ºC to set minimum comfort temperature for happy face
        comfort_temperature_min = ZCLAttributeDef(
            id=0x0102,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )

        # comfort temperature max: A value in 0.01ºC to set maximum comfort temperature for happy face
        comfort_temperature_max = ZCLAttributeDef(
            id=0x0103,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )

        # comfort humidity min: A value in 0.01%RH to set minimum comfort humidity for happy face
        comfort_humidity_min = ZCLAttributeDef(
            id=0x0104,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )

        # comfort humidity max: A value in 0.01%RH to set maximum comfort humidity for happy face
        comfort_humidity_max = ZCLAttributeDef(
            id=0x0105,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )

        # A value in 0.01ºC offset to fix up incorrect values from sensor
        temperature_offset = ZCLAttributeDef(
            id=0x0100,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )

        # A value in 0.01%RH offset to fix up incorrect values from sensor
        humidity_offset = ZCLAttributeDef(
            id=0x0101,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )
        # Measurement interval, step 1 second, range: 3..255 seconds. Default 10 seconds.
        measurement_interval = ZCLAttributeDef(
            id=0x0107,
            type=t.uint8_t,
            access="rw",
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("MiaoMiaoCe", "MHO-C401N-z")
    .applies_to("MiaMiaoCe", "MHO-C401N-z")  # typo until v. 1.2.2
    .applies_to("MiaoMiaoCe", "MHO-C401-z")
    .applies_to("MiaoMiaoCe", "MHO-C122-z")
    .applies_to("MiaMiaoCe", "MHO-C122-z")  # typo until v. 1.2.2
    .applies_to("Xiaomi", "LYWSD03MMC-z")
    .applies_to("Tuya", "TS0201-z")
    .applies_to("Tuya", "TH03Z-z")
    .applies_to("Tuya", "ZTH01-z")
    .applies_to("Tuya", "ZTH02-z")
    .applies_to("Tuya", "LKTMZL02-z")
    .applies_to("Tuya", "ZY-ZTH02-z")
    .applies_to("Sonoff", "TH03-z")
    .applies_to("Qingping", "CGDK2-z")
    .removes(CustomUserInterfaceCluster.cluster_id, cluster_type=ClusterType.Client)
    .adds(CustomUserInterfaceCluster)
    .number(
        CustomUserInterfaceCluster.AttributeDefs.temperature_offset.name,
        CustomUserInterfaceCluster.cluster_id,
        min_value=-327.67,
        max_value=327.67,
        step=0.01,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="temperature_offset",
        fallback_name="Temperature offset",
        multiplier=0.01,
        mode="box",
    )
    .number(
        CustomUserInterfaceCluster.AttributeDefs.humidity_offset.name,
        CustomUserInterfaceCluster.cluster_id,
        min_value=-327.67,
        max_value=327.67,
        step=0.01,
        unit=PERCENTAGE,
        translation_key="humidity_offset",
        fallback_name="Humidity offset",
        multiplier=0.01,
        mode="box",
    )
    .number(
        CustomUserInterfaceCluster.AttributeDefs.comfort_temperature_min.name,
        CustomUserInterfaceCluster.cluster_id,
        min_value=-327.67,
        max_value=327.67,
        step=0.01,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="comfort_temperature_min",
        fallback_name="Comfort temperature min",
        multiplier=0.01,
        mode="box",
    )
    .number(
        CustomUserInterfaceCluster.AttributeDefs.comfort_temperature_max.name,
        CustomUserInterfaceCluster.cluster_id,
        min_value=-327.67,
        max_value=327.67,
        step=0.01,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="comfort_temperature_max",
        fallback_name="Comfort temperature max",
        multiplier=0.01,
        mode="box",
    )
    .number(
        CustomUserInterfaceCluster.AttributeDefs.comfort_humidity_min.name,
        CustomUserInterfaceCluster.cluster_id,
        min_value=0,
        max_value=99,
        step=1,
        unit=PERCENTAGE,
        translation_key="comfort_humidity_min",
        fallback_name="Comfort humidity min",
        multiplier=0.01,
        mode="box",
    )
    .number(
        CustomUserInterfaceCluster.AttributeDefs.comfort_humidity_max.name,
        CustomUserInterfaceCluster.cluster_id,
        min_value=0,
        max_value=99,
        step=1,
        unit=PERCENTAGE,
        translation_key="comfort_humidity_max",
        fallback_name="Comfort humidity max",
        multiplier=0.01,
        mode="box",
    )
    .number(
        CustomUserInterfaceCluster.AttributeDefs.measurement_interval.name,
        CustomUserInterfaceCluster.cluster_id,
        min_value=3,
        max_value=255,
        unit=UnitOfTime.SECONDS,
        translation_key="measurement_interval",
        fallback_name="Measurement interval",
        mode="box",
    )
    .switch(
        CustomUserInterfaceCluster.AttributeDefs.display.name,
        CustomUserInterfaceCluster.cluster_id,
        off_value=1,
        on_value=0,
        translation_key="display_enabled",
        fallback_name="Display enabled",
    )
    .switch(
        CustomUserInterfaceCluster.AttributeDefs.schedule_programming_visibility.name,
        CustomUserInterfaceCluster.cluster_id,
        translation_key="show_smiley",
        fallback_name="Show smiley",
        off_value=ScheduleProgrammingVisibility.Disabled,
        on_value=ScheduleProgrammingVisibility.Enabled,
    )
    .add_to_registry()
)
