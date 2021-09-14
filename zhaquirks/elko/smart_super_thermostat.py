"""Module to handle quirks of the Elko Smart Super thermostat.

"""
import logging

import zigpy.types as t
import zigpy.profiles.zha as zha_p

from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Groups,
    Scenes,
    Ota,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.elko import (
    ELKO,
    ElkoThermostat,
    ElkoThermostatCluster,
    ElkoUserInterfaceCluster,
)

UNKNOWN_1 = 0x0401
DISPLAY_TEXT = 0x0402
ACTIVE_SENSOR = 0x0403
UNKNOWN_2 = 0x0404
REGULATOR_MODE = 0x0405
DEVICE_ON = 0x0406
UNKNOWN_3 = 0x0407
POWER_CONSUMPTION = 0x0408
FLOOR_SENSOR_TEMPERATURE = 0x0409
UNKNOWN_4 = 0x0410
NIGHT_LOWERING = 0x0411
UNKNOWN_5 = 0x0412
CHILD_LOCK = 0x0413
PROTECTION_MAX_TEMP = 0x0414
HEATING_ACTIVE = 0x0415
UNKNOWN_7 = 0x0416
UNKNOWN_8 = 0x0417
UNKNOWN_9 = 0x0418
UNKNOWN_A = 0x0419


class ElkoSuperTRThermostatCluster(ElkoThermostatCluster):
    """Elko custom thermostat cluster."""

    class Sensor(t.enum8):
        """Working modes of the thermostat."""

        Air = 0x00
        Floor = 0x01
        Protection = 0x03

    manufacturer_attributes = {
        UNKNOWN_1: ("unknown_1", t.uint16_t),
        DISPLAY_TEXT: ("display_text", t.CharacterString),
        ACTIVE_SENSOR: ("active_sensor", Sensor),
        UNKNOWN_2: ("unknown_2", t.uint8_t),
        REGULATOR_MODE: ("regulator_mode", t.Bool),
        DEVICE_ON: ("device_on", t.Bool),
        UNKNOWN_3: ("unknown_3", t.LongOctetString),
        POWER_CONSUMPTION: ("power_consumtion", t.uint16_t),
        FLOOR_SENSOR_TEMPERATURE: ("floor_sensor_temperature", t.int16s),
        UNKNOWN_4: ("unknown_4", t.uint16_t),
        NIGHT_LOWERING: ("night_lowering", t.Bool),
        UNKNOWN_5: ("unknown_5", t.Bool),
        CHILD_LOCK: ("child_lock", t.Bool),
        PROTECTION_MAX_TEMP: ("protection_max_temp", t.uint8_t),
        HEATING_ACTIVE: ("heating_active", t.Bool),
        UNKNOWN_7: ("unknown_7", t.LongOctetString),
        UNKNOWN_8: ("unknown_8", t.int8s),
        UNKNOWN_9: ("unknown_9", t.uint8_t),
        UNKNOWN_A: ("unknown_a", t.uint8_t),
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == HEATING_ACTIVE:
            self.endpoint.device.thermostat_bus.listener_event(
                "heating_active_change", value
            )
        elif attrid == CHILD_LOCK:
            self.endpoint.device.ui_bus.listener_event("child_lock_change", value)


class ElkoSuperTRThermostat(ElkoThermostat):
    """Elko thermostat custom device"""

    signature = {
        MODELS_INFO: [(ELKO, "Super TR")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Thermostat.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    ElkoSuperTRThermostatCluster,
                    ElkoUserInterfaceCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }
