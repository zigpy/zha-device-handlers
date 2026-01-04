"""Device handler for Sercomm SZ-WTD02N flood sensor."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.sercomm import SERCOMM, SercommPowerConfiguration

(
    QuirkBuilder(SERCOMM, "SZ-WTD02N_SF")
    .replaces(SercommPowerConfiguration, endpoint_id=1)
    .add_to_registry()
)
