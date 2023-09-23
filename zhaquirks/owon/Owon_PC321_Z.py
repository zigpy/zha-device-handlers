"""QUIRK FOR OWON PC321 Z"""

import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

_LOGGER = logging.getLogger(__name__)


class Owon_PC321_Z_Simple_Metering(CustomCluster, Metering):
    """Owon PC321 CustomCluster"""

    cluster_id = 0x0702
    ep_attribute: str = "owon_smartenergy_metering"

    attributes = Metering.attributes.copy()
    attributes.update(
        {
            0x2000: ("L1_phase_power", t.uint24_t, True),
            0x2001: ("L2_phase_power", t.uint24_t, True),
            0x2002: ("L3_phase_power", t.uint24_t, True),
            0x2100: ("L1_phase_reactive_power", t.uint24_t, True),
            0x2101: ("L2_phase_reactive_power", t.uint24_t, True),
            0x2102: ("L3_phase_reactive_power", t.uint24_t, True),
            0x2103: ("reactive_power_summation_of_the_3_phases", t.uint24_t, True),
            0x3000: ("L1_phase_voltage", t.uint24_t, True),
            0x3001: ("L2_phase_voltage", t.uint24_t, True),
            0x3002: ("L3_phase_voltage", t.uint24_t, True),
            0x3100: ("L1_phase_current", t.uint24_t, True),
            0x3101: ("L2_phase_current", t.uint24_t, True),
            0x3102: ("L3_phase_current", t.uint24_t, True),
            0x3103: ("current_summation_of_the_3_phases", t.uint24_t, True),
            0x3104: ("leakage_current", t.uint24_t, True),
            0x4000: ("L1_phase_energy_consumption", t.uint48_t, True),
            0x4001: ("L2_phase_energy_consumption", t.uint48_t, True),
            0x4002: ("L3_phase_energy_consumption", t.uint48_t, True),
            0x4100: ("L1_phase_reactive_energy_consumption", t.uint48_t, True),
            0x4101: ("L2_phase_reactive_energy_consumption", t.uint48_t, True),
            0x4102: ("L3_phase_reactive_energy_consumption", t.uint48_t, True),
            0x4103: ("reactive_energy_summation_of_the_3_phases", t.uint48_t, True),
            0x5005: ("frequency", t.uint8_t, True),
        }
    )


"""New Device Owon PC321 Z"""


class Owon_PC321_Z(CustomDevice):
    signature = {
        # MODELS_INFO: [("Owon", "PC321")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=13
            # device_version=1
            # input_clusters=[0, 3, 1794]
            # output_clusters=[3]>
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
        "manufacturer": "OWON Technology Inc.",
    }
    replacement = {
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=13
            # device_version=1
            # input_clusters=[0, 3, 1794, 65504]
            # output_clusters=[3]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.CONSUMPTION_AWARENESS_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Owon_PC321_Z_Simple_Metering,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        },
    }
