"""Innr SP 120 plug."""

from zigpy.profiles import zll
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.innr import (
    INNR,
    ElectricalMeasurementClusterInnr,
    MeteringClusterInnrOld,
)


class MeteringClusterInnrSP120(MeteringClusterInnrOld):
    """SP 120 metering: also recover the manufacturer-framed summation report.

    The SP 120 (NXP/Jennic JN516x) firmware reports the standard
    ``current_summ_delivered`` (0x0000) with the manufacturer-specific bit set
    (Innr manufacturer code 0x1166). Since zigpy 0.91 resolves reported
    attributes against the frame's manufacturer code, that report no longer
    matches the standard ZCL attribute and is dropped -- energy then only updates
    on the startup read. Define the attribute the device actually reports and
    mirror its value onto the standard ZCL attribute the energy sensor reads.

    Scoped to the SP 120 on purpose: this is a quirk of that old JN516x firmware.
    The SP 234 and the newer SP 240/242/244 family run different firmware/stacks
    that report summation normally, so they keep the plain metering clusters.
    """

    class AttributeDefs(Metering.AttributeDefs):
        """Metering attributes plus the manufacturer-specific summation reported."""

        current_summ_delivered_mfg = ZCLAttributeDef(
            id=0x0000,
            type=t.uint48_t,
            manufacturer_code=0x1166,
        )

    def __init__(self, *args, **kwargs) -> None:
        """Listen for the manufacturer-specific summation reports."""
        super().__init__(*args, **kwargs)
        self.on_event(AttributeReportedEvent.event_type, self._mirror_summation)
        self.on_event(AttributeUpdatedEvent.event_type, self._mirror_summation)

    def _mirror_summation(
        self, event: AttributeReportedEvent | AttributeUpdatedEvent
    ) -> None:
        """Mirror the manufacturer-specific summation onto the ZCL attribute."""
        if event.attribute_name == self.AttributeDefs.current_summ_delivered_mfg.name:
            self.update_attribute(
                Metering.AttributeDefs.current_summ_delivered, event.value
            )


class SP120(CustomDevice):
    """Innr SP 120 smart plug."""

    signature = {
        MODELS_INFO: [(INNR, "SP 120")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.ON_OFF_PLUGIN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: 0x1000,
                INPUT_CLUSTERS: [
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.ON_OFF_PLUGIN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    ElectricalMeasurementClusterInnr,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    LevelControl.cluster_id,
                    MeteringClusterInnrSP120,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: 0x1000,
                INPUT_CLUSTERS: [
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
