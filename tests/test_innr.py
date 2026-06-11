"""Tests for Innr quirks."""

from zigpy.profiles import zll
import zigpy.types as t
from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.innr import MeteringClusterInnrNew, MeteringClusterInnrOld
from zhaquirks.innr.innr_sp120_plug import SP120, MeteringClusterInnrSP120

# Real SP 120 device-initiated metering report:
#   fc=0x1c   -> manufacturer-specific, server-to-client, disable-default-response
#   manuf=0x1166 (Innr), TSN=0x16, cmd=0x0a (Report_Attributes)
#   attr 0x0430 (Innr manufacturer-specific, uint64) = 0
#   attr 0x0000 (current_summ_delivered, uint48)     = 35
SP120_MANUF_SUMMATION_REPORT = (
    b"\x1c\x66\x11\x16\x0a"
    b"\x30\x04\x27\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x25\x23\x00\x00\x00\x00\x00"
)


async def test_sp120_manufacturer_framed_summation(zigpy_device_from_quirk):
    """SP 120 reports current_summ_delivered inside a manufacturer-specific frame.

    The firmware sets the manufacturer-specific bit on its device-initiated
    metering report even though it carries the *standard* current_summ_delivered
    attribute. Without the quirk, zigpy resolves the attribute against the frame's
    manufacturer code, fails to match the standard attribute, and drops the report
    as an unknown manufacturer attribute (name resolves to ``None``) -- so the
    energy sensor only updates on startup reads. The quirk defines the
    manufacturer-specific attribute the device reports and mirrors its value onto
    the standard ZCL attribute, so the energy sensor updates again.
    """
    device = zigpy_device_from_quirk(SP120)
    metering_cluster = device.endpoints[1].smartenergy_metering

    events = []
    metering_cluster.on_event(AttributeReportedEvent.event_type, events.append)
    metering_cluster.on_event(AttributeUpdatedEvent.event_type, events.append)

    device.packet_received(
        t.ZigbeePacket(
            profile_id=zll.PROFILE_ID,
            cluster_id=Metering.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(SP120_MANUF_SUMMATION_REPORT),
        )
    )

    # The report must resolve to the *named* standard attribute. Without the
    # quirk, the manufacturer-framed report yields an unknown attribute with
    # ``attribute_name is None``, which ZHA never maps to the energy entity.
    summation_events = [
        e
        for e in events
        if e.attribute_name == Metering.AttributeDefs.current_summ_delivered.name
    ]
    assert summation_events, "current_summ_delivered report was not parsed"
    assert summation_events[-1].value == 35

    # ...and it is cached as the standard attribute the energy sensor reads.
    # ZHA reads by name; the bare attribute ID 0x0000 is intentionally ambiguous
    # now that a manufacturer-specific attribute shares it.
    cached, _ = await metering_cluster.read_attributes(
        ["current_summ_delivered"], only_cache=True
    )
    assert cached["current_summ_delivered"] == 35


async def test_sp120_plain_summation_still_parses(zigpy_device_from_quirk):
    """A normal (non-manufacturer) summation report is unaffected by the override."""
    device = zigpy_device_from_quirk(SP120)
    metering_cluster = device.endpoints[1].smartenergy_metering

    events = []
    metering_cluster.on_event(AttributeReportedEvent.event_type, events.append)
    metering_cluster.on_event(AttributeUpdatedEvent.event_type, events.append)

    # fc=0x18 (no manufacturer bit), TSN=0x01, cmd=0x0a,
    # attr 0x0000 (current_summ_delivered, uint48) = 1234
    device.packet_received(
        t.ZigbeePacket(
            profile_id=zll.PROFILE_ID,
            cluster_id=Metering.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(
                b"\x18\x01\x0a\x00\x00\x25\xd2\x04\x00\x00\x00\x00"
            ),
        )
    )

    summation_events = [
        e
        for e in events
        if e.attribute_name == Metering.AttributeDefs.current_summ_delivered.name
    ]
    assert summation_events, "current_summ_delivered report was not parsed"
    assert summation_events[-1].value == 1234
    cached, _ = await metering_cluster.read_attributes(
        ["current_summ_delivered"], only_cache=True
    )
    assert cached["current_summ_delivered"] == 1234


def test_metering_manuf_mirror_scoped_to_sp120() -> None:
    """Only the SP 120 cluster carries the manufacturer-framed summation handling.

    The manufacturer-framing is a quirk of the SP 120's old JN516x firmware. The
    SP 234 and SP 240/242/244 family (different firmware/stacks that report
    summation normally) keep the plain metering clusters, so they don't carry the
    extra manufacturer attribute (nor the same-ID lookup ambiguity it introduces).
    """
    mfg_attr = "current_summ_delivered_mfg"
    # SP 120 cluster recovers it
    assert mfg_attr in MeteringClusterInnrSP120.attributes_by_name
    # SP 234 / SP 240 (old & new firmware) clusters do not
    assert mfg_attr not in MeteringClusterInnrOld.attributes_by_name
    assert mfg_attr not in MeteringClusterInnrNew.attributes_by_name
    # the standard attribute remains intact on all of them
    for cls in (
        MeteringClusterInnrSP120,
        MeteringClusterInnrOld,
        MeteringClusterInnrNew,
    ):
        assert "current_summ_delivered" in cls.attributes_by_name
