"""Module for Legrand shutter switches."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import BinaryInput, OnOff

from zhaquirks.legrand import (
    LEGRAND,
    LegrandCluster,
    LegrandIdentify,
    LegrandShutterCluster,
    ShutterCalibrationMode,
)

(
    QuirkBuilder(f" {LEGRAND}", " Shutter SW with level control")
    .replaces(LegrandCluster)
    .replaces(LegrandIdentify)
    .replaces(LegrandShutterCluster)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=BinaryInput.cluster_id)
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.device_class == "opening",
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
    .enum(
        attribute_name=LegrandShutterCluster.AttributeDefs.calibration_mode.name,
        cluster_id=LegrandShutterCluster.cluster_id,
        enum_class=ShutterCalibrationMode,
        translation_key="calibration_mode",
        fallback_name="Calibration mode",
    )
    .add_to_registry()
)
