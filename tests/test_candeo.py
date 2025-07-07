"""Tests for Candeo."""

from zigpy.zcl.clusters.measurement import IlluminanceMeasurement

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.candeo import CANDEO

zhaquirks.setup()


async def test_candeo_motion_illuminance(zigpy_device_from_v2_quirk):
    """Test that illuminance value is converted correctly."""
    device = zigpy_device_from_v2_quirk(CANDEO, "C-ZB-SEMO")

    test_values = {
        "test1": {"in": 33598, "out": 18074},
        "test2": {"in": 24112, "out": 1},
        "test3": {"in": 34977, "out": 36895},
        "test4": {"in": 34299, "out": 26989},
    }

    for test_value in test_values.values():
        dev_illuminance_cluster = device.endpoints[1].illuminance
        dev_illuminance_listener = ClusterListener(dev_illuminance_cluster)
        dev_illuminance_attr_id = IlluminanceMeasurement.AttributeDefs.measured_value.id
        test_in = test_value.get("in")
        dev_illuminance_cluster.update_attribute(dev_illuminance_attr_id, test_in)
        assert len(dev_illuminance_listener.attribute_updates) == 1
        assert (
            dev_illuminance_listener.attribute_updates[0][0] == dev_illuminance_attr_id
        )
        test_out = test_value.get("out")
        assert dev_illuminance_listener.attribute_updates[0][1] == test_out
