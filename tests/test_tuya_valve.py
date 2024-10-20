"""Tests for Tuya quirks."""

from datetime import datetime, timezone
from unittest import mock
from unittest.mock import patch

import pytest
from zigpy.quirks.v2 import EntityMetadata
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
import zhaquirks.tuya
import zhaquirks.tuya.ts0601_valve

zhaquirks.setup()


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_valve.ParksidePSBZS,))
async def test_command_psbzs(zigpy_device_from_quirk, quirk):
    """Test executing cluster commands for PARKSIDE water valve."""

    water_valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = water_valve_dev.endpoints[1].tuya_manufacturer
    switch_cluster = water_valve_dev.endpoints[1].on_off
    tuya_listener = ClusterListener(tuya_cluster)

    assert len(tuya_listener.cluster_commands) == 0
    assert len(tuya_listener.attribute_updates) == 0

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        rsp = await switch_cluster.command(0x0001)

        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=61184,
            sequence=1,
            data=b"\x01\x01\x00\x00\x01\x01\x01\x00\x01\x01",
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert rsp.status == foundation.Status.SUCCESS


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_valve.ParksidePSBZS,))
async def test_write_attr_psbzs(zigpy_device_from_quirk, quirk):
    """Test write cluster attributes for PARKSIDE water valve."""

    water_valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = water_valve_dev.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        (status,) = await tuya_cluster.write_attributes(
            {
                "timer_duration": 15,
            }
        )
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=61184,
            sequence=1,
            data=b"\x01\x01\x00\x00\x01\x05\x02\x00\x04\x00\x00\x00\x0f",
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await tuya_cluster.write_attributes(
            {
                "frost_lock_reset": 0,
            }
        )
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=61184,
            sequence=2,
            data=b"\x01\x02\x00\x00\x02m\x01\x00\x01\x00",
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_valve.ParksidePSBZS,))
async def test_report_values_psbzs(zigpy_device_from_quirk, quirk):
    """Test receiving attributes from PARKSIDE water valve."""

    water_valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = water_valve_dev.endpoints[1].tuya_manufacturer
    tuya_listener = ClusterListener(tuya_cluster)

    assert len(tuya_listener.cluster_commands) == 0
    assert len(tuya_listener.attribute_updates) == 0

    frames = (
        b"\x09\x5d\x02\x00\x4c\x06\x02\x00\x04\x00\x00\x00\x04",  # time left 4min
        b"\x09\x5d\x02\x00\x4c\x06\x02\x00\x04\x00\x00\x02\x57",  # time left max 599min
        b"\x09\x56\x02\x00\x21\x6c\x01\x00\x01\x01",  # frost lock active
        b"\x09\x56\x02\x00\x21\x6c\x01\x00\x01\x00",  # frost lock inactive
    )
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(tuya_listener.attribute_updates) == 4
    assert tuya_listener.attribute_updates[0][0] == 0xEF12
    assert tuya_listener.attribute_updates[0][1] == 4
    assert tuya_listener.attribute_updates[1][0] == 0xEF12
    assert tuya_listener.attribute_updates[1][1] == 599
    assert tuya_listener.attribute_updates[2][0] == 0xEF13
    assert tuya_listener.attribute_updates[2][1] == 0  # frost lock state is inverted
    assert tuya_listener.attribute_updates[3][0] == 0xEF13
    assert tuya_listener.attribute_updates[3][1] == 1  # frost lock state is inverted


@pytest.mark.parametrize(
    "model,manuf,use_minutes",
    [
        ("_TZE200_sh1btabb", "TS0601", True),
        ("_TZE200_a7sghmms", "TS0601", False),
        ("_TZE204_a7sghmms", "TS0601", False),
        ("_TZE200_7ytb3h8u", "TS0601", False),
        ("_TZE204_7ytb3h8u", "TS0601", False),
        ("_TZE284_7ytb3h8u", "TS0601", False),
    ],
)
async def test_giex_02_quirk(zigpy_device_from_v2_quirk, model, manuf, use_minutes):
    """Test Giex GX02 Valve Quirk."""

    quirked_device = zigpy_device_from_v2_quirk(model, manuf)
    metering_cluster = quirked_device.endpoints[1].smartenergy_metering
    assert metering_cluster.unsupported_attributes == {0x0400, "instantaneous_demand"}
    for entity in range(6, 8):
        number_metadata: EntityMetadata = quirked_device.exposes_metadata[
            (1, zhaquirks.tuya.TUYA_CLUSTER_ID, ClusterType.Server)
        ][entity]

        if not use_minutes:
            assert number_metadata.max == zhaquirks.tuya.ts0601_valve.GIEX_12HRS_AS_SEC
        else:
            assert number_metadata.max == zhaquirks.tuya.ts0601_valve.GIEX_24HRS_AS_MIN


async def test_giex_functions():
    """Test various Giex Valve functions."""
    assert zhaquirks.tuya.ts0601_valve.giex_string_to_td("12:01:05,3") == 43265
    assert zhaquirks.tuya.ts0601_valve.giex_string_to_ts("--:--:--") is None

    class MockDatetime:
        def now(self, tz: timezone):
            """Mock now."""
            return datetime(2024, 10, 2, 12, 10, 23, tzinfo=tz)

        def strptime(self, v: str, fmt: str):
            """Mock strptime."""
            return datetime.strptime(v, fmt)

    with patch("zhaquirks.tuya.ts0601_valve.datetime", MockDatetime()):
        assert (
            zhaquirks.tuya.ts0601_valve.giex_string_to_ts("20:12:01")
            == datetime.fromisoformat("2024-10-02T12:10:23+04:00").timestamp()
            + zhaquirks.tuya.ts0601_valve.UNIX_EPOCH_TO_ZCL_EPOCH
        )


@pytest.mark.parametrize(
    "model,manuf",
    [
        ("_TZE284_8zizsafo", "TS0601"),
    ],
)
async def test_giex_03_quirk(zigpy_device_from_v2_quirk, model, manuf):
    """Test Giex GX03 Valve Quirk."""

    quirked_device = zigpy_device_from_v2_quirk(model, manuf)
    tuya_cluster = quirked_device.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        (status,) = await tuya_cluster.write_attributes(
            {
                "valve_duration_1": 10,
            }
        )
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=61184,
            sequence=1,
            data=b"\x01\x01\x00\x00\x01\x19\x02\x00\x04\x00\x00\x00\x0a",
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]
