"""Tuya EARU PC311-Z-TY Single-Phase Power Clamp."""
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time
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
from zhaquirks.tuya import TuyaManufClusterAttributes

# attributes and conversion factors per
# https://github.com/zigpy/zha-device-handlers/issues/2650
#   it seems we need to add 512 (0x200) to most values from there
OFFSET = 512
#   although some may need 256 (0x100)?
ENERGY_FORWARD_AB_ATTR = 1 + OFFSET
ENERGY_REVERSE_AB_ATTR = 2 + OFFSET
TOTAL_POWER_AB_ATTR = 9 + OFFSET
ENERGY_FORWARD_A_ATTR = 101 + OFFSET
ENERGY_REVERSE_A_ATTR = 102 + OFFSET
ENERGY_FORWARD_B_ATTR = 103 + OFFSET
ENERGY_REVERSE_B_ATTR = 104 + OFFSET
CURRENT_AB_ATTR = 105 + OFFSET
VOLTAGE_ATTR = 106 + OFFSET
CURRENT_A_ATTR = 107 + OFFSET
TOTAL_POWER_A_ATTR = 108 + OFFSET
POWER_FACTOR_A_ATTR = 109 + OFFSET
CURRENT_B_ATTR = 110 + OFFSET
TOTAL_POWER_B_ATTR = 111 + OFFSET
POWER_FACTOR_B_ATTR = 112 + OFFSET
AC_FREQUENCY_ATTR = 113 + OFFSET
POWER_DIRECTION_A_ATTR = 114 + OFFSET
POWER_DIRECTION_B_ATTR = 115 + OFFSET
UPDATEFREQ_ATTR = 116 + OFFSET

ENERGY_DIV = 100
VOLTAGE_DIV = 10
CURRENT_DIV = 1000

EARU_SPECIFIC_CLUSTER = 0xFF66  # no idea what this is for..

_LOGGER = logging.getLogger(__name__)


class Tuya_EnergyMeter_2Clamp(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the Tuya Power Meter device."""

    attributes = TuyaManufClusterAttributes.attributes.copy()
    attributes.update(
        {
            ENERGY_FORWARD_AB_ATTR: ("energy_both", t.uint32_t, True),
            ENERGY_REVERSE_AB_ATTR: ("energy_reverse", t.uint32_t, True),
            ENERGY_FORWARD_A_ATTR: ("energy_A", t.uint32_t, True),
            ENERGY_REVERSE_A_ATTR: ("energy_rev_A", t.uint32_t, True),
            ENERGY_FORWARD_B_ATTR: ("energy_B", t.uint32_t, True),
            ENERGY_REVERSE_B_ATTR: ("energy_rev_B", t.uint32_t, True),
            VOLTAGE_ATTR: ("voltage", t.uint16_t, True),
            TOTAL_POWER_AB_ATTR: ("power_both", t.int16s, True),
            TOTAL_POWER_A_ATTR: ("power_A", t.int16s, True),
            TOTAL_POWER_B_ATTR: ("power_B", t.int16s, True),
            CURRENT_AB_ATTR: ("current_both", t.int16s, True),
            CURRENT_A_ATTR: ("current_A", t.int16s, True),
            CURRENT_B_ATTR: ("current_B", t.int16s, True),
            POWER_FACTOR_A_ATTR: ("power_factor_A", t.uint16_t, True),
            POWER_FACTOR_B_ATTR: ("power_factor_B", t.uint16_t, True),
            AC_FREQUENCY_ATTR: ("ac_frequency", t.uint16_t, True),
            # unclear whether these work (i.e "not for me")
            POWER_DIRECTION_A_ATTR: (
                "power_direction_A",
                t.uint16_t,
                True,
            ),  # 0:forward, 1:reverse
            POWER_DIRECTION_B_ATTR: ("power_direction_B", t.uint16_t, True),
            UPDATEFREQ_ATTR: ("updatefrequency", t.uint16_t, True),
        }
    )

    def __init__(self, *args, **kwargs):
        """Init attributes."""
        _LOGGER.warning("initializing quirky powerclamp attributes")
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        """Route the raw sensor data to the correct generic attributes (with units)"""

        _LOGGER.debug(f"quirky _update_attribute( 0x{attrid:04x}, {value})")

        if attrid == VOLTAGE_ATTR:
            # shared over total, A, B but will report only once
            self.endpoint.device.clamp_bus["power"]["ab"].listener_event(
                "voltage_reported", value
            )
            value /= VOLTAGE_DIV
        elif attrid == AC_FREQUENCY_ATTR:
            self.endpoint.device.clamp_bus["power"]["ab"].listener_event(
                "ac_frequency_reported", value
            )
        elif attrid == TOTAL_POWER_AB_ATTR:
            self.endpoint.device.clamp_bus["power"]["ab"].listener_event(
                "power_reported", value
            )
        elif attrid == TOTAL_POWER_A_ATTR:
            self.endpoint.device.clamp_bus["power"]["a"].listener_event(
                "power_reported", value
            )
        elif attrid == TOTAL_POWER_B_ATTR:
            self.endpoint.device.clamp_bus["power"]["b"].listener_event(
                "power_reported", value
            )
        elif attrid == POWER_FACTOR_A_ATTR:
            self.endpoint.device.clamp_bus["power"]["a"].listener_event(
                "power_factor_reported", value
            )
        elif attrid == POWER_FACTOR_B_ATTR:
            self.endpoint.device.clamp_bus["power"]["b"].listener_event(
                "power_factor_reported", value
            )
        elif attrid == CURRENT_AB_ATTR:
            self.endpoint.device.clamp_bus["power"]["ab"].listener_event(
                "current_reported", value
            )
            value /= CURRENT_DIV
        elif attrid == CURRENT_A_ATTR:
            self.endpoint.device.clamp_bus["power"]["a"].listener_event(
                "current_reported", value
            )
            value /= CURRENT_DIV
        elif attrid == CURRENT_B_ATTR:
            self.endpoint.device.clamp_bus["power"]["b"].listener_event(
                "current_reported", value
            )
            value /= CURRENT_DIV
        elif attrid == ENERGY_FORWARD_AB_ATTR:
            self.endpoint.device.clamp_bus["energy"]["ab"].listener_event(
                "energy_forward_reported", value
            )
            value /= ENERGY_DIV
        elif attrid == ENERGY_REVERSE_AB_ATTR:
            self.endpoint.device.clamp_bus["energy"]["ab"].listener_event(
                "energy_reverse_reported", value
            )
            value /= ENERGY_DIV
        elif attrid == ENERGY_FORWARD_A_ATTR:
            self.endpoint.device.clamp_bus["energy"]["a"].listener_event(
                "energy_forward_reported", value
            )
            value /= ENERGY_DIV
        elif attrid == ENERGY_REVERSE_A_ATTR:
            self.endpoint.device.clamp_bus["energy"]["a"].listener_event(
                "energy_reverse_reported", value
            )
            value /= ENERGY_DIV
        elif attrid == ENERGY_FORWARD_B_ATTR:
            self.endpoint.device.clamp_bus["energy"]["b"].listener_event(
                "energy_forward_reported", value
            )
            value /= ENERGY_DIV
        elif attrid == ENERGY_REVERSE_B_ATTR:
            self.endpoint.device.clamp_bus["energy"]["b"].listener_event(
                "energy_reverse_reported", value
            )
            value /= ENERGY_DIV
        else:
            _LOGGER.warning(
                f"UNKNOWN quirky _update_attribute( 0x{attrid:04x}, {value})"
            )

        # the helper classes below "know" how to divide themselves,
        # but we also want correct data in the raw reported
        # attribs - hence value /= x  above
        super()._update_attribute(attrid, value)


class PowerMeasurement_2Clamp(LocalDataCluster, ElectricalMeasurement):
    """Custom class for power, voltage and current measurement."""

    # use constants from zigpy/zcl/clusters/homeautomation.py
    cluster_id = ElectricalMeasurement.cluster_id
    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: CURRENT_DIV,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: VOLTAGE_DIV,
    }

    def ac_frequency_reported(self, value):
        self._update_attribute(
            ElectricalMeasurement.AttributeDefs.ac_frequency.id, value
        )

    def voltage_reported(self, value):
        self._update_attribute(
            ElectricalMeasurement.AttributeDefs.rms_voltage.id, value
        )

    def power_reported(self, value):
        self._update_attribute(
            ElectricalMeasurement.AttributeDefs.active_power.id, value
        )

    def power_factor_reported(self, value):
        self._update_attribute(
            ElectricalMeasurement.AttributeDefs.power_factor.id, value
        )

    def current_reported(self, value):
        self._update_attribute(
            ElectricalMeasurement.AttributeDefs.rms_current.id, value
        )


class Metering_2Clamp(LocalDataCluster, Metering):
    """Custom class for energy measurement."""

    # from zigpy/zcl/clusters/smartenergy.py
    cluster_id = Metering.cluster_id
    POWER_WATT = 0x0000

    """Setting unit of measurement."""
    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.unit_of_measure.id: POWER_WATT,
        Metering.AttributeDefs.divisor.id: ENERGY_DIV,
    }

    def energy_forward_reported(self, value):
        # this is "current" as in "now", not "Amperes"
        self._update_attribute(Metering.AttributeDefs.current_summ_delivered.id, value)

    def energy_reverse_reported(self, value):
        self._update_attribute(Metering.AttributeDefs.current_summ_received.id, value)


# still unclear why we cannot use instances?
# anyway, these will be our replacement endpoints.
class EnergyTotal(Metering_2Clamp):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.clamp_bus["energy"]["ab"].add_listener(self)


class EnergyA(Metering_2Clamp):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.clamp_bus["energy"]["a"].add_listener(self)


class EnergyB(Metering_2Clamp):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.clamp_bus["energy"]["b"].add_listener(self)


class PowerTotal(PowerMeasurement_2Clamp):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.clamp_bus["power"]["ab"].add_listener(self)


class PowerA(PowerMeasurement_2Clamp):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.clamp_bus["power"]["a"].add_listener(self)


class PowerB(PowerMeasurement_2Clamp):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.clamp_bus["power"]["b"].add_listener(self)


class DualPowerMeter(CustomDevice):
    """EARU PC311-Z-TY : Tuya single-phase dual clamp power meter.
    - bidirectional
    - 80A max
    """

    def __init__(self, *args, **kwargs):
        """Init device."""
        _LOGGER.warning("initializing quirky powerclamp")
        self.clamp_bus = {}
        for i in ["power", "energy"]:
            self.clamp_bus[i] = {}
            for j in ["ab", "a", "b"]:
                self.clamp_bus[i][j] = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [
            ("_TZE200_rks0sgb7", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=51
            # device_version=1
            # input_clusters: [ 0x0000, 0x0004, 0x0005, 0xef00, 0xff66 ]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufClusterAttributes.cluster_id,
                    EARU_SPECIFIC_CLUSTER,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Tuya_EnergyMeter_2Clamp,
                    EnergyTotal,
                    PowerTotal,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            10: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [
                    EnergyA,
                    PowerA,
                ],
            },
            20: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [
                    EnergyB,
                    PowerB,
                ],
            },
        }
    }
