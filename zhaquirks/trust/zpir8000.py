"""Device handler for Trust ZPIR-8000 sensors."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import MotionWithReset


class MotionCluster(MotionWithReset):
    """Motion cluster."""

    reset_s: int = 30


(
    QuirkBuilder("ADUROLIGHT", "VMS_ADUROLIGHT")
    .replaces(MotionCluster, endpoint_id=1)
    .add_to_registry()
)
