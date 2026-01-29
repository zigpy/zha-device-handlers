"""Device handler for hivehome.com MOT003 sensors."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.hivehome import HIVEHOME, MotionCluster

(
    QuirkBuilder(HIVEHOME, "MOT003")
    .replaces(MotionCluster, endpoint_id=6)
    .add_to_registry()
)
