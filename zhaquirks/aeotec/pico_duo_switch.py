"""Aeotec Pico Duo Switch (ZGA003)."""

from zha.application.platforms.sensor import DeviceTemperature
from zigpy.zcl.clusters.general import DeviceTemperature as DeviceTemperatureCluster

from zhaquirks.aeotec.pico_switch import (
    AeotecSwitchActions,
    AeotecSwitchType,
    AeotecSwitchTypeConfigCluster,
    WholeDegreeDeviceTemperature,
)
from zhaquirks.builder import QuirkBuilder

(
    QuirkBuilder("AEOTEC", "ZGA003")
    .friendly_name(manufacturer="Aeotec", model="Pico Duo Switch")
    # Relays are on endpoints 1 and 2, external switch inputs are on endpoints 3 and 4
    .replaces(AeotecSwitchTypeConfigCluster, endpoint_id=3)
    .replaces(AeotecSwitchTypeConfigCluster, endpoint_id=4)
    # S1 controls relay 1 and S2 controls relay 2, so each child device takes the
    # relay's endpoint and its input's endpoint. ZHA's automatic split would only take
    # the relay endpoints and leave the input settings on the main device; the ids and
    # names match the child devices it would create.
    .child_device(
        "1",
        endpoint_ids=[1, 3],
        translation_key="channel",
        translation_placeholders={"index": "1"},
        fallback_name="Channel 1",
    )
    .child_device(
        "2",
        endpoint_ids=[2, 4],
        translation_key="channel",
        translation_placeholders={"index": "2"},
        fallback_name="Channel 2",
    )
    .replaces_entity(
        DeviceTemperature,
        WholeDegreeDeviceTemperature,
        endpoint_id=1,
        cluster_id=DeviceTemperatureCluster.cluster_id,
    )
    # S1 input
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_type.name,
        enum_class=AeotecSwitchType,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        translation_key="switch_type_id",
        fallback_name="S1 switch type",
        translation_placeholders={"id": "S1"},
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_actions.name,
        enum_class=AeotecSwitchActions,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        translation_key="switch_actions_id",
        fallback_name="S1 switch actions",
        translation_placeholders={"id": "S1"},
    )
    .switch(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.controls.name,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        translation_key="local_control_id",
        fallback_name="S1 local control",
        translation_placeholders={"id": "S1"},
    )
    # S2 input
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_type.name,
        enum_class=AeotecSwitchType,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=4,
        translation_key="switch_type_id",
        fallback_name="S2 switch type",
        translation_placeholders={"id": "S2"},
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_actions.name,
        enum_class=AeotecSwitchActions,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=4,
        translation_key="switch_actions_id",
        fallback_name="S2 switch actions",
        translation_placeholders={"id": "S2"},
    )
    .switch(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.controls.name,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=4,
        translation_key="local_control_id",
        fallback_name="S2 local control",
        translation_placeholders={"id": "S2"},
    )
    .add_to_registry()
)
