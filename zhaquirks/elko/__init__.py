"""Module for Elko quirks implementations."""
import logging

from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.quirks import CustomCluster, CustomDevice
from zhaquirks import Bus, LocalDataCluster


ELKO = "ELKO"
MANUFACTURER = 0x1002  # 4098


class ElkoThermostatCluster(CustomCluster, Thermostat):
    """Thermostat cluster for Elko Thermostats"""

    def __init__(self, *args, **kwargs):
        """Init thermostat cluster"""
        super().__init__(*args, **kwargs)
        self.endpoint.device.thermostat_bus.add_listener(self)

    def heating_active_change(self, value):
        """State update from device"""
        if value == 0:
            mode = self.RunningMode.Off
            state = self.RunningState.Idle
        else:
            mode = self.RunningMode.Heat
            state = self.RunningState.Heat_State_On

        self._update_attribute(self.attridx["running_mode"], mode)
        self._update_attribute(self.attridx["running_state"], state)


class ElkoUserInterfaceCluster(LocalDataCluster, UserInterface):
    """User interface cluster for Elko Thermostats"""

    def __init__(self, *args, **kwargs):
        """Init UI cluster"""
        super().__init__(*args, **kwargs)
        self.endpoint.device.ui_bus.add_listener(self)

    def child_lock_change(self, mode):
        """Enable/disable child lock"""
        if mode:
            lockout = self.KeypadLockout.Level_1_lockout
        else:
            lockout = self.KeypadLockout.No_lockout

        self._update_attribute(self.attridx["keypad_lockout"], lockout)


class ElkoThermostat(CustomDevice):
    """Generic Elko Thermostat device"""

    def __init__(self, *args, **kwargs):
        """Init device"""
        self.thermostat_bus = Bus()
        self.ui_bus = Bus()
        super().__init__(*args, **kwargs)
