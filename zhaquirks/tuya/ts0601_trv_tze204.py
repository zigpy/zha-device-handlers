from typing import Optional, Union

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    AnalogOutput,
    Basic,
    Groups,
    OnOff,
    Ota,
    Scenes,
    Time,
)

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
    TUYA_DP_TYPE_BOOL,
    TUYA_DP_TYPE_ENUM,
    TUYA_DP_TYPE_FAULT,
    TUYA_DP_TYPE_VALUE,
    TuyaManufClusterAttributes,
    TuyaPowerConfigurationCluster2AA,
    TuyaThermostat,
    TuyaThermostatCluster,
    TuyaUserInterfaceCluster,
)

PCDM_PRESET = TUYA_DP_TYPE_ENUM + 2
PCDM_TARGET_TEMP_ATTR = TUYA_DP_TYPE_VALUE + 4
PCDM_TEMPERATURE_ATTR = TUYA_DP_TYPE_VALUE + 5
PCDM_BATTERY_ATTR = TUYA_DP_TYPE_VALUE + 6
PCDM_CHILD_LOCK_ATTR = TUYA_DP_TYPE_BOOL + 7
PCDM_WINDOW_MODE_ATTR = TUYA_DP_TYPE_BOOL + 14
PCDM_BATTERY_LOW_ATTR = TUYA_DP_TYPE_FAULT + 35
PCDM_TEMPERATURE_CORRECTION_ATTR = TUYA_DP_TYPE_VALUE + 47
PCDM_SYSTEM_MODE_ATTR = TUYA_DP_TYPE_ENUM + 49
PCDM_TARGET_MANUAL_ATTR = TUYA_DP_TYPE_VALUE + 4
PCDM_TARGET_HOLIDAY_ATTR = TUYA_DP_TYPE_VALUE + 21
PCDM_TARGET_CONFORT_ATTR = TUYA_DP_TYPE_VALUE + 24
PCDM_TARGET_ECO_ATTR = TUYA_DP_TYPE_VALUE + 25
PCDM_FROST_PROTECT = TUYA_DP_TYPE_BOOL + 36
PCDM_BOOST_MODE = TUYA_DP_TYPE_BOOL + 37

PcdmManuClusterSelf = None


class PcdmManufTrvCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of some thermostatic valves."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        global PcdmManuClusterSelf
        PcdmManuClusterSelf = self

    set_time_offset = 1970

    attributes = TuyaManufClusterAttributes.attributes.copy()
    attributes.update(
        {
            PCDM_PRESET: ("operation_preset", t.uint8_t, True),
            PCDM_BATTERY_ATTR: ("battery", t.uint32_t, True),
            PCDM_BATTERY_LOW_ATTR: ("battery_low", t.uint8_t, True),
            PCDM_BOOST_MODE: ("boost_duration_seconds", t.uint8_t, True),
            PCDM_CHILD_LOCK_ATTR: ("child_lock", t.uint8_t, True),
            PCDM_FROST_PROTECT: ("frost_protection", t.uint8_t, True),
            PCDM_WINDOW_MODE_ATTR: ("window_detection", t.uint8_t, True),
            PCDM_SYSTEM_MODE_ATTR: ("system_mode", t.uint8_t, True),
            PCDM_TARGET_TEMP_ATTR: ("target_temperature", t.uint32_t, True),
            PCDM_TEMPERATURE_ATTR: ("temperature", t.uint32_t, True),
            PCDM_TEMPERATURE_CORRECTION_ATTR: (
                "temperature_calibration",
                t.int32s,
                True,
            ),
            PCDM_TARGET_MANUAL_ATTR: ("occupied_heating_setpoint", t.uint32_t, True),
            PCDM_TARGET_CONFORT_ATTR: ("comfort_heating_setpoint", t.uint32_t, True),
            PCDM_TARGET_ECO_ATTR: ("eco_heating_setpoint", t.uint32_t, True),
        }
    )

    TEMPERATURE_ATTRS = {
        PCDM_TARGET_TEMP_ATTR: "occupied_heating_setpoint",
        PCDM_TARGET_CONFORT_ATTR: "comfort_heating_setpoint",
        PCDM_TARGET_ECO_ATTR: "eco_heating_setpoint",
        PCDM_TEMPERATURE_ATTR: "local_temperature",
    }

    async def write_attributes(self, attributes, manufacturer=None):
        return await super().write_attributes(
            attributes, manufacturer=foundation.ZCLHeader.NO_MANUFACTURER_ID
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid in self.TEMPERATURE_ATTRS:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                self.TEMPERATURE_ATTRS[attrid],
                value * 10,  # decidegree to centidegree
            )
        elif attrid == PCDM_BATTERY_ATTR:
            self.endpoint.device.battery_bus.listener_event("battery_change", value)
        elif attrid == PCDM_BATTERY_LOW_ATTR and value > 0:
            self.endpoint.device.battery_bus.listener_event("battery_change", 5)
        elif attrid == PCDM_BOOST_MODE:
            self.endpoint.device.boost_bus.listener_event(
                "set_change", 1 if value > 0 else 0
            )
        elif attrid == PCDM_CHILD_LOCK_ATTR:
            self.endpoint.device.ui_bus.listener_event(
                "child_lock_change", 1 if value > 0 else 0
            )
        elif attrid == PCDM_WINDOW_MODE_ATTR:
            self.endpoint.device.window_detection_bus.listener_event("set_value", value)
        elif attrid == PCDM_PRESET:
            self.endpoint.device.thermostat_bus.listener_event("program_change", value)
        elif attrid == PCDM_FROST_PROTECT and value == 1:
            self.endpoint.device.thermostat_bus.listener_event("program_change", 5)
        elif attrid == PCDM_SYSTEM_MODE_ATTR:
            self.endpoint.device.thermostat_bus.listener_event("mode_change", value)
        elif attrid == PCDM_TEMPERATURE_CORRECTION_ATTR:
            self.endpoint.device.temperature_calibration_bus.listener_event(
                "set_value", value
            )


class PcdmTemperatureOffset(LocalDataCluster, AnalogOutput):
    """AnalogOutput cluster for setting temperature offset."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.temperature_calibration_bus.add_listener(self)
        self._update_attribute(
            self.attributes_by_name["description"].id, "Temperature Offset"
        )
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 12)
        self._update_attribute(self.attributes_by_name["min_present_value"].id, -12)
        self._update_attribute(self.attributes_by_name["resolution"].id, 1)
        self._update_attribute(self.attributes_by_name["application_type"].id, 0x0009)
        self._update_attribute(self.attributes_by_name["engineering_units"].id, 62)

    def set_value(self, value):  # is this useful?
        """Set new temperature offset value."""
        self._update_attribute(self.attributes_by_name["present_value"].id, value)

    def get_value(self):  # is this useful?
        """Get current temperature offset value."""
        return self._attr_cache.get(self.attributes_by_name["present_value"].id)

    async def write_attributes(self, attributes, manufacturer=None):
        """Modify value before passing it to the set_data tuya command."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attributes_by_name[attrid].id
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            intValue = str(int(float(value)))  # remove any decimal part
            self._update_attribute(attrid, intValue)

            if attrid == 0x0055:  # `present_value`
                await PcdmManuClusterSelf.endpoint.tuya_manufacturer.write_attributes(
                    {PCDM_TEMPERATURE_CORRECTION_ATTR: intValue}, manufacturer=None
                )

        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class PcdmThermostat(TuyaThermostatCluster):
    """Thermostat cluster for some thermostatic valves."""

    class Preset(t.enum8):
        """Working modes of the thermostat."""

        Schedule = 0x00
        Away = 0x01
        Manual = 0x02
        Comfort = 0x03
        Eco = 0x04
        FrostProtect = 0x05

    attributes = TuyaThermostatCluster.attributes.copy()
    attributes.update(
        {
            PCDM_PRESET: ("operation_preset", Preset, True),
        }
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.thermostat_bus.listener_event(
            "temperature_change", "min_heat_setpoint_limit", 500
        )
        self.endpoint.device.thermostat_bus.listener_event(
            "temperature_change", "max_heat_setpoint_limit", 4500
        )

    def map_attribute(self, attribute, value):
        if attribute == "occupied_heating_setpoint":
            # centidegree to decidegree
            return {PCDM_TARGET_TEMP_ATTR: round(value / 10)}
        if attribute == "local_temperature":
            # centidegree to decidegree
            return {PCDM_TEMPERATURE_ATTR: round(value / 10)}
        if attribute == "local_temperature_calibration":
            # centidegree to decidegree
            return {PCDM_TEMPERATURE_CORRECTION_ATTR: round(value / 10)}
        if attribute == "system_mode":
            if value == self.SystemMode.Off:
                return {PCDM_SYSTEM_MODE_ATTR: 0}
            if value == self.SystemMode.Heat:
                return {PCDM_SYSTEM_MODE_ATTR: 1}
            else:
                self.error("Unsupported value for SystemMode")
        if attribute == "programing_oper_mode":
            if value == self.ProgrammingOperationMode.Schedule_programming_mode:
                return {PCDM_PRESET: self.Preset.Schedule.value}
            if value == self.ProgrammingOperationMode.Simple:
                return {PCDM_PRESET: self.Preset.Manual.value}
            if value == self.ProgrammingOperationMode.Economy_mode:
                return {PCDM_PRESET: self.Preset.Eco.value}
        if attribute == "operation_preset":
            if value == self.Preset.FrostProtect:
                return {PCDM_FROST_PROTECT: 1}
            return {PCDM_PRESET: value.value}

    def mode_change(self, value):
        """System Mode change."""
        self._update_attribute(
            self.attributes_by_name["system_mode"].id, self.SystemMode.Heat
        )
        if value == 0:
            mode = self.RunningMode.Off
            state = self.RunningState.Idle
        else:
            mode = self.RunningMode.Heat
            state = self.RunningState.Heat_State_On
        self._update_attribute(self.attributes_by_name["running_mode"].id, mode)
        self._update_attribute(self.attributes_by_name["running_state"].id, state)

    def program_change(self, value):
        """Programming mode change."""
        operation_preset = None
        prog_mode = None
        if value == 0:
            prog_mode = self.ProgrammingOperationMode.Schedule_programming_mode
            operation_preset = self.Preset.Schedule
        elif value == 1:
            prog_mode = self.ProgrammingOperationMode.Simple
            operation_preset = self.Preset.Away
        elif value == 2:
            prog_mode = self.ProgrammingOperationMode.Simple
            operation_preset = self.Preset.Manual
        elif value == 3:
            prog_mode = self.ProgrammingOperationMode.Simple
            operation_preset = self.Preset.Comfort
        elif value == 4:
            prog_mode = self.ProgrammingOperationMode.Economy_mode
            operation_preset = self.Preset.Eco
        elif value == 5:
            operation_preset = self.Preset.FrostProtect
        else:
            self.error("Unsupported value for Mode")

        if prog_mode is not None:
            self._update_attribute(
                self.attributes_by_name["programing_oper_mode"].id, prog_mode
            )
            self._update_attribute(
                self.attributes_by_name["system_mode"].id, self.SystemMode.Heat
            )

        if operation_preset is not None:
            self._update_attribute(
                self.attributes_by_name["operation_preset"].id, operation_preset
            )


class PcdmUserInterface(TuyaUserInterfaceCluster):
    """HVAC User interface cluster for tuya electric heating thermostats."""

    _CHILD_LOCK_ATTR = PCDM_CHILD_LOCK_ATTR


class PcdmHelperOnOff(LocalDataCluster, OnOff):
    """Helper OnOff cluster for various functions controlled by switch."""

    def set_change(self, value):
        """Set new OnOff value."""
        self._update_attribute(self.attributes_by_name["on_off"].id, value)

    def get_attr_val_to_write(self, value):
        """Return dict with attribute and value for thermostat."""
        return None

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
            attr_val = self.get_attr_val_to_write(value)
            if attr_val is not None:
                # global self in case when different endpoint has to exist
                return await PcdmManuClusterSelf.endpoint.tuya_manufacturer.write_attributes(
                    attr_val, manufacturer=manufacturer
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
                    return foundation.GENERAL_COMMANDS[
                        foundation.GeneralCommand.Default_Response
                    ].schema(command_id=command_id, status=foundation.Status.FAILURE)
                value = not value
            (res,) = await self.write_attributes(
                {"on_off": value},
                manufacturer=manufacturer,
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)

        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND)


class PcdmBoost(PcdmHelperOnOff):
    """On/Off cluster for the boost function of the heating thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.boost_bus.add_listener(self)

    def get_attr_val_to_write(self, value):
        """Return dict with attribute and value for boot mode."""
        return {PCDM_BOOST_MODE: 1 if value else 0}


class PcdmWindowDetection(PcdmHelperOnOff):
    """On/Off cluster for the window detection function of the heating thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.window_detection_bus.add_listener(self)

    def get_attr_val_to_write(self, value):
        """Return dict with attribute and value for boot mode."""
        return {PCDM_WINDOW_MODE_ATTR: 1 if value else 0}


class PcdmTrv(TuyaThermostat):
    """PCDRM Thermostatic radiator valve"""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.boost_bus = Bus()
        self.temperature_calibration_bus = Bus()
        self.window_detection_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=0 input_clusters=[0, 4, 5, 61184]
        #  output_clusters=[10, 25]>
        MODELS_INFO: [
            ("_TZE204_pcdmj88b", "TS0601"),
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
                    PcdmManufTrvCluster,
                    PcdmBoost,
                    PcdmTemperatureOffset,
                    PcdmThermostat,
                    PcdmUserInterface,
                    TuyaPowerConfigurationCluster2AA,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COMBINED_INTERFACE,
                INPUT_CLUSTERS: [
                    PcdmWindowDetection,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }
