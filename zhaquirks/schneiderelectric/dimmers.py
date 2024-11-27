"""Schneider Electric dimmers and switches quirks."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.schneiderelectric import (
    SE_MANUF_NAME,
    SEBallast,
    SEBasic,
    SEOnOff,
    SESpecific,
)

(
    QuirkBuilder(SE_MANUF_NAME, "NHROTARY/DIMMER/1")
    .applies_to(SE_MANUF_NAME, "NHROTARY/UNIDIM/1")
    .applies_to(SE_MANUF_NAME, "NHPB/DIMMER/1")
    .applies_to(SE_MANUF_NAME, "NHPB/UNIDIM/1")
    .replaces(SEBasic, endpoint_id=3)
    .replaces(SEBallast, endpoint_id=3)
    .replaces(SEOnOff, endpoint_id=3)
    .replaces(SEBasic, endpoint_id=21)
    .replaces(SESpecific, endpoint_id=21)
    .add_to_registry()
)

(
    QuirkBuilder(SE_MANUF_NAME, "NHPB/SWITCH/1")
    .replaces(SEBasic)
    .replaces(SEOnOff)
    .replaces(SEBasic, endpoint_id=21)
    .replaces(SESpecific, endpoint_id=21)
    .add_to_registry()
)
