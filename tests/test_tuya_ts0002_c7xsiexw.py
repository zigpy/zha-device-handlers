"""Tests for _TZ3000_c7xsiexw TS0002."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic

from zhaquirks.tuya.ts0002_c7xsiexw import TS0002C7XSDevice


@pytest.mark.asyncio
async def test_ts0002_c7xsiexw_commissioning(device_mock):
    """Test the proprietary relay separation commissioning sequence."""

    device_mock.manufacturer = "_TZ3000_c7xsiexw"
    device_mock.model = "TS0002"

    # The builder-created quirk should use our custom Zigpy device class.
    quirked = DEVICE_REGISTRY.resolve(device_mock)

    assert isinstance(quirked, TS0002C7XSDevice)

    with (
        mock.patch.object(
            quirked.application,
            "get_sequence",
            side_effect=[1, 2, 3],
        ),
        mock.patch.object(
            quirked,
            "request",
            new=mock.AsyncMock(),
        ) as request_mock,
        mock.patch(
            "zhaquirks.tuya.ts0002_c7xsiexw.asyncio.sleep",
            new=mock.AsyncMock(),
        ) as sleep_mock,
    ):
        await quirked.apply_custom_configuration()

    assert request_mock.await_count == 3

    read_call = request_mock.await_args_list[0]
    ffde_call = request_mock.await_args_list[1]
    f0_call = request_mock.await_args_list[2]

    assert read_call.kwargs == {
        "profile": zha.PROFILE_ID,
        "cluster": Basic.cluster_id,
        "src_ep": 1,
        "dst_ep": 0xFF,
        "sequence": 1,
        "data": bytes(
            [
                0x10,
                0x01,
                0x00,
                0x04,
                0x00,
                0x00,
                0x00,
                0x01,
                0x00,
                0x05,
                0x00,
                0x07,
                0x00,
                0xFE,
                0xFF,
            ]
        ),
        "expect_reply": False,
    }

    assert ffde_call.kwargs == {
        "profile": zha.PROFILE_ID,
        "cluster": Basic.cluster_id,
        "src_ep": 1,
        "dst_ep": 1,
        "sequence": 2,
        "data": bytes(
            [
                0x00,
                0x02,
                0x02,
                0xDE,
                0xFF,
                0x20,
                0x0D,
            ]
        ),
        "expect_reply": False,
    }

    assert f0_call.kwargs == {
        "profile": zha.PROFILE_ID,
        "cluster": Basic.cluster_id,
        "src_ep": 1,
        "dst_ep": 1,
        "sequence": 3,
        "data": bytes(
            [
                0x11,
                0x03,
                0xF0,
            ]
        ),
        "expect_reply": False,
    }

    sleep_mock.assert_awaited_once_with(2.55)
