"""Tests for Candeo."""

import pytest
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.candeo import CANDEO

zhaquirks.setup()


@pytest.mark.parametrize(
    "lux_in, lux_out",
    (
        (0, 1),
        (24112, 1),  # 1 lux
        (33598, 18074),  # 64 lux
        (34299, 26989),  # 500 lux
        (34977, 36895),  # 4891 lux
    ),
)
async def test_candeo_motion_illuminance(zigpy_device_from_v2_quirk, lux_in, lux_out):
    """Test that illuminance value is converted correctly."""
    device = zigpy_device_from_v2_quirk(CANDEO, "C-ZB-SEMO")

    illuminance_cluster = device.endpoints[1].illuminance
    illuminance_listener = ClusterListener(illuminance_cluster)
    illuminance_attr_id = IlluminanceMeasurement.AttributeDefs.measured_value.id

    illuminance_cluster.update_attribute(illuminance_attr_id, lux_in)
    assert len(illuminance_listener.attribute_updates) == 1
    assert illuminance_listener.attribute_updates[0][0] == illuminance_attr_id
    assert illuminance_listener.attribute_updates[0][1] == lux_out
