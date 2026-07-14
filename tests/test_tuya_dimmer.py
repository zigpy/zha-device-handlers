"""Tests for Tuya quirks."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya.ts110e import TS110EExternalSwitchType

zhaquirks.setup()

# real frames captured from a _TZ3210_k1msuvg6 dimmer:
# genuine reports (physical toggle / command echo) have DDR=0,
# the periodic reports with the stale MCU state have DDR=1
TS110E_GENUINE_ON_REPORT = b"\x08\x89\x0a\x00\x00\x10\x01"
TS110E_GENUINE_OFF_REPORT = b"\x08\x8a\x0a\x00\x00\x10\x00"
TS110E_GENUINE_LEVEL_REPORT = b"\x08\x8b\x0a\x00\x00\x20\x94"  # level 148
TS110E_STALE_ON_REPORT = b"\x18\x8f\x0a\x00\x00\x10\x01"
TS110E_STALE_LEVEL_REPORT = b"\x18\x90\x0a\x00\x00\x20\x03"  # level 3 = "1%"


@pytest.mark.parametrize(
    "quirk", (zhaquirks.tuya.ts0601_dimmer.TuyaDoubleSwitchDimmer,)
)
async def test_command(zigpy_device_from_quirk, quirk):
    """Test write cluster attributes."""

    dimmer_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = dimmer_dev.endpoints[1].tuya_manufacturer
    dimmer1_cluster = dimmer_dev.endpoints[1].level
    switch1_cluster = dimmer_dev.endpoints[1].on_off
    switch2_cluster = dimmer_dev.endpoints[2].on_off
    tuya_listener = ClusterListener(tuya_cluster)

    assert len(tuya_listener.cluster_commands) == 0
    assert len(tuya_listener.attribute_updates) == 0

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        rsp = await switch2_cluster.command(0x0001)  # turn_on
        await wait_for_zigpy_tasks()

        m1.assert_called_with(
            cluster=61184,
            sequence=1,
            data=b"\x01\x01\x00\x00\x01\x07\x01\x00\x01\x01",
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
        )
        assert rsp.status == foundation.Status.SUCCESS

        rsp = await dimmer1_cluster.command(0x0000, 225)  # move_to_level
        await wait_for_zigpy_tasks()

        m1.assert_called_with(
            cluster=61184,
            sequence=2,
            data=b"\x01\x02\x00\x00\x02\x02\x02\x00\x04\x00\x00\x03r",
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
        )
        assert rsp.status == foundation.Status.SUCCESS

        rsp = await switch1_cluster.command(0x0001)  # turn_on
        await wait_for_zigpy_tasks()

        m1.assert_called_with(
            cluster=61184,
            sequence=3,
            data=b"\x01\x03\x00\x00\x03\x01\x01\x00\x01\x01",
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
        )
        assert rsp.status == foundation.Status.SUCCESS

        rsp = await dimmer1_cluster.command(0x0004, 125)  # move_to_level_with_on_off
        await wait_for_zigpy_tasks()

        # Should not trigger switch as it is already on
        m1.assert_called_with(
            cluster=61184,
            sequence=4,
            data=b"\x01\x04\x00\x00\x04\x02\x02\x00\x04\x00\x00\x01\xea",
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
        )
        assert rsp.status == foundation.Status.SUCCESS

        rsp = await dimmer1_cluster.command(0x0004, 0)  # move_to_level_with_on_off
        await wait_for_zigpy_tasks()

        # Should switch off without dimming
        m1.assert_called_with(
            cluster=61184,
            sequence=5,
            data=b"\x01\x05\x00\x00\x05\x01\x01\x00\x01\x00",
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
        )
        assert rsp.status == foundation.Status.SUCCESS

        rsp = await dimmer1_cluster.command(0x0004, 25)  # move_to_level_with_on_off
        await wait_for_zigpy_tasks()

        # Should switch on and then switch to level
        m1.assert_any_call(
            cluster=61184,
            sequence=6,
            data=b"\x01\x06\x00\x00\x06\x01\x01\x00\x01\x01",
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
        )
        m1.assert_called_with(
            cluster=61184,
            sequence=7,
            data=b"\x01\x07\x00\x00\x07\x02\x02\x00\x04\x00\x00\x00b",
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
        )
        assert rsp.status == foundation.Status.SUCCESS


@pytest.mark.parametrize(
    "quirk", (zhaquirks.tuya.ts0601_dimmer.TuyaDoubleSwitchDimmer,)
)
async def test_write_attr(zigpy_device_from_quirk, quirk):
    """Test write cluster attributes."""

    dimmer_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = dimmer_dev.endpoints[1].tuya_manufacturer
    dimmer1_cluster = dimmer_dev.endpoints[1].level

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        (status,) = await dimmer1_cluster.write_attributes(
            {
                "minimum_level": 25,
            }
        )
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=61184,
            sequence=1,
            data=b"\x01\x01\x00\x00\x01\x03\x02\x00\x04\x00\x00\x00b",
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

    # # write_attributes doesn't update the cluster's attribute value and
    # # delegates it to the device response message
    # succ, fail = await dimmer1_cluster.read_attributes(("minimum_level",))
    # assert succ["minimum_level"] == 25


@pytest.mark.parametrize(
    "quirk", (zhaquirks.tuya.ts0601_dimmer.TuyaDoubleSwitchDimmer,)
)
async def test_dim_values(zigpy_device_from_quirk, quirk):
    """Test dimming values."""

    dimmer_dev = zigpy_device_from_quirk(quirk)

    dimmer2_cluster = dimmer_dev.endpoints[2].level
    dimmer2_listener = ClusterListener(dimmer2_cluster)

    tuya_cluster = dimmer_dev.endpoints[1].tuya_manufacturer

    assert len(dimmer2_listener.cluster_commands) == 0
    assert len(dimmer2_listener.attribute_updates) == 0

    # payload=553
    hdr, args = tuya_cluster.deserialize(
        b"\tV\x02\x01y\x08\x02\x00\x04\x00\x00\x02\x29"
    )
    tuya_cluster.handle_message(hdr, args)
    assert len(dimmer2_listener.attribute_updates) == 1
    assert dimmer2_listener.attribute_updates[0][0] == 0x0000
    assert dimmer2_listener.attribute_updates[0][1] == 141

    succ, fail = await dimmer2_cluster.read_attributes(("current_level",))
    assert succ["current_level"] == 141

    # payload=700
    hdr, args = tuya_cluster.deserialize(
        b"\tV\x02\x01y\x08\x02\x00\x04\x00\x00\x02\xbc"
    )
    tuya_cluster.handle_message(hdr, args)
    succ, fail = await dimmer2_cluster.read_attributes(("current_level",))
    assert succ["current_level"] == 178

    # payload=982
    hdr, args = tuya_cluster.deserialize(
        b"\tV\x02\x01y\x08\x02\x00\x04\x00\x00\x03\xd6"
    )
    tuya_cluster.handle_message(hdr, args)
    succ, fail = await dimmer2_cluster.read_attributes(("current_level",))
    assert succ["current_level"] == 250

    # payload=657
    hdr, args = tuya_cluster.deserialize(
        b"\tV\x02\x01y\x08\x02\x00\x04\x00\x00\x02\x91"
    )
    tuya_cluster.handle_message(hdr, args)
    succ, fail = await dimmer2_cluster.read_attributes(("current_level",))
    assert succ["current_level"] == 167

    # payload=400
    hdr, args = tuya_cluster.deserialize(
        b"\tV\x02\x01y\x08\x02\x00\x04\x00\x00\x01\x90"
    )
    tuya_cluster.handle_message(hdr, args)
    succ, fail = await dimmer2_cluster.read_attributes(("current_level",))
    assert succ["current_level"] == 102

    # payload=149
    hdr, args = tuya_cluster.deserialize(
        b"\tV\x02\x01y\x08\x02\x00\x04\x00\x00\x00\x95"
    )
    tuya_cluster.handle_message(hdr, args)
    succ, fail = await dimmer2_cluster.read_attributes(("current_level",))
    assert succ["current_level"] == 37

    # payload=339
    hdr, args = tuya_cluster.deserialize(
        b"\tV\x02\x01y\x08\x02\x00\x04\x00\x00\x01\x53"
    )
    tuya_cluster.handle_message(hdr, args)
    succ, fail = await dimmer2_cluster.read_attributes(("current_level",))
    assert succ["current_level"] == 86


@pytest.mark.parametrize(
    "quirk", (zhaquirks.tuya.ts0601_dimmer.TuyaDoubleSwitchDimmer,)
)
async def test_doubledimmer_state_report(zigpy_device_from_quirk, quirk):
    """Test tuya double switch."""

    TUYA_EP2_DIMM_1 = b"\tV\x02\x01y\x08\x02\x00\x04\x00\x00\x02\xc5"
    TUYA_EP2_DIMM_2 = b"\tW\x02\x01z\x08\x02\x00\x04\x00\x00\x02\x9e"

    dimmer_dev = zigpy_device_from_quirk(quirk)

    dimmer1_cluster = dimmer_dev.endpoints[1].level
    dimmer1_listener = ClusterListener(dimmer1_cluster)

    dimmer2_cluster = dimmer_dev.endpoints[2].level
    dimmer2_listener = ClusterListener(dimmer2_cluster)

    tuya_cluster = dimmer_dev.endpoints[1].tuya_manufacturer

    assert len(dimmer1_listener.cluster_commands) == 0
    assert len(dimmer1_listener.attribute_updates) == 0
    assert len(dimmer2_listener.cluster_commands) == 0
    assert len(dimmer2_listener.attribute_updates) == 0

    # events from channel 2 updates only EP 2
    hdr, args = tuya_cluster.deserialize(TUYA_EP2_DIMM_1)
    tuya_cluster.handle_message(hdr, args)
    assert len(dimmer1_listener.attribute_updates) == 0
    assert len(dimmer2_listener.attribute_updates) == 1
    assert dimmer2_listener.attribute_updates[0][0] == 0x0000
    assert dimmer2_listener.attribute_updates[0][1] == 180

    # events from channel 1 updates only EP 1
    hdr, args = tuya_cluster.deserialize(TUYA_EP2_DIMM_2)
    tuya_cluster.handle_message(hdr, args)
    assert len(dimmer1_listener.attribute_updates) == 0
    assert len(dimmer2_listener.attribute_updates) == 2
    assert dimmer2_listener.attribute_updates[1][0] == 0x0000
    assert dimmer2_listener.attribute_updates[1][1] == 170


@pytest.fixture
def ts110e_k1msuvg6(zigpy_device_from_v2_quirk):
    """TS110E _TZ3210_k1msuvg6 device with the v2 quirk applied."""
    return zigpy_device_from_v2_quirk("_TZ3210_k1msuvg6", "TS110E")


async def test_ts110e_k1msuvg6_stale_report_filter(ts110e_k1msuvg6):
    """Genuine reports update the state, stale MCU reports are dropped."""
    on_off_cluster = ts110e_k1msuvg6.endpoints[1].on_off
    level_cluster = ts110e_k1msuvg6.endpoints[1].level
    on_off_listener = ClusterListener(on_off_cluster)
    level_listener = ClusterListener(level_cluster)

    # seed a known level so the unknown-brightness logic stays out of the way
    level_cluster.update_attribute(LevelControl.AttributeDefs.current_level.id, 148)

    # genuine off report (DDR=0) is accepted
    hdr, args = on_off_cluster.deserialize(TS110E_GENUINE_OFF_REPORT)
    on_off_cluster.handle_message(hdr, args)
    assert on_off_cluster.get(OnOff.AttributeDefs.on_off.id) == 0

    # stale on report (DDR=1) is dropped, light stays off
    hdr, args = on_off_cluster.deserialize(TS110E_STALE_ON_REPORT)
    on_off_cluster.handle_message(hdr, args)
    assert on_off_cluster.get(OnOff.AttributeDefs.on_off.id) == 0

    # stale level report (DDR=1) is dropped, level stays intact
    hdr, args = level_cluster.deserialize(TS110E_STALE_LEVEL_REPORT)
    level_cluster.handle_message(hdr, args)
    assert level_cluster.get(LevelControl.AttributeDefs.current_level.id) == 148

    # genuine level report (DDR=0) is accepted
    hdr, args = level_cluster.deserialize(TS110E_GENUINE_LEVEL_REPORT)
    level_cluster.handle_message(hdr, args)
    assert level_cluster.get(LevelControl.AttributeDefs.current_level.id) == 0x94

    assert len(on_off_listener.attribute_updates) == 1
    # seeded level + genuine report
    assert len(level_listener.attribute_updates) == 2


async def test_ts110e_k1msuvg6_cache_only_reads(ts110e_k1msuvg6):
    """Reads of on_off/current_level are served from cache, others pass."""
    on_off_cluster = ts110e_k1msuvg6.endpoints[1].on_off

    with mock.patch.object(
        on_off_cluster, "request", mock.AsyncMock(return_value=[[]])
    ) as m1:
        # not cached yet -> no result, but the device is not queried
        succ, fail = await on_off_cluster.read_attributes(["on_off"])
        assert m1.call_count == 0
        assert "on_off" not in succ

        # cached after a genuine report -> served from cache, no device query
        hdr, args = on_off_cluster.deserialize(TS110E_GENUINE_ON_REPORT)
        on_off_cluster.handle_message(hdr, args)
        succ, fail = await on_off_cluster.read_attributes(["on_off"])
        assert m1.call_count == 0
        assert succ["on_off"] == 1

        # reads of other attributes still go to the device
        await on_off_cluster.read_attributes(["start_up_on_off"])
        assert m1.call_count == 1


async def test_ts110e_k1msuvg6_on_before_brightness(ts110e_k1msuvg6):
    """An explicit on() is sent before move_to_level_with_on_off."""
    level_cluster = ts110e_k1msuvg6.endpoints[1].level

    with mock.patch.object(
        level_cluster.endpoint, "request", mock.AsyncMock(return_value=None)
    ) as m1:
        await level_cluster.command(
            LevelControl.ServerCommandDefs.move_to_level_with_on_off.id,
            level=100,
            transition_time=0,
        )
        await wait_for_zigpy_tasks()

        assert [call.kwargs["cluster"] for call in m1.mock_calls] == [
            OnOff.cluster_id,
            LevelControl.cluster_id,
        ]

    # level 0 turns the light off: no on() beforehand
    with mock.patch.object(
        level_cluster.endpoint, "request", mock.AsyncMock(return_value=None)
    ) as m2:
        await level_cluster.command(
            LevelControl.ServerCommandDefs.move_to_level_with_on_off.id,
            level=0,
            transition_time=0,
        )
        await wait_for_zigpy_tasks()

        assert [call.kwargs["cluster"] for call in m2.mock_calls] == [
            LevelControl.cluster_id
        ]


async def test_ts110e_k1msuvg6_unknown_brightness_forced(ts110e_k1msuvg6):
    """Turning on with no known brightness forces full brightness."""
    on_off_cluster = ts110e_k1msuvg6.endpoints[1].on_off
    level_cluster = ts110e_k1msuvg6.endpoints[1].level

    with mock.patch.object(
        level_cluster.endpoint, "request", mock.AsyncMock(return_value=None)
    ) as m1:
        hdr, args = on_off_cluster.deserialize(TS110E_GENUINE_ON_REPORT)
        on_off_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

        assert level_cluster.get(LevelControl.AttributeDefs.current_level.id) == 254
        # pre-on() plus the move_to_level_with_on_off command
        assert [call.kwargs["cluster"] for call in m1.mock_calls] == [
            OnOff.cluster_id,
            LevelControl.cluster_id,
        ]


async def test_ts110e_k1msuvg6_known_brightness_untouched(ts110e_k1msuvg6):
    """Turning on with a known brightness sends nothing to the device."""
    on_off_cluster = ts110e_k1msuvg6.endpoints[1].on_off
    level_cluster = ts110e_k1msuvg6.endpoints[1].level
    level_cluster.update_attribute(LevelControl.AttributeDefs.current_level.id, 148)

    with mock.patch.object(
        level_cluster.endpoint, "request", mock.AsyncMock(return_value=None)
    ) as m1:
        hdr, args = on_off_cluster.deserialize(TS110E_GENUINE_ON_REPORT)
        on_off_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

        assert m1.call_count == 0
        assert level_cluster.get(LevelControl.AttributeDefs.current_level.id) == 148


def test_ts110e_k1msuvg6_switch_type_attribute(ts110e_k1msuvg6):
    """The external switch type attribute and select entity are exposed."""
    level_cluster = ts110e_k1msuvg6.endpoints[1].level

    attr_def = level_cluster.attributes_by_name["external_switch_type"]
    assert attr_def.id == 0xFC02
    assert attr_def.type is TS110EExternalSwitchType
