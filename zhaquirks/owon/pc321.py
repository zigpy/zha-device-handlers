"""QUIRK FOR OWON PC321 (non-Tuya version)."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.owon import OWON

OWON_PC321 = "PC321"
OWON_PC321_CLUSTER_ID = 0xFD32

"""Owon PC321 Attributes"""

# Consumption
OWON_METERING_ENERGY_CONSUMPTION_PH_A_ATTR = 0x4000
OWON_METERING_ENERGY_CONSUMPTION_PH_B_ATTR = 0x4001
OWON_METERING_ENERGY_CONSUMPTION_PH_C_ATTR = 0x4002
OWON_METERING_TOTAL_ENERGY_CONSUMPTION_ATTR = 0x0000
# Active power
OWON_METERING_ACTIVE_POWER_PH_A_ATTR = 0x2000
OWON_METERING_ACTIVE_POWER_PH_B_ATTR = 0x2001
OWON_METERING_ACTIVE_POWER_PH_C_ATTR = 0x2002
OWON_METERING_TOTAL_ACTIVE_POWER_ATTR = 0x0400
# Reactive power
OWON_METERING_REACTIVE_POWER_PH_A_ATTR = 0x2100
OWON_METERING_REACTIVE_POWER_PH_B_ATTR = 0x2101
OWON_METERING_REACTIVE_POWER_PH_C_ATTR = 0x2102
OWON_METERING_TOTAL_REACTIVE_POWER_ATTR = 0x2103
# Voltage
OWON_METERING_VOLTAGE_PH_A_ATTR = 0x3000
OWON_METERING_VOLTAGE_PH_B_ATTR = 0x3001
OWON_METERING_VOLTAGE_PH_C_ATTR = 0x3002
# Active current
OWON_METERING_ACTIVE_CURRENT_PH_A_ATTR = 0x3100
OWON_METERING_ACTIVE_CURRENT_PH_B_ATTR = 0x3101
OWON_METERING_ACTIVE_CURRENT_PH_C_ATTR = 0x3102
OWON_METERING_TOTAL_ACTIVE_CURRENT_ATTR = 0x3103
# Reactive energy consumption
OWON_METERING_REACTIVE_ENERGY_CONSUMPTION_PH_A_ATTR = 0x4100
OWON_METERING_REACTIVE_ENERGY_CONSUMPTION_PH_B_ATTR = 0x4101
OWON_METERING_REACTIVE_ENERGY_CONSUMPTION_PH_C_ATTR = 0x4102
OWON_METERING_TOTAL_REACTIVE_ENERGY_CONSUMPTION_ATTR = 0x4103
# Frequency
OWON_METERING_AC_FREQUENCY_ATTR = 0x5005
# Leakage
OWON_METERING_LEAKAGE_CURRENT_ATTR = 0x3104


class OwonMetering(CustomCluster, Metering):
    """Owon non-standard Metering cluster attributes, to be mapped into bus for later use in another clusters."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)

        # Consumption
        if attrid == OWON_METERING_ENERGY_CONSUMPTION_PH_A_ATTR:
            self.endpoint.device.energy_consumption_ph_a_bus.listener_event("energy_consumption_ph_a_reported", value)
        elif attrid == OWON_METERING_ENERGY_CONSUMPTION_PH_B_ATTR:
            self.endpoint.device.energy_consumption_ph_b_bus.listener_event("energy_consumption_ph_b_reported", value)
        elif attrid == OWON_METERING_ENERGY_CONSUMPTION_PH_C_ATTR:
            self.endpoint.device.energy_consumption_ph_c_bus.listener_event("energy_consumption_ph_c_reported", value)
        elif attrid == OWON_METERING_TOTAL_ENERGY_CONSUMPTION_ATTR:
            self.endpoint.device.total_energy_consumption_bus.listener_event("total_energy_consumption_reported", value)
        # Active power
        elif attrid == OWON_METERING_ACTIVE_POWER_PH_A_ATTR:
            self.endpoint.device.active_power_bus.listener_event("active_power_reported", value)
        elif attrid == OWON_METERING_ACTIVE_POWER_PH_B_ATTR:
            self.endpoint.device.active_power_ph_b_bus.listener_event("active_power_ph_b_reported", value)
        elif attrid == OWON_METERING_ACTIVE_POWER_PH_C_ATTR:
            self.endpoint.device.active_power_ph_c_bus.listener_event("active_power_ph_c_reported", value)
        elif attrid == OWON_METERING_TOTAL_ACTIVE_POWER_ATTR:
            self.endpoint.device.total_active_power_bus.listener_event("total_active_power_reported", value)
        # Reactive power
        elif attrid == OWON_METERING_REACTIVE_POWER_PH_A_ATTR:
            self.endpoint.device.reactive_power_bus.listener_event("reactive_power_reported", value)
        elif attrid == OWON_METERING_REACTIVE_POWER_PH_B_ATTR:
            self.endpoint.device.reactive_power_ph_b_bus.listener_event("reactive_power_ph_b_reported", value)
        elif attrid == OWON_METERING_REACTIVE_POWER_PH_C_ATTR:
            self.endpoint.device.reactive_power_ph_c_bus.listener_event("reactive_power_ph_c_reported", value)
        elif attrid == OWON_METERING_TOTAL_REACTIVE_POWER_ATTR:
            self.endpoint.device.total_reactive_power_bus.listener_event("total_reactive_power_reported", value)
        # Voltage
        elif attrid == OWON_METERING_VOLTAGE_PH_A_ATTR:
            self.endpoint.device.rms_voltage_bus.listener_event("rms_voltage_reported", value)
        elif attrid == OWON_METERING_VOLTAGE_PH_B_ATTR:
            self.endpoint.device.rms_voltage_ph_b_bus.listener_event("rms_voltage_ph_b_reported", value)
        elif attrid == OWON_METERING_VOLTAGE_PH_C_ATTR:
            self.endpoint.device.rms_voltage_ph_c_bus.listener_event("rms_voltage_ph_c_reported", value)
        # Active current
        elif attrid == OWON_METERING_ACTIVE_CURRENT_PH_A_ATTR:
            self.endpoint.device.active_current_bus.listener_event("active_current_reported", value)
        elif attrid == OWON_METERING_ACTIVE_CURRENT_PH_B_ATTR:
            self.endpoint.device.active_current_ph_b_bus.listener_event("active_current_ph_b_reported", value)
        elif attrid == OWON_METERING_ACTIVE_CURRENT_PH_C_ATTR:
            self.endpoint.device.active_current_ph_c_bus.listener_event("active_current_ph_c_reported", value)
        elif attrid == OWON_METERING_TOTAL_ACTIVE_CURRENT_ATTR:
            self.endpoint.device.instantaneous_active_current_bus.listener_event("instantaneous_active_current_reported", value)
        # Reactive energy consumption
        elif attrid == OWON_METERING_REACTIVE_ENERGY_CONSUMPTION_PH_A_ATTR:
            self.endpoint.device.reactive_energy_consumption_ph_a_bus.listener_event("reactive_energy_consumption_ph_a_reported", value)
        elif attrid == OWON_METERING_REACTIVE_ENERGY_CONSUMPTION_PH_B_ATTR:
            self.endpoint.device.reactive_energy_consumption_ph_b_bus.listener_event("reactive_energy_consumption_ph_b_reported", value)
        elif attrid == OWON_METERING_REACTIVE_ENERGY_CONSUMPTION_PH_C_ATTR:
            self.endpoint.device.reactive_energy_consumption_ph_c_bus.listener_event("reactive_energy_consumption_ph_c_reported", value)
        elif attrid == OWON_METERING_TOTAL_REACTIVE_ENERGY_CONSUMPTION_ATTR:
            self.endpoint.device.total_reactive_energy_consumption_bus.listener_event("total_reactive_energy_consumption_reported", value)
        # Frequency
        elif attrid == OWON_METERING_AC_FREQUENCY_ATTR:
            self.endpoint.device.ac_frequency_bus.listener_event("ac_frequency_reported", value)
        # Leakage
        elif attrid == OWON_METERING_LEAKAGE_CURRENT_ATTR:
            self.endpoint.device.leakage_current_bus.listener_event("leakage_current_reported", value)

class OwonManufacturerSpecific(LocalDataCluster):
    """Owon manufacturer specific attributes."""

    cluster_id = OWON_PC321_CLUSTER_ID
    ep_attribute = "owon_pc321_manufacturer_specific_cluster"

    attributes = {
        # Energy Consumption
        OWON_METERING_ENERGY_CONSUMPTION_PH_A_ATTR: ("energy_consumption_ph_a", t.uint48_t, True),
        OWON_METERING_ENERGY_CONSUMPTION_PH_B_ATTR: ("energy_consumption_ph_b", t.uint48_t, True),
        OWON_METERING_ENERGY_CONSUMPTION_PH_C_ATTR: ("energy_consumption_ph_c", t.uint48_t, True),
        OWON_METERING_TOTAL_ENERGY_CONSUMPTION_ATTR: ("total_energy_consumption", t.uint48_t, True),
        # Active power
        OWON_METERING_ACTIVE_POWER_PH_A_ATTR: ("active_power_ph_a", t.uint24_t, True),
        OWON_METERING_ACTIVE_POWER_PH_B_ATTR: ("active_power_ph_b", t.uint24_t, True),
        OWON_METERING_ACTIVE_POWER_PH_C_ATTR: ("active_power_ph_c", t.uint24_t, True),
        OWON_METERING_TOTAL_ACTIVE_POWER_ATTR: ("total_active_power", t.uint24_t, True),
        # Reactive power
        OWON_METERING_REACTIVE_POWER_PH_A_ATTR: ("reactive_power_ph_a", t.uint24_t, True),
        OWON_METERING_REACTIVE_POWER_PH_B_ATTR: ("reactive_power_ph_b", t.uint24_t, True),
        OWON_METERING_REACTIVE_POWER_PH_C_ATTR: ("reactive_power_ph_c", t.uint24_t, True),
        OWON_METERING_TOTAL_REACTIVE_POWER_ATTR: ("total_reactive_power", t.uint24_t, True),
        # Voltage
        OWON_METERING_VOLTAGE_PH_A_ATTR: ("rms_voltage_ph_a", t.uint24_t, True),
        OWON_METERING_VOLTAGE_PH_B_ATTR: ("rms_voltage_ph_b", t.uint24_t, True),
        OWON_METERING_VOLTAGE_PH_C_ATTR: ("rms_voltage_ph_c", t.uint24_t, True),
        # Active current
        OWON_METERING_ACTIVE_CURRENT_PH_A_ATTR: ("active_current_ph_a", t.uint24_t, True),
        OWON_METERING_ACTIVE_CURRENT_PH_B_ATTR: ("active_current_ph_b", t.uint24_t, True),
        OWON_METERING_ACTIVE_CURRENT_PH_C_ATTR: ("active_current_ph_c", t.uint24_t, True),
        OWON_METERING_TOTAL_ACTIVE_CURRENT_ATTR: ("total_active_current", t.uint24_t, True),
        # Reactive energy consumption
        OWON_METERING_REACTIVE_ENERGY_CONSUMPTION_PH_A_ATTR: ("reactive_energy_consumption_ph_a", t.uint48_t, True),
        OWON_METERING_REACTIVE_ENERGY_CONSUMPTION_PH_B_ATTR: ("reactive_energy_consumption_ph_b", t.uint48_t, True),
        OWON_METERING_REACTIVE_ENERGY_CONSUMPTION_PH_C_ATTR: ("reactive_energy_consumption_ph_c", t.uint48_t, True),
        OWON_METERING_TOTAL_REACTIVE_ENERGY_CONSUMPTION_ATTR: ("total_reactive_energy_consumption", t.uint48_t, True),
        # Frequency
        OWON_METERING_AC_FREQUENCY_ATTR: ("ac_frequency", t.uint8_t, True),
        # Leakage
        OWON_METERING_LEAKAGE_CURRENT_ATTR: ("leakage_current", t.uint24_t, True),
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        # Energy Consumption
        self.endpoint.device.energy_consumption_ph_a_bus.add_listener(self)
        self.endpoint.device.energy_consumption_ph_b_bus.add_listener(self)
        self.endpoint.device.energy_consumption_ph_c_bus.add_listener(self)
        self.endpoint.device.total_energy_consumption_bus.add_listener(self)
        # Active power
        self.endpoint.device.active_power_bus.add_listener(self)
        self.endpoint.device.active_power_ph_b_bus.add_listener(self)
        self.endpoint.device.active_power_ph_c_bus.add_listener(self)
        self.endpoint.device.total_active_power_bus.add_listener(self)
        # Reactive power
        self.endpoint.device.reactive_power_bus.add_listener(self)
        self.endpoint.device.reactive_power_ph_b_bus.add_listener(self)
        self.endpoint.device.reactive_power_ph_c_bus.add_listener(self)
        self.endpoint.device.total_reactive_power_bus.add_listener(self)
        # Voltage
        self.endpoint.device.rms_voltage_bus.add_listener(self)
        self.endpoint.device.rms_voltage_ph_b_bus.add_listener(self)
        self.endpoint.device.rms_voltage_ph_c_bus.add_listener(self)
        # Active current
        self.endpoint.device.active_current_bus.add_listener(self)
        self.endpoint.device.active_current_ph_b_bus.add_listener(self)
        self.endpoint.device.active_current_ph_c_bus.add_listener(self)
        self.endpoint.device.instantaneous_active_current_bus.add_listener(self)
        # Reactive Energy Consumption
        self.endpoint.device.reactive_energy_consumption_ph_a_bus.add_listener(self)
        self.endpoint.device.reactive_energy_consumption_ph_b_bus.add_listener(self)
        self.endpoint.device.reactive_energy_consumption_ph_c_bus.add_listener(self)
        self.endpoint.device.total_reactive_energy_consumption_bus.add_listener(self)
        # Frequency
        self.endpoint.device.ac_frequency_bus.add_listener(self)
        # Leakage
        self.endpoint.device.leakage_current_bus.add_listener(self)

    # Energy Consumption
    def energy_consumption_ph_a_reported(self, value):
        """Energy Consumption Phase A reported."""
        self._update_attribute(OWON_METERING_ENERGY_CONSUMPTION_PH_A_ATTR, value)
    def energy_consumption_ph_b_reported(self, value):
        """Energy Consumption Phase B reported."""
        self._update_attribute(OWON_METERING_ENERGY_CONSUMPTION_PH_B_ATTR, value)
    def energy_consumption_ph_c_reported(self, value):
        """Energy Consumption Phase C reported."""
        self._update_attribute(OWON_METERING_ENERGY_CONSUMPTION_PH_C_ATTR, value)
    def total_energy_consumption_reported(self, value):
        """Total Energy Consumption reported."""
        self._update_attribute(OWON_METERING_TOTAL_ENERGY_CONSUMPTION_ATTR, value)
    # Active power
    def active_power_reported(self, value):
        """Active Power Phase A reported."""
        self._update_attribute(OWON_METERING_ACTIVE_POWER_PH_A_ATTR, value)
    def active_power_ph_b_reported(self, value):
        """Active Power Phase B reported."""
        self._update_attribute(OWON_METERING_ACTIVE_POWER_PH_B_ATTR, value)
    def active_power_ph_c_reported(self, value):
        """Active Power Phase C reported."""
        self._update_attribute(OWON_METERING_ACTIVE_POWER_PH_C_ATTR, value)
    def total_active_power_reported(self, value):
        """Total Active Power reported."""
        self._update_attribute(OWON_METERING_TOTAL_ACTIVE_POWER_ATTR, value)
    # Reactive power
    def reactive_power_reported(self, value):
        """Reactive Power Phase A reported."""
        self._update_attribute(OWON_METERING_REACTIVE_POWER_PH_A_ATTR, value)
    def reactive_power_ph_b_reported(self, value):
        """Reactive Power Phase B reported."""
        self._update_attribute(OWON_METERING_REACTIVE_POWER_PH_B_ATTR, value)
    def reactive_power_ph_c_reported(self, value):
        """Reactive Power Phase C reported."""
        self._update_attribute(OWON_METERING_REACTIVE_POWER_PH_C_ATTR, value)
    def total_reactive_power_reported(self, value):
        """Total Reactive Power reported."""
        self._update_attribute(OWON_METERING_TOTAL_REACTIVE_POWER_ATTR, value)
    # Voltage
    def rms_voltage_reported(self, value):
        """RMS Voltage Phase A reported."""
        self._update_attribute(OWON_METERING_VOLTAGE_PH_A_ATTR, value)
    def rms_voltage_ph_b_reported(self, value):
        """RMS Voltage Phase B reported."""
        self._update_attribute(OWON_METERING_VOLTAGE_PH_B_ATTR, value)
    def rms_voltage_ph_c_reported(self, value):
        """RMS Voltage Phase C reported."""
        self._update_attribute(OWON_METERING_VOLTAGE_PH_C_ATTR, value)
    # Active current
    def active_current_reported(self, value):
        """Active Current Phase A reported."""
        self._update_attribute(OWON_METERING_ACTIVE_CURRENT_PH_A_ATTR, value)
    def active_current_ph_b_reported(self, value):
        """Active Current Phase B reported."""
        self._update_attribute(OWON_METERING_ACTIVE_CURRENT_PH_B_ATTR, value)
    def active_current_ph_c_reported(self, value):
        """Active Current Phase C reported."""
        self._update_attribute(OWON_METERING_ACTIVE_CURRENT_PH_C_ATTR, value)
    def instantaneous_active_current_reported(self, value):
        """Instantaneous Total Active Current reported."""
        self._update_attribute(OWON_METERING_TOTAL_ACTIVE_CURRENT_ATTR, value)
    # Reactive Energy Consumption
    def reactive_energy_consumption_ph_a_reported(self, value):
        """Reactive Energy Consumption Phase A reported."""
        self._update_attribute(OWON_METERING_REACTIVE_ENERGY_CONSUMPTION_PH_A_ATTR, value)
    def reactive_energy_consumption_ph_b_reported(self, value):
        """Reactive Energy Consumption Phase B reported."""
        self._update_attribute(OWON_METERING_REACTIVE_ENERGY_CONSUMPTION_PH_B_ATTR, value)
    def reactive_energy_consumption_ph_c_reported(self, value):
        """Reactive Energy Consumption Phase C reported."""
        self._update_attribute(OWON_METERING_REACTIVE_ENERGY_CONSUMPTION_PH_C_ATTR, value)
    def total_reactive_energy_consumption_reported(self, value):
        """Total Reactive Energy Consumption reported."""
        self._update_attribute(OWON_METERING_TOTAL_REACTIVE_ENERGY_CONSUMPTION_ATTR, value)
    # Frequency
    def ac_frequency_reported(self, value):
        """AC Frequency reported."""
        self._update_attribute(OWON_METERING_AC_FREQUENCY_ATTR, value)
    # Leakage
    def leakage_current_reported(self, value):
        """Leakage Current reported."""
        self._update_attribute(OWON_METERING_LEAKAGE_CURRENT_ATTR, value)


class OwonElectricalMeasurement(LocalDataCluster, ElectricalMeasurement):
    """Owon PC321 attributes that can be mapped to ElectricalMeasurement cluster."""

    cluster_id = ElectricalMeasurement.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        # Active power
        self.endpoint.device.active_power_bus.add_listener(self)
        self.endpoint.device.active_power_ph_b_bus.add_listener(self)
        self.endpoint.device.active_power_ph_c_bus.add_listener(self)
        self.endpoint.device.total_active_power_bus.add_listener(self)
        # Reactive power
        self.endpoint.device.reactive_power_bus.add_listener(self)
        self.endpoint.device.reactive_power_ph_b_bus.add_listener(self)
        self.endpoint.device.reactive_power_ph_c_bus.add_listener(self)
        self.endpoint.device.total_reactive_power_bus.add_listener(self)
        # Voltage
        self.endpoint.device.rms_voltage_bus.add_listener(self)
        self.endpoint.device.rms_voltage_ph_b_bus.add_listener(self)
        self.endpoint.device.rms_voltage_ph_c_bus.add_listener(self)
        # Active current
        self.endpoint.device.active_current_bus.add_listener(self)
        self.endpoint.device.active_current_ph_b_bus.add_listener(self)
        self.endpoint.device.active_current_ph_c_bus.add_listener(self)
        self.endpoint.device.instantaneous_active_current_bus.add_listener(self)
        # Frequency
        self.endpoint.device.ac_frequency_bus.add_listener(self)

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
        ElectricalMeasurement.AttributeDefs.ac_frequency_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 1,
    }

    # Active power
    def active_power_reported(self, value):
        """Active Power Phase A reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['active_power'].id, value)
    def active_power_ph_b_reported(self, value):
        """Active Power Phase B reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['active_power_ph_b'].id, value)
    def active_power_ph_c_reported(self, value):
        """Active Power Phase C reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['active_power_ph_c'].id, value)
    def total_active_power_reported(self, value):
        """Total Active Power reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['total_active_power'].id, value)
    # Reactive power
    def reactive_power_reported(self, value):
        """Reactive Power Phase A reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['reactive_power'].id, value)
    def reactive_power_ph_b_reported(self, value):
        """Reactive Power Phase B reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['reactive_power_ph_b'].id, value)
    def reactive_power_ph_c_reported(self, value):
        """Reactive Power Phase C reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['reactive_power_ph_c'].id, value)
    def total_reactive_power_reported(self, value):
        """Total Reactive Power reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['total_reactive_power'].id, value)
    # Voltage
    def rms_voltage_reported(self, value):
        """RMS Voltage Phase A reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['rms_voltage'].id, value)
    def rms_voltage_ph_b_reported(self, value):
        """RMS Voltage Phase B reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['rms_voltage_ph_b'].id, value)
    def rms_voltage_ph_c_reported(self, value):
        """RMS Voltage Phase C reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['rms_voltage_ph_c'].id, value)
    # Active current
    def active_current_reported(self, value):
        """Active Current Phase A reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['active_current'].id, value)
    def active_current_ph_b_reported(self, value):
        """Active Current Phase B reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['active_current_ph_b'].id, value)
    def active_current_ph_c_reported(self, value):
        """Active Current Phase C reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['active_current_ph_c'].id, value)
    def instantaneous_active_current_reported(self, value):
        """Instantaneous Active Current reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['instantaneous_active_current'].id, value)
    # Frequency
    def ac_frequency_reported(self, value):
        """AC Frequency reported."""
        self._update_attribute(ElectricalMeasurement.attributes_by_name['ac_frequency'].id, value)

class Owon_PC321(CustomDevice):
    """OwonPC321 Custom Device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        # Active Consumption
        self.energy_consumption_ph_a_bus = Bus()
        self.energy_consumption_ph_b_bus = Bus()
        self.energy_consumption_ph_c_bus = Bus()
        self.total_energy_consumption_bus = Bus()
        # Active power
        self.active_power_bus = Bus()
        self.active_power_ph_b_bus = Bus()
        self.active_power_ph_c_bus = Bus()
        self.total_active_power_bus = Bus()
        # Reactive power
        self.reactive_power_bus = Bus()
        self.reactive_power_ph_b_bus = Bus()
        self.reactive_power_ph_c_bus = Bus()
        self.total_reactive_power_bus = Bus()
        # Voltage
        self.rms_voltage_bus = Bus()
        self.rms_voltage_ph_b_bus = Bus()
        self.rms_voltage_ph_c_bus = Bus()
        # Active current
        self.active_current_bus = Bus()
        self.active_current_ph_b_bus = Bus()
        self.active_current_ph_c_bus = Bus()
        self.instantaneous_active_current_bus = Bus()
        # Reactive consumption
        self.reactive_energy_consumption_ph_a_bus = Bus()
        self.reactive_energy_consumption_ph_b_bus = Bus()
        self.reactive_energy_consumption_ph_c_bus = Bus()
        self.total_reactive_energy_consumption_bus = Bus()
        # Frequency
        self.ac_frequency_bus = Bus()
        # Leakage
        self.leakage_current_bus = Bus()

        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(OWON, OWON_PC321)],
        ENDPOINTS: {
            # device_version="0x000d"
            # input_clusters=["0x0000", "0x0003", "0x0702"]
            # output_clusters=["0x0003"]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Metering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OwonMetering,
                    OwonElectricalMeasurement,
                    OwonManufacturerSpecific,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        },
    }
