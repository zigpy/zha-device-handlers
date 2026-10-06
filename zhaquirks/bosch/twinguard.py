"""Quirk for Bosch Twinguard smoke detector
     Identifies as 'Champion' """
import zigpy.types as t
import math
#import logging
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Alarms,
    Basic,
    Groups,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
    Time,
    AnalogInput,
)
from zigpy.zcl.clusters.measurement import (
    CarbonMonoxideConcentration,
    IlluminanceMeasurement,
    PressureMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks import LocalDataCluster

HUMIDITY_ID = 0x4000
UNKNOWN1_ID = 0x4001  # no values observed
UNKNOWN2_ID = 0x4002  # no values observed
VOC_ID = 0x4003  # usually varies between 0-6, can spike to ~80, e.g. when cooking
TEMPERATURE_ID = 0x4004
ILLUMINANCE_ID = 0x4005  # seems to be lux
BATTERY_ID = 0x4006   # no values usually observed, though once reported 200 while testing code (on fresh batteries)
UNKNOWN7_ID = 0x4007  # value seems to flip between 11 and 0
UNKNOWN8_ID = 0x4008  # no values observed
UNKNOWN9_ID = 0x4009  # not pressure, value mostly 1000, occasionally dips as low as 850
UNKNOWNa_ID = 0x400a  # no values observed
UNKNOWNb_ID = 0x400b  # no values observed
UNKNOWNc_ID = 0x400c  # value varies between approx 79 - 86

MEASURED_VALUE = 0x0000


## TODO: implement alarm functions. Relevant code snippet from z2m:
#            deviceAddCustomCluster('twinguardAlarm', {
#                ID: 0xe007,
#                attributes: {
#                    alarm_status: {ID: 0x5000, type: Zcl.DataType.BITMAP32},
#                commands: {
#                    burglarAlarm: {
#                        ID: 0x01,
#                        parameters: [
#                            {name: 'data', type: Zcl.DataType.UINT8}, // data:1 trips the siren data:0 should stop the siren


class TwinguardMeasurementCluster(CustomCluster, AnalogInput):
    cluster_id = 0xE002
    name = "TwinguardReports"
    ep_attribute = "twinguard_reports"
    attributes = {
        HUMIDITY_ID: ("humidity", t.uint16_t),
        UNKNOWN1_ID: ("unknown_1", t.uint16_t),
        UNKNOWN2_ID: ("unknown_2", t.uint16_t),
        VOC_ID: ("voc", t.uint16_t),
        TEMPERATURE_ID: ("temperature", t.int16s),
        ILLUMINANCE_ID: ("illuminance", t.uint16_t),
        BATTERY_ID: ("battery", t.uint16_t),
        UNKNOWN7_ID: ("unknown_7", t.uint16_t),
        UNKNOWN8_ID: ("unknown_8", t.uint16_t),
        UNKNOWN9_ID: ("unknown_9", t.uint16_t),
        UNKNOWNa_ID: ("unknown_a", t.uint16_t),
        UNKNOWNb_ID: ("unknown_b", t.uint16_t),
        UNKNOWNc_ID: ("unknown_c", t.uint16_t)
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        self.endpoint.twinguard_data.update_attribute(attrid, value)
        
        if attrid == TEMPERATURE_ID:
            self.endpoint.temperature.update_attribute(MEASURED_VALUE, value)
        elif attrid == HUMIDITY_ID:
            self.endpoint.humidity.update_attribute(MEASURED_VALUE, value)
        elif attrid == ILLUMINANCE_ID:
            self.endpoint.illuminance.update_attribute(MEASURED_VALUE, value)
        elif attrid == VOC_ID:
            ''' TODO: still needs proper scaling. ZHA multiplies VOC values by
            10^6, so for now that is undone here to get raw values again
            '''
            self.endpoint.voc_level.update_attribute(MEASURED_VALUE, value/1000000)

      
class TwinguardData(LocalDataCluster):
    cluster_id = 0x042E
    name = "TwinguardData"
    ep_attribute = "twinguard_data"

    attributes = {
        HUMIDITY_ID: ("humidity", t.uint16_t),
        UNKNOWN1_ID: ("unknown_1", t.uint16_t),
        UNKNOWN2_ID: ("unknown_2", t.uint16_t),
        VOC_ID: ("voc", t.uint16_t),
        TEMPERATURE_ID: ("temperature", t.int16s),
        ILLUMINANCE_ID: ("illuminance", t.uint16_t),
        BATTERY_ID: ("battery", t.uint16_t),
        UNKNOWN7_ID: ("unknown_7", t.uint16_t),
        UNKNOWN8_ID: ("unknown_8", t.uint16_t),
        UNKNOWN9_ID: ("unknown_9", t.uint16_t),
        UNKNOWNa_ID: ("unknown_a", t.uint16_t),
        UNKNOWNb_ID: ("unknown_b", t.uint16_t),
        UNKNOWNc_ID: ("unknown_c", t.uint16_t)
    }


    SIX_MINUTES = 360
    MIN_CHANGE = 1
    ONE_MINUTE = 60

    async def bind(self):
        """Bind cluster, unsure if this is needed."""
        result = await self.endpoint.twinguard_reports.bind()
        await self.endpoint.twinguard_reports.configure_reporting(
            self.TEMPERATURE_ID,
            self.ONE_MINUTE,
            self.SIX_MINUTES,
            self.MIN_CHANGE,
        )
        return result


class BoschTemperatureMeasurement(CustomCluster, TemperatureMeasurement):
    """Handles invalid values for Temperature."""

    name = "Temperature"
    ep_attribute = "temperature"
    attributes = {
        MEASURED_VALUE: ("measured_value", t.uint16_t),
    }


class BoschRelativeHumidity(CustomCluster, RelativeHumidity):
    """Handles invalid values for Temperature."""

    name = "Humidity"
    ep_attribute = "humidity"
    attributes = {
        MEASURED_VALUE: ("measured_value", t.uint16_t),
    }    


class BoschVOCMeasurement(CustomCluster):
    cluster_id = 0xFC03
    name = "VOC Level"
    ep_attribute = "voc_level"
    attributes = {
        MEASURED_VALUE: ("measured_value", t.uint16_t),
    }


class BoschIlluminanceMeasurement(CustomCluster, IlluminanceMeasurement):
    name = "Illuminance"
    ep_attribute = "illuminance"

    def _update_attribute(self, attrid, value):
        """ Twinguard value already in lux. This formula converts the value to
                  the raw illuminance value expected by the Zigbee spec and ZHA,
                  which ZHA then converts back to lux.
                  If value is 0 (i.e. no measurable light), then leave it as 0."""
        if value == 0:
            super()._update_attribute(attrid, value)
        else:
            super()._update_attribute(attrid, round(10000 * math.log10(value) + 1))

    async def bind(self):
        """Bind cluster."""
        result = await self.endpoint.twinguard_reports.bind()
        return result


class BoschStChampion(CustomDevice):
    """Bosch St Champion custom device implementation."""
    """Manufacturer string can be 'BOSCH ST' or 'BoschSmartHomeGmbH' depending on
          the router it pairs with!"""
    
    signature = {
        MODELS_INFO: [("BOSCH ST", "Champion"),("BoschSmartHomeGmbH", "Champion")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0060,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Alarms.cluster_id,
                    0xe000,
                    0xe004,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Alarms.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Alarms.cluster_id,
                    0xe001,
                    0xe004,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Alarms.cluster_id,
                ],
            },
            3: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0xf000,
                INPUT_CLUSTERS: [
                    0x0000,
                    0x0003,
                    TwinguardMeasurementCluster.cluster_id
                ],
                OUTPUT_CLUSTERS: [
                    0x0003
                ],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0062,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Alarms.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Alarms.cluster_id,
                ],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LIGHT_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x03f4,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    PressureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x03f0,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    RelativeHumidity.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
            10: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0xf002,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    0xe005,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
            11: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x03f2,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    CarbonMonoxideConcentration.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
            12: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x03f3,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    0xe003,
                    0xe006,
                    0xe007,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0060,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Alarms.cluster_id,
                    0xe000,
                    0xe004,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Alarms.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Alarms.cluster_id,
                    0xe001,
                    0xe004,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Alarms.cluster_id,
                ],
            },
            3: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0xf000,
                INPUT_CLUSTERS: [
                    0x0000,
                    0x0003,
                    TwinguardMeasurementCluster,
                    TwinguardData,
                    BoschTemperatureMeasurement,
                    BoschRelativeHumidity,
                    BoschIlluminanceMeasurement,
                    BoschVOCMeasurement,
              ],
                OUTPUT_CLUSTERS: [
                    0x0003
              ]
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0062,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Alarms.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Alarms.cluster_id,
                ],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
#                    TemperatureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LIGHT_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
#                    IlluminanceMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x03f4,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    PressureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x03f0,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
#                    RelativeHumidity.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
            10: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0xf002,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    0xe005,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
            11: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x03f2,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    CarbonMonoxideConcentration.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
            12: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x03f3,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    0xe003,
                    0xe006,
                    0xe007,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
        },
    }
