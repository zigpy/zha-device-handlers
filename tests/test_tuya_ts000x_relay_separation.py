"""Tests for Tuya TS000x relay separation commissioning."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY

from zhaquirks.tuya.ts000x_relay_separation import TuyaRelaySeparationDevice


@pytest.mark.parametrize(
    ("manufacturer", "model"),
    [
        ("_TZ3000_c7xsiexw", "TS0002"),
        ("_TZ3000_iol4bl2y", "TS0003"),
    ],
)
@pytest.mark.asyncio
async def test_tuya_relay_separation_commissioning(
    device_mock,
    manufacturer,
    model,
):
    """Test the proprietary Tuya relay separation commissioning sequence."""
    device_mock.manufacturer = manufacturer
    device_mock.model = model

    quirked = DEVICE_REGISTRY.resolve(device_mock)

    assert isinstance(quirked, TuyaRelaySeparationDevice)

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
            "zhaquirks.tuya.ts000x_relay_separation.asyncio.sleep",
            new=mock.AsyncMock(),
        ) as sleep_mock,
    ):
        await quirked.apply_custom_configuration()

    assert request_mock.await_count == 3

    first_request = request_mock.await_args_list[0].kwargs
    assert first_request["profile"] == 0x0104
    assert first_request["cluster"] == 0x0000
    assert first_request["src_ep"] == 1
    assert first_request["dst_ep"] == 0xFF
    assert first_request["sequence"] == 1
    assert first_request["expect_reply"] is False
    assert first_request["data"] == bytes(
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
    )

    second_request = request_mock.await_args_list[1].kwargs
    assert second_request["profile"] == 0x0104
    assert second_request["cluster"] == 0x0000
    assert second_request["src_ep"] == 1
    assert second_request["dst_ep"] == 1
    assert second_request["sequence"] == 2
    assert second_request["expect_reply"] is False
    assert second_request["data"] == bytes(
        [
            0x00,
            0x02,
            0x02,
            0xDE,
            0xFF,
            0x20,
            0x0D,
        ]
    )

    sleep_mock.assert_awaited_once_with(2.55)

    third_request = request_mock.await_args_list[2].kwargs
    assert third_request["profile"] == 0x0104
    assert third_request["cluster"] == 0x0000
    assert third_request["src_ep"] == 1
    assert third_request["dst_ep"] == 1
    assert third_request["sequence"] == 3
    assert third_request["expect_reply"] is False
    assert third_request["data"] == bytes(
        [
            0x11,
            0x03,
            0xF0,
        ]
    )
