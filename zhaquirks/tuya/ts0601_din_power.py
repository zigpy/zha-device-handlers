"""Tuya Din Power Meter."""

from typing import Final

from zigpy.profiles import zha
from zigpy.quirks.v2 import SensorDeviceClass, SensorStateClass
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfEnergy
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import ZCLAttributeDef

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
    TuyaLocalCluster,
    TuyaManufClusterAttributes,
    TuyaOnOff,
    TuyaSwitch,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder

TUYA_TOTAL_ENERGY_ATTR = 0x0211
TUYA_CURRENT_ATTR = 0x0212
TUYA_POWER_ATTR = 0x0213
TUYA_VOLTAGE_ATTR = 0x0214
TUYA_DIN_SWITCH_ATTR = 0x0101

SWITCH_EVENT = "switch_event"

"""Hiking Power Meter Attributes"""
HIKING_DIN_SWITCH_ATTR = 0x0110
HIKING_TOTAL_ENERGY_DELIVERED_ATTR = 0x0201
HIKING_TOTAL_ENERGY_RECEIVED_ATTR = 0x0266
HIKING_VOLTAGE_CURRENT_ATTR = 0x0006
HIKING_POWER_ATTR = 0x0267
HIKING_FREQUENCY_ATTR = 0x0269
HIKING_POWER_FACTOR_ATTR = 0x026F
HIKING_TOTAL_REACTIVE_ATTR = 0x026D
HIKING_REACTIVE_POWER_ATTR = 0x026E


class TuyaManufClusterDinPower(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the Tuya Power Meter device."""

    class AttributeDefs(TuyaManufClusterAttributes.AttributeDefs):
        """Attribute definitions."""

        energy: Final = ZCLAttributeDef(
            id=TUYA_TOTAL_ENERGY_ATTR, type=t.uint32_t, is_manufacturer_specific=True
        )
        current: Final = ZCLAttributeDef(
            id=TUYA_CURRENT_ATTR, type=t.int16s, is_manufacturer_specific=True
        )
        power: Final = ZCLAttributeDef(
            id=TUYA_POWER_ATTR, type=t.uint16_t, is_manufacturer_specific=True
        )
        voltage: Final = ZCLAttributeDef(
            id=TUYA_VOLTAGE_ATTR, type=t.uint16_t, is_manufacturer_specific=True
        )
        switch: Final = ZCLAttributeDef(
            id=TUYA_DIN_SWITCH_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == TUYA_TOTAL_ENERGY_ATTR:
            self.endpoint.smartenergy_metering.energy_deliver_reported(value / 100)
        elif attrid == TUYA_CURRENT_ATTR:
            self.endpoint.electrical_measurement.current_reported(value)
        elif attrid == TUYA_POWER_ATTR:
            self.endpoint.electrical_measurement.power_reported(value / 10)
        elif attrid == TUYA_VOLTAGE_ATTR:
            self.endpoint.electrical_measurement.voltage_reported(value / 10)
        elif attrid == TUYA_DIN_SWITCH_ATTR:
            self.endpoint.device.switch_bus.listener_event(
                SWITCH_EVENT, self.endpoint.endpoint_id, value
            )


class TuyaPowerMeasurement(LocalDataCluster, ElectricalMeasurement):
    """Custom class for power, voltage and current measurement."""

    POWER_ID = 0x050B
    VOLTAGE_ID = 0x0505
    CURRENT_ID = 0x0508
    REACTIVE_POWER_ID = 0x050E
    AC_FREQUENCY_ID = 0x0300
    TOTAL_REACTIVE_POWER_ID = 0x0305
    POWER_FACTOR_ID = 0x0510

    AC_CURRENT_MULTIPLIER = 0x0602
    AC_CURRENT_DIVISOR = 0x0603
    AC_FREQUENCY_MULTIPLIER = 0x0400
    AC_FREQUENCY_DIVISOR = 0x0401

    _CONSTANT_ATTRIBUTES = {
        AC_CURRENT_MULTIPLIER: 1,
        AC_CURRENT_DIVISOR: 1000,
        AC_FREQUENCY_MULTIPLIER: 1,
        AC_FREQUENCY_DIVISOR: 100,
    }

    def voltage_reported(self, value):
        """Voltage reported."""
        self._update_attribute(self.VOLTAGE_ID, value)

    def power_reported(self, value):
        """Power reported."""
        self._update_attribute(self.POWER_ID, value)

    def power_factor_reported(self, value):
        """Power Factor reported."""
        self._update_attribute(self.POWER_FACTOR_ID, value)

    def reactive_power_reported(self, value):
        """Reactive Power reported."""
        self._update_attribute(self.REACTIVE_POWER_ID, value)

    def current_reported(self, value):
        """Ampers reported."""
        self._update_attribute(self.CURRENT_ID, value)

    def frequency_reported(self, value):
        """AC Frequency reported."""
        self._update_attribute(self.AC_FREQUENCY_ID, value)

    def reactive_energy_reported(self, value):
        """Summation Reactive Energy reported."""
        self._update_attribute(self.TOTAL_REACTIVE_POWER_ID, value)


class TuyaElectricalMeasurement(LocalDataCluster, Metering):
    """Custom class for total energy measurement."""

    CURRENT_DELIVERED_ID = 0x0000
    CURRENT_RECEIVED_ID = 0x0001
    POWER_WATT = 0x0000

    """Setting unit of measurement."""
    _CONSTANT_ATTRIBUTES = {0x0300: POWER_WATT}

    def energy_deliver_reported(self, value):
        """Summation Energy Deliver reported."""
        self._update_attribute(self.CURRENT_DELIVERED_ID, value)

    def energy_receive_reported(self, value):
        """Summation Energy Receive reported."""
        self._update_attribute(self.CURRENT_RECEIVED_ID, value)


class HikingManufClusterDinPower(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the Hiking Power Meter device."""

    class AttributeDefs(TuyaManufClusterAttributes.AttributeDefs):
        """Attribute definitions."""

        switch: Final = ZCLAttributeDef(
            id=HIKING_DIN_SWITCH_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )
        energy_delivered: Final = ZCLAttributeDef(
            id=HIKING_TOTAL_ENERGY_DELIVERED_ATTR,
            type=t.uint32_t,
            is_manufacturer_specific=True,
        )
        energy_received: Final = ZCLAttributeDef(
            id=HIKING_TOTAL_ENERGY_RECEIVED_ATTR,
            type=t.uint32_t,
            is_manufacturer_specific=True,
        )
        voltage_current: Final = ZCLAttributeDef(
            id=HIKING_VOLTAGE_CURRENT_ATTR,
            type=t.uint32_t,
            is_manufacturer_specific=True,
        )
        power: Final = ZCLAttributeDef(
            id=HIKING_POWER_ATTR, type=t.int32s, is_manufacturer_specific=True
        )
        frequency: Final = ZCLAttributeDef(
            id=HIKING_FREQUENCY_ATTR, type=t.uint16_t, is_manufacturer_specific=True
        )
        total_reactive_energy: Final = ZCLAttributeDef(
            id=HIKING_TOTAL_REACTIVE_ATTR, type=t.int32s, is_manufacturer_specific=True
        )
        reactive_power: Final = ZCLAttributeDef(
            id=HIKING_REACTIVE_POWER_ATTR, type=t.int16s, is_manufacturer_specific=True
        )
        power_factor: Final = ZCLAttributeDef(
            id=HIKING_POWER_FACTOR_ATTR, type=t.uint16_t, is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == HIKING_DIN_SWITCH_ATTR:
            self.endpoint.device.switch_bus.listener_event(SWITCH_EVENT, 16, value)
        elif attrid == HIKING_TOTAL_ENERGY_DELIVERED_ATTR:
            self.endpoint.smartenergy_metering.energy_deliver_reported(value / 100)
        elif attrid == HIKING_TOTAL_ENERGY_RECEIVED_ATTR:
            self.endpoint.smartenergy_metering.energy_receive_reported(value / 100)
        elif attrid == HIKING_VOLTAGE_CURRENT_ATTR:
            self.endpoint.electrical_measurement.current_reported(value >> 16)
            self.endpoint.electrical_measurement.voltage_reported(
                (value & 0x0000FFFF) / 10
            )
        elif attrid == HIKING_POWER_ATTR:
            self.endpoint.electrical_measurement.power_reported(value)
        elif attrid == HIKING_FREQUENCY_ATTR:
            self.endpoint.electrical_measurement.frequency_reported(value)
        elif attrid == HIKING_TOTAL_REACTIVE_ATTR:
            self.endpoint.electrical_measurement.reactive_energy_reported(value)
        elif attrid == HIKING_REACTIVE_POWER_ATTR:
            self.endpoint.electrical_measurement.reactive_power_reported(value)
        elif attrid == HIKING_POWER_FACTOR_ATTR:
            self.endpoint.electrical_measurement.power_factor_reported(value / 10)


class TuyaPowerMeter(TuyaSwitch):
    """Tuya power meter device."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.switch_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # device_version=1
        # input_clusters=[0x0000, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x000a, 0x0019]
        MODELS_INFO: [
            ("_TZE200_byzdayie", "TS0601"),
            ("_TZE200_ewxhg6o9", "TS0601"),
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
                    TuyaManufClusterDinPower,
                    TuyaPowerMeasurement,
                    TuyaElectricalMeasurement,
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }


class Tuya3PhaseElectricalMeasurement(ElectricalMeasurement, TuyaLocalCluster):
    """Tuya Electrical Measurement cluster."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 100,
    }


(
    TuyaQuirkBuilder("_TZE204_ugekduaj", "TS0601")
    .tuya_dp(
        dp_id=101,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="ac_frequency",
    )
    # Energy consumed
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy_consumed",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Total energy",
    )
    .tuya_sensor(
        dp_id=112,
        attribute_name="energy_consumed_ph_a",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_a",
        fallback_name="Energy phase A",
    )
    .tuya_sensor(
        dp_id=114,
        attribute_name="energy_consumed_ph_b",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_b",
        fallback_name="Energy phase B",
    )
    .tuya_sensor(
        dp_id=116,
        attribute_name="energy_consumed_ph_c",
        divisor=100,
        type=t.uint32_t,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_c",
        fallback_name="Energy phase C",
    )
    # Energy produced
    .tuya_sensor(
        dp_id=2,
        attribute_name="energy_produced",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced",
        fallback_name="Energy produced",
    )
    .tuya_sensor(
        dp_id=113,
        attribute_name="energy_produced_ph_a",
        type=t.uint32_t,
        converter=lambda x: x / 100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced_ph_a",
        fallback_name="Energy produced phase A",
    )
    .tuya_sensor(
        dp_id=115,
        attribute_name="energy_produced_ph_b",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced_ph_b",
        fallback_name="Energy produced phase B",
    )
    .tuya_sensor(
        dp_id=117,
        attribute_name="energy_produced_ph_c",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced_ph_c",
        fallback_name="Energy produced phase C",
    )
    # Power
    .tuya_dp(
        dp_id=111,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="total_active_power",
    )
    .tuya_dp(
        dp_id=104,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="active_power",
    )
    .tuya_dp(
        dp_id=107,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="active_power_ph_b",
    )
    .tuya_dp(
        dp_id=110,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="active_power_ph_c",
    )
    # Voltage
    .tuya_dp(
        dp_id=102,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage",
    )
    .tuya_dp(
        dp_id=105,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage_ph_b",
    )
    .tuya_dp(
        dp_id=108,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage_ph_c",
    )
    # Current
    .tuya_dp(
        dp_id=103,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_current",
    )
    .tuya_dp(
        dp_id=106,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_current_ph_b",
    )
    .tuya_dp(
        dp_id=109,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_current_ph_c",
    )
    # Power factor
    .tuya_sensor(
        dp_id=15,
        attribute_name="power_factor",
        type=t.uint8_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER_FACTOR,
        unit=PERCENTAGE,
        translation_key="total_power_factor",
        fallback_name="Total power factor",
    )
    .tuya_dp(
        dp_id=118,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor",
    )
    .tuya_dp(
        dp_id=119,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_b",
    )
    .tuya_dp(
        dp_id=120,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_c",
    )
    .adds(Tuya3PhaseElectricalMeasurement)
    .skip_configuration()
    .add_to_registry()
)


class HikingPowerMeter(TuyaSwitch):
    """Hiking Power Meter Device - DDS238-2."""

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # device_version=1
        # input_clusters=[0x0000, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x000a, 0x0019]
        MODELS_INFO: [("_TZE200_bkkmqmyo", "TS0601")],
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
                    HikingManufClusterDinPower,
                    TuyaElectricalMeasurement,
                    TuyaPowerMeasurement,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            16: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }
