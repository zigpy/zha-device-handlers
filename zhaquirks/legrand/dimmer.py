"""Module for Legrand dimmers."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import BinaryInput, OnOff
from zigpy.zcl.clusters.lighting import Ballast

from zhaquirks.legrand import (
    LEGRAND,
    DeviceMode,
    LegrandCluster,
    LegrandIdentify,
    LegrandPowerConfigurationCluster,
)

# Some devices with firmware 0x39 have Ballast cluster,
# but some of them don't. But in any case Ballast works,
# if we add it here.
(
    QuirkBuilder(f" {LEGRAND}", " Dimmer switch w/o neutral")
    .replaces(LegrandCluster, endpoint_id=1)
    .replaces(LegrandCluster, cluster_type=ClusterType.Client, endpoint_id=1)
    .adds(Ballast, endpoint_id=1)
    .add_to_registry()
)


(
    QuirkBuilder(f" {LEGRAND}", " Dimmer switch with neutral")
    .replaces(LegrandCluster)
    .replaces(LegrandIdentify)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=BinaryInput.cluster_id)
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.device_class == "opening",
    )
    .switch(
        attribute_name=LegrandCluster.AttributeDefs.device_mode.name,
        cluster_id=LegrandCluster.cluster_id,
        on_value=DeviceMode.Dimmer_On,
        off_value=DeviceMode.Dimmer_Off,
        translation_key="dimmer_mode",
        fallback_name="Dimmer mode",
    )
    .switch(
        attribute_name=LegrandCluster.AttributeDefs.led_dark.name,
        cluster_id=LegrandCluster.cluster_id,
        translation_key="turn_on_led_when_off",
        fallback_name="Turn on LED when off",
    )
    .switch(
        attribute_name=LegrandCluster.AttributeDefs.led_on.name,
        cluster_id=LegrandCluster.cluster_id,
        translation_key="turn_on_led_when_on",
        fallback_name="Turn on LED when on",
    )
    .add_to_registry()
)


(
    QuirkBuilder(f" {LEGRAND}", " Remote dimmer switch")
    .replaces(LegrandPowerConfigurationCluster, endpoint_id=1)
    .replaces(LegrandCluster, endpoint_id=1)
    .replaces(LegrandCluster, cluster_type=ClusterType.Client, endpoint_id=1)
    .add_to_registry()
)
