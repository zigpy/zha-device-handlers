"""Doorsensors."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class DS01DoorSensor(CustomDevice):
    """One of the long rectangular Doorsensors working on 2xAAA.

    It doesn't correctly implement the PollControl Cluster.
    The device will send "PollControl:checkin()" on PollControl cluster,
        but doesn't respond when checkin_response is sent after that from the coordinator

    The model zbeacon DS01 sounds a lot like ("eWeLink", "DS01") from Sonoff sold as Sonoff SNZB-04
    The device tested is sold as Elivco and IHseno IH-MC01 and uses a TuYa ZTU module as described here:
        https://github.com/dresden-elektronik/deconz-rest-plugin/issues/7415
    """

    signature = {
        MODELS_INFO: [("zbeacon", "DS01")],
        ENDPOINTS: {
            # SizePrefixedSimpleDescriptor(
            # endpoint=1, profile=260, device_type=1026, device_version=0,
            # input_clusters=[0, 3, 1, 1280, 32], output_clusters=[25])
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        }
    }
