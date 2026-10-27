"""Tests for SmartHjemmet quirks."""

from unittest import mock

import pytest
from zigpy.profiles import zha
from zigpy.zcl import AttributeUpdatedEvent
from zigpy.zcl.clusters.general import MultistateInput

from tests.common import ButtonEventRecorder
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

    attr_event_listener = mock.Mock()
    cluster.on_event(AttributeUpdatedEvent.event_type, attr_event_listener)

    multistate_value = MultistateInput.AttributeDefs.present_value.id
    multistate_text = MultistateInput.AttributeDefs.state_text.id

    # test that attribute writes are passed through with no events
    cluster.update_attribute(MultistateInput.AttributeDefs.state_text.id, "test")
    assert listener.zha_send_event.call_count == 0
    assert len(attr_event_listener.mock_calls) == 1
    event = attr_event_listener.mock_calls[0].args[0]
    assert event.attribute_id == multistate_text
    assert event.value == "test"

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


@pytest.mark.parametrize("model", ["QUAD-ZIG-SW", "MULTI-ZIG-SW"])
async def test_quadzigsw_button_events(zigpy_device_from_v2_quirk, model):
    """Test the button event entities of the SmartHjemmet QUAD-ZIG-SW."""
    device = zigpy_device_from_v2_quirk(
        "smarthjemmet.dk", model, endpoint_ids=[1, 2, 3, 4, 5]
    )
    for endpoint_id in (2, 3, 4, 5):
        device.endpoints[endpoint_id].profile_id = zha.PROFILE_ID
        device.endpoints[endpoint_id].device_type = 0xFFFE

    recorder = await ButtonEventRecorder.create(device)
    event_types = [
        "single_press",
        "multi_press",
        "long_press_start",
        "long_press_end",
    ]
    assert recorder.event_types() == {f"button_{i}": event_types for i in range(1, 5)}
    assert recorder.entities["button_4"].endpoint.id == 5

    present_value = MultistateInput.AttributeDefs.present_value.id

    for endpoint_id in (2, 3, 4, 5):
        cluster = device.endpoints[endpoint_id].multistate_input
        # release (not classified before a hold), single, double, triple, hold,
        # release, unknown
        for value in (0, 1, 2, 3, 4, 0, 5):
            cluster.update_attribute(present_value, value)

    assert recorder.pop() == [
        (f"button_{i}", event_type, *attributes)
        for i in range(1, 5)
        for event_type, *attributes in (
            ("single_press",),
            ("multi_press", {"press_count": 2}),
            ("multi_press", {"press_count": 3}),
            ("long_press_start",),
            ("long_press_end",),
        )
    ]
