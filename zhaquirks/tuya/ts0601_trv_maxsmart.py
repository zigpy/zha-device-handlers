import logging
import math
from typing import Optional, Union

import zigpy.types as t
from zhaquirks import Bus, LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TuyaManufClusterAttributes,
    TuyaPowerConfigurationCluster,
    TuyaThermostat,
    TuyaThermostatCluster,
    TuyaUserInterfaceCluster,
)
from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    AnalogOutput,
    Basic,
    BinaryInput,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.hvac import Thermostat

_LOGGER = logging.getLogger(__name__)

# target room temp in Auto mode, degrees/2
MAXSMART_TARGET_TEMP_AUTO_ATTR = 0x0269
# target room temp in Manual mode, degrees/2
MAXSMART_TARGET_TEMP_MAN_ATTR = 0x0210
# Placeholder for target temperature, depends if it's Auto mode or Manual
MAXSMART_TARGET_TEMP_ATTR = 0x0269
MAXSMART_TEMPERATURE_ATTR = 0x0218  # current room temp, degrees/10
MAXSMART_MODE_ATTR = 0x0402  # [0] scheduled [1] manual [2] away
MAXSMART_CHILD_LOCK_ATTR = 0x011E  # [0] unlocked [1] child-locked
# temperature calibration (decidegree)
MAXSMART_TEMP_CALIBRATION_ATTR = 0x0268
# minimum limit of temperature setting
MAXSMART_MIN_TEMPERATURE_VAL = 50  # degrees/100
# maximum limit of temperature setting
MAXSMART_MAX_TEMPERATURE_VAL = 2950  # degrees/100
MAXSMART_WINDOW_DETECT_ATTR = 0x016B  # [0] off [1] on
# temperature for window detect, degrees/2
MAXSMART_WINDOW_DETECT_TEMP_ATTR = 0x0274
MAXSMART_WINDOW_DETECT_TIME_ATTR = 0x0275  # time for window detect, minutes
MAXSMART_COMFORT_TEMP_ATTR = 0x0265  # comfort mode temperaure (decidegree)
MAXSMART_ECO_TEMP_ATTR = 0x0266  # eco mode temperature (decidegree)
MAXSMART_BATTERY_ATTR = 0x0222  # battery charge
# [19, 1, 1, 0, 0, 34, 0, 0] start: year, month, day, hour, minute, temperature/2, two bytes of operating time(hours)
MAXSMART_AWAY_DATA_ATTR = 0x0067
MAXSMART_BOOST_COUNTDOWN = 0x0276  # seconds
MAXSMART_BOOST_ATTR = 0x016A  # [0] off [1] on
MAXSMART_SCHEDULE_MONDAY = 0x006D
MAXSMART_SCHEDULE_TUESDAY = 0x006E
MAXSMART_SCHEDULE_WEDNESDAY = 0x006F
MAXSMART_SCHEDULE_THURSDAY = 0x0070
MAXSMART_SCHEDULE_FRIDAY = 0x0071
MAXSMART_SCHEDULE_SATURDAY = 0x0072
MAXSMART_SCHEDULE_SUNDAY = 0x0073
MaxsmartManufClusterSelf = {}
SILVERCREST_BATTERY_ATTR = 0x0223  # battery charge
SILVERCREST_CHILD_LOCK_ATTR = 0x0128  # [0] unlocked [1] child-locked


class data144(t.FixedList, item_type=t.uint8_t, length=18):
    """General data, Discrete, 144 bit."""

    pass


class CustomTuyaOnOff(LocalDataCluster, OnOff):
    """Custom Tuya OnOff cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.thermostat_onoff_bus.add_listener(self)

    # pylint: disable=R0201
    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""
        return {}

    async def write_attributes(self, attributes, manufacturer=None):
        """Implement writeable attributes."""

        records = self._write_attr_records(attributes)

        if not records:
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

        manufacturer_attrs = {}
        for record in records:
            attr_name = self.attributes[record.attrid][0]
            new_attrs = self.map_attribute(attr_name, record.value.value)

            _LOGGER.debug(
                "[0x%04x:%s:0x%04x] Mapping standard %s (0x%04x) "
                "with value %s to custom %s",
                self.endpoint.device.nwk,
                self.endpoint.endpoint_id,
                self.cluster_id,
                attr_name,
                record.attrid,
                repr(record.value.value),
                repr(new_attrs),
            )

            manufacturer_attrs.update(new_attrs)

        if not manufacturer_attrs:
            return [
                [
                    foundation.WriteAttributesStatusRecord(
                        foundation.Status.FAILURE, r.attrid
                    )
                    for r in records
                ]
            ]

        await MaxsmartManufClusterSelf[
            self.endpoint.device.ieee
        ].endpoint.tuya_manufacturer.write_attributes(
            manufacturer_attrs, manufacturer=manufacturer
        )

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    async def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default Cluster command."""

        if command_id in (0x0000, 0x0001, 0x0002):

            if command_id == 0x0000:
                value = False
            elif command_id == 0x0001:
                value = True
            else:
                attrid = self.attridx["on_off"]
                success, _ = await self.read_attributes(
                    (attrid,), manufacturer=manufacturer
                )
                try:
                    value = success[attrid]
                except KeyError:
                    return foundation.Status.FAILURE
                value = not value

            (res,) = await self.write_attributes(
                {"on_off": value},
                manufacturer=manufacturer,
            )
            return [command_id, res[0].status]

        return [command_id, foundation.Status.UNSUP_CLUSTER_COMMAND]


class MaxsmartManufCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of some thermostatic valves."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartManufCluster_bus.add_listener(self)
        global MaxsmartManufClusterSelf
        MaxsmartManufClusterSelf[self.endpoint.device.ieee] = self

    set_time_offset = 1970

    manufacturer_attributes = {
        MAXSMART_CHILD_LOCK_ATTR: ("child_lock", t.uint8_t),
        MAXSMART_WINDOW_DETECT_ATTR: ("window_detection", t.uint8_t),
        MAXSMART_WINDOW_DETECT_TEMP_ATTR: ("window_detection_temp", t.uint32_t),
        MAXSMART_WINDOW_DETECT_TIME_ATTR: ("window_detection_time", t.uint32_t),
        MAXSMART_TARGET_TEMP_AUTO_ATTR: ("target_temperature_auto", t.uint32_t),
        MAXSMART_TARGET_TEMP_MAN_ATTR: ("target_temperature_manual", t.uint32_t),
        MAXSMART_TEMPERATURE_ATTR: ("temperature", t.uint32_t),
        MAXSMART_MODE_ATTR: ("mode", t.uint8_t),
        MAXSMART_TEMP_CALIBRATION_ATTR: ("temperature_calibration", t.int32s),
        MAXSMART_COMFORT_TEMP_ATTR: ("comfort_mode_temperature", t.uint32_t),
        MAXSMART_ECO_TEMP_ATTR: ("eco_mode_temperature", t.uint32_t),
        MAXSMART_BATTERY_ATTR: ("battery", t.uint32_t),
        MAXSMART_AWAY_DATA_ATTR: ("away_data", t.data64),
        MAXSMART_BOOST_COUNTDOWN: ("boost_countdown", t.uint32_t),
        MAXSMART_BOOST_ATTR: ("boost_enabled", t.uint8_t),
        MAXSMART_SCHEDULE_MONDAY: ("schedule_monday", data144),
        MAXSMART_SCHEDULE_TUESDAY: ("schedule_tuesday", data144),
        MAXSMART_SCHEDULE_WEDNESDAY: ("schedule_wednsday", data144),
        MAXSMART_SCHEDULE_THURSDAY: ("schedule_thursday", data144),
        MAXSMART_SCHEDULE_FRIDAY: ("schedule_friday", data144),
        MAXSMART_SCHEDULE_SATURDAY: ("schedule_saturday", data144),
        MAXSMART_SCHEDULE_SUNDAY: ("schedule_sunday", data144),
    }

    DIRECT_MAPPED_ATTRS = {
        MAXSMART_TEMPERATURE_ATTR: ("local_temp", lambda value: value * 10),
        MAXSMART_TARGET_TEMP_AUTO_ATTR: (
            "occupied_heating_setpoint",
            lambda value: value / 2 * 100,
        ),
        MAXSMART_TARGET_TEMP_MAN_ATTR: (
            "occupied_heating_setpoint",
            lambda value: value / 2 * 100,
        ),
        MAXSMART_AWAY_DATA_ATTR: (
            "unoccupied_heating_setpoint",
            lambda value: value[2] / 2 * 100,
        ),
        MAXSMART_COMFORT_TEMP_ATTR: (
            "comfort_heating_setpoint",
            lambda value: value / 2,
        ),
        MAXSMART_ECO_TEMP_ATTR: ("eco_heating_setpoint", lambda value: value / 2),
        MAXSMART_TEMP_CALIBRATION_ATTR: (
            "local_temperature_calibration",
            lambda value: value * 10,
        ),
        MAXSMART_WINDOW_DETECT_TEMP_ATTR: (
            "window_detection_temp",
            lambda value: value / 2,
        ),
        MAXSMART_WINDOW_DETECT_TIME_ATTR: ("window_detection_time", None),
    }

    def _update_attribute(self, attrid, value):
        """Override default _update_attribute."""
        super()._update_attribute(attrid, value)

        if attrid in self.DIRECT_MAPPED_ATTRS:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                self.DIRECT_MAPPED_ATTRS[attrid][0],
                value
                if self.DIRECT_MAPPED_ATTRS[attrid][1] is None
                else self.DIRECT_MAPPED_ATTRS[attrid][1](value),
            )

        if attrid == MAXSMART_BATTERY_ATTR:
            self.endpoint.device.battery_bus.listener_event(
                "battery_change",
                100
                if value > 130
                else 0
                if value < 70
                else round(((value - 70) * 1.67), 1),
            )
        elif attrid == MAXSMART_WINDOW_DETECT_ATTR:
            self.endpoint.device.MaxsmartWindowDetection_bus.listener_event(
                "set_value", value
            )
        elif attrid in (MAXSMART_MODE_ATTR, MAXSMART_BOOST_ATTR):
            if attrid == MAXSMART_BOOST_ATTR and value == 1:
                self.endpoint.device.thermostat_bus.listener_event("mode_change", 3)
            elif attrid == MAXSMART_MODE_ATTR:
                self.endpoint.device.thermostat_bus.listener_event("mode_change", value)
        elif attrid in (
            MAXSMART_TEMPERATURE_ATTR,
            MAXSMART_TARGET_TEMP_AUTO_ATTR,
            MAXSMART_TARGET_TEMP_MAN_ATTR,
        ):
            if attrid == MAXSMART_TARGET_TEMP_AUTO_ATTR:
                self.endpoint.device.thermostat_bus.listener_event(
                    "temperature_change",
                    "occupied_heating_setpoint_auto",
                    self.DIRECT_MAPPED_ATTRS[MAXSMART_TARGET_TEMP_AUTO_ATTR][1](value),
                )
            elif attrid == MAXSMART_TARGET_TEMP_MAN_ATTR:
                self.endpoint.device.thermostat_bus.listener_event(
                    "temperature_change",
                    "occupied_heating_setpoint_manual",
                    self.DIRECT_MAPPED_ATTRS[MAXSMART_TARGET_TEMP_MAN_ATTR][1](value),
                )
            self.endpoint.device.thermostat_bus.listener_event(
                "hass_climate_state_change", attrid, value
            )
        elif attrid == MAXSMART_CHILD_LOCK_ATTR:
            mode = 1 if value else 0
            self.endpoint.device.ui_bus.listener_event("child_lock_change", mode)
            self.endpoint.device.thermostat_onoff_bus.listener_event(
                "child_lock_change", mode
            )
        elif attrid == MAXSMART_AWAY_DATA_ATTR:
            self.endpoint.device.MaxsmartAwayYear_bus.listener_event(
                "set_value", value[7]
            )
            self.endpoint.device.MaxsmartAwayMonth_bus.listener_event(
                "set_value", value[6]
            )
            self.endpoint.device.MaxsmartAwayDay_bus.listener_event(
                "set_value", value[5]
            )
            self.endpoint.device.MaxsmartAwayHour_bus.listener_event(
                "set_value", value[4]
            )
            self.endpoint.device.MaxsmartAwayMinute_bus.listener_event(
                "set_value", value[3]
            )
            self.endpoint.device.MaxsmartAwayTemperature_bus.listener_event(
                "set_value", value[2]
            )
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                "occupied_heating_setpoint_away",
                self.DIRECT_MAPPED_ATTRS[MAXSMART_AWAY_DATA_ATTR][1](value),
            )
            self.endpoint.device.MaxsmartAwayOperTime_bus.listener_event(
                "set_value", value[1], value[0]
            )
        elif attrid == MAXSMART_ECO_TEMP_ATTR:
            self.endpoint.device.MaxsmartEcoTemperature_bus.listener_event(
                "set_value", self.DIRECT_MAPPED_ATTRS[MAXSMART_ECO_TEMP_ATTR][1](value)
            )
        elif attrid == MAXSMART_COMFORT_TEMP_ATTR:
            self.endpoint.device.MaxsmartComfortTemperature_bus.listener_event(
                "set_value",
                self.DIRECT_MAPPED_ATTRS[MAXSMART_COMFORT_TEMP_ATTR][1](value),
            )
        elif attrid == MAXSMART_WINDOW_DETECT_TEMP_ATTR:
            self.endpoint.device.MaxsmartWindowDetectTemperature_bus.listener_event(
                "set_value",
                self.DIRECT_MAPPED_ATTRS[MAXSMART_WINDOW_DETECT_TEMP_ATTR][1](value),
            )
        elif attrid == MAXSMART_WINDOW_DETECT_TIME_ATTR:
            self.endpoint.device.MaxsmartWindowDetectTime_bus.listener_event(
                "set_value", value
            )
        elif attrid == MAXSMART_BOOST_COUNTDOWN:
            self.endpoint.device.MaxsmartBoostCountdown_bus.listener_event(
                "set_value", value
            )
        elif attrid == MAXSMART_TEMP_CALIBRATION_ATTR:
            self.endpoint.device.MaxsmartTempCalibration_bus.listener_event(
                "set_value", value
            )
        elif attrid in (
            MAXSMART_SCHEDULE_MONDAY,
            MAXSMART_SCHEDULE_TUESDAY,
            MAXSMART_SCHEDULE_WEDNESDAY,
            MAXSMART_SCHEDULE_THURSDAY,
            MAXSMART_SCHEDULE_FRIDAY,
            MAXSMART_SCHEDULE_SATURDAY,
            MAXSMART_SCHEDULE_SUNDAY,
        ):
            self.endpoint.device.thermostat_bus.listener_event(
                "schedule_change", attrid, value
            )

    def away_cluster_get(self, field, attributes):
        """Function to return structure needed to away attribute."""
        year = self.endpoint.device.MaxsmartAwayYear_bus.listener_event("get_value")[0]
        month = self.endpoint.device.MaxsmartAwayMonth_bus.listener_event("get_value")[
            0
        ]
        day = self.endpoint.device.MaxsmartAwayDay_bus.listener_event("get_value")[0]
        hour = self.endpoint.device.MaxsmartAwayHour_bus.listener_event("get_value")[0]
        minute = self.endpoint.device.MaxsmartAwayMinute_bus.listener_event(
            "get_value"
        )[0]
        temperature = self.endpoint.device.MaxsmartAwayTemperature_bus.listener_event(
            "get_value"
        )[0]
        oper_time = self.endpoint.device.MaxsmartAwayOperTime_bus.listener_event(
            "get_value"
        )[0]
        oper_time = bytearray(int(oper_time).to_bytes(2, "big"))
        away_data = {
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "minute": minute,
            "temperature": temperature,
            "oper_time": oper_time,
        }
        if field == "oper_time":
            away_data[field] = bytearray(
                int(attributes["present_value"]).to_bytes(2, "big")
            )
        else:
            away_data[field] = attributes["present_value"]

        data = t.data64()
        data.append(away_data["oper_time"][1])
        data.append(away_data["oper_time"][0])
        data.append(int(away_data["temperature"] * 2))
        data.append(int(away_data["minute"]))
        data.append(int(away_data["hour"]))
        data.append(int(away_data["day"]))
        data.append(int(away_data["month"]))
        data.append(int(away_data["year"] - 2000))

        return data


class SilvercrestManufCluster(MaxsmartManufCluster):
    """Manufacturer Specific Cluster of some thermostatic valves - specific for Silvercrest."""

    MAXSMART_CHILD_LOCK_ATTR = SILVERCREST_CHILD_LOCK_ATTR
    MAXSMART_BATTERY_ATTR = SILVERCREST_BATTERY_ATTR


class MaxsmartThermostat(TuyaThermostatCluster):
    """Thermostat cluster for some thermostatic valves."""

    class Preset(t.enum8):
        """Working modes of the thermostat."""

        Away = 0x00
        Schedule = 0x01
        Manual = 0x02
        Comfort = 0x03
        Eco = 0x04
        Boost = 0x05
        Complex = 0x06

    _CONSTANT_ATTRIBUTES = {
        0x001B: Thermostat.ControlSequenceOfOperation.Heating_Only,
        0x001C: Thermostat.SystemMode.Heat,
    }

    manufacturer_attributes = {
        0x4000: ("comfort_heating_setpoint", t.int16s),
        0x4001: ("eco_heating_setpoint", t.int16s),
        0x4002: ("operation_preset", Preset),
        0x4004: ("boost_duration_seconds", t.uint32_t),
        0x4006: ("occupied_heating_setpoint_auto", t.uint32_t),
        0x4007: ("occupied_heating_setpoint_manual", t.uint32_t),
        0x4008: ("occupied_heating_setpoint_away", t.uint32_t),
        0x4009: ("window_detection_temp", t.int16s),
        0x4010: ("window_detection_time", t.int16s),
    }

    # Loop for creating attributes for schedule 7 * 18
    i = 0
    for x in range(0, 7):
        day = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        for y in range(1, 18):
            name = "temperature" if y % 2 else "hour"
            manufacturer_attributes[0x4100 + i] = (
                "schedule_" + day[x] + "_" + str(math.ceil(y / 2)) + "_" + name,
                t.Half,
            )
            i += 1

    DIRECT_MAPPING_ATTRS = {
        "occupied_heating_setpoint_auto": (
            MAXSMART_TARGET_TEMP_AUTO_ATTR,
            lambda value: round(value / 100 * 2),
        ),
        "occupied_heating_setpoint_manual": (
            MAXSMART_TARGET_TEMP_MAN_ATTR,
            lambda value: round(value / 100 * 2),
        ),
        "occupied_heating_setpoint_away": (MAXSMART_AWAY_DATA_ATTR, None),
        "comfort_heating_setpoint": (
            MAXSMART_COMFORT_TEMP_ATTR,
            lambda value: round(value / 100 * 2),
        ),
        "eco_heating_setpoint": (
            MAXSMART_ECO_TEMP_ATTR,
            lambda value: round(value / 100 * 2),
        ),
        "local_temperature_calibration": (
            MAXSMART_TEMP_CALIBRATION_ATTR,
            lambda value: round(value / 10),
        ),
        "window_detection_temp": (
            MAXSMART_WINDOW_DETECT_TEMP_ATTR,
            lambda value: round(value / 100 * 2),
        ),
        "window_detection_time": (MAXSMART_WINDOW_DETECT_TIME_ATTR, None),
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.thermostat_bus.add_listener(self)
        self.endpoint.device.thermostat_bus.listener_event(
            "temperature_change",
            "min_heat_setpoint_limit",
            MAXSMART_MIN_TEMPERATURE_VAL,
        )
        self.endpoint.device.thermostat_bus.listener_event(
            "temperature_change",
            "max_heat_setpoint_limit",
            MAXSMART_MAX_TEMPERATURE_VAL,
        )

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""

        if attribute in self.DIRECT_MAPPING_ATTRS:
            return {
                self.DIRECT_MAPPING_ATTRS[attribute][0]: value
                if self.DIRECT_MAPPING_ATTRS[attribute][1] is None
                else self.DIRECT_MAPPING_ATTRS[attribute][1](value)
            }

        if attribute == "occupied_heating_setpoint":
            mode = self._attr_cache.get(
                self.attridx["operation_preset"], self.Preset.Schedule
            )
            attribute_mode = None
            if mode == self.Preset.Schedule:
                attribute_mode = "occupied_heating_setpoint_auto"
            elif mode == self.Preset.Manual:
                attribute_mode = "occupied_heating_setpoint_manual"

            if mode != self.Preset.Away:
                return {
                    self.DIRECT_MAPPING_ATTRS[attribute_mode][0]: value
                    if self.DIRECT_MAPPING_ATTRS[attribute_mode][1] is None
                    else self.DIRECT_MAPPING_ATTRS[attribute_mode][1](value)
                }
            else:
                attribute_mode = "occupied_heating_setpoint_away"
                data = self.endpoint.device.MaxsmartManufCluster_bus.listener_event(
                    "away_cluster_get", "temperature", {"present_value": value / 100}
                )
                self._update_attribute(
                    self.attridx["occupied_heating_setpoint"], data[0][2] / 2 * 100
                )
                return {self.DIRECT_MAPPING_ATTRS[attribute_mode][0]: data[0]}

        if attribute == "operation_preset":
            if value == 0:
                return {MAXSMART_MODE_ATTR: 2, MAXSMART_BOOST_ATTR: 0}
            if value == 1:
                return {MAXSMART_MODE_ATTR: 0, MAXSMART_BOOST_ATTR: 0}
            if value == 2:
                return {MAXSMART_MODE_ATTR: 1, MAXSMART_BOOST_ATTR: 0}
            if value == 5:
                return {MAXSMART_BOOST_ATTR: 1}

        if attribute in ("programing_oper_mode", "occupancy"):
            if attribute == "occupancy":
                occupancy = value
                oper_mode = self._attr_cache.get(
                    self.attridx["programing_oper_mode"],
                    self.ProgrammingOperationMode.Simple,
                )
            else:
                occupancy = self._attr_cache.get(
                    self.attridx["occupancy"], self.Occupancy.Occupied
                )
                oper_mode = value
            if occupancy == self.Occupancy.Unoccupied:
                return {MAXSMART_MODE_ATTR: 2}
            if occupancy == self.Occupancy.Occupied:
                if oper_mode == self.ProgrammingOperationMode.Schedule_programming_mode:
                    return {MAXSMART_MODE_ATTR: 0}
                if oper_mode == self.ProgrammingOperationMode.Simple:
                    return {MAXSMART_MODE_ATTR: 1}
                self.error("Unsupported value for ProgrammingOperationMode")
            else:
                self.error("Unsupported value for Occupancy")

        if attribute == "system_mode":
            return {
                MAXSMART_MODE_ATTR: self._attr_cache.get(
                    self.attridx["operation_preset"], 1
                )
            }

        if "schedule_" in attribute:
            data = data144()
            day = {
                MAXSMART_SCHEDULE_MONDAY: "monday",
                MAXSMART_SCHEDULE_TUESDAY: "tuesday",
                MAXSMART_SCHEDULE_WEDNESDAY: "wednesday",
                MAXSMART_SCHEDULE_THURSDAY: "thursday",
                MAXSMART_SCHEDULE_FRIDAY: "friday",
                MAXSMART_SCHEDULE_SATURDAY: "saturday",
                MAXSMART_SCHEDULE_SUNDAY: "sunday",
            }
            for num, (attrid, day_name) in enumerate(day.items()):
                if day_name in attribute:
                    for y in reversed(range(1, 18)):
                        name = "temperature" if y % 2 else "hour"
                        attr_name = (
                            "schedule_"
                            + day_name
                            + "_"
                            + str(math.ceil(y / 2))
                            + "_"
                            + name
                        )
                        cached = self._attr_cache.get(self.attridx[attr_name])
                        if y % 2 != 0:
                            if attribute == attr_name:
                                val = round(value * 2)
                            else:
                                val = round(cached * 2)
                        else:
                            if attribute == attr_name:
                                val = round(value * 4)
                            else:
                                val = round(cached * 4)
                        data.append(val)
                    data.append(num + 1)
                    return {attrid: data}

    def hass_climate_state_change(self, attrid, value):
        """Update of the HASS Climate gui state according to temp difference."""
        if attrid == MAXSMART_TEMPERATURE_ATTR:
            temp_current = value * 10
            temp_set = self._attr_cache.get(self.attridx["occupied_heating_setpoint"])
        else:
            temp_set = value / 2 * 100
            temp_current = self._attr_cache.get(self.attridx["local_temp"])

        state = 0 if (int(temp_current) >= int(temp_set)) else 1
        self.endpoint.device.thermostat_bus.listener_event("state_change", state)

    def mode_change(self, value):
        """System Mode change."""
        if value == 0:
            operation_preset = self.Preset.Schedule
            prog_mode = self.ProgrammingOperationMode.Schedule_programming_mode
            occupancy = self.Occupancy.Occupied
            temp_auto = self._attr_cache.get(
                self.attridx["occupied_heating_setpoint_auto"]
            )
            self._update_attribute(self.attridx["occupied_heating_setpoint"], temp_auto)
        elif value == 1:
            operation_preset = self.Preset.Manual
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Occupied
            temp_manual = self._attr_cache.get(
                self.attridx["occupied_heating_setpoint_manual"]
            )
            self._update_attribute(
                self.attridx["occupied_heating_setpoint"], temp_manual
            )
        elif value == 2:
            operation_preset = self.Preset.Away
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Unoccupied
            temp_away = self._attr_cache.get(
                self.attridx["occupied_heating_setpoint_away"]
            )
            self._update_attribute(self.attridx["occupied_heating_setpoint"], temp_away)
        elif value == 3:
            operation_preset = self.Preset.Boost
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Occupied

        self._update_attribute(self.attridx["programing_oper_mode"], prog_mode)
        self._update_attribute(self.attridx["occupancy"], occupancy)
        self._update_attribute(self.attridx["operation_preset"], operation_preset)

    def schedule_change(self, attrid, value):
        """Scheduler attribute change."""
        day = {
            MAXSMART_SCHEDULE_MONDAY: "monday",
            MAXSMART_SCHEDULE_TUESDAY: "tuesday",
            MAXSMART_SCHEDULE_WEDNESDAY: "wednesday",
            MAXSMART_SCHEDULE_THURSDAY: "thursday",
            MAXSMART_SCHEDULE_FRIDAY: "friday",
            MAXSMART_SCHEDULE_SATURDAY: "saturday",
            MAXSMART_SCHEDULE_SUNDAY: "sunday",
        }
        for y in range(1, 18):
            name = "temperature" if y % 2 else "hour"
            self._update_attribute(
                self.attridx[
                    "schedule_" + day[attrid] + "_" + str(math.ceil(y / 2)) + "_" + name
                ],
                value[17 - y] / 2 if y % 2 else value[17 - y] / 4,
            )


class MaxsmartUserInterface(TuyaUserInterfaceCluster):
    """HVAC User interface cluster for tuya electric heating thermostats."""

    _CHILD_LOCK_ATTR = MAXSMART_CHILD_LOCK_ATTR


class MaxsmartChildLock(CustomTuyaOnOff):
    """On/Off cluster for the child lock function."""

    def child_lock_change(self, value):
        """Child lock change."""
        self._update_attribute(self.attridx["on_off"], value)

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""
        if attribute == "on_off":
            return {MAXSMART_CHILD_LOCK_ATTR: value}


class MaxsmartAwayYear(LocalDataCluster, AnalogOutput):
    """Analog output for Away year."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartAwayYear_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "G01 Away Year start")
        self._update_attribute(self.attridx["max_present_value"], 9999)
        self._update_attribute(self.attridx["resolution"], 1)
        self._update_attribute(self.attridx["application_type"], 14 << 16)
        self._update_attribute(self.attridx["engineering_units"], 67)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value + 2000)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attridx["present_value"])

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attridx[attrid]
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)
            data = self.endpoint.device.MaxsmartManufCluster_bus.listener_event(
                "away_cluster_get", "year", attributes
            )
            await MaxsmartManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MAXSMART_AWAY_DATA_ATTR: data[0]}, manufacturer=None
            )

        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MaxsmartAwayMonth(LocalDataCluster, AnalogOutput):
    """Analog output for Away month."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartAwayMonth_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "G01 Away Month start")
        self._update_attribute(self.attridx["max_present_value"], 12)
        self._update_attribute(self.attridx["min_present_value"], 1)
        self._update_attribute(self.attridx["resolution"], 1)
        self._update_attribute(self.attridx["application_type"], 14 << 16)
        self._update_attribute(self.attridx["engineering_units"], 68)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attridx["present_value"])

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attridx[attrid]
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)
            data = self.endpoint.device.MaxsmartManufCluster_bus.listener_event(
                "away_cluster_get", "month", attributes
            )
            await MaxsmartManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MAXSMART_AWAY_DATA_ATTR: data[0]}, manufacturer=None
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MaxsmartAwayDay(LocalDataCluster, AnalogOutput):
    """Analog output for Away day."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartAwayDay_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "G01 Away Day start")
        self._update_attribute(self.attridx["max_present_value"], 31)
        self._update_attribute(self.attridx["min_present_value"], 1)
        self._update_attribute(self.attridx["resolution"], 1)
        self._update_attribute(self.attridx["application_type"], 14 << 16)
        self._update_attribute(self.attridx["engineering_units"], 70)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attridx["present_value"])

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attridx[attrid]
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)
            data = self.endpoint.device.MaxsmartManufCluster_bus.listener_event(
                "away_cluster_get", "day", attributes
            )
            await MaxsmartManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MAXSMART_AWAY_DATA_ATTR: data[0]}, manufacturer=None
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MaxsmartAwayHour(LocalDataCluster, AnalogOutput):
    """Analog output for Away hour."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartAwayHour_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "G02 Away Hour start")
        self._update_attribute(self.attridx["max_present_value"], 23)
        self._update_attribute(self.attridx["min_present_value"], 0)
        self._update_attribute(self.attridx["resolution"], 1)
        self._update_attribute(self.attridx["application_type"], 14 << 16)
        self._update_attribute(self.attridx["engineering_units"], 71)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attridx["present_value"])

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attridx[attrid]
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)
            data = self.endpoint.device.MaxsmartManufCluster_bus.listener_event(
                "away_cluster_get", "hour", attributes
            )
            await MaxsmartManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MAXSMART_AWAY_DATA_ATTR: data[0]}, manufacturer=None
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MaxsmartAwayMinute(LocalDataCluster, AnalogOutput):
    """Analog output for Away minute."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartAwayMinute_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "G02 Away Minute start")
        self._update_attribute(self.attridx["max_present_value"], 59)
        self._update_attribute(self.attridx["min_present_value"], 0)
        self._update_attribute(self.attridx["resolution"], 1)
        self._update_attribute(self.attridx["application_type"], 14 << 16)
        self._update_attribute(self.attridx["engineering_units"], 72)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attridx["present_value"])

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attridx[attrid]
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)
            data = self.endpoint.device.MaxsmartManufCluster_bus.listener_event(
                "away_cluster_get", "minute", attributes
            )
            await MaxsmartManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MAXSMART_AWAY_DATA_ATTR: data[0]}, manufacturer=None
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MaxsmartAwayTemperature(LocalDataCluster, AnalogOutput):
    """Analog output for Away temperature."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartAwayTemperature_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "G03 Away Temperature")
        self._update_attribute(
            self.attridx["max_present_value"], MAXSMART_MAX_TEMPERATURE_VAL / 100
        )
        self._update_attribute(
            self.attridx["min_present_value"], MAXSMART_MIN_TEMPERATURE_VAL / 100
        )
        self._update_attribute(self.attridx["resolution"], 0.5)
        self._update_attribute(self.attridx["application_type"], 13 << 16)
        self._update_attribute(self.attridx["engineering_units"], 62)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value / 2)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attridx["present_value"])

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attridx[attrid]
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)
            data = self.endpoint.device.MaxsmartManufCluster_bus.listener_event(
                "away_cluster_get", "temperature", attributes
            )
            await MaxsmartManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MAXSMART_AWAY_DATA_ATTR: data[0]}, manufacturer=None
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MaxsmartAwayOperTime(LocalDataCluster, AnalogOutput):
    """Analog output for Away operating time."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartAwayOperTime_bus.add_listener(self)
        self._update_attribute(
            self.attridx["description"], "G04 Away Operating time(hours)"
        )
        self._update_attribute(self.attridx["max_present_value"], 65535)
        self._update_attribute(self.attridx["min_present_value"], 1)
        self._update_attribute(self.attridx["resolution"], 1)
        self._update_attribute(self.attridx["application_type"], 14 << 16)
        self._update_attribute(self.attridx["engineering_units"], 71)

    def set_value(self, value1, value0):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value1 << 8 | value0)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attridx["present_value"])

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attridx[attrid]
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)
            data = self.endpoint.device.MaxsmartManufCluster_bus.listener_event(
                "away_cluster_get", "oper_time", attributes
            )
            await MaxsmartManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MAXSMART_AWAY_DATA_ATTR: data[0]}, manufacturer=None
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MaxsmartEcoTemperature(LocalDataCluster, AnalogOutput):
    """Analog output for Eco temperature."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartEcoTemperature_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "G04 Eco Temperature")
        self._update_attribute(
            self.attridx["max_present_value"], MAXSMART_MAX_TEMPERATURE_VAL / 100
        )
        self._update_attribute(
            self.attridx["min_present_value"], MAXSMART_MIN_TEMPERATURE_VAL / 100
        )
        self._update_attribute(self.attridx["resolution"], 0.5)
        self._update_attribute(self.attridx["application_type"], 13 << 16)
        self._update_attribute(self.attridx["engineering_units"], 62)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attridx["present_value"])

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attridx[attrid]
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)

            await MaxsmartManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MAXSMART_ECO_TEMP_ATTR: value * 2}, manufacturer=None
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MaxsmartComfortTemperature(LocalDataCluster, AnalogOutput):
    """Analog output for Comfort temperature."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartComfortTemperature_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "G04 Comfort Temperature")
        self._update_attribute(
            self.attridx["max_present_value"], MAXSMART_MAX_TEMPERATURE_VAL / 100
        )
        self._update_attribute(
            self.attridx["min_present_value"], MAXSMART_MIN_TEMPERATURE_VAL / 100
        )
        self._update_attribute(self.attridx["resolution"], 0.5)
        self._update_attribute(self.attridx["application_type"], 13 << 16)
        self._update_attribute(self.attridx["engineering_units"], 62)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attridx["present_value"])

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attridx[attrid]
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)

            await MaxsmartManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MAXSMART_COMFORT_TEMP_ATTR: value * 2}, manufacturer=None
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MaxsmartWindowDetectTemperature(LocalDataCluster, AnalogOutput):
    """Analog output for Window detect temperature."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartWindowDetectTemperature_bus.add_listener(self)
        self._update_attribute(
            self.attridx["description"], "G05 Window detect Temperature"
        )
        self._update_attribute(
            self.attridx["max_present_value"], MAXSMART_MAX_TEMPERATURE_VAL / 100
        )
        self._update_attribute(
            self.attridx["min_present_value"], MAXSMART_MIN_TEMPERATURE_VAL / 100
        )
        self._update_attribute(self.attridx["resolution"], 0.5)
        self._update_attribute(self.attridx["application_type"], 13 << 16)
        self._update_attribute(self.attridx["engineering_units"], 62)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attridx["present_value"])

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attridx[attrid]
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)
            await MaxsmartManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MAXSMART_WINDOW_DETECT_TEMP_ATTR: value * 2}, manufacturer=None
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MaxsmartWindowDetectTime(LocalDataCluster, AnalogOutput):
    """Analog output for Window detect time."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartWindowDetectTime_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "G05 Window detect Time")
        self._update_attribute(self.attridx["max_present_value"], 60)
        self._update_attribute(self.attridx["min_present_value"], 0)
        self._update_attribute(self.attridx["resolution"], 1)
        self._update_attribute(self.attridx["application_type"], 14 << 16)
        self._update_attribute(self.attridx["engineering_units"], 72)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attridx["present_value"])

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attridx[attrid]
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)
            await MaxsmartManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MAXSMART_WINDOW_DETECT_TIME_ATTR: value}, manufacturer=None
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MaxsmartWindowDetection(LocalDataCluster, BinaryInput):
    """Binary cluster for the window detection function."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartWindowDetection_bus.add_listener(self)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value)


class MaxsmartBoostCountdown(LocalDataCluster, AnalogOutput):
    """Analog output for Bostt countdown time."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartBoostCountdown_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "G06 Boost countdown")
        self._update_attribute(self.attridx["max_present_value"], 9999)
        self._update_attribute(self.attridx["resolution"], 1)
        self._update_attribute(self.attridx["application_type"], 14 << 16)
        self._update_attribute(self.attridx["engineering_units"], 73)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value)


class MaxsmartTempCalibration(LocalDataCluster, AnalogOutput):
    """Analog output for Temperature calibration."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MaxsmartTempCalibration_bus.add_listener(self)
        self._update_attribute(
            self.attridx["description"], "G07 Temperature calibration"
        )
        self._update_attribute(self.attridx["max_present_value"], 5.5)
        self._update_attribute(self.attridx["min_present_value"], -5.5)
        self._update_attribute(self.attridx["resolution"], 0.5)
        self._update_attribute(self.attridx["application_type"], 13 << 16)
        self._update_attribute(self.attridx["engineering_units"], 62)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attridx["present_value"])

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attridx[attrid]
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)
            await MaxsmartManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MAXSMART_TEMP_CALIBRATION_ATTR: value}, manufacturer=None
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MaxsmartLocalTempUpdate(LocalDataCluster, OnOff):
    """Local temperature update switch."""

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer attributes writing to the set_data tuya command."""
        records = self._write_attr_records(attributes)
        if not records:
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

        for record in records:
            attr_name = self.attributes[record.attrid][0]
            if attr_name == "on_off":
                return await MaxsmartManufClusterSelf[
                    self.endpoint.device.ieee
                ].endpoint.tuya_manufacturer.write_attributes(
                    {MAXSMART_TEMPERATURE_ATTR: 0}, manufacturer=None
                )

        return [
            [
                foundation.WriteAttributesStatusRecord(
                    foundation.Status.FAILURE, r.attrid
                )
                for r in records
            ]
        ]

    async def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default Cluster command."""

        if command_id in (0x0000, 0x0001, 0x0002):
            if command_id == 0x0000:
                value = False
            elif command_id == 0x0001:
                value = True
            else:
                attrid = self.attridx["on_off"]
                success, _ = await self.read_attributes(
                    (attrid,), manufacturer=manufacturer
                )
                try:
                    value = success[attrid]
                except KeyError:
                    return foundation.Status.FAILURE
                value = not value

            (res,) = await self.write_attributes(
                {"on_off": value}, manufacturer=manufacturer
            )

            return [command_id, res]

        return [command_id, foundation.Status.UNSUP_CLUSTER_COMMAND]


class Maxsmart(TuyaThermostat):
    """Maxsmart Thermostatic radiator valve."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.thermostat_onoff_bus = Bus()
        self.MaxsmartManufCluster_bus = Bus()
        self.MaxsmartWindowDetection_bus = Bus()
        self.MaxsmartAwayYear_bus = Bus()
        self.MaxsmartAwayMonth_bus = Bus()
        self.MaxsmartAwayDay_bus = Bus()
        self.MaxsmartAwayHour_bus = Bus()
        self.MaxsmartAwayMinute_bus = Bus()
        self.MaxsmartAwayTemperature_bus = Bus()
        self.MaxsmartAwayOperTime_bus = Bus()
        self.MaxsmartEcoTemperature_bus = Bus()
        self.MaxsmartComfortTemperature_bus = Bus()
        self.MaxsmartWindowDetectTemperature_bus = Bus()
        self.MaxsmartWindowDetectTime_bus = Bus()
        self.MaxsmartBoostCountdown_bus = Bus()
        self.MaxsmartTempCalibration_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  endpoint=1 profile=260 device_type=769 device_version=0 input_clusters=[0, 4, 5, 10, 61184]
        #  output_clusters=[25]>
        MODELS_INFO: [
            ("_TZE200_qc4fpmcn", "TS0601"),
            ("_TZE200_i48qyn9s", "TS0601"),
            ("_TZE200_fhn3negr", "TS0601"),
            ("_TZE200_thbr5z34", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    TuyaManufClusterAttributes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MaxsmartManufCluster,
                    MaxsmartThermostat,
                    MaxsmartUserInterface,
                    MaxsmartWindowDetection,
                    TuyaPowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MaxsmartChildLock,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartAwayYear],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartAwayMonth],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartAwayDay],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartAwayHour],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartAwayMinute],
                OUTPUT_CLUSTERS: [],
            },
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartAwayTemperature],
                OUTPUT_CLUSTERS: [],
            },
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartAwayOperTime],
                OUTPUT_CLUSTERS: [],
            },
            10: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartEcoTemperature],
                OUTPUT_CLUSTERS: [],
            },
            11: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartComfortTemperature],
                OUTPUT_CLUSTERS: [],
            },
            12: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartWindowDetectTemperature],
                OUTPUT_CLUSTERS: [],
            },
            13: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartWindowDetectTime],
                OUTPUT_CLUSTERS: [],
            },
            14: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartBoostCountdown],
                OUTPUT_CLUSTERS: [],
            },
            15: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartTempCalibration],
                OUTPUT_CLUSTERS: [],
            },
            16: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MaxsmartLocalTempUpdate,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class Silvercrest(TuyaThermostat):
    """Silvercrest version of Maxsmart Thermostatic radiator valve."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.thermostat_onoff_bus = Bus()
        self.MaxsmartManufCluster_bus = Bus()
        self.MaxsmartWindowDetection_bus = Bus()
        self.MaxsmartAwayYear_bus = Bus()
        self.MaxsmartAwayMonth_bus = Bus()
        self.MaxsmartAwayDay_bus = Bus()
        self.MaxsmartAwayHour_bus = Bus()
        self.MaxsmartAwayMinute_bus = Bus()
        self.MaxsmartAwayTemperature_bus = Bus()
        self.MaxsmartAwayOperTime_bus = Bus()
        self.MaxsmartEcoTemperature_bus = Bus()
        self.MaxsmartComfortTemperature_bus = Bus()
        self.MaxsmartWindowDetectTemperature_bus = Bus()
        self.MaxsmartWindowDetectTime_bus = Bus()
        self.MaxsmartBoostCountdown_bus = Bus()
        self.MaxsmartTempCalibration_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  endpoint=1 profile=260 device_type=769 device_version=0 input_clusters=[0, 3, 4, 5, 61184]
        #  output_clusters=[10, 25]>
        MODELS_INFO: [
            ("_TZE200_chyvmhay", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufClusterAttributes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    SilvercrestManufCluster,
                    MaxsmartThermostat,
                    MaxsmartUserInterface,
                    MaxsmartWindowDetection,
                    TuyaPowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MaxsmartChildLock,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartAwayYear],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartAwayMonth],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartAwayDay],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartAwayHour],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartAwayMinute],
                OUTPUT_CLUSTERS: [],
            },
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartAwayTemperature],
                OUTPUT_CLUSTERS: [],
            },
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartAwayOperTime],
                OUTPUT_CLUSTERS: [],
            },
            10: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartEcoTemperature],
                OUTPUT_CLUSTERS: [],
            },
            11: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartComfortTemperature],
                OUTPUT_CLUSTERS: [],
            },
            12: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartWindowDetectTemperature],
                OUTPUT_CLUSTERS: [],
            },
            13: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartWindowDetectTime],
                OUTPUT_CLUSTERS: [],
            },
            14: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartBoostCountdown],
                OUTPUT_CLUSTERS: [],
            },
            15: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MaxsmartTempCalibration],
                OUTPUT_CLUSTERS: [],
            },
            16: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MaxsmartLocalTempUpdate,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }
