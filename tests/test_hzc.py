"""Tests for HZC quirks."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.hzc.d061gb import HzcLevelControl

zhaquirks.setup()


@pytest.mark.parametrize(
    ("raw", "percent"),
    (
        (0, 0),
        (127, 50),
        (254, 100),
        (255, 0),  # "off" sentinel
    ),
)
def test_on_level_percent_conversion(raw: int, percent: int) -> None:
    """Test the on_level raw to percent conversions."""

    assert HzcLevelControl.wire_to_percent(raw) == percent


@pytest.mark.parametrize(
    ("percent", "raw"),
    (
        (0, 255),  # 0% maps to the "off" sentinel
        (50, 127),
        (100, 254),
    ),
)
def test_on_level_wire_conversion(percent: int, raw: int) -> None:
    """Test the on_level percent to raw conversions."""

    assert HzcLevelControl.percent_to_wire(percent) == raw


@pytest.mark.parametrize(
    ("raw", "percent"),
    (
        (0, 0),
        (127, 50),
        (254, 100),
    ),
)
def test_start_level_percent_conversion(raw: int, percent: int) -> None:
    """Test the start_level raw to percent conversions."""

    assert HzcLevelControl.wire_to_percent_start(raw) == percent
    assert HzcLevelControl.percent_to_wire_start(percent) == raw


async def test_d061gb_level_control(zigpy_device_from_v2_quirk) -> None:
    """Test the HZC D061-GB level control attribute reporting."""

    dimmer = zigpy_device_from_v2_quirk("HZC", "D061-GB")
    cluster = dimmer.endpoints[1].level
    assert isinstance(cluster, HzcLevelControl)

    listener = ClusterListener(cluster)

    on_level_id = LevelControl.AttributeDefs.on_level.id
    start_level_id = HzcLevelControl.AttributeDefs.start_level.id

    # on_level reports are exposed as 0-100%, with 255 reported as 0%
    cluster.update_attribute(on_level_id, 255)
    assert listener.attribute_updates[-1] == (on_level_id, 0)

    cluster.update_attribute(on_level_id, 254)
    assert listener.attribute_updates[-1] == (on_level_id, 100)

    cluster.update_attribute(on_level_id, 127)
    assert listener.attribute_updates[-1] == (on_level_id, 50)

    # start_level is a plain linear 0-254 mapping with no "off" sentinel
    cluster.update_attribute(start_level_id, 127)
    assert listener.attribute_updates[-1] == (start_level_id, 50)

    # other attributes and None values pass through untouched
    cluster.update_attribute(LevelControl.AttributeDefs.current_level.id, 200)
    assert listener.attribute_updates[-1] == (0x0000, 200)

    cluster.update_attribute(on_level_id, None)
    # None clears the cached attribute instead of reporting a value
    assert cluster.get("on_level") is None


async def test_d061gb_write_attributes(zigpy_device_from_v2_quirk) -> None:
    """Test the HZC D061-GB write attribute conversion."""

    dimmer = zigpy_device_from_v2_quirk("HZC", "D061-GB")
    cluster = dimmer.endpoints[1].level

    with mock.patch.object(
        cluster.endpoint,
        "request",
        return_value=foundation.DefaultResponse(foundation.Status.SUCCESS),
    ) as request:
        # on_level is written raw as 0-254, and the attribute cache keeps 0-100%
        (status,) = await cluster.write_attributes({"on_level": 50})
        assert [r.status for r in status] == [foundation.Status.SUCCESS]
        assert request.call_args.kwargs["data"].endswith(b"\x11\x00\x20\x7f")
        assert cluster.get("on_level") == 50

        # 0% is written as the 0xFF "off" sentinel
        (status,) = await cluster.write_attributes({"on_level": 0})
        assert [r.status for r in status] == [foundation.Status.SUCCESS]
        assert request.call_args.kwargs["data"].endswith(b"\x11\x00\x20\xff")
        assert cluster.get("on_level") == 0

        # start_level is written raw as 0-254
        (status,) = await cluster.write_attributes({"start_level": 50})
        assert [r.status for r in status] == [foundation.Status.SUCCESS]
        assert request.call_args.kwargs["data"].endswith(b"\x05\xb0\x20\x7f")
        assert cluster.get("start_level") == 50

        # unrelated attributes are written untouched
        (status,) = await cluster.write_attributes({"min_level": 10})
        assert [r.status for r in status] == [foundation.Status.SUCCESS]
        assert request.call_args.kwargs["data"].endswith(b"\x02\x00\x20\x0a")
        assert cluster.get("min_level") == 10

        # both converted attributes can be written together
        (status,) = await cluster.write_attributes({"on_level": 50, "start_level": 50})
        assert [r.status for r in status] == [
            foundation.Status.SUCCESS,
            foundation.Status.SUCCESS,
        ]
        assert request.call_args.kwargs["data"].endswith(
            b"\x11\x00\x20\x7f\x05\xb0\x20\x7f"
        )
        assert cluster.get("on_level") == 50
        assert cluster.get("start_level") == 50
