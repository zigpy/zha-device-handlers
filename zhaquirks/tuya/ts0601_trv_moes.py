import logging
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
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.hvac import Thermostat

_LOGGER = logging.getLogger(__name__)

MOES_TARGET_TEMP_ATTR = 0x0202  # target room temp (decidegree)
MOES_TEMPERATURE_ATTR = 0x0203  # current room temp (decidegree)
MOES_MODE_ATTR = 0x0404  # [0] away [1] scheduled [2] manual [3] comfort [4] eco [5] boost [6] complex
MOES_CHILD_LOCK_ATTR = 0x0107  # [0] unlocked [1] locked
MOES_VALVE_DETECT_ATTR = 0x0114  # [0] do not report [1] report
MOES_TEMP_CALIBRATION_ATTR = 0x022C  # temperature calibration (decidegree)
MOES_MIN_TEMPERATURE_ATTR = 0x0266  # minimum limit of temperature setting (decidegree)
MOES_MAX_TEMPERATURE_ATTR = 0x0267  # maximum limit of temperature setting (decidegree)
MOES_WINDOW_DETECT_ATTR = 0x0068  # [0,35,5] on/off, temperature, operating time (min)
MOES_BOOST_TIME_ATTR = 0x0269  # BOOST mode operating time in (sec)
MOES_FORCE_VALVE_ATTR = 0x046A  # [0] normal [1] open [2] close
MOES_COMFORT_TEMP_ATTR = 0x026B  # comfort mode temperaure (decidegree)
MOES_ECO_TEMP_ATTR = 0x026C  # eco mode temperature (decidegree)
MOES_VALVE_STATE_ATTR = 0x026D  # opening percentage
MOES_BATTERY_LOW_ATTR = 0x016E  # battery low warning
MOES_WEEK_FORMAT_ATTR = 0x046F  # [0] 5 days [1] 6 days, [2] 7 days
MOES_AWAY_TEMP_ATTR = 0x0272  # away mode temperature (decidegree)
MOES_AUTO_LOCK_ATTR = 0x0174  # [0] auto [1] manual
MOES_AWAY_DAYS_ATTR = 0x0275  # away mode duration (days)

# schedule [6,0,20,8,0,15,11,30,15,12,30,15,17,30,20,22,0,15]
# 6:00 - 20*, 8:00 - 15*, 11:30 - 15*, 12:30 - 15*, 17:30 - 20*, 22:00 - 15*
# Top bits in hours have special meaning
#   8: ??
#   7: Current schedule indicator
MOES_SCHEDULE_WORKDAY_ATTR = 0x0070
MOES_SCHEDULE_WEEKEND_ATTR = 0x0071
MoesManufClusterSelf = {}


class data144(t.FixedList, item_type=t.uint8_t, length=18):
    """General data, Discrete, 144 bit."""

    pass


class MoesManufCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of some thermostatic valves."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        global MoesManufClusterSelf
        MoesManufClusterSelf[self.endpoint.device.ieee] = self

    set_time_offset = 1970

    manufacturer_attributes = {
        MOES_TEMPERATURE_ATTR: ("temperature", t.uint32_t),
        MOES_TARGET_TEMP_ATTR: ("target_temperature", t.uint32_t),
        MOES_MODE_ATTR: ("mode", t.uint8_t),
        MOES_CHILD_LOCK_ATTR: ("child_lock", t.uint8_t),
        MOES_VALVE_DETECT_ATTR: ("valve_detect", t.uint8_t),
        MOES_TEMP_CALIBRATION_ATTR: ("temperature_calibration", t.int32s),
        MOES_MIN_TEMPERATURE_ATTR: ("min_temperature", t.uint32_t),
        MOES_MAX_TEMPERATURE_ATTR: ("max_temperature", t.uint32_t),
        MOES_WINDOW_DETECT_ATTR: ("window_detection", t.data24),
        MOES_BOOST_TIME_ATTR: ("boost_duration_seconds", t.uint32_t),
        MOES_FORCE_VALVE_ATTR: ("valve_force_state", t.uint8_t),
        MOES_COMFORT_TEMP_ATTR: ("comfort_mode_temperature", t.uint32_t),
        MOES_ECO_TEMP_ATTR: ("eco_mode_temperature", t.uint32_t),
        MOES_VALVE_STATE_ATTR: ("valve_state", t.uint32_t),
        MOES_BATTERY_LOW_ATTR: ("battery_low", t.uint8_t),
        MOES_WEEK_FORMAT_ATTR: ("week_format", t.uint8_t),
        MOES_AWAY_TEMP_ATTR: ("away_mode_temperature", t.uint32_t),
        MOES_AUTO_LOCK_ATTR: ("auto_lock", t.uint8_t),
        MOES_AWAY_DAYS_ATTR: ("away_duration_days", t.uint32_t),
        MOES_SCHEDULE_WORKDAY_ATTR: ("workday_schedule", data144),
        MOES_SCHEDULE_WEEKEND_ATTR: ("weekend_schedule", data144),
    }

    DIRECT_MAPPED_ATTRS = {
        MOES_TEMPERATURE_ATTR: ("local_temp", lambda value: value * 10),
        MOES_TARGET_TEMP_ATTR: ("occupied_heating_setpoint", lambda value: value * 10),
        MOES_MODE_ATTR: ("operation_preset", None),
        MOES_TEMP_CALIBRATION_ATTR: (
            "local_temperature_calibration",
            lambda value: value * 10,
        ),
        MOES_MIN_TEMPERATURE_ATTR: (
            "min_heat_setpoint_limit",
            lambda value: value * 100,
        ),
        MOES_MAX_TEMPERATURE_ATTR: (
            "max_heat_setpoint_limit",
            lambda value: value * 100,
        ),
        MOES_AWAY_TEMP_ATTR: ("unoccupied_heating_setpoint", lambda value: value * 100),
        MOES_COMFORT_TEMP_ATTR: ("comfort_heating_setpoint", lambda value: value * 100),
        MOES_ECO_TEMP_ATTR: ("eco_heating_setpoint", lambda value: value * 100),
        MOES_VALVE_STATE_ATTR: ("valve_open_percentage", None),
        MOES_AWAY_DAYS_ATTR: ("unoccupied_duration_days", None),
        MOES_BOOST_TIME_ATTR: ("boost_duration_seconds", None),
        MOES_WEEK_FORMAT_ATTR: ("work_days", None),
        MOES_FORCE_VALVE_ATTR: ("valve_force_state", None),
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
        elif attrid in (MOES_SCHEDULE_WORKDAY_ATTR, MOES_SCHEDULE_WEEKEND_ATTR):
            self.endpoint.device.thermostat_bus.listener_event(
                "schedule_change", attrid, value
            )

        if attrid == MOES_WINDOW_DETECT_ATTR:
            self.endpoint.device.MoesWindowDetection_bus.listener_event(
                "window_detect_change", value
            )
        elif attrid == MOES_CHILD_LOCK_ATTR:
            mode = 1 if value else 0
            self.endpoint.device.ui_bus.listener_event("child_lock_change", mode)
            self.endpoint.device.MoesChildLock_bus.listener_event("switch_change", mode)
        elif attrid == MOES_MODE_ATTR:
            self.endpoint.device.thermostat_bus.listener_event("mode_change", value)
        elif attrid == MOES_VALVE_STATE_ATTR:
            self.endpoint.device.thermostat_bus.listener_event("state_change", value)
            self.endpoint.device.MoesValveState_bus.listener_event("set_value", value)
        elif attrid == MOES_AUTO_LOCK_ATTR:
            mode = 1 if value else 0
            self.endpoint.device.ui_bus.listener_event("autolock_change", mode)
        elif attrid == MOES_BATTERY_LOW_ATTR:
            self.endpoint.device.battery_bus.listener_event(
                "battery_change", 5 if value else 100
            )
        elif attrid == MOES_TEMP_CALIBRATION_ATTR:
            self.endpoint.device.MoesTempCalibration_bus.listener_event(
                "set_value",
                self.DIRECT_MAPPED_ATTRS[MOES_TEMP_CALIBRATION_ATTR][1](value),
            )
        elif attrid == MOES_BOOST_TIME_ATTR:
            self.endpoint.device.MoesBoostTime_bus.listener_event(
                "set_value",
                value,
            )
        elif attrid == MOES_VALVE_DETECT_ATTR:
            self.endpoint.device.MoesValveDetect_bus.listener_event(
                "switch_change",
                value,
            )
        elif attrid == MOES_MIN_TEMPERATURE_ATTR:
            self.endpoint.device.MoesMinTemp_bus.listener_event(
                "set_value",
                value,
            )
        elif attrid == MOES_MAX_TEMPERATURE_ATTR:
            self.endpoint.device.MoesMaxTemp_bus.listener_event(
                "set_value",
                value,
            )
        elif attrid == MOES_COMFORT_TEMP_ATTR:
            self.endpoint.device.MoesComfortTemp_bus.listener_event(
                "set_value",
                value,
            )
        elif attrid == MOES_ECO_TEMP_ATTR:
            self.endpoint.device.MoesEcoTemp_bus.listener_event(
                "set_value",
                value,
            )
        elif attrid == MOES_AWAY_TEMP_ATTR:
            self.endpoint.device.MoesAwayTemp_bus.listener_event(
                "set_value",
                value,
            )
        elif attrid == MOES_AWAY_DAYS_ATTR:
            self.endpoint.device.MoesAwayDays_bus.listener_event(
                "set_value",
                value,
            )


class MoesThermostat(TuyaThermostatCluster):
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

    class WorkDays(t.enum8):
        """Workday configuration for scheduler operation mode."""

        MonToFri = 0x00
        MonToSat = 0x01
        MonToSun = 0x02

    class ForceValveState(t.enum8):
        """Force valve state option."""

        Normal = 0x00
        Open = 0x01
        Close = 0x02

    _CONSTANT_ATTRIBUTES = {
        0x001B: Thermostat.ControlSequenceOfOperation.Heating_Only,
        0x001C: Thermostat.SystemMode.Heat,
    }

    manufacturer_attributes = {
        0x4000: ("comfort_heating_setpoint", t.int16s),
        0x4001: ("eco_heating_setpoint", t.int16s),
        0x4002: ("operation_preset", Preset),
        0x4003: ("work_days", WorkDays),
        0x4004: ("valve_open_percentage", t.uint8_t),
        0x4005: ("boost_duration_seconds", t.uint32_t),
        0x4006: ("valve_force_state", ForceValveState),
        0x4007: ("unoccupied_duration_days", t.uint32_t),
        0x4110: ("workday_schedule_1_hour", t.uint8_t),
        0x4111: ("workday_schedule_1_minute", t.uint8_t),
        0x4112: ("workday_schedule_1_temperature", t.int16s),
        0x4120: ("workday_schedule_2_hour", t.uint8_t),
        0x4121: ("workday_schedule_2_minute", t.uint8_t),
        0x4122: ("workday_schedule_2_temperature", t.int16s),
        0x4130: ("workday_schedule_3_hour", t.uint8_t),
        0x4131: ("workday_schedule_3_minute", t.uint8_t),
        0x4132: ("workday_schedule_3_temperature", t.int16s),
        0x4140: ("workday_schedule_4_hour", t.uint8_t),
        0x4141: ("workday_schedule_4_minute", t.uint8_t),
        0x4142: ("workday_schedule_4_temperature", t.int16s),
        0x4150: ("workday_schedule_5_hour", t.uint8_t),
        0x4151: ("workday_schedule_5_minute", t.uint8_t),
        0x4152: ("workday_schedule_5_temperature", t.int16s),
        0x4160: ("workday_schedule_6_hour", t.uint8_t),
        0x4161: ("workday_schedule_6_minute", t.uint8_t),
        0x4162: ("workday_schedule_6_temperature", t.int16s),
        0x4210: ("weekend_schedule_1_hour", t.uint8_t),
        0x4211: ("weekend_schedule_1_minute", t.uint8_t),
        0x4212: ("weekend_schedule_1_temperature", t.int16s),
        0x4220: ("weekend_schedule_2_hour", t.uint8_t),
        0x4221: ("weekend_schedule_2_minute", t.uint8_t),
        0x4222: ("weekend_schedule_2_temperature", t.int16s),
        0x4230: ("weekend_schedule_3_hour", t.uint8_t),
        0x4231: ("weekend_schedule_3_minute", t.uint8_t),
        0x4232: ("weekend_schedule_3_temperature", t.int16s),
        0x4240: ("weekend_schedule_4_hour", t.uint8_t),
        0x4241: ("weekend_schedule_4_minute", t.uint8_t),
        0x4242: ("weekend_schedule_4_temperature", t.int16s),
        0x4250: ("weekend_schedule_5_hour", t.uint8_t),
        0x4251: ("weekend_schedule_5_minute", t.uint8_t),
        0x4252: ("weekend_schedule_5_temperature", t.int16s),
        0x4260: ("weekend_schedule_6_hour", t.uint8_t),
        0x4261: ("weekend_schedule_6_minute", t.uint8_t),
        0x4262: ("weekend_schedule_6_temperature", t.int16s),
    }

    DIRECT_MAPPING_ATTRS = {
        "occupied_heating_setpoint": (
            MOES_TARGET_TEMP_ATTR,
            lambda value: round(value / 10),
        ),
        "unoccupied_heating_setpoint": (
            MOES_AWAY_TEMP_ATTR,
            lambda value: round(value / 100),
        ),
        "comfort_heating_setpoint": (
            MOES_COMFORT_TEMP_ATTR,
            lambda value: round(value / 100),
        ),
        "eco_heating_setpoint": (MOES_ECO_TEMP_ATTR, lambda value: round(value / 100)),
        "min_heat_setpoint_limit": (
            MOES_MIN_TEMPERATURE_ATTR,
            lambda value: round(value / 100),
        ),
        "max_heat_setpoint_limit": (
            MOES_MAX_TEMPERATURE_ATTR,
            lambda value: round(value / 100),
        ),
        "local_temperature_calibration": (
            MOES_TEMP_CALIBRATION_ATTR,
            lambda value: round(value / 10),
        ),
        "work_days": (MOES_WEEK_FORMAT_ATTR, None),
        "operation_preset": (MOES_MODE_ATTR, None),
        "boost_duration_seconds": (MOES_BOOST_TIME_ATTR, None),
        "valve_force_state": (MOES_FORCE_VALVE_ATTR, None),
        "unoccupied_duration_days": (MOES_AWAY_DAYS_ATTR, None),
    }

    WORKDAY_SCHEDULE_ATTRS = {
        "workday_schedule_6_temperature": 1500,
        "workday_schedule_6_minute": 0,
        "workday_schedule_6_hour": 22,
        "workday_schedule_5_temperature": 2000,
        "workday_schedule_5_minute": 30,
        "workday_schedule_5_hour": 17,
        "workday_schedule_4_temperature": 1500,
        "workday_schedule_4_minute": 30,
        "workday_schedule_4_hour": 12,
        "workday_schedule_3_temperature": 1500,
        "workday_schedule_3_minute": 30,
        "workday_schedule_3_hour": 11,
        "workday_schedule_2_temperature": 1500,
        "workday_schedule_2_minute": 0,
        "workday_schedule_2_hour": 8,
        "workday_schedule_1_temperature": 2000,
        "workday_schedule_1_minute": 0,
        "workday_schedule_1_hour": 6,
    }

    WEEKEND_SCHEDULE_ATTRS = {
        "weekend_schedule_6_temperature": 1500,
        "weekend_schedule_6_minute": 0,
        "weekend_schedule_6_hour": 22,
        "weekend_schedule_5_temperature": 2000,
        "weekend_schedule_5_minute": 30,
        "weekend_schedule_5_hour": 17,
        "weekend_schedule_4_temperature": 1500,
        "weekend_schedule_4_minute": 30,
        "weekend_schedule_4_hour": 12,
        "weekend_schedule_3_temperature": 1500,
        "weekend_schedule_3_minute": 30,
        "weekend_schedule_3_hour": 11,
        "weekend_schedule_2_temperature": 1500,
        "weekend_schedule_2_minute": 0,
        "weekend_schedule_2_hour": 8,
        "weekend_schedule_1_temperature": 2000,
        "weekend_schedule_1_minute": 0,
        "weekend_schedule_1_hour": 6,
    }

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""

        if attribute in self.DIRECT_MAPPING_ATTRS:
            return {
                self.DIRECT_MAPPING_ATTRS[attribute][0]: value
                if self.DIRECT_MAPPING_ATTRS[attribute][1] is None
                else self.DIRECT_MAPPING_ATTRS[attribute][1](value)
            }
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
                return {MOES_MODE_ATTR: 0}
            if occupancy == self.Occupancy.Occupied:
                if oper_mode == self.ProgrammingOperationMode.Schedule_programming_mode:
                    return {MOES_MODE_ATTR: 1}
                if oper_mode == self.ProgrammingOperationMode.Simple:
                    return {MOES_MODE_ATTR: 2}
                if oper_mode == self.ProgrammingOperationMode.Economy_mode:
                    return {MOES_MODE_ATTR: 4}
                self.error("Unsupported value for ProgrammingOperationMode")
            else:
                self.error("Unsupported value for Occupancy")
        if attribute == "system_mode":
            return {
                MOES_MODE_ATTR: self._attr_cache.get(
                    self.attridx["operation_preset"], 2
                )
            }
        if attribute in self.WORKDAY_SCHEDULE_ATTRS:
            data = data144()
            for num, (attr, default) in enumerate(self.WORKDAY_SCHEDULE_ATTRS.items()):

                if num % 3 == 0:
                    if attr == attribute:
                        val = round(value / 100)
                    else:
                        val = round(
                            self._attr_cache.get(self.attridx[attr], default) / 100
                        )
                else:
                    if attr == attribute:
                        val = value
                    else:
                        val = self._attr_cache.get(self.attridx[attr], default)

                data.append(val)
            return {MOES_SCHEDULE_WORKDAY_ATTR: data}
        if attribute in self.WEEKEND_SCHEDULE_ATTRS:
            data = data144()
            for num, (attr, default) in enumerate(self.WEEKEND_SCHEDULE_ATTRS.items()):

                if num % 3 == 0:
                    if attr == attribute:
                        val = round(value / 100)
                    else:
                        val = round(
                            self._attr_cache.get(self.attridx[attr], default) / 100
                        )
                else:
                    if attr == attribute:
                        val = value
                    else:
                        val = self._attr_cache.get(self.attridx[attr], default)

                data.append(val)
            return {MOES_SCHEDULE_WEEKEND_ATTR: data}

    def mode_change(self, value):
        """System Mode change."""
        if value == 0:
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Unoccupied
        elif value == 1:
            prog_mode = self.ProgrammingOperationMode.Schedule_programming_mode
            occupancy = self.Occupancy.Occupied
        elif value == 2:
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Occupied
        elif value == 3:
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Occupied
        elif value == 4:
            prog_mode = self.ProgrammingOperationMode.Economy_mode
            occupancy = self.Occupancy.Occupied
        elif value == 5:
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Occupied
        else:
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Occupied

        self._update_attribute(self.attridx["programing_oper_mode"], prog_mode)
        self._update_attribute(self.attridx["occupancy"], occupancy)

    def schedule_change(self, attr, value):
        """Scheduler attribute change."""

        if attr == MOES_SCHEDULE_WORKDAY_ATTR:
            self._update_attribute(
                self.attridx["workday_schedule_1_hour"], value[17] & 0x3F
            )
            self._update_attribute(self.attridx["workday_schedule_1_minute"], value[16])
            self._update_attribute(
                self.attridx["workday_schedule_1_temperature"], value[15] * 100
            )
            self._update_attribute(
                self.attridx["workday_schedule_2_hour"], value[14] & 0x3F
            )
            self._update_attribute(self.attridx["workday_schedule_2_minute"], value[13])
            self._update_attribute(
                self.attridx["workday_schedule_2_temperature"], value[12] * 100
            )
            self._update_attribute(
                self.attridx["workday_schedule_3_hour"], value[11] & 0x3F
            )
            self._update_attribute(self.attridx["workday_schedule_3_minute"], value[10])
            self._update_attribute(
                self.attridx["workday_schedule_3_temperature"], value[9] * 100
            )
            self._update_attribute(
                self.attridx["workday_schedule_4_hour"], value[8] & 0x3F
            )
            self._update_attribute(self.attridx["workday_schedule_4_minute"], value[7])
            self._update_attribute(
                self.attridx["workday_schedule_4_temperature"], value[6] * 100
            )
            self._update_attribute(
                self.attridx["workday_schedule_5_hour"], value[5] & 0x3F
            )
            self._update_attribute(self.attridx["workday_schedule_5_minute"], value[4])
            self._update_attribute(
                self.attridx["workday_schedule_5_temperature"], value[3] * 100
            )
            self._update_attribute(
                self.attridx["workday_schedule_6_hour"], value[2] & 0x3F
            )
            self._update_attribute(self.attridx["workday_schedule_6_minute"], value[1])
            self._update_attribute(
                self.attridx["workday_schedule_6_temperature"], value[0] * 100
            )
        elif attr == MOES_SCHEDULE_WEEKEND_ATTR:
            self._update_attribute(
                self.attridx["weekend_schedule_1_hour"], value[17] & 0x3F
            )
            self._update_attribute(self.attridx["weekend_schedule_1_minute"], value[16])
            self._update_attribute(
                self.attridx["weekend_schedule_1_temperature"], value[15] * 100
            )
            self._update_attribute(
                self.attridx["weekend_schedule_2_hour"], value[14] & 0x3F
            )
            self._update_attribute(self.attridx["weekend_schedule_2_minute"], value[13])
            self._update_attribute(
                self.attridx["weekend_schedule_2_temperature"], value[12] * 100
            )
            self._update_attribute(
                self.attridx["weekend_schedule_3_hour"], value[11] & 0x3F
            )
            self._update_attribute(self.attridx["weekend_schedule_3_minute"], value[10])
            self._update_attribute(
                self.attridx["weekend_schedule_3_temperature"], value[9] * 100
            )
            self._update_attribute(
                self.attridx["weekend_schedule_4_hour"], value[8] & 0x3F
            )
            self._update_attribute(self.attridx["weekend_schedule_4_minute"], value[7])
            self._update_attribute(
                self.attridx["weekend_schedule_4_temperature"], value[6] * 100
            )
            self._update_attribute(
                self.attridx["weekend_schedule_5_hour"], value[5] & 0x3F
            )
            self._update_attribute(self.attridx["weekend_schedule_5_minute"], value[4])
            self._update_attribute(
                self.attridx["weekend_schedule_5_temperature"], value[3] * 100
            )
            self._update_attribute(
                self.attridx["weekend_schedule_6_hour"], value[2] & 0x3F
            )
            self._update_attribute(self.attridx["weekend_schedule_6_minute"], value[1])
            self._update_attribute(
                self.attridx["weekend_schedule_6_temperature"], value[0] * 100
            )


class MoesUserInterface(TuyaUserInterfaceCluster):
    """HVAC User interface cluster for tuya electric heating thermostats."""

    _CHILD_LOCK_ATTR = MOES_CHILD_LOCK_ATTR

    manufacturer_attributes = {
        0x5000: ("auto_lock", t.Bool),
    }

    def autolock_change(self, value):
        """Automatic lock change."""

        self._update_attribute(self.attridx["auto_lock"], value)

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""

        if attribute == "auto_lock":
            return {MOES_AUTO_LOCK_ATTR: value}


class MoesWindowDetection(LocalDataCluster, OnOff):
    """On/Off cluster for the window detection function of the electric heating thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MoesWindowDetection_bus.add_listener(self)

    manufacturer_attributes = {
        0x6000: ("window_detection_temperature", t.int16s),
        0x6001: ("window_detection_timeout_minutes", t.uint8_t),
    }

    def window_detect_change(self, value):
        """Window detection change."""

        self._update_attribute(
            self.attridx["window_detection_timeout_minutes"], value[0]
        )
        self._update_attribute(
            self.attridx["window_detection_temperature"], value[1] * 100
        )
        self._update_attribute(self.attridx["on_off"], value[2])

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer attributes writing to the set_data tuya command."""

        records = self._write_attr_records(attributes)

        if not records:
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

        has_change = False
        data = t.data24()
        data.append(
            self._attr_cache.get(
                self.attridx["window_detection_timeout_minutes"],
                5,
            )
        )
        data.append(
            round(
                self._attr_cache.get(
                    self.attridx["window_detection_temperature"],
                    50,
                )
                / 100
            )
        )
        data.append(
            self._attr_cache.get(
                self.attridx["on_off"],
                False,
            )
        )

        for record in records:
            attr_name = self.attributes[record.attrid][0]
            if attr_name == "on_off":
                data[2] = record.value.value
                has_change = True
            elif attr_name == "window_detection_temperature":
                data[1] = record.value.value / 100
                has_change = True
            elif attr_name == "window_detection_timeout_minutes":
                data[0] = record.value.value
                has_change = True

        if has_change:
            return await self.endpoint.tuya_manufacturer.write_attributes(
                {MOES_WINDOW_DETECT_ATTR: data}, manufacturer=manufacturer
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
                {"on_off": value},
                manufacturer=manufacturer,
            )
            return [command_id, res[0].status]

        return [command_id, foundation.Status.UNSUP_CLUSTER_COMMAND]


class MoesChildLock(LocalDataCluster, OnOff):
    """On/Off cluster for the child lock function of the electric heating thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MoesChildLock_bus.add_listener(self)

    def switch_change(self, value):
        """Child lock change."""
        self._update_attribute(self.attridx["on_off"], value)

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer attributes writing to the set_data tuya command."""
        records = self._write_attr_records(attributes)
        if not records:
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

        has_change = False
        for record in records:
            attr_name = self.attributes[record.attrid][0]
            if attr_name == "on_off":
                value = record.value.value
                has_change = True

        if has_change:
            return await MoesManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MOES_CHILD_LOCK_ATTR: value}, manufacturer=manufacturer
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


class MoesValveState(LocalDataCluster, AnalogOutput):
    """Analog output for Valve State."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MoesValveState_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "Valve State")
        self._update_attribute(self.attridx["max_present_value"], 100)
        self._update_attribute(self.attridx["min_present_value"], 0)
        self._update_attribute(self.attridx["resolution"], 1)
        self._update_attribute(self.attridx["application_type"], 4 << 16)
        self._update_attribute(self.attridx["engineering_units"], 98)

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

            await MoesManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MOES_VALVE_STATE_ATTR: value}, manufacturer=None
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MoesTempCalibration(LocalDataCluster, AnalogOutput):
    """Analog output for Temp Calibration."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MoesTempCalibration_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "Temperature Calibration")
        self._update_attribute(self.attridx["max_present_value"], 9)
        self._update_attribute(self.attridx["min_present_value"], -9)
        self._update_attribute(self.attridx["resolution"], 1)
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

            await MoesManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MOES_TEMP_CALIBRATION_ATTR: value},
                manufacturer=None,
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MoesBoostTime(LocalDataCluster, AnalogOutput):
    """Analog output for Boost Time."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MoesBoostTime_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "Boost Time")
        self._update_attribute(self.attridx["max_present_value"], 9999)
        self._update_attribute(self.attridx["min_present_value"], 0)
        self._update_attribute(self.attridx["resolution"], 1)
        self._update_attribute(self.attridx["application_type"], 14 << 16)
        self._update_attribute(self.attridx["engineering_units"], 73)

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

            await MoesManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MOES_BOOST_TIME_ATTR: value},
                manufacturer=None,
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MoesValveDetect(LocalDataCluster, OnOff):
    """On/Off cluster for the valve detect function of the electric heating thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MoesValveDetect_bus.add_listener(self)

    def switch_change(self, value):
        """Valve detect change."""
        self._update_attribute(self.attridx["on_off"], value)

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer attributes writing to the set_data tuya command."""
        records = self._write_attr_records(attributes)
        if not records:
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

        has_change = False
        for record in records:
            attr_name = self.attributes[record.attrid][0]
            if attr_name == "on_off":
                value = record.value.value
                has_change = True

        if has_change:
            return await MoesManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MOES_VALVE_DETECT_ATTR: value}, manufacturer=manufacturer
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


class MoesMinTemp(LocalDataCluster, AnalogOutput):
    """Analog output for Minimum temperature."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MoesMinTemp_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "Min. temperature")
        self._update_attribute(self.attridx["max_present_value"], 15)
        self._update_attribute(self.attridx["min_present_value"], 5)
        self._update_attribute(self.attridx["resolution"], 1)
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

            await MoesManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MOES_MIN_TEMPERATURE_ATTR: value},
                manufacturer=None,
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MoesMaxTemp(LocalDataCluster, AnalogOutput):
    """Analog output for Maximum temperature."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MoesMaxTemp_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "Max. temperature")
        self._update_attribute(self.attridx["max_present_value"], 35)
        self._update_attribute(self.attridx["min_present_value"], 15)
        self._update_attribute(self.attridx["resolution"], 1)
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

            await MoesManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MOES_MAX_TEMPERATURE_ATTR: value},
                manufacturer=None,
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MoesComfortTemp(LocalDataCluster, AnalogOutput):
    """Analog output for Comfort temperature."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MoesComfortTemp_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "Comfort temperature")
        self._update_attribute(self.attridx["max_present_value"], 35)
        self._update_attribute(self.attridx["min_present_value"], 5)
        self._update_attribute(self.attridx["resolution"], 1)
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

            await MoesManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MOES_COMFORT_TEMP_ATTR: value},
                manufacturer=None,
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MoesEcoTemp(LocalDataCluster, AnalogOutput):
    """Analog output for Eco temperature."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MoesEcoTemp_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "Eco temperature")
        self._update_attribute(self.attridx["max_present_value"], 35)
        self._update_attribute(self.attridx["min_present_value"], 5)
        self._update_attribute(self.attridx["resolution"], 1)
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

            await MoesManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MOES_ECO_TEMP_ATTR: value},
                manufacturer=None,
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MoesAwayTemp(LocalDataCluster, AnalogOutput):
    """Analog output for Away temperature."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MoesAwayTemp_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "Away temperature")
        self._update_attribute(self.attridx["max_present_value"], 35)
        self._update_attribute(self.attridx["min_present_value"], 5)
        self._update_attribute(self.attridx["resolution"], 1)
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

            await MoesManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MOES_AWAY_TEMP_ATTR: value},
                manufacturer=None,
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MoesAwayDays(LocalDataCluster, AnalogOutput):
    """Analog output for Away days."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.MoesAwayDays_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "Away days")
        self._update_attribute(self.attridx["max_present_value"], 9999)
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

            await MoesManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {MOES_AWAY_DAYS_ATTR: value},
                manufacturer=None,
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class MoesHY368_Type1(TuyaThermostat):
    """MoesHY368 Thermostatic radiator valve."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.MoesWindowDetection_bus = Bus()
        self.MoesChildLock_bus = Bus()
        self.MoesValveState_bus = Bus()
        self.MoesTempCalibration_bus = Bus()
        self.MoesBoostTime_bus = Bus()
        self.MoesValveDetect_bus = Bus()
        self.MoesMinTemp_bus = Bus()
        self.MoesMaxTemp_bus = Bus()
        self.MoesComfortTemp_bus = Bus()
        self.MoesEcoTemp_bus = Bus()
        self.MoesAwayTemp_bus = Bus()
        self.MoesAwayDays_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=0 input_clusters=[0, 4, 5, 61184]
        #  output_clusters=[10, 25]>
        MODELS_INFO: [
            ("_TZE200_ckud7u2l", "TS0601"),
            ("_TZE200_ywdxldoj", "TS0601"),
            ("_TZE200_cwnjrr72", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
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
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesManufCluster,
                    MoesThermostat,
                    MoesUserInterface,
                    MoesWindowDetection,
                    TuyaPowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MoesChildLock],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesValveState],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesTempCalibration],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesBoostTime],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MoesValveDetect],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesMinTemp],
                OUTPUT_CLUSTERS: [],
            },
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesMaxTemp],
                OUTPUT_CLUSTERS: [],
            },
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesComfortTemp],
                OUTPUT_CLUSTERS: [],
            },
            10: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesEcoTemp],
                OUTPUT_CLUSTERS: [],
            },
            11: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesAwayTemp],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class MoesHY368_Type2(TuyaThermostat):
    """MoesHY368 Thermostatic radiator valve (2nd cluster signature)."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.MoesWindowDetection_bus = Bus()
        self.MoesChildLock_bus = Bus()
        self.MoesValveState_bus = Bus()
        self.MoesTempCalibration_bus = Bus()
        self.MoesBoostTime_bus = Bus()
        self.MoesValveDetect_bus = Bus()
        self.MoesMinTemp_bus = Bus()
        self.MoesMaxTemp_bus = Bus()
        self.MoesComfortTemp_bus = Bus()
        self.MoesEcoTemp_bus = Bus()
        self.MoesAwayTemp_bus = Bus()
        self.MoesAwayDays_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  endpoint=1 profile=260 device_type=0 device_version=0 input_clusters=[0, 3]
        #  output_clusters=[3, 25]>
        MODELS_INFO: [
            ("_TYST11_ckud7u2l", "kud7u2l"),
            ("_TYST11_ywdxldoj", "wdxldoj"),
            ("_TYST11_cwnjrr72", "wnjrr72"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [Basic.cluster_id, Identify.cluster_id],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
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
                    MoesManufCluster,
                    MoesThermostat,
                    MoesUserInterface,
                    MoesWindowDetection,
                    TuyaPowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MoesChildLock],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesValveState],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesTempCalibration],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesBoostTime],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MoesValveDetect],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesMinTemp],
                OUTPUT_CLUSTERS: [],
            },
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesMaxTemp],
                OUTPUT_CLUSTERS: [],
            },
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesComfortTemp],
                OUTPUT_CLUSTERS: [],
            },
            10: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesEcoTemp],
                OUTPUT_CLUSTERS: [],
            },
            11: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [MoesAwayTemp],
                OUTPUT_CLUSTERS: [],
            },
        }
    }
