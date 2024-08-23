"""Tests for Sinope."""

from unittest import mock

import pytest
from zigpy.device import Device
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import DeviceTemperature
from zigpy.zcl.clusters.measurement import FlowMeasurement

from tests.common import ClusterListener
from zhaquirks.const import COMMAND_BUTTON_DOUBLE
from zhaquirks.sinope import SINOPE_MANUFACTURER_CLUSTER_ID
import zhaquirks.sinope.light
import zhaquirks.sinope.switch

zhaquirks.setup()


@pytest.mark.parametrize("quirk", (zhaquirks.sinope.switch.SinopeTechnologiesCalypso,))
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


@pytest.mark.parametrize("quirk", (zhaquirks.sinope.switch.SinopeTechnologiesValveG2,))
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


@pytest.mark.parametrize("quirk", (zhaquirks.sinope.light.SinopeTechnologieslight,))
async def test_sinope_light_switch(zigpy_device_from_quirk, quirk):
    """Test that button presses are sent as events."""
    device: Device = zigpy_device_from_quirk(quirk)

    data = b"\x1c\x9c\x11\x81\nT\x000\x04"  # off button double down
    cluster_id = 0xFF01
    endpoint_id = 1

    class Listener:
        zha_send_event = mock.MagicMock()

    cluster_listener = Listener()
    device.endpoints[endpoint_id].in_clusters[cluster_id].add_listener(cluster_listener)

    device.handle_message(260, cluster_id, endpoint_id, endpoint_id, data)

    assert cluster_listener.zha_send_event.call_count == 1
    assert cluster_listener.zha_send_event.call_args == mock.call(
        COMMAND_BUTTON_DOUBLE,
        {"attribute_id": 84, "attribute_name": "action_report", "value": 4},
    )

    cluster_listener.zha_send_event.reset_mock()


@pytest.mark.parametrize("quirk", (zhaquirks.sinope.light.SinopeTechnologieslight,))
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
            zhaquirks.sinope.light.SinopeTechnologiesManufacturerCluster.attributes_by_name[
                "action_report"
            ].id,
            3600,
            10800,
            1,
        )

        assert len(request_mock.mock_calls) == 1
        assert len(bind_mock.mock_calls) == 1
