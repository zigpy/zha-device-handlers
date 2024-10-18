"""Tests for Tuya quirks."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks

zhaquirks.setup()


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
            priority=t.PacketPriority.NORMAL,
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
            priority=t.PacketPriority.NORMAL,
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
            priority=t.PacketPriority.NORMAL,
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
            priority=t.PacketPriority.NORMAL,
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
            priority=t.PacketPriority.NORMAL,
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
            priority=t.PacketPriority.NORMAL,
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
            priority=t.PacketPriority.NORMAL,
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
            priority=t.PacketPriority.NORMAL,
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
