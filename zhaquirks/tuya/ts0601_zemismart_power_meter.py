"""Tuya Din Power Meter."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks import LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TuyaManufClusterAttributes
from zhaquirks.tuya.ts0601_din_power import TuyaElectricalMeasurement

"""Zemismart Power Meter Attributes"""
ZEMISMART_TOTAL_ENERGY_ATTR = 0x0201
ZEMISMART_TOTAL_REVERSE_ENERGY_ATTR = 0x0202
ZEMISMART_VCP_ATTR = 0x0006


class ZemismartPowerMeasurement(LocalDataCluster, ElectricalMeasurement):
    """Custom class for power, voltage and current measurement."""

    cluster_id = ElectricalMeasurement.cluster_id

    POWER_ID = 0x050B
    VOLTAGE_ID = 0x0505
    CURRENT_ID = 0x0508

    AC_VOLTAGE_MULTIPLIER = 0x0600
    AC_VOLTAGE_DIVISOR = 0x0601
    AC_CURRENT_MULTIPLIER = 0x0602
    AC_CURRENT_DIVISOR = 0x0603

    _CONSTANT_ATTRIBUTES = {
        AC_VOLTAGE_MULTIPLIER: 1,
        AC_VOLTAGE_DIVISOR: 10,
        AC_CURRENT_MULTIPLIER: 1,
        AC_CURRENT_DIVISOR: 1000,
    }

    def voltage_reported(self, value):
        """Voltage reported."""
        self._update_attribute(self.VOLTAGE_ID, value)

    def power_reported(self, value):
        """Power reported."""
        self._update_attribute(self.POWER_ID, value)

    def current_reported(self, value):
        """Ampers reported."""
        self._update_attribute(self.CURRENT_ID, value)


class ZemismartElectricalMeasurement(TuyaElectricalMeasurement):
    """Custom class for total energy measurement."""

    POWER_UNIT = 0x300
    POWER_DIVISOR = 0x302
    POWER_WATT = 0x0000  # Actually this does not work. Data is interpreted as kWh.

    """Setting unit of measurement."""
    _CONSTANT_ATTRIBUTES = {0x0300: POWER_WATT, POWER_DIVISOR: 1000}


class ZemismartManufCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the Zemismart SPM01 Power Meter device."""

    attributes = {
        ZEMISMART_TOTAL_ENERGY_ATTR: ("energy", t.uint32_t, True),
        ZEMISMART_TOTAL_REVERSE_ENERGY_ATTR: ("reverse_energy", t.uint32_t, True),
        ZEMISMART_VCP_ATTR: ("vcp_raw", t.data64, True),
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == ZEMISMART_TOTAL_ENERGY_ATTR:
            self.endpoint.smartenergy_metering.energy_deliver_reported(value)
        elif attrid == ZEMISMART_TOTAL_REVERSE_ENERGY_ATTR:
            self.endpoint.smartenergy_metering.energy_receive_reported(value)
        elif attrid == ZEMISMART_VCP_ATTR:
            self.endpoint.electrical_measurement.voltage_reported(
                (value[7] * 256) + value[6]
            )
            self.endpoint.electrical_measurement.current_reported(
                (value[5] * 256 * 256) + (value[4] * 256) + value[3]
            )
            self.endpoint.electrical_measurement.power_reported(
                (value[2] * 256 * 256) + (value[1] * 256) + value[0]
            )


class TuyaZemismartPowerMeter(CustomDevice):
    """Tuya power meter device."""

    signature = {
        # "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0,
        # user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>,
        # mac_capability_flags=<MACCapabilityFlags.FullFunctionDevice|MainsPowered|RxOnWhenIdle|AllocateAddress: 142>,
        # manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>,
        # *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False,
        # *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True,
        # *is_security_capable=False)",
        # device_version=1
        # input_clusters=[0x0000, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x000a, 0x0019]
        MODELS_INFO: [
            ("_TZE200_bcusnqt8", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=51
            # device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
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
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    ZemismartManufCluster,
                    ZemismartElectricalMeasurement,
                    ZemismartPowerMeasurement,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
