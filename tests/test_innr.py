"""Tests for Innr quirks."""

import pytest
from zigpy.profiles import zll
import zigpy.types as t
from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks
from zhaquirks.innr import MeteringClusterInnrNew, MeteringClusterInnrOld
from zhaquirks.innr.innr_sp120_plug import SP120

zhaquirks.setup()

# firmware version that fixed the metering divisor bug (max_version is exclusive)
SP240_DIVISOR_FIX_FW_VERSION = 0x191B3685


@pytest.mark.parametrize(
    ("firmware_version", "expected_cluster", "expected_divisor"),
    [
        # firmware before the fix uses the old override (divisor 100)
        (
            SP240_DIVISOR_FIX_FW_VERSION - 1,
            MeteringClusterInnrOld,
            100,
        ),
        # the fixed firmware and newer use the new override (divisor 1000)
        (
            SP240_DIVISOR_FIX_FW_VERSION,
            MeteringClusterInnrNew,
            1000,
        ),
        (
            SP240_DIVISOR_FIX_FW_VERSION + 1,
            MeteringClusterInnrNew,
            1000,
        ),
        # a device that does not report a firmware version is treated as new
        # (the new quirk has allow_missing=True, the old one allow_missing=False)
        (
            None,
            MeteringClusterInnrNew,
            1000,
        ),
    ],
)
def test_innr_sp240_firmware_version_metering(
    zigpy_device_from_v2_quirk,
    firmware_version,
    expected_cluster,
    expected_divisor,
):
    """Test the correct Innr SP 240 quirk is selected based on firmware version."""
    device = zigpy_device_from_v2_quirk(
        "innr", "SP 240", firmware_version=firmware_version
    )

    metering_cluster = device.endpoints[1].smartenergy_metering
    assert isinstance(metering_cluster, expected_cluster)

    # the constant divisor override is applied regardless of what the device reports
    assert metering_cluster.get(Metering.AttributeDefs.divisor.id) == expected_divisor


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
