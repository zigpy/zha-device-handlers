"""Tests for Tuya Garage."""

import pytest
from zigpy.zcl import foundation

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()


@pytest.mark.parametrize(
    "manuf,model,msg,attr,value",
    [
        (
            "_TZE200_nklqjk62",
            "TS0601",
            b"\x09\x9c\x02\x00\x6b\x01\x01\x00\x01\x01",
            "garage_door_trigger",
            1,
        ),  # Set 1, dp 1
        (
            "_TZE204_nklqjk62",
            "TS0601",
            b"\x09\x9c\x02\x00\x6b\x01\x01\x00\x01\x01",
            "garage_door_trigger",
            1,
        ),  # Set 1, dp 1
        (
            "_TZE200_wfxuhoea",
            "TS0601",
            b"\x09\x9c\x02\x00\x6b\x01\x01\x00\x01\x01",
            "garage_door_trigger",
            1,
        ),  # Set 1, dp 1
        (
            "_TZE608_c75zqghm",
            "TS0603",
            b"\x09\x9c\x02\x00\x6b\x01\x01\x00\x01\x01",
            "garage_door_trigger",
            1,
        ),  # Set 1, dp 1
        (
            "_TZE608_fmemczv1",
            "TS0603",
            b"\x09\x9c\x02\x00\x6b\x01\x01\x00\x01\x01",
            "garage_door_trigger",
            1,
        ),  # Set 1, dp 1
    ],
)
async def test_handle_get_data(
    zigpy_device_from_v2_quirk, manuf, model, msg, attr, value
):
    """Test handle_get_data for multiple attributes."""

    quirked = zigpy_device_from_v2_quirk(manuf, model)
    ep = quirked.endpoints[1]
    cluster = ep.tuya_manufacturer

    assert cluster is not None
    assert isinstance(cluster, TuyaMCUCluster)

    listener = ClusterListener(cluster)

    hdr, data = cluster.deserialize(msg)
    status = cluster.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    attr_id = cluster.attributes_by_name[attr].id
    assert len(listener.attribute_updates) == 1
    assert listener.attribute_updates[0][0] == attr_id
    assert listener.attribute_updates[0][1] == value
    assert cluster.get(attr_id) == value
