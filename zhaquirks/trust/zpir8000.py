"""Device handler for Trust ZPIR-8000 sensors."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.trust import MotionCluster

(QuirkBuilder("ADUROLIGHT", "VMS_ADUROLIGHT").replaces(MotionCluster).add_to_registry())
