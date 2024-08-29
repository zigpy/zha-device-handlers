"""Xiaomi LYWSD03MMC Bluetooth temperature and humidity sensor."""

from zigpy.profiles import zha
from zigpy.types import Bool, int16s, uint16_t
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.hvac import UserInterface
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import XiaomiCustomDevice


class CalibratableTemperatureMeasurementCluster(CustomCluster, TemperatureMeasurement):
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


class CalibratableRelativeHumidityCluster(CustomCluster, RelativeHumidity):
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


class SmileyUserInterfaceCluster(CustomCluster):
    """Custom User Interface Cluster with smiley control."""

    cluster_id = UserInterface.cluster_id

    class AttributeDefs(BaseAttributeDefs):
        """Attribute Definitions."""

        # of the 3 ZCL spec attributes, only the first one (TemperatureDisplayMode) is implemented
        # KeypadLockout is implemented but completely unused in the device firmware
        # ScheduleProgrammingVisibility is not implemented at all
        # https://github.com/devbis/z03mmc/blob/1.1.0/src/sensorEpCfg.c#L256
        temperature_display_mode = UserInterface.AttributeDefs.temperature_display_mode

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


# https://github.com/devbis/z03mmc
# defined by 1.1.0 firmware (0x11003001)
# see README.md in the repo for more info
class LYWSD03MMC(XiaomiCustomDevice):
    """LYWSD03MMC sensor."""

    signature = {
        MODELS_INFO: [("Xiaomi", "LYWSD03MMC")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    PowerConfiguration.cluster_id,
                    RelativeHumidity.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    UserInterface.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    PowerConfiguration.cluster_id,
                    CalibratableTemperatureMeasurementCluster,
                    CalibratableRelativeHumidityCluster,
                    SmileyUserInterfaceCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
