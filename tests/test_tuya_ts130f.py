"""Tests for Tuya TS130F curtain switch quirks."""

from unittest import mock

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent
from zigpy.zcl.clusters.closures import WindowCovering

import zhaquirks
from zhaquirks.tuya.ts130f import TuyaTS130FTI2

zhaquirks.setup()


def lift_report(tsn: int, raw_position: int) -> t.ZigbeePacket:
    """Return a Report_Attributes frame for current_position_lift_percentage.

    Same layout as frames captured from a `_TZ3000_1dd0d5yi` unit:
    fc=0x08, tsn, cmd=0x0a, attr=0x0008, type=0x20 (uint8), value.
    """
    return t.ZigbeePacket(
        profile_id=zha.PROFILE_ID,
        cluster_id=WindowCovering.cluster_id,
        src_ep=1,
        dst_ep=1,
        data=t.SerializableBytes(
            bytes([0x08, tsn, 0x0A, 0x08, 0x00, 0x20, raw_position])
        ),
    )


async def test_ts130f_drops_repeated_position_reports(zigpy_device_from_quirk):
    """A lift position report equal to the cached position is not processed."""
    device = zigpy_device_from_quirk(TuyaTS130FTI2)
    cluster = device.endpoints[1].window_covering

    events = []
    cluster.on_event(AttributeReportedEvent.event_type, events.append)
    cluster.on_event(AttributeUpdatedEvent.event_type, events.append)

    def positions():
        return [
            e.value
            for e in events
            if e.attribute_id
            == WindowCovering.AttributeDefs.current_position_lift_percentage.id
        ]

    with mock.patch.object(cluster, "send_default_rsp") as send_default_rsp:
        # Sequence captured while closing: the unit re-sends 20 about 200 ms later
        for tsn, raw_position in ((0x0D, 10), (0x0E, 20), (0x0F, 20), (0x10, 30)):
            device.packet_received(lift_report(tsn, raw_position))

    # Positions are inverted by the quirk (100 - raw) and the duplicate is dropped
    assert positions() == [90, 80, 70]
    assert (
        cluster.get(WindowCovering.AttributeDefs.current_position_lift_percentage.id)
        == 70
    )
    # Every frame is still acknowledged
    assert send_default_rsp.call_count == 4


async def test_ts130f_first_position_report_is_kept(zigpy_device_from_quirk):
    """A position report is kept when there is no cached position yet."""
    device = zigpy_device_from_quirk(TuyaTS130FTI2)
    cluster = device.endpoints[1].window_covering
    assert (
        cluster.get(WindowCovering.AttributeDefs.current_position_lift_percentage.id)
        is None
    )

    device.packet_received(lift_report(0x01, 100))

    assert (
        cluster.get(WindowCovering.AttributeDefs.current_position_lift_percentage.id)
        == 0
    )
