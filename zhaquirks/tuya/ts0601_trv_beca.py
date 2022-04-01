"""Beca TRV devices support."""
import logging
from typing import Optional, Union

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    AnalogInput,
    AnalogOutput,
    Basic,
    BinaryInput,
    Groups,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.hvac import Thermostat

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

_LOGGER = logging.getLogger(__name__)

BECA_TARGET_TEMP_ATTR = 0x0202  # target room temp (decidegree)
BECA_TEMPERATURE_ATTR = 0x0203  # current room temp (decidegree)
BECA_MODE_ATTR = 0x0401  # [0] schedule [1] manual [2] temporary manual [3] away
BECA_CHILD_LOCK_ATTR = 0x010D  # [0] unlocked [1] locked
BECA_TEMP_CALIBRATION_ATTR = 0x0269  # temperature calibration (degree)
BECA_MIN_TEMPERATURE_ATTR = 0x026D  # minimum limit of temperature setting (degree)
BECA_MAX_TEMPERATURE_ATTR = 0x026C  # maximum limit of temperature setting (degree)
BECA_WINDOW_DETECT_ATTR = 0x0409  # opened window [1] detected [0] not detected
BECA_WINDOW_DETECT_A2_ATTR = 0x0108  # opened window function [0] inactive [1] active
BECA_BOOST_TIME_ATTR = 0x0267  # BOOST mode operating time in (sec)
BECA_BOOST_ATTR = 0x0104  # [0] off [1] on
BECA_BOOST_COUNTDOWN_ATTR = 0x0205  # (seconds)
BECA_ECO_TEMP_ATTR = 0x026B  # eco mode temperature (degree)
BECA_ECO_MODE_ATTR = 0x016A  # [0] off [1] on
BECA_VALVE_STATE_ATTR = 0x0268  # opening percentage
BECA_BATTERY_ATTR = 0x020E  # battery percentage remaining 0-100%
BECA_SCHEDULE = 0x0065  # schedule
# [6, 0, 40, 11, 30, 42, 13, 30, 44, 17, 30, 46, 6, 0, 48, 12, 0, 46, 14, 30, 44, 17, 30, 42, 6, 0, 38, 12, 30, 40, 14, 30, 42, 18, 30, 40] for :
# Monday to friday : 06:00 20°C / 11:30 21°C / 13:30 22°C / 17:30 23°C
# Saturday : 06:00 24°C / 12:00 23°C / 14:30 22°C / 17:30 21°C
# Sunday : 06:00 19°C / 12:30 20°C / 14:30 21°C / 18:30 20°C )
BecaManufClusterSelf = {}


class data288(t.FixedList, item_type=t.uint8_t, length=36):
    """General data, Discrete, 288 bit."""

    pass


class BecaManufCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of thermostatic valves."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        global BecaManufClusterSelf
        BecaManufClusterSelf[self.endpoint.device.ieee] = self

    set_time_offset = 1970

    attributes = TuyaManufClusterAttributes.attributes.copy()
    attributes = {
        BECA_TEMPERATURE_ATTR: ("temperature", t.uint32_t),
        BECA_TARGET_TEMP_ATTR: ("target_temperature", t.uint32_t),
        BECA_MODE_ATTR: ("mode", t.uint8_t),
        BECA_CHILD_LOCK_ATTR: ("child_lock", t.uint8_t),
        BECA_TEMP_CALIBRATION_ATTR: ("temperature_calibration", t.int32s),
        BECA_MIN_TEMPERATURE_ATTR: ("min_temperature", t.uint32_t),
        BECA_MAX_TEMPERATURE_ATTR: ("max_temperature", t.uint32_t),
        BECA_WINDOW_DETECT_ATTR: ("window_detection", t.uint8_t),
        BECA_WINDOW_DETECT_A2_ATTR: ("window_detection_A2_function", t.uint8_t),
        BECA_BOOST_TIME_ATTR: ("boost_duration_seconds", t.uint32_t),
        BECA_BOOST_ATTR: ("boost_enabled", t.uint8_t),
        BECA_BOOST_COUNTDOWN_ATTR: ("boost_duration_seconds", t.uint32_t),
        BECA_ECO_TEMP_ATTR: ("eco_mode_temperature", t.uint32_t),
        BECA_ECO_MODE_ATTR: ("eco_mode_enabled", t.uint8_t),
        BECA_VALVE_STATE_ATTR: ("valve_state", t.uint32_t),
        BECA_BATTERY_ATTR: ("battery", t.uint32_t),
        BECA_SCHEDULE: ("schedule", data288),
    }

    DIRECT_MAPPED_ATTRS = {
        BECA_TEMPERATURE_ATTR: ("local_temperature", lambda value: value * 10),
        BECA_TARGET_TEMP_ATTR: ("occupied_heating_setpoint", lambda value: value * 100),
        BECA_TEMP_CALIBRATION_ATTR: ("local_temperature_calibration", None),
        BECA_MIN_TEMPERATURE_ATTR: (
            "min_heat_setpoint_limit",
            lambda value: value * 100,
        ),
        BECA_MAX_TEMPERATURE_ATTR: (
            "max_heat_setpoint_limit",
            lambda value: value * 100,
        ),
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

        if attrid == BECA_WINDOW_DETECT_ATTR:
            self.endpoint.device.BecaWindowDetection_bus.listener_event(
                "set_value", value
            )
        if attrid == BECA_WINDOW_DETECT_A2_ATTR:
            self.endpoint.device.BecaWindowDetection_A2_bus.listener_event(
                "switch_change", value
            )
        elif attrid == BECA_CHILD_LOCK_ATTR:
            mode = 1 if value else 0
            self.endpoint.device.ui_bus.listener_event("child_lock_change", mode)
            self.endpoint.device.BecaChildLock_bus.listener_event("switch_change", mode)
        elif attrid in (BECA_MODE_ATTR, BECA_BOOST_ATTR, BECA_ECO_MODE_ATTR):
            if attrid == BECA_BOOST_ATTR and value == 1:
                self.endpoint.device.thermostat_bus.listener_event("mode_change", 5)
            elif attrid == BECA_ECO_MODE_ATTR and value == 1:
                self.endpoint.device.thermostat_bus.listener_event("mode_change", 4)
            elif attrid == BECA_MODE_ATTR:
                self.endpoint.device.thermostat_bus.listener_event("mode_change", value)
        elif attrid == BECA_VALVE_STATE_ATTR:
            self.endpoint.device.thermostat_bus.listener_event("state_change", value)
            self.endpoint.device.BecaValveState_bus.listener_event("set_value", value)
        elif attrid == BECA_TEMP_CALIBRATION_ATTR:
            self.endpoint.device.BecaTempCalibration_bus.listener_event(
                "set_value", value
            )
        elif attrid == BECA_BOOST_TIME_ATTR:
            self.endpoint.device.BecaBoostTime_bus.listener_event("set_value", value)
        elif attrid == BECA_BOOST_COUNTDOWN_ATTR:
            self.endpoint.device.BecaBoostCountdown_bus.listener_event(
                "set_value", value
            )
        elif attrid == BECA_ECO_TEMP_ATTR:
            self.endpoint.device.BecaEcoTemp_bus.listener_event("set_value", value)
        elif attrid == BECA_BATTERY_ATTR:
            self.endpoint.device.battery_bus.listener_event("battery_change", value)
        elif attrid == BECA_MIN_TEMPERATURE_ATTR:
            self.endpoint.device.BecaMinTemp_bus.listener_event("set_value", value)
        elif attrid == BECA_MAX_TEMPERATURE_ATTR:
            self.endpoint.device.BecaMaxTemp_bus.listener_event("set_value", value)
        elif attrid == BECA_SCHEDULE:
            self.endpoint.device.thermostat_bus.listener_event("schedule_change", value)


class BecaThermostat(TuyaThermostatCluster):
    """Thermostat cluster for thermostatic valves."""

    class Preset(t.enum8):
        """Working modes of the thermostat."""

        Away = 0x00
        Schedule = 0x01
        Manual = 0x02
        Comfort = 0x03
        Eco = 0x04
        Boost = 0x05
        Complex = 0x06
        TempManual = 0x07

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

    attributes = TuyaThermostatCluster.attributes.copy()
    attributes.update(
        {
            0x4002: ("operation_preset", Preset),
            0x4110: ("schedule_workday_1_hour", t.uint8_t),
            0x4111: ("schedule_workday_1_minute", t.uint8_t),
            0x4112: ("schedule_workday_1_temperature", t.uint8_t),
            0x4113: ("schedule_workday_2_hour", t.uint8_t),
            0x4114: ("schedule_workday_2_minute", t.uint8_t),
            0x4115: ("schedule_workday_2_temperature", t.uint8_t),
            0x4116: ("schedule_workday_3_hour", t.uint8_t),
            0x4117: ("schedule_workday_3_minute", t.uint8_t),
            0x4118: ("schedule_workday_3_temperature", t.uint8_t),
            0x4119: ("schedule_workday_4_hour", t.uint8_t),
            0x4120: ("schedule_workday_4_minute", t.uint8_t),
            0x4121: ("schedule_workday_4_temperature", t.uint8_t),
            0x4122: ("schedule_saturday_1_hour", t.uint8_t),
            0x4123: ("schedule_saturday_1_minute", t.uint8_t),
            0x4124: ("schedule_saturday_1_temperature", t.uint8_t),
            0x4125: ("schedule_saturday_2_hour", t.uint8_t),
            0x4126: ("schedule_saturday_2_minute", t.uint8_t),
            0x4127: ("schedule_saturday_2_temperature", t.uint8_t),
            0x4128: ("schedule_saturday_3_hour", t.uint8_t),
            0x4129: ("schedule_saturday_3_minute", t.uint8_t),
            0x4130: ("schedule_saturday_3_temperature", t.uint8_t),
            0x4131: ("schedule_saturday_4_hour", t.uint8_t),
            0x4132: ("schedule_saturday_4_minute", t.uint8_t),
            0x4133: ("schedule_saturday_4_temperature", t.uint8_t),
            0x4134: ("schedule_sunday_1_hour", t.uint8_t),
            0x4135: ("schedule_sunday_1_minute", t.uint8_t),
            0x4136: ("schedule_sunday_1_temperature", t.uint8_t),
            0x4137: ("schedule_sunday_2_hour", t.uint8_t),
            0x4138: ("schedule_sunday_2_minute", t.uint8_t),
            0x4139: ("schedule_sunday_2_temperature", t.uint8_t),
            0x4140: ("schedule_sunday_3_hour", t.uint8_t),
            0x4141: ("schedule_sunday_3_minute", t.uint8_t),
            0x4142: ("schedule_sunday_3_temperature", t.uint8_t),
            0x4143: ("schedule_sunday_4_hour", t.uint8_t),
            0x4144: ("schedule_sunday_4_minute", t.uint8_t),
            0x4145: ("schedule_sunday_4_temperature", t.uint8_t),
        }
    )

    DIRECT_MAPPING_ATTRS = {
        "min_heat_setpoint_limit": (
            BECA_MIN_TEMPERATURE_ATTR,
            lambda value: round(value / 100),
        ),
        "max_heat_setpoint_limit": (
            BECA_MAX_TEMPERATURE_ATTR,
            lambda value: round(value / 100),
        ),
        "local_temperature_calibration": (
            BECA_TEMP_CALIBRATION_ATTR,
            lambda value: value,
        ),
    }

    SCHEDULE_ATTRS = {
        "schedule_sunday_4_temperature": 20,
        "schedule_sunday_4_minute": 30,
        "schedule_sunday_4_hour": 18,
        "schedule_sunday_3_temperature": 21,
        "schedule_sunday_3_minute": 30,
        "schedule_sunday_3_hour": 14,
        "schedule_sunday_2_temperature": 20,
        "schedule_sunday_2_minute": 30,
        "schedule_sunday_2_hour": 12,
        "schedule_sunday_1_temperature": 19,
        "schedule_sunday_1_minute": 0,
        "schedule_sunday_1_hour": 6,
        "schedule_saturday_4_temperature": 21,
        "schedule_saturday_4_minute": 30,
        "schedule_saturday_4_hour": 17,
        "schedule_saturday_3_temperature": 22,
        "schedule_saturday_3_minute": 30,
        "schedule_saturday_3_hour": 14,
        "schedule_saturday_2_temperature": 23,
        "schedule_saturday_2_minute": 00,
        "schedule_saturday_2_hour": 12,
        "schedule_saturday_1_temperature": 24,
        "schedule_saturday_1_minute": 0,
        "schedule_saturday_1_hour": 6,
        "schedule_workday_4_temperature": 23,
        "schedule_workday_4_minute": 30,
        "schedule_workday_4_hour": 17,
        "schedule_workday_3_temperature": 22,
        "schedule_workday_3_minute": 30,
        "schedule_workday_3_hour": 13,
        "schedule_workday_2_temperature": 21,
        "schedule_workday_2_minute": 30,
        "schedule_workday_2_hour": 11,
        "schedule_workday_1_temperature": 20,
        "schedule_workday_1_minute": 0,
        "schedule_workday_1_hour": 6,
    }

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""

        if attribute in self.DIRECT_MAPPING_ATTRS:
            return {
                self.DIRECT_MAPPING_ATTRS[attribute][0]: value
                if self.DIRECT_MAPPING_ATTRS[attribute][1] is None
                else self.DIRECT_MAPPING_ATTRS[attribute][1](value)
            }

        if attribute == "occupied_heating_setpoint":
            mode = self._attr_cache.get(self.attributes_by_name["operation_preset"].id)
            if mode == self.Preset.Schedule:
                return {BECA_MODE_ATTR: 2, BECA_TARGET_TEMP_ATTR: value / 100}
            else:
                return {BECA_TARGET_TEMP_ATTR: value / 100}

        if attribute == "operation_preset":
            if value == 0:
                return {BECA_MODE_ATTR: 3, BECA_BOOST_ATTR: 0, BECA_ECO_MODE_ATTR: 0}
            if value == 1:
                return {BECA_MODE_ATTR: 0, BECA_BOOST_ATTR: 0, BECA_ECO_MODE_ATTR: 0}
            if value == 2:
                return {BECA_MODE_ATTR: 1, BECA_BOOST_ATTR: 0, BECA_ECO_MODE_ATTR: 0}
            if value == 4:
                return {BECA_BOOST_ATTR: 0, BECA_ECO_MODE_ATTR: 1}
            if value == 5:
                return {BECA_BOOST_ATTR: 1, BECA_ECO_MODE_ATTR: 0}
            if value == 7:
                return {BECA_MODE_ATTR: 2, BECA_BOOST_ATTR: 0, BECA_ECO_MODE_ATTR: 0}

        if attribute in ("programing_oper_mode", "occupancy"):
            if attribute == "occupancy":
                occupancy = value
                oper_mode = self._attr_cache.get(
                    self.attributes_by_name["programing_oper_mode"].id,
                    self.ProgrammingOperationMode.Simple,
                )
            else:
                occupancy = self._attr_cache.get(
                    self.attributes_by_name["occupancy"].id, self.Occupancy.Occupied
                )
                oper_mode = value
            if occupancy == self.Occupancy.Unoccupied:
                return {BECA_MODE_ATTR: 3}
            if occupancy == self.Occupancy.Occupied:
                if oper_mode == self.ProgrammingOperationMode.Schedule_programming_mode:
                    return {BECA_MODE_ATTR: 0}
                if oper_mode == self.ProgrammingOperationMode.Simple:
                    return {BECA_MODE_ATTR: 1}
                self.error("Unsupported value for ProgrammingOperationMode")
            else:
                self.error("Unsupported value for Occupancy")

        if attribute in self.SCHEDULE_ATTRS:
            data = data288()
            for num, (attr, default) in enumerate(self.SCHEDULE_ATTRS.items()):
                if num % 3 == 0:
                    if attr == attribute:
                        val = round(value * 2)
                    else:
                        val = round(
                            self._attr_cache.get(self.attributes_by_name[attr].id, default) * 2
                        )
                else:
                    if attr == attribute:
                        val = value
                    else:
                        val = self._attr_cache.get(self.attributes_by_name[attr].id, default)

                data.append(val)
            return {BECA_SCHEDULE: data}

    def mode_change(self, value):
        """System Mode change."""
        if value == 1:
            operation_preset = self.Preset.Manual
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Occupied
        elif value == 2:
            operation_preset = self.Preset.TempManual
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Occupied
        elif value == 3:
            operation_preset = self.Preset.Away
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Unoccupied
        elif value == 4:
            operation_preset = self.Preset.Eco
            prog_mode = self.ProgrammingOperationMode.Economy_mode
            occupancy = self.Occupancy.Occupied
        elif value == 5:
            operation_preset = self.Preset.Boost
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Occupied
        else:
            operation_preset = self.Preset.Schedule
            prog_mode = self.ProgrammingOperationMode.Schedule_programming_mode
            occupancy = self.Occupancy.Occupied

        self._update_attribute(self.attributes_by_name["programing_oper_mode"].id, prog_mode)
        self._update_attribute(self.attributes_by_name["occupancy"].id, occupancy)
        self._update_attribute(self.attributes_by_name["operation_preset"].id, operation_preset)

    def schedule_change(self, value):
        """Scheduler attribute change."""
        self._update_attribute(self.attributes_by_name["schedule_workday_1_hour"].id, value[35])
        self._update_attribute(self.attributes_by_name["schedule_workday_1_minute"].id, value[34])
        self._update_attribute(
            self.attributes_by_name["schedule_workday_1_temperature"].id, value[33] / 2
        )
        self._update_attribute(self.attributes_by_name["schedule_workday_2_hour"].id, value[32])
        self._update_attribute(self.attributes_by_name["schedule_workday_2_minute"].id, value[31])
        self._update_attribute(
            self.attributes_by_name["schedule_workday_2_temperature"].id, value[30] / 2
        )
        self._update_attribute(self.attributes_by_name["schedule_workday_3_hour"].id, value[29])
        self._update_attribute(self.attributes_by_name["schedule_workday_3_minute"].id, value[28])
        self._update_attribute(
            self.attributes_by_name["schedule_workday_3_temperature"].id, value[27] / 2
        )
        self._update_attribute(self.attributes_by_name["schedule_workday_4_hour"].id, value[26])
        self._update_attribute(self.attributes_by_name["schedule_workday_4_minute"].id, value[25])
        self._update_attribute(
            self.attributes_by_name["schedule_workday_4_temperature"].id, value[24] / 2
        )
        self._update_attribute(self.attributes_by_name["schedule_saturday_1_hour"].id, value[23])
        self._update_attribute(self.attributes_by_name["schedule_saturday_1_minute"].id, value[22])
        self._update_attribute(
            self.attributes_by_name["schedule_saturday_1_temperature"].id, value[21] / 2
        )
        self._update_attribute(self.attributes_by_name["schedule_saturday_2_hour"].id, value[20])
        self._update_attribute(self.attributes_by_name["schedule_saturday_2_minute"].id, value[19])
        self._update_attribute(
            self.attributes_by_name["schedule_saturday_2_temperature"].id, value[18] / 2
        )
        self._update_attribute(self.attributes_by_name["schedule_saturday_3_hour"].id, value[17])
        self._update_attribute(self.attributes_by_name["schedule_saturday_3_minute"].id, value[16])
        self._update_attribute(
            self.attributes_by_name["schedule_saturday_3_temperature"].id, value[15] / 2
        )
        self._update_attribute(self.attributes_by_name["schedule_saturday_4_hour"].id, value[14])
        self._update_attribute(self.attributes_by_name["schedule_saturday_4_minute"].id, value[13])
        self._update_attribute(
            self.attributes_by_name["schedule_saturday_4_temperature"].id, value[12] / 2
        )
        self._update_attribute(self.attributes_by_name["schedule_sunday_1_hour"].id, value[11])
        self._update_attribute(self.attributes_by_name["schedule_sunday_1_minute"].id, value[10])
        self._update_attribute(
            self.attributes_by_name["schedule_sunday_1_temperature"].id, value[9] / 2
        )
        self._update_attribute(self.attributes_by_name["schedule_sunday_2_hour"].id, value[8])
        self._update_attribute(self.attributes_by_name["schedule_sunday_2_minute"].id, value[7])
        self._update_attribute(
            self.attributes_by_name["schedule_sunday_2_temperature"].id, value[6] / 2
        )
        self._update_attribute(self.attributes_by_name["schedule_sunday_3_hour"].id, value[5])
        self._update_attribute(self.attributes_by_name["schedule_sunday_3_minute"].id, value[4])
        self._update_attribute(
            self.attributes_by_name["schedule_sunday_3_temperature"].id, value[3] / 2
        )
        self._update_attribute(self.attributes_by_name["schedule_sunday_4_hour"].id, value[2])
        self._update_attribute(self.attributes_by_name["schedule_sunday_4_minute"].id, value[1])
        self._update_attribute(
            self.attributes_by_name["schedule_sunday_4_temperature"].id, value[0] / 2
        )


class BecaUserInterface(TuyaUserInterfaceCluster):
    """HVAC User interface cluster for tuya electric heating thermostats."""

    _CHILD_LOCK_ATTR = BECA_CHILD_LOCK_ATTR


class BecaWindowDetection(LocalDataCluster, BinaryInput):
    """BinaryInput cluster for showing opened window detection state of the electric heating thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.BecaWindowDetection_bus.add_listener(self)
        self._update_attribute(self.attributes_by_name["description"].id, "Open Window Detected")

    def set_value(self, value):
        """Set opened window value."""
        self._update_attribute(self.attributes_by_name["present_value"].id, not value)


class BecaWindowDetection_A2(LocalDataCluster, OnOff):
    """On/Off cluster for enabling the window detection function (Settings - A2) of the electric heating thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.BecaWindowDetection_A2_bus.add_listener(self)

    def switch_change(self, value):
        """Window detect (Settings - A2) change."""
        self._update_attribute(self.attributes_by_name["on_off"].id, value)

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer attributes writing to the set_data tuya command."""
        records = self._write_attr_records(attributes)
        if not records:
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

        has_change = False
        for record in records:
            attr_name = self.attributes[record.attrid].name
            if attr_name == "on_off":
                value = record.value.value
                has_change = True

        if has_change:
            return await BecaManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {BECA_WINDOW_DETECT_A2_ATTR: value}, manufacturer=manufacturer
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
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
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
                attrid = self.attributes_by_name["on_off"].id
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


class BecaChildLock(LocalDataCluster, OnOff):
    """On/Off cluster for the child lock function of the electric heating thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.BecaChildLock_bus.add_listener(self)

    def switch_change(self, value):
        """Child lock change."""
        self._update_attribute(self.attributes_by_name["on_off"].id, value)

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer attributes writing to the set_data tuya command."""
        records = self._write_attr_records(attributes)
        if not records:
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

        has_change = False
        for record in records:
            attr_name = self.attributes[record.attrid].name
            if attr_name == "on_off":
                value = record.value.value
                has_change = True

        if has_change:
            return await BecaManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {BECA_CHILD_LOCK_ATTR: value}, manufacturer=manufacturer
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
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
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
                attrid = self.attributes_by_name["on_off"].id
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


class BecaValveState(LocalDataCluster, AnalogInput):
    """Analog input for valve opening state."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.BecaValveState_bus.add_listener(self)
        self._update_attribute(self.attributes_by_name["description"].id, "Valve State")
        self._update_attribute(self.attributes_by_name["resolution"].id, 1)
        self._update_attribute(self.attributes_by_name["engineering_units"].id, 98)
        self._update_attribute(self.attributes_by_name["application_type"].id, 4 << 16)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attributes_by_name["present_value"].id, value)


class BecaTempCalibration(LocalDataCluster, AnalogOutput):
    """Analog output for Temp Calibration."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.BecaTempCalibration_bus.add_listener(self)
        self._update_attribute(self.attributes_by_name["description"].id, "Temperature Calibration")
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 9)
        self._update_attribute(self.attributes_by_name["min_present_value"].id, -9)
        self._update_attribute(self.attributes_by_name["resolution"].id, 1)
        self._update_attribute(self.attributes_by_name["application_type"].id, 0x0009)
        self._update_attribute(self.attributes_by_name["engineering_units"].id, 62)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attributes_by_name["present_value"].id, value)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attributes_by_name["present_value"].id)

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attributes_by_name[attrid].id
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)

            await BecaManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {BECA_TEMP_CALIBRATION_ATTR: value},
                manufacturer=None,
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class BecaBoostTime(LocalDataCluster, AnalogOutput):
    """Analog output for setting Boost Time duration value."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.BecaBoostTime_bus.add_listener(self)
        self._update_attribute(self.attributes_by_name["description"].id, "Boost Time")
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 900)
        self._update_attribute(self.attributes_by_name["min_present_value"].id, 100)
        self._update_attribute(self.attributes_by_name["resolution"].id, 10)
        self._update_attribute(self.attributes_by_name["application_type"].id, 14 << 16)
        self._update_attribute(self.attributes_by_name["engineering_units"].id, 73)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attributes_by_name["present_value"].id, value)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attributes_by_name["present_value"].id)

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attributes_by_name[attrid].id
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)

            await BecaManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {BECA_BOOST_TIME_ATTR: value},
                manufacturer=None,
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class BecaBoostCountdown(LocalDataCluster, AnalogInput):
    """Analog input for Boost Countdown time."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.BecaBoostCountdown_bus.add_listener(self)
        self._update_attribute(self.attributes_by_name["description"].id, "Boost Countdown")
        self._update_attribute(self.attributes_by_name["resolution"].id, 1)
        self._update_attribute(self.attributes_by_name["application_type"].id, 14 << 16)
        self._update_attribute(self.attributes_by_name["engineering_units"].id, 72)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attributes_by_name["present_value"].id, value)


class BecaEcoTemp(LocalDataCluster, AnalogOutput):
    """Analog output for Eco Temperature."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.BecaEcoTemp_bus.add_listener(self)
        self._update_attribute(self.attributes_by_name["description"].id, "Eco Temperature")
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 35)
        self._update_attribute(self.attributes_by_name["min_present_value"].id, 5)
        self._update_attribute(self.attributes_by_name["resolution"].id, 1)
        self._update_attribute(self.attributes_by_name["application_type"].id, 0 << 16)
        self._update_attribute(self.attributes_by_name["engineering_units"].id, 62)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attributes_by_name["present_value"].id, value)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attributes_by_name["present_value"].id)

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attributes_by_name[attrid].id
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)

            await BecaManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {BECA_ECO_TEMP_ATTR: value},
                manufacturer=None,
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class BecaMinTemp(LocalDataCluster, AnalogOutput):
    """Analog output for setting Min Temperature."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.BecaMinTemp_bus.add_listener(self)
        self._update_attribute(self.attributes_by_name["description"].id, "Min Temperature")
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 15)
        self._update_attribute(self.attributes_by_name["min_present_value"].id, 5)
        self._update_attribute(self.attributes_by_name["resolution"].id, 1)
        self._update_attribute(self.attributes_by_name["application_type"].id, 0 << 16)
        self._update_attribute(self.attributes_by_name["engineering_units"].id, 62)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attributes_by_name["present_value"].id, value)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attributes_by_name["present_value"].id)

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attributes_by_name[attrid].id
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)

            await BecaManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {BECA_MIN_TEMPERATURE_ATTR: value},
                manufacturer=None,
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class BecaMaxTemp(LocalDataCluster, AnalogOutput):
    """Analog output for setting Max Temperature."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.BecaMaxTemp_bus.add_listener(self)
        self._update_attribute(self.attributes_by_name["description"].id, "Max Temperature")
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 45)
        self._update_attribute(self.attributes_by_name["min_present_value"].id, 15)
        self._update_attribute(self.attributes_by_name["resolution"].id, 1)
        self._update_attribute(self.attributes_by_name["application_type"].id, 0 << 16)
        self._update_attribute(self.attributes_by_name["engineering_units"].id, 62)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attributes_by_name["present_value"].id, value)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attributes_by_name["present_value"].id)

    async def write_attributes(self, attributes, manufacturer=None):
        """Override the default Cluster write_attributes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attributes_by_name[attrid].id
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)

            await BecaManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {BECA_MAX_TEMPERATURE_ATTR: value},
                manufacturer=None,
            )
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class Beca(TuyaThermostat):
    """BECA Thermostatic radiator valve."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.BecaWindowDetection_bus = Bus()
        self.BecaWindowDetection_A2_bus = Bus()
        self.BecaChildLock_bus = Bus()
        self.BecaValveState_bus = Bus()
        self.BecaTempCalibration_bus = Bus()
        self.BecaBoostTime_bus = Bus()
        self.BecaBoostCountdown_bus = Bus()
        self.BecaEcoTemp_bus = Bus()
        self.BecaMinTemp_bus = Bus()
        self.BecaMaxTemp_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=0 input_clusters=[0, 4, 5, 61184]
        #  output_clusters=[10, 25]>
        MODELS_INFO: [
            ("_TZE200_b6wax7g0", "TS0601"),
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
                    BecaManufCluster,
                    BecaThermostat,
                    BecaUserInterface,
                    BecaWindowDetection,
                    TuyaPowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [BecaChildLock],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [BecaValveState],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [BecaWindowDetection_A2],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [BecaTempCalibration],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [BecaBoostTime],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [BecaBoostCountdown],
                OUTPUT_CLUSTERS: [],
            },
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [BecaEcoTemp],
                OUTPUT_CLUSTERS: [],
            },
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [BecaMinTemp],
                OUTPUT_CLUSTERS: [],
            },
            10: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [BecaMaxTemp],
                OUTPUT_CLUSTERS: [],
            },
        }
    }
