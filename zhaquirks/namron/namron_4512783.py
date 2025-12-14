"""Namron 4512783 Floor Heating Thermostat quirk.

This quirk exposes manufacturer-specific attributes for the Namron 4512783
floor heating thermostat, enabling regulator mode (percentage-based power
control) in addition to standard thermostat mode.

Manufacturer-specific attributes (Thermostat cluster 0x0201):
    0x8004 - operation_mode: Controls device operating mode
             0 = Thermostat mode (temperature-based control)
             6 = Regulator mode (percentage-based power control)
    0x801D - regulator_percentage: Power output percentage (0-100) in regulator mode
"""

from typing import Final

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.clusters.measurement import RelativeHumidity
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.namron import NAMRON


class NamronOperationMode(t.enum8):
    """Namron thermostat operation mode."""

    Thermostat = 0x00
    Regulator = 0x06


class NamronThermostatCluster(CustomCluster, Thermostat):
    """Namron manufacturer-specific thermostat cluster.

    Extends the standard Thermostat cluster with manufacturer-specific
    attributes for operation mode and regulator percentage control.
    """

    class AttributeDefs(Thermostat.AttributeDefs):
        """Manufacturer-specific attribute definitions."""

        operation_mode: Final = ZCLAttributeDef(
            id=0x8004,
            type=NamronOperationMode,
            is_manufacturer_specific=True,
        )
        regulator_percentage: Final = ZCLAttributeDef(
            id=0x801D,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


class NamronFloorHeating4512783(CustomDevice):
    """Namron 4512783 floor heating thermostat."""

    manufacturer_code = 0x126A  # 4714

    signature = {
        # <NodeDescriptor logical_type=Router manufacturer_code=4714>
        MODELS_INFO: [(NAMRON, "4512783")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=769
            # device_version=0
            # input_clusters=[0, 3, 4, 5, 6, 513, 516, 1029, 1794, 2820, 4096, 57346]
            # output_clusters=[3, 25, 1030]>
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
                    UserInterface.cluster_id,
                    RelativeHumidity.cluster_id,
                    0x0702,  # Metering
                    ElectricalMeasurement.cluster_id,
                    0x1000,  # Touchlink
                    0xE002,  # Manufacturer specific
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    0x0406,  # Occupancy Sensing
                ],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0 input_clusters=[] output_clusters=[33]>
            242: {
                PROFILE_ID: 0xA1E0,  # Green Power profile
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [0x0021],  # Green Power
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
                    OnOff.cluster_id,
                    NamronThermostatCluster,
                    UserInterface.cluster_id,
                    RelativeHumidity.cluster_id,
                    0x0702,  # Metering
                    ElectricalMeasurement.cluster_id,
                    0x1000,  # Touchlink
                    0xE002,  # Manufacturer specific
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    0x0406,  # Occupancy Sensing
                ],
            },
            242: {
                PROFILE_ID: 0xA1E0,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [0x0021],
            },
        },
    }
