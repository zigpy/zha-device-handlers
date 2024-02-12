"""Tests for Sinope."""

import pytest
from zigpy.zcl.clusters.general import DeviceTemperature
from zigpy.zcl.clusters.measurement import FlowMeasurement

import zhaquirks.sinope.switch

from tests.common import ClusterListener

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
