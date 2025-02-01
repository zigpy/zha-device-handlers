"""Tests for Sinope."""

from unittest import mock

import pytest
from zigpy.device import Device
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import DeviceTemperature
from zigpy.zcl.clusters.measurement import FlowMeasurement

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.const import (
    COMMAND_M_INITIAL_PRESS,
    COMMAND_M_LONG_RELEASE,
    COMMAND_M_MULTI_PRESS_COMPLETE,
    COMMAND_M_SHORT_RELEASE,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.sinope import SINOPE_MANUFACTURER_CLUSTER_ID
from zhaquirks.sinope.light import (
    SinopeTechnologieslight,
    SinopeTechnologiesManufacturerCluster,
)
from zhaquirks.sinope.switch import SinopeTechnologiesCalypso, SinopeTechnologiesValveG2

zhaquirks.setup()

ButtonAction = SinopeTechnologiesManufacturerCluster.Action

SINOPE_MANUFACTURER_ID = 4508  # 0x119C


@pytest.mark.parametrize("quirk", (SinopeTechnologiesCalypso,))
async def test_sinope_device_temp(zigpy_device_from_quirk, quirk):
    """Test that device temperature is multiplied."""
    device = zigpy_device_from_quirk(quirk)

    dev_temp_cluster = device.endpoints[1].device_temperature
    dev_temp_listener = ClusterListener(dev_temp_cluster)
    dev_temp_attr_id = DeviceTemperature.AttributeDefs.current_temperature.id
    dev_temp_other_attr_id = DeviceTemperature.AttributeDefs.min_temp_experienced.id

    # verify current temperature is multiplied by 100
    dev_temp_cluster.update_attribute(dev_temp_attr_id, 25)
    assert len(dev_temp_listener.attribute_updates) == 1
    assert dev_temp_listener.attribute_updates[0][0] == dev_temp_attr_id
    assert dev_temp_listener.attribute_updates[0][1] == 2500  # multiplied by 100

    # verify other attributes are not modified
    dev_temp_cluster.update_attribute(dev_temp_other_attr_id, 25)
    assert len(dev_temp_listener.attribute_updates) == 2
    assert dev_temp_listener.attribute_updates[1][0] == dev_temp_other_attr_id
    assert dev_temp_listener.attribute_updates[1][1] == 25  # not modified


@pytest.mark.parametrize("quirk", (SinopeTechnologiesValveG2,))
async def test_sinope_flow_measurement(zigpy_device_from_quirk, quirk):
    """Test that flow measurement measured value is divided."""
    device = zigpy_device_from_quirk(quirk)

    flow_measurement_cluster = device.endpoints[1].flow
    flow_measurement_listener = ClusterListener(flow_measurement_cluster)
    flow_measurement_attr_id = FlowMeasurement.AttributeDefs.measured_value.id
    flow_measurement_other_attr_id = FlowMeasurement.AttributeDefs.min_measured_value.id

    # verify measured value is divided by 10
    flow_measurement_cluster.update_attribute(flow_measurement_attr_id, 2500)
    assert len(flow_measurement_listener.attribute_updates) == 1
    assert flow_measurement_listener.attribute_updates[0][0] == flow_measurement_attr_id
    assert flow_measurement_listener.attribute_updates[0][1] == 250.0  # divided by 10

    # verify other attributes are not modified
    flow_measurement_cluster.update_attribute(flow_measurement_other_attr_id, 25)
    assert len(flow_measurement_listener.attribute_updates) == 2
    assert (
        flow_measurement_listener.attribute_updates[1][0]
        == flow_measurement_other_attr_id
    )
    assert flow_measurement_listener.attribute_updates[1][1] == 25  # not modified


def _get_packet_data(
    command: foundation.GeneralCommand,
    attr: foundation.Attribute | None = None,
    dirc: foundation.Direction = foundation.Direction.Server_to_Client,
) -> bytes:
    hdr = foundation.ZCLHeader.general(
        1, command, SINOPE_MANUFACTURER_ID, dirc
    ).serialize()
    if attr is not None:
        cmd = foundation.GENERAL_COMMANDS[command].schema([attr]).serialize()
    else:
        cmd = b""
    return t.SerializableBytes(hdr + cmd).serialize()


@pytest.mark.parametrize("quirk", (SinopeTechnologieslight,))
@pytest.mark.parametrize(
    "press_type,button,exp_event",
    (
        (ButtonAction.Pressed_off, TURN_OFF, COMMAND_M_INITIAL_PRESS),
        (ButtonAction.Pressed_on, TURN_ON, COMMAND_M_INITIAL_PRESS),
        (ButtonAction.Released_off, TURN_OFF, COMMAND_M_SHORT_RELEASE),
        (ButtonAction.Released_on, TURN_ON, COMMAND_M_SHORT_RELEASE),
        (ButtonAction.Double_on, TURN_ON, COMMAND_M_MULTI_PRESS_COMPLETE),
        (ButtonAction.Double_off, TURN_OFF, COMMAND_M_MULTI_PRESS_COMPLETE),
        (ButtonAction.Long_on, TURN_ON, COMMAND_M_LONG_RELEASE),
        (ButtonAction.Long_off, TURN_OFF, COMMAND_M_LONG_RELEASE),
        # Should gracefully handle broken actions.
        (t.uint8_t(0x00), None, None),
    ),
)
async def test_sinope_light_switch(
    zigpy_device_from_quirk, quirk, press_type, button, exp_event
):
    """Test that button presses are sent as events."""
    device: Device = zigpy_device_from_quirk(quirk)
    cluster_id = SINOPE_MANUFACTURER_CLUSTER_ID
    endpoint_id = 1

    class Listener:
        zha_send_event = mock.MagicMock()

    cluster_listener = Listener()
    device.endpoints[endpoint_id].in_clusters[cluster_id].add_listener(cluster_listener)

    attr = foundation.Attribute(
        attrid=0x54,  # "action_report" attribute
        value=foundation.TypeValue(
            type=t.enum8(0x30),
            value=press_type,
        ),
    )
    data = _get_packet_data(foundation.GeneralCommand.Report_Attributes, attr)

    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=cluster_id,
            src_ep=endpoint_id,
            dst_ep=endpoint_id,
            data=t.SerializableBytes(data),
        )
    )

    if exp_event is None:
        assert cluster_listener.zha_send_event.call_count == 0
    else:
        assert cluster_listener.zha_send_event.call_count == 1
        assert cluster_listener.zha_send_event.call_args == mock.call(
            exp_event,
            {
                "attribute_id": 84,
                "attribute_name": "action_report",
                "button": button,
                "description": press_type.name,
                "value": press_type.value,
            },
        )


@pytest.mark.parametrize("quirk", (SinopeTechnologieslight,))
async def test_sinope_light_switch_non_action_report(zigpy_device_from_quirk, quirk):
    """Test commands not handled by custom handler.

    Make sure that non attribute report commands and attribute reports that don't
    concern action_report are passed through to base class.
    """

    device: Device = zigpy_device_from_quirk(quirk)
    cluster_id = SINOPE_MANUFACTURER_CLUSTER_ID
    endpoint_id = 1

    class Listener:
        zha_send_event = mock.MagicMock()

    cluster_listener = Listener()
    device.endpoints[endpoint_id].in_clusters[cluster_id].add_listener(cluster_listener)

    # read attributes general command
    data = _get_packet_data(foundation.GeneralCommand.Read_Attributes)
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=cluster_id,
            src_ep=endpoint_id,
            dst_ep=endpoint_id,
            data=t.SerializableBytes(data),
        )
    )
    # no ZHA events emitted because we only handle Report_Attributes
    assert cluster_listener.zha_send_event.call_count == 0

    # report attributes command, but not "action_report"
    attr = foundation.Attribute(
        attrid=0x10,  # "on_intensity" attribute
        value=foundation.TypeValue(
            type=t.int16s(0x29), value=t.int16s(50)
        ),  # 0x29 = t.int16s
    )
    data = _get_packet_data(foundation.GeneralCommand.Report_Attributes, attr)
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=cluster_id,
            src_ep=endpoint_id,
            dst_ep=endpoint_id,
            data=t.SerializableBytes(data),
        )
    )
    # ZHA event emitted because we pass non "action_report"
    # reports to the base class handler.
    assert cluster_listener.zha_send_event.call_count == 1


@pytest.mark.parametrize("quirk", (SinopeTechnologieslight,))
async def test_sinope_light_switch_reporting(zigpy_device_from_quirk, quirk):
    """Test that configuring reporting for action_report works."""
    device: Device = zigpy_device_from_quirk(quirk)

    manu_cluster = device.endpoints[1].in_clusters[SINOPE_MANUFACTURER_CLUSTER_ID]

    request_patch = mock.patch("zigpy.zcl.Cluster.request", mock.AsyncMock())
    bind_patch = mock.patch("zigpy.zcl.Cluster.bind", mock.AsyncMock())

    with request_patch as request_mock, bind_patch as bind_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        await manu_cluster.bind()
        await manu_cluster.configure_reporting(
            SinopeTechnologiesManufacturerCluster.AttributeDefs.action_report.id,
            3600,
            10800,
            1,
        )

        assert len(request_mock.mock_calls) == 1
        assert len(bind_mock.mock_calls) == 1


@pytest.mark.parametrize("quirk", (SinopeTechnologieslight,))
async def test_sinope_light_device_triggers_def(zigpy_device_from_quirk, quirk):
    """Test device automation triggers.

    Make sure that values are actual ints and not instances of an enum class.
    """

    device: Device = zigpy_device_from_quirk(quirk)

    for config in device.device_automation_triggers.values():
        val = config.get("args", {}).get("value")
        if val is not None:
            assert type(val) is int, type(val)
