"""Xiaomi LYWSD03MMC Bluetooth temperature and humidity sensor."""

# https://github.com/devbis/z03mmc
# defined by 1.1.0 firmware (0x11003001)
# see README.md in the repo for more info

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature
from zigpy.types import Bool, int16s, uint16_t
from zigpy.zcl.clusters.hvac import UserInterface
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import CustomCluster


class TemperatureMeasurementCustom(CustomCluster, TemperatureMeasurement):
    """Temperature Measurement Cluster with calibration attribute."""

    class AttributeDefs(TemperatureMeasurement.AttributeDefs):
        """Attribute Definitions."""

        # A value in 0.01ºC offset to fix up incorrect values from sensor
        temperature_calibration = ZCLAttributeDef(
            id=0x0010,
            type=int16s,
            access="rw",
            is_manufacturer_specific=True,
        )


class RelativeHumidityCustom(CustomCluster, RelativeHumidity):
    """Relative Humidity Cluster with calibration attribute."""

    class AttributeDefs(RelativeHumidity.AttributeDefs):
        """Attribute Definitions."""

        # A value in 0.01%RH offset to fix up incorrect values from sensor
        humidity_calibration = ZCLAttributeDef(
            id=0x0010,
            type=int16s,
            access="rw",
            is_manufacturer_specific=True,
        )


class UserInterfaceCustom(CustomCluster, UserInterface):
    """Custom User Interface Cluster with smiley control."""

    class AttributeDefs(UserInterface.AttributeDefs):
        """Attribute Definitions."""

        # of the 3 ZCL Thermostat User Interface spec attributes,
        # only the first one (TemperatureDisplayMode) is implemented fully.
        # KeypadLockout is implemented but completely unused in the device firmware
        # and ScheduleProgrammingVisibility is not implemented at all
        # https://github.com/devbis/z03mmc/blob/1.1.0/src/sensorEpCfg.c#L256

        # 0 - smiley is off, 1 - smiley is on (according to comfort values)
        smiley = ZCLAttributeDef(
            id=0x0010,
            type=Bool,
            access="rw",
            is_manufacturer_specific=True,
        )

        # display. 0 - display is off, 1 - display is on
        display = ZCLAttributeDef(
            id=0x0011,
            type=Bool,
            access="rw",
            is_manufacturer_specific=True,
        )

        # comfort temperature min: A value in 0.01ºC to set minimum comfort temperature for happy face
        comfort_temperature_min = ZCLAttributeDef(
            id=0x0102,
            type=int16s,
            access="rw",
            is_manufacturer_specific=True,
        )

        # comfort temperature max: A value in 0.01ºC to set maximum comfort temperature for happy face
        comfort_temperature_max = ZCLAttributeDef(
            id=0x0103,
            type=int16s,
            access="rw",
            is_manufacturer_specific=True,
        )

        # comfort humidity min: A value in 0.01%RH to set minimum comfort humidity for happy face
        comfort_humidity_min = ZCLAttributeDef(
            id=0x0104,
            type=uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )

        # comfort humidity max: A value in 0.01%RH to set maximum comfort humidity for happy face
        comfort_humidity_max = ZCLAttributeDef(
            id=0x0105,
            type=uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Xiaomi", "LYWSD03MMC")
    .replaces(TemperatureMeasurementCustom, endpoint_id=1)
    .replaces(RelativeHumidityCustom, endpoint_id=1)
    .replaces(UserInterfaceCustom, endpoint_id=1)
    .number(
        attribute_name=TemperatureMeasurementCustom.AttributeDefs.temperature_calibration.name,
        cluster_id=TemperatureMeasurementCustom.cluster_id,
        endpoint_id=1,
        min_value=-99,
        max_value=99,
        step=0.01,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        mode="box",
        translation_key="temperature_offset",
        fallback_name="Temperature offset",
    )
    .number(
        attribute_name=RelativeHumidityCustom.AttributeDefs.humidity_calibration.name,
        cluster_id=RelativeHumidityCustom.cluster_id,
        endpoint_id=1,
        min_value=-99,
        max_value=99,
        step=0.01,
        unit=PERCENTAGE,
        multiplier=0.01,
        mode="box",
        translation_key="humidity_offset",
        fallback_name="Humidity offset",
    )
    .number(
        attribute_name=UserInterfaceCustom.AttributeDefs.comfort_temperature_min.name,
        cluster_id=UserInterfaceCustom.cluster_id,
        endpoint_id=1,
        min_value=-99,
        max_value=99,
        step=0.01,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        mode="box",
        translation_key="comfort_temperature_min",
        fallback_name="Comfort temperature min",
    )
    .number(
        attribute_name=UserInterfaceCustom.AttributeDefs.comfort_temperature_max.name,
        cluster_id=UserInterfaceCustom.cluster_id,
        endpoint_id=1,
        min_value=-99,
        max_value=99,
        step=0.01,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        mode="box",
        translation_key="comfort_temperature_max",
        fallback_name="Comfort temperature max",
    )
    .number(
        attribute_name=UserInterfaceCustom.AttributeDefs.comfort_humidity_min.name,
        cluster_id=UserInterfaceCustom.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=99,
        step=1,
        unit=PERCENTAGE,
        multiplier=0.01,
        mode="box",
        translation_key="comfort_humidity_min",
        fallback_name="Comfort humidity min",
    )
    .number(
        attribute_name=UserInterfaceCustom.AttributeDefs.comfort_humidity_max.name,
        cluster_id=UserInterfaceCustom.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=99,
        step=1,
        unit=PERCENTAGE,
        multiplier=0.01,
        mode="box",
        translation_key="comfort_humidity_max",
        fallback_name="Comfort humidity max",
    )
    .switch(
        attribute_name=UserInterfaceCustom.AttributeDefs.display.name,
        cluster_id=UserInterfaceCustom.cluster_id,
        endpoint_id=1,
        off_value=False,
        on_value=True,
        translation_key="display_enabled",
        fallback_name="Display enabled",
    )
    .switch(
        attribute_name=UserInterfaceCustom.AttributeDefs.smiley.name,
        cluster_id=UserInterfaceCustom.cluster_id,
        endpoint_id=1,
        off_value=False,
        on_value=True,
        translation_key="show_smiley",
        fallback_name="Show smiley",
    )
    .add_to_registry()
)
