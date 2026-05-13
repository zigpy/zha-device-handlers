"""Custom quirk for Excellux NTCHT01 with external temperature probe."""

from zigpy.zcl.clusters.general import Basic, Identify
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks import CustomDevice
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster


class ExternalProbeTempCluster(TuyaLocalCluster, TemperatureMeasurement):
    """Virtual cluster for the external temperature probe on DP 5."""

    def __init__(self, *args, **kwargs):
        """Init and inject initial state to avoid unsupported attribute error."""
        super().__init__(*args, **kwargs)
        # Söödame andurile kohe algväärtuse 0, et ZHA ei märgiks seda "unsupported" (toetamata) anduriks!
        self._update_attribute(self.attributes_by_name["measured_value"].id, 0)


class NTCHT01TuyaMCU(TuyaMCUCluster):
    """Custom Tuya MCU cluster mapping for Excellux."""

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        5: DPToAttributeMapping(
            ExternalProbeTempCluster.ep_attribute,
            "measured_value",
            endpoint_id=2,
        ),
    }
    data_point_handlers = {
        5: "_dp_2_attr_update",
    }


class ExcelluxNTCHT01(CustomDevice):
    """Excellux NTCHT01 custom quirk."""

    signature = {
        MODELS_INFO: [("NTCHT01", "Excellux")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0302,
                INPUT_CLUSTERS: [
                    0x0000,
                    0x0001,
                    0x0003,
                    0x0402,
                    0x0405,
                    0x1000,
                    0xEF00,
                ],
                OUTPUT_CLUSTERS: [0x0003, 0x1000, 0xEF00],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0302,
                INPUT_CLUSTERS: [
                    0x0000,
                    0x0001,
                    0x0003,
                    0x0402,
                    0x0405,
                    0x1000,
                    NTCHT01TuyaMCU,
                ],
                OUTPUT_CLUSTERS: [0x0003, 0x1000, NTCHT01TuyaMCU],
            },
            2: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0302,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    ExternalProbeTempCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }
