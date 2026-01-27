"""Doorsensors."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import PollControl

# One of the long rectangular Doorsensors working on 2xAAA.
#
# It doesn't correctly implement the PollControl Cluster.
# The device will send "PollControl:checkin()" on PollControl cluster,
#     but doesn't respond when checkin_response is sent after that from the coordinator
#
# The model zbeacon DS01 sounds a lot like ("eWeLink", "DS01") from Sonoff sold as Sonoff SNZB-04
# The device tested is sold as Elivco and IHseno IH-MC01 and uses a TuYa ZTU module as described here:
#     https://github.com/dresden-elektronik/deconz-rest-plugin/issues/7415

(
    QuirkBuilder("zbeacon", "DS01")
    .removes(PollControl, endpoint_id=1)
    .add_to_registry()
)  # fmt:skip
