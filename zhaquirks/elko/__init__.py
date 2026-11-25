"""Module for Elko quirks implementations."""

from typing import Any

from zigpy.zcl import foundation
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.clusters import CustomCluster
from zhaquirks.legacy import CustomDevice

ELKO = "ELKO"


class ElkoThermostatCluster(CustomCluster, Thermostat):
    """Thermostat cluster for Elko Thermostats."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Cluster attributes."""

    def __init__(self, *args, **kwargs):
        """Init thermostat cluster."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.thermostat_bus.add_listener(self)

    def heating_active_change(self, value):
        """State update from device."""
        if value == 0:
            mode = self.RunningMode.Off
            state = self.RunningState.Idle
        else:
            mode = self.RunningMode.Heat
            state = self.RunningState.Heat_State_On

        self._update_attribute(self.attributes_by_name["running_mode"].id, mode)
        self._update_attribute(self.attributes_by_name["running_state"].id, state)


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

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Write the keypad lockout to the thermostat's child lock attribute."""
        lockout = None
        local_attrs = {}
        for record in self._write_attr_records(attributes):
            if record.attrid == self.AttributeDefs.keypad_lockout.id:
                lockout = record.value.value
            else:
                local_attrs[record.attrid] = record.value.value

        if local_attrs:
            await super().write_attributes(local_attrs, **kwargs)

        if lockout is None:
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

        child_lock = lockout != self.KeypadLockout.No_lockout
        result = await self.endpoint.thermostat.write_attributes(
            {"child_lock": child_lock}
        )
        if all(record.status == foundation.Status.SUCCESS for record in result[0]):
            # A successful write only updates the thermostat's attribute cache
            self.child_lock_change(child_lock)

        return result


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


class ElkoThermostat(CustomDevice):
    """Generic Elko Thermostat device."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.thermostat_bus = Bus()
        self.ui_bus = Bus()
        self.power_bus = Bus()
        super().__init__(*args, **kwargs)
