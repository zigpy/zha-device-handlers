"""Tests for Sinope."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import DeviceTemperature, PowerConfiguration
from zigpy.zcl.clusters.smartenergy import Metering

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
from zhaquirks.sinope import SINOPE, SINOPE_MANUFACTURER_CLUSTER_ID
from zhaquirks.sinope.light import (
    LightManufacturerCluster,
    SinopeTechnologiesManufacturerCluster,
)

zhaquirks.setup()

ButtonAction = SinopeTechnologiesManufacturerCluster.Action

SINOPE_MANUFACTURER_ID = 4508  # 0x119C

SINOPE_MODELS = [
    "SW2500ZB",  # light.py
    "RM3500ZB",  # switch.py
    "TH1123ZB",  # thermostat.py
    "WL4200",  # sensor.py
]


async def test_sinope_device_temp(zigpy_device_from_v2_quirk):
    """Test that device temperature is multiplied."""
    device = zigpy_device_from_v2_quirk(SINOPE, "RM3500ZB")

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


async def test_sinope_flow_measurement(zigpy_device_from_v2_quirk):
    """Test that metering values are handled correctly for Sinope valve."""
    device = zigpy_device_from_v2_quirk(SINOPE, "VA4220ZB")

    metering_cluster = device.endpoints[1].smartenergy_metering
    metering_listener = ClusterListener(metering_cluster)
    metering_attr_id = Metering.AttributeDefs.current_summ_delivered.id
    metering_other_attr_id = Metering.AttributeDefs.multiplier.id

    # verify measured value is divided by 10
    metering_cluster.update_attribute(metering_attr_id, 2500)
    assert len(metering_listener.attribute_updates) == 1
    assert metering_listener.attribute_updates[0][0] == metering_attr_id
    assert metering_listener.attribute_updates[0][1] == 2500  # not divided

    # verify other attributes are not modified
    metering_cluster.update_attribute(metering_other_attr_id, 25)
    assert len(metering_listener.attribute_updates) == 2
    assert metering_listener.attribute_updates[1][0] == metering_other_attr_id
    assert metering_listener.attribute_updates[1][1] == 25  # not modified


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


@pytest.mark.parametrize(LightManufacturerCluster)
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
    zigpy_device_from_v2_quirk, press_type, button, exp_event
):
    """Test that button presses are sent as events."""
    device = zigpy_device_from_v2_quirk(SINOPE, "DM2500ZB")
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


async def test_sinope_light_switch_non_action_report(zigpy_device_from_v2_quirk):
    """Test commands not handled by custom handler.

    Make sure that non attribute report commands and attribute reports that don't
    concern action_report are passed through to base class.
    """

    device = zigpy_device_from_v2_quirk(SINOPE, "SW2500ZB")
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


@pytest.mark.parametrize("model", SINOPE_MODELS)
async def test_sinope_reporting(zigpy_device_from_v2_quirk, model):
    """Generic test that manufacturer cluster configures reporting for all attributes."""
    device = zigpy_device_from_v2_quirk(SINOPE, model)

    manu_cluster = device.endpoints[1].in_clusters[SINOPE_MANUFACTURER_CLUSTER_ID]

    request_patch = mock.patch("zigpy.zcl.Cluster.request", mock.AsyncMock())
    bind_patch = mock.patch("zigpy.zcl.Cluster.bind", mock.AsyncMock())

    with request_patch as request_mock, bind_patch as bind_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        await manu_cluster.bind()
        await manu_cluster.configure_reporting_all()

        assert len(bind_mock.mock_calls) == 1

        # Check that all attributes have been configured
        called_attrs = []
        for call in request_mock.mock_calls:
            reports = call.args[3]  # list of AttributeReport
            for report in reports:
                called_attrs.append(report.attrid)

        for attr_id in manu_cluster.MANUFACTURER_REPORTING:
            assert attr_id in called_attrs

        # Check that number of call is coherent
        assert len(request_mock.mock_calls) >= len(manu_cluster.MANUFACTURER_REPORTING)


@pytest.mark.parametrize("model", SINOPE_MODELS)
async def test_sinope_reporting_failure(zigpy_device_from_v2_quirk, model):
    """Test that reporting failure is handled gracefully for all models."""
    device = zigpy_device_from_v2_quirk(SINOPE, model)
    manu_cluster = device.endpoints[1].in_clusters[SINOPE_MANUFACTURER_CLUSTER_ID]

    with mock.patch("zigpy.zcl.Cluster.request", side_effect=Exception("boom")):
        await manu_cluster.configure_reporting_all()


async def test_sinope_light_device_triggers_def(zigpy_device_from_v2_quirk):
    """Test device automation triggers.

    Make sure that values are actual ints and not instances of an enum class.
    """

    device = zigpy_device_from_v2_quirk(SINOPE, "SW2500ZB")

    for config in device.device_automation_triggers.values():
        val = config.get("args", {}).get("value")
        if val is not None:
            assert type(val) is int, type(val)


async def test_sinope_device_current_sum(zigpy_device_from_v2_quirk):
    """Test that device current_summation_delivered is divided by 100."""
    device = zigpy_device_from_v2_quirk(SINOPE, "SW2500ZB")

    dev_summ_cluster = device.endpoints[1].sinope_manufacturer_specific
    dev_summ_listener = ClusterListener(dev_summ_cluster)
    dev_summ_attr_id = dev_summ_cluster.AttributeDefs.current_summation_delivered.id
    dev_summ_other_attr_id = dev_summ_cluster.AttributeDefs.connected_load.id

    # verify current temperature is divided by 100
    dev_summ_cluster.update_attribute(dev_summ_attr_id, 2500)
    assert len(dev_summ_listener.attribute_updates) == 1
    assert dev_summ_listener.attribute_updates[0][0] == dev_summ_attr_id
    assert dev_summ_listener.attribute_updates[0][1] == 25  # divided by 100

    # verify other attributes are not modified
    dev_summ_cluster.update_attribute(dev_summ_other_attr_id, 2500)
    assert len(dev_summ_listener.attribute_updates) == 2
    assert dev_summ_listener.attribute_updates[1][0] == dev_summ_other_attr_id
    assert dev_summ_listener.attribute_updates[1][1] == 2500  # not modified


@pytest.mark.parametrize("model", ["VA4220ZB", "LM4110-ZB"])
async def test_sinope_device_battery_voltage(zigpy_device_from_v2_quirk, model):
    """Test that device battery voltage is divided by 10."""
    device = zigpy_device_from_v2_quirk(SINOPE, model)

    dev_volt_cluster = device.endpoints[1].in_clusters[PowerConfiguration.cluster_id]
    dev_volt_listener = ClusterListener(dev_volt_cluster)
    dev_volt_attr_id = dev_volt_cluster.AttributeDefs.battery_voltage.id
    dev_volt_other_attr_id = (
        dev_volt_cluster.AttributeDefs.battery_percentage_remaining.id
    )

    # verify battery voltage is divided by 10
    dev_volt_cluster.update_attribute(dev_volt_attr_id, 55)
    assert len(dev_volt_listener.attribute_updates) == 1
    assert dev_volt_listener.attribute_updates[0][0] == dev_volt_attr_id
    assert dev_volt_listener.attribute_updates[0][1] == 5.5  # divided by 10

    # verify other attributes are not modified
    dev_volt_cluster.update_attribute(dev_volt_other_attr_id, 55)
    assert len(dev_volt_listener.attribute_updates) == 2
    assert dev_volt_listener.attribute_updates[1][0] == dev_volt_other_attr_id
    assert dev_volt_listener.attribute_updates[1][1] == 55  # not modified
