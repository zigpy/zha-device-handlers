"""Tests for Tuya quirks."""

from unittest import mock

import pytest
from zigpy.zcl import foundation

import zhaquirks

from tests.common import ClusterListener, wait_for_zigpy_tasks

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
            61184,
            1,
            b"\x01\x01\x00\x00\x01\x01\x01\x00\x01\x01",
            expect_reply=True,
            command_id=0,
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
            61184,
            1,
            b"\x01\x01\x00\x00\x01\x05\x02\x00\x04\x00\x00\x00\x0f",
            expect_reply=False,
            command_id=0,
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
            61184,
            2,
            b"\x01\x02\x00\x00\x02m\x01\x00\x01\x00",
            expect_reply=False,
            command_id=0,
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
        b"\x09\x5D\x02\x00\x4C\x06\x02\x00\x04\x00\x00\x00\x04",  # time left 4min
        b"\x09\x5D\x02\x00\x4C\x06\x02\x00\x04\x00\x00\x02\x57",  # time left max 599min
        b"\x09\x56\x02\x00\x21\x6C\x01\x00\x01\x01",  # frost lock active
        b"\x09\x56\x02\x00\x21\x6C\x01\x00\x01\x00",  # frost lock inactive
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
