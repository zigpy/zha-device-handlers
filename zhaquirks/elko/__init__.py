"""Module for Elko quirks implementations."""

from zigpy.quirks.v2 import CustomDeviceV2
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.hvac import UserInterface

from zhaquirks import Bus, LocalDataCluster

ELKO = "ELKO"


class ElkoUserInterfaceCluster(LocalDataCluster, UserInterface):
    """User interface cluster for Elko Thermostats."""

    def __init__(self, *args, **kwargs):
        """Init UI cluster."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.ui_bus.add_listener(self)

    def child_lock_change(self, mode):
        """Enable/disable child lock."""
        if mode:
            lockout = self.KeypadLockout.Level_1_lockout
        else:
            lockout = self.KeypadLockout.No_lockout

        self._update_attribute(self.attributes_by_name["keypad_lockout"].id, lockout)


class ElkoElectricalMeasurementCluster(LocalDataCluster, ElectricalMeasurement):
    """Electrical measurement cluster for Elko Thermostats."""

    ACTIVE_POWER_ID = 0x050B

    def __init__(self, *args, **kwargs):
        """Init electrical measurement cluster."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.power_bus.add_listener(self)

    def power_reported(self, value):
        """Report consumption."""
        self._update_attribute(self.ACTIVE_POWER_ID, value)


class ElkoThermostat(CustomDeviceV2):
    """Generic Elko Thermostat device."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.thermostat_bus = Bus()
        self.ui_bus = Bus()
        self.power_bus = Bus()
        super().__init__(*args, **kwargs)
