"""Module to handle quirks of the  Zen Within thermostat."""

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters import general, homeautomation, hvac

from . import ZEN, ZenPowerConfiguration
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class ZenThermostat(CustomDevice):
    """Zen Within Thermostat custom device."""

    signature = {
        # Node Descriptor: <Optional byte1=2 byte2=64 mac_capability_flags=128
        # manufacturer_code=4440 maximum_buffer_size=82
        # maximum_incoming_transfer_size=128 server_mask=0
        # maximum_outgoing_transfer_size=128 descriptor_capability_field=0>
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769 device_version=0
        # input_clusters=[0, 1, 3, 4, 5, 32, 513, 514, 516, 2821]
        # output_clusters=[10, 25]>
        MODELS_INFO: [(ZEN, "Zen-01")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    general.Basic.cluster_id,
                    general.PowerConfiguration.cluster_id,
                    general.Identify.cluster_id,
                    general.Groups.cluster_id,
                    general.Scenes.cluster_id,
                    general.PollControl.cluster_id,
                    hvac.Thermostat.cluster_id,
                    hvac.Fan.cluster_id,
                    hvac.UserInterface.cluster_id,
                    homeautomation.Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [general.Time.cluster_id, general.Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    general.Basic.cluster_id,
                    ZenPowerConfiguration,
                    general.Identify.cluster_id,
                    general.Groups.cluster_id,
                    general.Scenes.cluster_id,
                    general.PollControl.cluster_id,
                    hvac.Thermostat.cluster_id,
                    hvac.Fan.cluster_id,
                    hvac.UserInterface.cluster_id,
                    homeautomation.Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [general.Time.cluster_id, general.Ota.cluster_id],
            }
        }
    }
