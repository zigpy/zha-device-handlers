"""CTM Lyng mTouch One"""
import logging

import zigpy.profiles.zha as zha
from zigpy.quirks import CustomDevice
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes, Time
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.ctm import (
    CTM,
    CtmAnalogOutputDataCluster,
    CtmDiagnosticsCluster,
    CtmOnOffDataCluster,
    CtmThermostatCluster,
)

_LOGGER = logging.getLogger(__name__)


class CtmMTouchOneCluster(CtmThermostatCluster):
    """CTM Lyng custom mTouch One cluster."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.thermostat_bus.add_listener(self)
        self.heating_demand = None
        self.last_temp = None

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        await self.configure_reporting_multiple(
            {
                "mean_power": (1, 3600, 0),
                "current_floor_temperature": (1, 1800, 0),
                "child_lock_enabled": (1, 3600, 0),
                "current_air_temperature": (1, 1800, 0),
            },
            manufacturer=None,
        )
        await self.read_attributes(
            [
                "load",
                "mean_power",
                "current_floor_temperature",
                "child_lock_enabled",
                "heating_active",
                "regulator_setpoint",
                "regulation_mode",
                "operation_mode",
                "current_air_temperature",
            ],
            manufacturer=None,
        )
        await self.endpoint.basic.read_attributes(
            [
                "app_version",
            ],
            allow_cache=True,
            manufacturer=None,
        )
        return result

    def set_running_state(self):
        """Set running_state and help keep running_state more accurate on early versions,
        which are slow to update heating_active attribute.
        """

        running_state = self.RunningState.Idle
        if self.get("heating_active", False):
            running_state = self.RunningState.Heat_State_On

        appversion = self.endpoint.basic.get("app_version", 0)
        if appversion < 65:
            if self.get("system_mode", self.SystemMode.Off) == self.SystemMode.Off:
                running_state = self.RunningState.Idle
            elif self.get("regulation_mode") == self.RegulationMode.Regulator:
                running_state = self.RunningState.Heat_State_On
            elif (setpoint := self.get("occupied_heating_setpoint")) is not None and (
                temperature := self.get("local_temperature")
            ) is not None:
                if setpoint < temperature:
                    running_state = self.RunningState.Idle
                elif setpoint > temperature:
                    running_state = self.RunningState.Heat_State_On

        if running_state != self.get("running_state"):
            super()._update_attribute(
                self.attributes_by_name["running_state"].id, running_state
            )

    async def write_regulator_setpoint(self, value):
        await self.read_attributes(
            [
                "regulation_mode",
            ],
            allow_cache=True,
            manufacturer=None,
        )
        if self.get("regulation_mode") == self.RegulationMode.Regulator:
            return await self.write_attributes(
                {"regulator_setpoint": value}, manufacturer=None
            )
        else:
            self.endpoint.device.regulator_bus.listener_event(
                "value_update", self.heating_demand
            )
            return False

    async def write_system_mode(self, value):
        value = self.SystemMode.Heat if value else self.SystemMode.Off
        return await self.write_attributes({"system_mode": value}, manufacturer=None)

    async def write_away_mode(self, value):
        value = (
            self.OperationMode.Night_Saving_Mode
            if value
            else self.OperationMode.Comfort_Mode
        )
        return await self.write_attributes({"operation_mode": value}, manufacturer=None)

    def _update_attribute(self, attrid, value):
        """Override updates to thermostat attributes."""

        _LOGGER.debug(f"Attribute update in: {self.attributes[attrid].name}: {value}")

        # Attributes not to be updated before overrides are processed
        if attrid not in (
            self.attributes_by_name["local_temperature"].id,
            self.attributes_by_name["system_mode"].id,
            self.attributes_by_name["occupied_heating_setpoint"].id,
            self.attributes_by_name["pi_heating_demand"].id,
        ):
            super()._update_attribute(attrid, value)

        # Attribute overrides
        if attrid == self.attributes_by_name["local_temperature"].id:
            """Thermostat only reports whole degrees and can be a bit bouncy in transitions,
            so let's use average of new and last temperature.
            """
            new_temp = value
            last_temp = self.last_temp if self.last_temp else new_temp
            value = int((new_temp + last_temp) / 2)
            self.last_temp = new_temp
            super()._update_attribute(
                self.attributes_by_name["local_temperature"].id, value
            )

        elif attrid == self.attributes_by_name["operation_mode"].id:
            if value in (self.OperationMode.Off, self.OperationMode.Anti_Freeze_Mode):
                system_mode = self.SystemMode.Off
                running_mode = self.RunningMode.Off
            else:
                system_mode = self.SystemMode.Heat
                running_mode = self.RunningMode.Heat

            super()._update_attribute(
                self.attributes_by_name["system_mode"].id, system_mode
            )
            super()._update_attribute(
                self.attributes_by_name["running_mode"].id, running_mode
            )
            system_mode = True if system_mode == self.SystemMode.Heat else False
            self.endpoint.device.system_mode_bus.listener_event(
                "on_off_change", system_mode
            )
            away_mode = True if value == self.OperationMode.Night_Saving_Mode else False
            self.endpoint.device.away_mode_bus.listener_event(
                "on_off_change", away_mode
            )
            self.set_running_state()

        elif attrid == self.attributes_by_name["regulator_setpoint"].id:
            if self.get("regulation_mode") != self.RegulationMode.Regulator:
                value = value * 100
            else:
                self.endpoint.device.regulator_bus.listener_event("value_update", value)
                value = None

            super()._update_attribute(
                self.attributes_by_name["occupied_heating_setpoint"].id, value
            )
            self.set_running_state()

        elif attrid == self.attributes_by_name["heating_active"].id:
            self.set_running_state()

        elif attrid == self.attributes_by_name["pi_heating_demand"].id:
            self.heating_demand = value
            if self.get("regulation_mode") != self.RegulationMode.Regulator:
                self.endpoint.device.regulator_bus.listener_event(
                    "value_update", self.heating_demand
                )

        elif attrid == self.attributes_by_name["child_lock_enabled"].id:
            self.endpoint.device.ui_bus.listener_event("child_lock_change", value)

        elif attrid == self.attributes_by_name["current_floor_temperature"].id:
            self.endpoint.device.floor_temp_bus.listener_event(
                "temperature_update", value
            )

        elif attrid == self.attributes_by_name["current_air_temperature"].id:
            self.endpoint.device.air_temp_bus.listener_event(
                "temperature_update", value
            )

        elif attrid == self.attributes_by_name["mean_power"].id:
            self.endpoint.device.power_bus.listener_event("power_reported", value)

        elif attrid == self.attributes_by_name["load"].id:
            self.endpoint.device.load_bus.listener_event("value_update", value)

    async def write_attributes(self, attributes, manufacturer=None):
        """Override writes to thermostat attributes."""

        ovrd_attr = {}
        for attr, value in attributes.items():
            if isinstance(attr, int):
                attr = self.attributes[attr].name

            if attr == "system_mode":
                if value == self.SystemMode.Off:
                    ovrd_attr["power_status"] = False
                else:
                    ovrd_attr["operation_mode"] = self.OperationMode.Comfort_Mode

            elif attr == "occupied_heating_setpoint":
                ovrd_attr["regulator_setpoint"] = int(round(value / 100))
                if self.get("operation_mode", None) != self.OperationMode.Comfort_Mode:
                    ovrd_attr["operation_mode"] = self.OperationMode.Comfort_Mode

            elif attr not in ovrd_attr:
                ovrd_attr[attr] = value

        _LOGGER.debug(f"Write attributes: {attributes} --> {ovrd_attr}")
        result = await super().write_attributes(ovrd_attr, manufacturer=manufacturer)
        _LOGGER.debug(f"Write attributes: {ovrd_attr} {result}")
        return result


class CtmUserInterfaceCluster(LocalDataCluster, UserInterface):
    """CTM Lyng custom User interface cluster."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.ui_bus.add_listener(self)

    def child_lock_change(self, enabled):
        """Enable/disable child lock."""
        if enabled:
            lockout = self.KeypadLockout.Level_1_lockout
        else:
            lockout = self.KeypadLockout.No_lockout

        self._update_attribute(self.attributes_by_name["keypad_lockout"].id, lockout)

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer the keypad_lockout attribute to child_lock."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attributes_by_name[attrid].id

            elif attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue

            self._update_attribute(attrid, value)

            if attrid == self.attributes_by_name["keypad_lockout"].id:
                enabled = False if value == self.KeypadLockout.No_lockout else True
                await self.endpoint.thermostat.write_attributes(
                    {"child_lock_enabled": enabled},
                    manufacturer=manufacturer,
                )

        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class CtmTemperatureCluster(LocalDataCluster, TemperatureMeasurement):
    """CTM Lyng custom temperature data cluster."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_attribute(self.attributes_by_name["min_measured_value"].id, 0)
        self._update_attribute(self.attributes_by_name["max_measured_value"].id, 9900)
        self.last_temp = None

    def temperature_update(self, value):
        """Thermostat only reports whole degrees and can be a bit bouncy in transitions,
        so let's use average of new and last temperature.
        """
        new_temp = value
        last_temp = self.last_temp if self.last_temp else new_temp
        value = int((new_temp + last_temp) / 2)
        self.last_temp = new_temp
        self._update_attribute(self.attributes_by_name["measured_value"].id, value)


class CtmAirTemperatureCluster(CtmTemperatureCluster):
    """CTM Lyng custom air temperature data cluster."""

    name = "Air Temperature"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.air_temp_bus.add_listener(self)


class CtmFloorTemperatureCluster(CtmTemperatureCluster):
    """CTM Lyng custom floor temperature data cluster."""

    name = "Floor Temperature"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.floor_temp_bus.add_listener(self)


class CtmElectricalMeasurementCluster(LocalDataCluster, ElectricalMeasurement):
    """CTM Lyng custom electrical measurement data cluster."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_attribute(
            self.attributes_by_name["measurement_type"].id,
            self.MeasurementType.Apparent_measurement_AC,
        )
        self._update_attribute(self.attributes_by_name["ac_power_multiplier"].id, 1)
        self._update_attribute(self.attributes_by_name["ac_power_divisor"].id, 1)
        self.endpoint.device.power_bus.add_listener(self)

    def power_reported(self, value):
        self._update_attribute(self.attributes_by_name["active_power"].id, value)


class CtmSetLoadCluster(CtmAnalogOutputDataCluster):
    """CTM Lyng custom analogOutput cluster for setting thermostat load."""

    name = "SetLoad"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.load_bus.add_listener(self)
        self._update_attribute(self.attributes_by_name["description"].id, "Load")
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 3600)
        self._update_attribute(self.attributes_by_name["min_present_value"].id, 0)
        self._update_attribute(self.attributes_by_name["resolution"].id, 1)
        self._update_attribute(
            self.attributes_by_name["application_type"].id, 0x0009FFFF
        )
        self._update_attribute(self.attributes_by_name["engineering_units"].id, 47)

    async def write_output_value(self, value):
        return await self.endpoint.thermostat.write_attributes(
            {"load": int(value)},
            manufacturer=None,
        )


class CtmRegulatorSetPointCluster(CtmAnalogOutputDataCluster):
    """CTM Lyng custom level cluster for setting setpoint in regulator mode."""

    name = "RegulatorSetPoint"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.regulator_bus.add_listener(self)
        self._update_attribute(
            self.attributes_by_name["description"].id, "Regulator SetPoint"
        )
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 99)
        self._update_attribute(self.attributes_by_name["min_present_value"].id, 1)
        self._update_attribute(self.attributes_by_name["resolution"].id, 1)
        self._update_attribute(
            self.attributes_by_name["application_type"].id, 0x0004FFFF
        )
        self._update_attribute(self.attributes_by_name["engineering_units"].id, 98)

    async def write_output_value(self, value):
        return await self.endpoint.device.thermostat_bus.async_event(
            "write_regulator_setpoint", int(value)
        )


class CtmSystemModeCluster(CtmOnOffDataCluster):
    """CTM Lyng custom onoff cluster for setting system mode."""

    name = "System Mode"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.system_mode_bus.add_listener(self)

    async def write_on_off(self, value):
        return await self.endpoint.device.thermostat_bus.async_event(
            "write_system_mode", value
        )


class CtmAwayModeCluster(CtmOnOffDataCluster):
    """CTM Lyng custom onoff cluster for setting away mode."""

    name = "Away Mode"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.away_mode_bus.add_listener(self)

    async def write_on_off(self, value):
        return await self.endpoint.device.thermostat_bus.async_event(
            "write_away_mode", value
        )


class CtmLyngMTouchOne(CustomDevice):
    """CTM Lyng custom device mtouch one."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.thermostat_bus = Bus()
        self.ui_bus = Bus()
        self.air_temp_bus = Bus()
        self.floor_temp_bus = Bus()
        self.power_bus = Bus()
        self.load_bus = Bus()
        self.regulator_bus = Bus()
        self.away_mode_bus = Bus()
        self.system_mode_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(CTM, "mTouch One")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=769
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6, 513, 4096, 65261]
            # output_clusters=[3, 10, 25, 1026]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Thermostat.cluster_id,
                    LightLink.cluster_id,
                    CtmDiagnosticsCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                    TemperatureMeasurement.cluster_id,
                ],
            },
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
                    CtmSystemModeCluster,
                    CtmMTouchOneCluster,
                    LightLink.cluster_id,
                    CtmDiagnosticsCluster,
                    CtmUserInterfaceCluster,
                    CtmAirTemperatureCluster,
                    CtmElectricalMeasurementCluster,
                    CtmSetLoadCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                    TemperatureMeasurement.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    CtmFloorTemperatureCluster,
                    CtmRegulatorSetPointCluster,
                    CtmAwayModeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
