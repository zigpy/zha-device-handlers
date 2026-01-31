"""Tests for Shelly."""

import zhaquirks
from zhaquirks.shelly import SHELLY

zhaquirks.setup()


async def test_shelly_ecowitt_ws90_cluster_attributes(zigpy_device_from_v2_quirk):
    """Test that custom Shelly WS90 cluster attributes are correctly defined."""
    device = zigpy_device_from_v2_quirk(SHELLY, "Ecowitt WS90")

    wind_cluster = device.endpoints[1].in_clusters[0xFC01]
    uv_cluster = device.endpoints[1].in_clusters[0xFC02]
    rain_cluster = device.endpoints[1].in_clusters[0xFC03]

    assert wind_cluster.attributes[0x0000].name == "wind_speed"
    assert wind_cluster.attributes[0x0004].name == "wind_direction"
    assert wind_cluster.attributes[0x0007].name == "gust_speed"

    assert uv_cluster.attributes[0x0000].name == "uv_index"

    assert rain_cluster.attributes[0x0000].name == "rain_status"
    assert rain_cluster.attributes[0x0001].name == "precipitation"
