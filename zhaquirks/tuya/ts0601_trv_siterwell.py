"""Map from manufacturer to standard clusters for thermostatic valves."""
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

# info from https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/common.js#L113
# and https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/fromZigbee.js#L362
SITERWELL_CHILD_LOCK_ATTR = 0x0107  # [0] unlocked [1] child-locked
SITERWELL_WINDOW_DETECT_ATTR = 0x0112  # [0] inactive [1] active
SITERWELL_VALVE_DETECT_ATTR = 0x0114  # [0] do not report [1] report
# [0,0,0,210] target room temp (decidegree)
SITERWELL_TARGET_TEMP_ATTR = 0x0202
# [0,0,0,200] current room temp (decidegree)
SITERWELL_TEMPERATURE_ATTR = 0x0203
SITERWELL_BATTERY_ATTR = 0x0215  # [0,0,0,98] battery charge
# [0] off [1] scheduled [2] manual [3] installation
SITERWELL_MODE_ATTR = 0x0404
SITERWELL_WINDOW_ALARM_ATTR = 0x0411  # [0] off [1] on
SITERWELL_VALVE_JAMMED_ALARM_ATTR = 0x0413  # [0] off [1] pn
# minimum limit of temperature setting
SITERWELL_MIN_TEMPERATURE_VAL = 5  # degrees
# maximum limit of temperature setting
SITERWELL_MAX_TEMPERATURE_VAL = 30  # degrees
SiterwellManufClusterSelf = {}


class SiterwellManufCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of some thermostatic valves."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.SiterwellManufCluster_bus.add_listener(self)
        global SiterwellManufClusterSelf
        SiterwellManufClusterSelf[self.endpoint.device.ieee] = self

    manufacturer_attributes = {
        SITERWELL_CHILD_LOCK_ATTR: ("child_lock", t.uint8_t),
        SITERWELL_WINDOW_DETECT_ATTR: ("window_detection", t.uint8_t),
        SITERWELL_VALVE_DETECT_ATTR: ("valve_detect", t.uint8_t),
        SITERWELL_TARGET_TEMP_ATTR: ("target_temperature", t.uint32_t),
        SITERWELL_TEMPERATURE_ATTR: ("temperature", t.uint32_t),
        SITERWELL_BATTERY_ATTR: ("battery", t.uint32_t),
        SITERWELL_MODE_ATTR: ("mode", t.uint8_t),
        SITERWELL_WINDOW_ALARM_ATTR: ("window_alarm", t.uint8_t),
        SITERWELL_VALVE_JAMMED_ALARM_ATTR: ("window_alarm", t.uint8_t),
    }

    TEMPERATURE_ATTRS = {
        SITERWELL_TARGET_TEMP_ATTR: (
            "occupied_heating_setpoint",
            lambda value: value * 10,
        ),
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)

        if attrid in self.TEMPERATURE_ATTRS:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                self.TEMPERATURE_ATTRS[attrid][0],
                value
                if self.TEMPERATURE_ATTRS[attrid][1] is None
                else self.TEMPERATURE_ATTRS[attrid][1](value),
            )
        elif attrid == SITERWELL_BATTERY_ATTR:
            self.endpoint.device.battery_bus.listener_event("battery_change", value)
        elif attrid == SITERWELL_WINDOW_DETECT_ATTR:
            self.endpoint.device.SiterwellWindowDetection_bus.listener_event(
                "window_detect_change", value
            )
        elif attrid == SITERWELL_WINDOW_ALARM_ATTR:
            self.endpoint.device.SiterwellWindowAlarm_bus.listener_event(
                "set_value", value
            )
        elif attrid == SITERWELL_MODE_ATTR:
            if 0 <= value <= 2:
                self.endpoint.device.thermostat_bus.listener_event("mode_change", value)
            self.endpoint.device.SiterwellInstallMode_bus.listener_event(
                "onoff_change", value
            )
        elif attrid == SITERWELL_VALVE_DETECT_ATTR:
            self.endpoint.device.SiterwellValveDetection_bus.listener_event(
                "valve_detect_change", value
            )
        elif attrid == SITERWELL_VALVE_JAMMED_ALARM_ATTR:
            self.endpoint.device.SiterwellValveAlarm_bus.listener_event(
                "set_value", value
            )
        elif attrid == SITERWELL_CHILD_LOCK_ATTR:
            mode = 1 if value else 0
            self.endpoint.device.ui_bus.listener_event("child_lock_change", mode)
            self.endpoint.device.SiterwellChildLock_bus.listener_event(
                "child_lock_change", mode
            )

        if attrid in (SITERWELL_TEMPERATURE_ATTR, SITERWELL_TARGET_TEMP_ATTR):
            if attrid == SITERWELL_TEMPERATURE_ATTR:
                temp_calibration = (
                    self.endpoint.device.SiterwellTempCalibration_bus.listener_event(
                        "get_value"
                    )[0]
                )
                self.endpoint.device.thermostat_bus.listener_event(
                    "temperature_change",
                    "local_temp",
                    (value + temp_calibration * 10) * 10,
                )
                self.endpoint.device.thermostat_bus.listener_event(
                    "hass_climate_state_change", attrid, value + temp_calibration * 10
                )
            else:
                self.endpoint.device.thermostat_bus.listener_event(
                    "hass_climate_state_change", attrid, value
                )


class SiterwellThermostat(TuyaThermostatCluster):
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
    }

    manufacturer_attributes = {
        0x4000: ("operation_preset", Preset),
    }

    DIRECT_MAPPING_ATTRS = {
        "occupied_heating_setpoint": (
            SITERWELL_TARGET_TEMP_ATTR,
            lambda value: round(value / 10),
        ),
        "operation_preset": (SITERWELL_MODE_ATTR, None),
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.thermostat_bus.add_listener(self)
        self.endpoint.device.thermostat_bus.listener_event(
            "temperature_change",
            "min_heat_setpoint_limit",
            SITERWELL_MIN_TEMPERATURE_VAL * 100,
        )
        self.endpoint.device.thermostat_bus.listener_event(
            "temperature_change",
            "max_heat_setpoint_limit",
            SITERWELL_MAX_TEMPERATURE_VAL * 100,
        )

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""

        if attribute in self.DIRECT_MAPPING_ATTRS:
            return {
                self.DIRECT_MAPPING_ATTRS[attribute][0]: value
                if self.DIRECT_MAPPING_ATTRS[attribute][1] is None
                else self.DIRECT_MAPPING_ATTRS[attribute][1](value)
            }

        if attribute in ("system_mode", "programing_oper_mode"):
            if attribute == "system_mode":
                system_mode = value
                oper_mode = self._attr_cache.get(
                    self.attridx["programing_oper_mode"],
                    self.ProgrammingOperationMode.Simple,
                )
            else:
                system_mode = self._attr_cache.get(
                    self.attridx["system_mode"], self.SystemMode.Heat
                )
                oper_mode = value
            if system_mode == self.SystemMode.Off:
                return {SITERWELL_MODE_ATTR: 0}
            if system_mode == self.SystemMode.Heat:
                if oper_mode == self.ProgrammingOperationMode.Schedule_programming_mode:
                    return {SITERWELL_MODE_ATTR: 1}
                if oper_mode == self.ProgrammingOperationMode.Simple:
                    return {SITERWELL_MODE_ATTR: 2}
                self.error("Unsupported value for ProgrammingOperationMode")
            else:
                self.error("Unsupported value for SystemMode")

    def hass_climate_state_change(self, attrid, value):
        """Update of the HASS Climate gui state."""
        if attrid == SITERWELL_TEMPERATURE_ATTR:
            temp_current = value * 10
            temp_set = self._attr_cache.get(self.attridx["occupied_heating_setpoint"])
        else:
            temp_set = value * 10
            temp_current = self._attr_cache.get(self.attridx["local_temp"])

        state = 0 if (int(temp_current) >= int(temp_set)) else 1
        self.endpoint.device.thermostat_bus.listener_event("state_change", state)

    def mode_change(self, value):
        """System Mode change."""
        if value == 0:
            operation_preset = self.Preset.Away
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Unoccupied
            system_mode = self.SystemMode.Off
            target_temp = self._attr_cache.get(
                self.attridx["occupied_heating_setpoint"]
            )
            self._update_attribute(
                self.attridx["unoccupied_heating_setpoint"], target_temp
            )
        elif value == 1:
            operation_preset = self.Preset.Schedule
            prog_mode = self.ProgrammingOperationMode.Schedule_programming_mode
            occupancy = self.Occupancy.Occupied
            system_mode = self.SystemMode.Heat
        elif value == 2:
            operation_preset = self.Preset.Manual
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Occupied
            system_mode = self.SystemMode.Heat

        self._update_attribute(self.attridx["system_mode"], system_mode)
        self._update_attribute(self.attridx["programing_oper_mode"], prog_mode)
        self._update_attribute(self.attridx["occupancy"], occupancy)
        self._update_attribute(self.attridx["operation_preset"], operation_preset)


class SiterwellUserInterface(TuyaUserInterfaceCluster):
    """HVAC User interface cluster for tuya electric heating thermostats."""

    _CHILD_LOCK_ATTR = SITERWELL_CHILD_LOCK_ATTR


class SiterwellWindowDetection(LocalDataCluster, OnOff):
    """On/Off cluster for the window detection function of the electric heating thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.SiterwellWindowDetection_bus.add_listener(self)

    def window_detect_change(self, value):
        """Window detect change."""
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
            return await self.endpoint.tuya_manufacturer.write_attributes(
                {SITERWELL_WINDOW_DETECT_ATTR: value}, manufacturer=manufacturer
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


class SiterwellValveDetection(LocalDataCluster, OnOff):
    """On/Off cluster for the valve detection function of the electric heating thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.SiterwellValveDetection_bus.add_listener(self)

    def valve_detect_change(self, value):
        """Window detect change."""
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
            return await SiterwellManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {SITERWELL_VALVE_DETECT_ATTR: value}, manufacturer=manufacturer
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


class SiterwellWindowAlarm(LocalDataCluster, BinaryInput):
    """Binary cluster for the window alarm function of the electric heating thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.SiterwellWindowAlarm_bus.add_listener(self)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value)


class SiterwellValveAlarm(LocalDataCluster, BinaryInput):
    """Binary cluster for the valve alarm function of the electric heating thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.SiterwellValveAlarm_bus.add_listener(self)

    def set_value(self, value):
        """Set value."""
        self._update_attribute(self.attridx["present_value"], value)


class SiterwellChildLock(LocalDataCluster, OnOff):
    """On/Off cluster for the child lock function of the electric heating thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.SiterwellChildLock_bus.add_listener(self)

    def child_lock_change(self, value):
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
            return await SiterwellManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {SITERWELL_CHILD_LOCK_ATTR: value}, manufacturer=manufacturer
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


class SiterwellInstallMode(LocalDataCluster, OnOff):
    """On/Off cluster for the install mode function of the electric heating thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.SiterwellInstallMode_bus.add_listener(self)

    def onoff_change(self, value):
        """Switch change for Installation mode."""
        if 0 <= value <= 2:
            self._update_attribute(self.attridx["on_off"], False)
        else:
            self._update_attribute(self.attridx["on_off"], True)

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
                mode = 1 if value is False else 3
                has_change = True

        if has_change:
            return await SiterwellManufClusterSelf[
                self.endpoint.device.ieee
            ].endpoint.tuya_manufacturer.write_attributes(
                {SITERWELL_MODE_ATTR: mode}, manufacturer=manufacturer
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


class SiterwellTempCalibration(LocalDataCluster, AnalogOutput):
    """AnalogOutput cluster for the local temperature calibration."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.SiterwellTempCalibration_bus.add_listener(self)
        self._update_attribute(self.attridx["description"], "Temperature Calibration")
        self._update_attribute(self.attridx["max_present_value"], 10)
        self._update_attribute(self.attridx["min_present_value"], -10)
        self._update_attribute(self.attridx["resolution"], 0.1)
        self._update_attribute(self.attridx["application_type"], 13 << 16)
        self._update_attribute(self.attridx["engineering_units"], 62)

    def get_value(self):
        """Get value."""
        return self._attr_cache.get(self.attridx["present_value"])


class SiterwellGS361_Type1(TuyaThermostat):
    """SiterwellGS361 Thermostatic radiator valve and clones."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.SiterwellManufCluster_bus = Bus()
        self.SiterwellWindowDetection_bus = Bus()
        self.SiterwellValveDetection_bus = Bus()
        self.SiterwellWindowAlarm_bus = Bus()
        self.SiterwellValveAlarm_bus = Bus()
        self.SiterwellChildLock_bus = Bus()
        self.SiterwellInstallMode_bus = Bus()
        self.SiterwellTempCalibration_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  endpoint=1 profile=260 device_type=0 device_version=0 input_clusters=[0, 3]
        #  output_clusters=[3, 25]>
        MODELS_INFO: [
            ("_TYST11_jeaxp72v", "eaxp72v"),
            ("_TYST11_kfvq6avy", "fvq6avy"),
            ("_TYST11_zivfvd7h", "ivfvd7h"),
            ("_TYST11_hhrtiq0x", "hrtiq0x"),
            ("_TYST11_ps5v5jor", "s5v5jor"),
            ("_TYST11_owwdxjbx", "wwdxjbx"),
            ("_TYST11_8daqwrsj", "daqwrsj"),
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
                    SiterwellManufCluster,
                    SiterwellThermostat,
                    SiterwellUserInterface,
                    SiterwellWindowDetection,
                    TuyaPowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    SiterwellValveDetection,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SIMPLE_SENSOR,
                INPUT_CLUSTERS: [
                    SiterwellWindowAlarm,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SIMPLE_SENSOR,
                INPUT_CLUSTERS: [
                    SiterwellValveAlarm,
                ],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    SiterwellChildLock,
                ],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    SiterwellInstallMode,
                ],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [SiterwellTempCalibration],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class SiterwellGS361_Type2(TuyaThermostat):
    """SiterwellGS361 Thermostatic radiator valve and clones (2nd cluster signature)."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.SiterwellManufCluster_bus = Bus()
        self.SiterwellWindowDetection_bus = Bus()
        self.SiterwellValveDetection_bus = Bus()
        self.SiterwellWindowAlarm_bus = Bus()
        self.SiterwellValveAlarm_bus = Bus()
        self.SiterwellChildLock_bus = Bus()
        self.SiterwellInstallMode_bus = Bus()
        self.SiterwellTempCalibration_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=0 input_clusters=[0, 4, 5, 61184]
        #  output_clusters=[10, 25]>
        MODELS_INFO: [
            ("_TZE200_jeaxp72v", "TS0601"),
            ("_TZE200_kfvq6avy", "TS0601"),
            ("_TZE200_zivfvd7h", "TS0601"),
            ("_TZE200_hhrtiq0x", "TS0601"),
            ("_TZE200_ps5v5jor", "TS0601"),
            ("_TZE200_owwdxjbx", "TS0601"),
            ("_TZE200_8daqwrsj", "TS0601"),
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
                    SiterwellManufCluster,
                    SiterwellThermostat,
                    SiterwellUserInterface,
                    SiterwellWindowDetection,
                    TuyaPowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    SiterwellValveDetection,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SIMPLE_SENSOR,
                INPUT_CLUSTERS: [
                    SiterwellWindowAlarm,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SIMPLE_SENSOR,
                INPUT_CLUSTERS: [
                    SiterwellValveAlarm,
                ],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    SiterwellChildLock,
                ],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    SiterwellInstallMode,
                ],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [SiterwellTempCalibration],
                OUTPUT_CLUSTERS: [],
            },
        }
    }
