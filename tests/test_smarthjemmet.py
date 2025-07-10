"""Tests for SmartHjemmet quirks."""

from unittest import mock

import pytest
from zigpy.zcl.clusters.general import MultistateInput

import zhaquirks

zhaquirks.setup()


@pytest.mark.parametrize("endpoint", (2, 3, 4, 5))
def test_quadzigsw(zigpy_device_from_v2_quirk, endpoint):
    """Test the SmartHjemmet QUAD-ZIG-SW."""
    device = zigpy_device_from_v2_quirk(
        "smarthjemmet.dk", "QUAD-ZIG-SW", endpoint_ids=[1, 2, 3, 4, 5]
    )

    cluster = device.endpoints[endpoint].multistate_input
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    multistate_value = MultistateInput.AttributeDefs.present_value.id
    multistate_text = MultistateInput.AttributeDefs.state_text.id

    # test that attribute writes are passed through with no events
    cluster.update_attribute(MultistateInput.AttributeDefs.state_text.id, "test")
    assert listener.zha_send_event.call_count == 0
    assert listener.attribute_updated.call_count == 1
    assert listener.attribute_updated.call_args[0][0] == multistate_text
    assert listener.attribute_updated.call_args[0][1] == "test"

    # test that the cluster does not send events for unknown values
    cluster.update_attribute(multistate_value, 5)
    assert listener.zha_send_event.call_count == 0

    # test that the cluster sends the correct events
    cluster.update_attribute(multistate_value, 0)
    assert listener.zha_send_event.call_count == 1
    listener.zha_send_event.assert_called_with("release", {"value": 0})

    cluster.update_attribute(multistate_value, 1)
    assert listener.zha_send_event.call_count == 2
    listener.zha_send_event.assert_called_with("single", {"value": 1})

    cluster.update_attribute(multistate_value, 2)
    assert listener.zha_send_event.call_count == 3
    listener.zha_send_event.assert_called_with("double", {"value": 2})

    cluster.update_attribute(multistate_value, 3)
    assert listener.zha_send_event.call_count == 4
    listener.zha_send_event.assert_called_with("triple", {"value": 3})

    cluster.update_attribute(multistate_value, 4)
    assert listener.zha_send_event.call_count == 5
    listener.zha_send_event.assert_called_with("hold", {"value": 4})
