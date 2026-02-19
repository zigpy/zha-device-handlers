"""Ubisys Cover J1 quirk."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks.quirk_ids import SE_POLL_SUMMATION
from zhaquirks.ubisys import UbisysCluster, UbisysInputConfigCluster


class UbisysElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Sets divisor attributes missing on the device."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 1000,
    }


class UbisysJ1InputConfigCluster(UbisysInputConfigCluster):
    """Input configuration for the J1.

    EP2 -> EP1 with WindowCovering self-binding.
    Only detached mode is exposed (input_mode templates are OnOff-based
    and don't apply to cover commands).
    """

    BIND_CLUSTERS: list[int] = [WindowCovering.cluster_id]


(
    QuirkBuilder(manufacturer="ubisys", model="J1 (5502)")
    .replaces(UbisysCluster, endpoint_id=232)
    .adds(UbisysJ1InputConfigCluster)
    .switch(
        attribute_name=UbisysJ1InputConfigCluster.AttributeDefs.detached.name,
        cluster_id=UbisysJ1InputConfigCluster.cluster_id,
        translation_key="detached",
        fallback_name="Detached mode",
    )
    .applies_to(manufacturer="ubisys", model="J1-R (5602)")
    .replaces(UbisysElectricalMeasurement, endpoint_id=3)
    # The device exposes total active power on multiple attributes,
    # but only supports attribute reporting on the SE "instantaneous demand" attribute,
    # so we disable the other entities by default
    # TODO: Disabling this entity also disables polling for the entire EM cluster in ZHA
    .change_entity_metadata(
        endpoint_id=3,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="3-2820",  # no translation key and no actual suffix for this
        new_entity_registry_enabled_default=False,
    )
    .change_entity_metadata(
        endpoint_id=3,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="total_active_power",
        new_entity_registry_enabled_default=False,
    )
    # SmartEnergy summation attributes do not support attribute reporting, need polling
    # TODO: Add support for this in ZHA
    .exposes_feature(SE_POLL_SUMMATION)
    # TODO: Fix/rework/rethink EM polling
    # ElectricalMeasurement cluster does not support attribute reporting at all,
    # so poll current explicitly (active power does, but if disabled, nothing will poll)
    # .exposes_feature(EM_POLL_CURRENT)
    .add_to_registry()
)
