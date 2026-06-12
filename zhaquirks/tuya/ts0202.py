"""Quirk for Tuya TS0202 IAS Zone motion sensors."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import MotionWithReset
from zhaquirks.tuya import TuyaPowerConfigurationCluster2AAA

(
    QuirkBuilder("_TZ3000_kmh5qpmb", "TS0202")
    .applies_to("_TZ3000_lf56vpxj", "TS0202")
    .replaces(MotionWithReset)
    .replaces(TuyaPowerConfigurationCluster2AAA)
    .skip_configuration()
    .add_to_registry()
)
