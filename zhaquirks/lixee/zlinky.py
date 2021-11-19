"""Quirk for ZLinky_TIC."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import Basic, GreenPowerProxy, Identify, Ota
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement, MeterIdentification
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.lixee import LIXEE


class ZLinkyTICMetering(CustomCluster, Metering):
    """ZLinky_TIC custom metring cluster."""

    # ZLinky_TIC reports current_summ_delivered in Wh
    # Home Assistant expects kWh (1kWh = 1000 Wh)
    MULTIPLIER = 0x0301
    DIVISOR = 0x0302
    _CONSTANT_ATTRIBUTES = {MULTIPLIER: 1, DIVISOR: 1000}


class ZLinkyTIC(CustomDevice):
    """ZLinky_TIC from LiXee."""

    signature = {
        MODELS_INFO: [(LIXEE, "ZLinky_TIC")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Metering.cluster_id,
                    MeterIdentification.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    0xFF66,  # Manufacturer Specific
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    ZLinkyTICMetering,
                    MeterIdentification.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    0xFF66,  # Manufacturer Specific
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
