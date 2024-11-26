"""Tests for Linxura quirks."""

from unittest import mock

import pytest
from zigpy.zcl.clusters.security import IasZone

import zhaquirks
import zhaquirks.linxura

zhaquirks.setup()


async def test_button_ias(zigpy_device_from_quirk):
    """Test Linxura button remotes."""

    device = zigpy_device_from_quirk(zhaquirks.linxura.button.LinxuraButton)
    ias_zone_status_attr_id = IasZone.AttributeDefs.zone_status.id
    cluster = device.endpoints[1].ias_zone
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    for i in range(0, 24):
        # button press
        cluster.update_attribute(ias_zone_status_attr_id, i)

        # update_attribute on the IasZone cluster is always called
        assert listener.attribute_updated.call_args[0][0] == ias_zone_status_attr_id
        assert listener.attribute_updated.call_args[0][1] == i

    # we get 20 events, 4 are discarded as invalid (0, 6, 12, 18)
    assert listener.attribute_updated.call_count == 24
    assert listener.zha_send_event.call_count == 20


@pytest.mark.parametrize(
    "message, button, press_type",
    [
        (
            b"\x18\n\n\x02\x00\x19\x01\x00\xfe\xff0\x01",
            "button_1",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x03\x00\xfe\xff0\x01",
            "button_1",
            "remote_button_double_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x05\x00\xfe\xff0\x01",
            "button_1",
            "remote_button_long_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x07\x00\xfe\xff0\x01",
            "button_2",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x09\x00\xfe\xff0\x01",
            "button_2",
            "remote_button_double_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x0b\x00\xfe\xff0\x01",
            "button_2",
            "remote_button_long_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x0d\x00\xfe\xff0\x01",
            "button_3",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x0f\x00\xfe\xff0\x01",
            "button_3",
            "remote_button_double_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x11\x00\xfe\xff0\x01",
            "button_3",
            "remote_button_long_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x13\x00\xfe\xff0\x01",
            "button_4",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x15\x00\xfe\xff0\x01",
            "button_4",
            "remote_button_double_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x17\x00\xfe\xff0\x01",
            "button_4",
            "remote_button_long_press",
        ),
    ],
)
async def test_button_triggers(zigpy_device_from_quirk, message, button, press_type):
    """Test ZHA_SEND_EVENT case."""
    device = zigpy_device_from_quirk(zhaquirks.linxura.button.LinxuraButton)
    cluster = device.endpoints[1].ias_zone
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    device.handle_message(260, cluster.cluster_id, 1, 1, message)
    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args == mock.call(
        f"{button}_{press_type}",
        {
            "button": button,
            "press_type": press_type,
        },
    )
