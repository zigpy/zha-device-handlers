"""Tests for Innr quirks."""

from zigpy.profiles import zll
import zigpy.types as t
from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.innr.innr_sp120_plug import SP120

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
    """The manufacturer-framed summation report updates current_summ_delivered."""
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

    # Must resolve to the named standard attribute (None without the quirk).
    summation_events = [
        e
        for e in events
        if e.attribute_name == Metering.AttributeDefs.current_summ_delivered.name
    ]
    assert len(summation_events) == 1
    assert summation_events[0].value == 35

    # ...and cached as the standard attribute the energy sensor reads.
    assert metering_cluster.get(Metering.AttributeDefs.current_summ_delivered) == 35


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
    assert len(summation_events) == 1
    assert summation_events[0].value == 1234
    assert metering_cluster.get(Metering.AttributeDefs.current_summ_delivered) == 1234
