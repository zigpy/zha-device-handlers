"""Develco IO Module."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import BinaryInput, OnOff

(
    QuirkBuilder("frient A/S", "IOMZB-110")
    # Name the two outputs
    .change_entity_metadata(
        endpoint_id=116,
        cluster_id=OnOff.cluster_id,
        unique_id_suffix="116-6",
        new_fallback_name="COM 1",
        new_translation_key="frient_com_1",
    )
    .change_entity_metadata(
        endpoint_id=117,
        cluster_id=OnOff.cluster_id,
        unique_id_suffix="117-6",
        new_fallback_name="COM 2",
        new_translation_key="frient_com_2",
    )
    # And the two inputs
    .change_entity_metadata(
        endpoint_id=112,
        cluster_id=BinaryInput.cluster_id,
        unique_id_suffix="112-15",
        new_fallback_name="IN1",
        new_translation_key="frient_in_1",
    )
    .change_entity_metadata(
        endpoint_id=113,
        cluster_id=BinaryInput.cluster_id,
        unique_id_suffix="113-15",
        new_fallback_name="IN2",
        new_translation_key="frient_in_2",
    )
    .change_entity_metadata(
        endpoint_id=114,
        cluster_id=BinaryInput.cluster_id,
        unique_id_suffix="114-15",
        new_fallback_name="IN3",
        new_translation_key="frient_in_3",
    )
    .change_entity_metadata(
        endpoint_id=115,
        cluster_id=BinaryInput.cluster_id,
        unique_id_suffix="115-15",
        new_fallback_name="IN4",
        new_translation_key="frient_in_4",
    )
    .add_to_registry()
)
