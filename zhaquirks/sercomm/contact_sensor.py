"""Device handler for Sercomm XHS2-SE contact sensor."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.sercomm import SERCOMM, SercommPowerConfiguration

(QuirkBuilder(SERCOMM, "XHS2-SE").replaces(SercommPowerConfiguration).add_to_registry())
