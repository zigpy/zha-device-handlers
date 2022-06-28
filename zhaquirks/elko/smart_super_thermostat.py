"""Module to handle quirks of the Elko Smart Super thermostat."""
import zigpy.profiles.zha as zha_p
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Groups, Identify, Ota, Scenes
from zigpy.zcl.clusters.hvac import Thermostat

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
    ElkoElectricalMeasurementCluster,
    ElkoThermostat,
    ElkoThermostatCluster,
    ElkoUserInterfaceCluster,
)

LOCAL_TEMP = 0x0000
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
UNKNOWN_6 = 0x0416
UNKNOWN_7 = 0x0417
UNKNOWN_8 = 0x0418
UNKNOWN_9 = 0x0419


class ElkoSuperTRThermostatCluster(ElkoThermostatCluster):
    """Elko custom thermostat cluster."""

    class Sensor(t.enum8):
        """Working modes of the thermostat."""

        AIR = 0x00
        FLOOR = 0x01
        PROTECTION = 0x03

    attributes = ElkoThermostatCluster.attributes.copy()
    attributes.update(
        {
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
            UNKNOWN_6: ("unknown_6", t.LongOctetString),
            UNKNOWN_7: ("unknown_7", t.int8s),
            UNKNOWN_8: ("unknown_8", t.uint8_t),
            UNKNOWN_9: ("unknown_9", t.uint8_t),
        }
    )

    def __init__(self, *args, **kwargs):
        """Init Elko thermostat."""
        super().__init__(*args, **kwargs)
        self.active_sensor = None

    async def write_attributes(self, attributes, manufacturer=None):
        """Override writes to thermostat attributes."""
        if "system_mode" in attributes:
            val = attributes.get("system_mode")
            night_lowering = 0
            if val == Thermostat.SystemMode.Off:
                device_on = 0
            elif val == Thermostat.SystemMode.Auto:
                device_on = 1
                night_lowering = 1
            elif val == Thermostat.SystemMode.Heat:
                device_on = 1
            attributes["device_on"] = device_on
            attributes["night_lowering"] = night_lowering

        return await super().write_attributes(attributes, manufacturer=manufacturer)

    def _update_attribute(self, attrid, value):
        if attrid == HEATING_ACTIVE:
            self.endpoint.device.thermostat_bus.listener_event(
                "heating_active_change", value
            )
        elif attrid == CHILD_LOCK:
            self.endpoint.device.ui_bus.listener_event("child_lock_change", value)
        elif attrid == ACTIVE_SENSOR:
            self.active_sensor = value
        elif attrid == LOCAL_TEMP:
            if (
                self.active_sensor is not None
                and self.active_sensor == self.Sensor.FLOOR
            ):
                # Ignore the air sensor reading if the floor sensor is selected
                return
        elif attrid == FLOOR_SENSOR_TEMPERATURE:
            if (
                self.active_sensor is not None
                and self.active_sensor == self.Sensor.FLOOR
            ):
                attrid = LOCAL_TEMP
        elif attrid == POWER_CONSUMPTION:
            if value is not None and value >= 0:
                self.endpoint.device.power_bus.listener_event("power_reported", value)

        super()._update_attribute(attrid, value)


class ElkoSuperTRThermostat(ElkoThermostat):
    """Elko thermostat custom device."""

    manufacturer_id_override = 0

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
                    ElkoElectricalMeasurementCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }
