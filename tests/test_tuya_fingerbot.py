"""Tests for Tuya fingerbot quirks."""

import asyncio
from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff, PowerConfiguration

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya import TUYA_SET_DATA
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.tuya_fingerbot import FingerBotCZF02OnOff, FingerBotModeCZF02

zhaquirks.setup()

CZF02_MANUFACTURERS = (
    "_TZE284_chcnj5st",
    "_TZE2841000000_chcnj5st",
    "_TZE284_gw05grph",
    "_TZE2841000000_gw05grph",
    "_TZE284_pislt0wa",
    "_TZE2841000000_pislt0wa",
)


@pytest.mark.parametrize("manufacturer", CZF02_MANUFACTURERS)
def test_czf02_signature(zigpy_device_from_v2_quirk, manufacturer):
    """Test the Lincukoo CZF02 quirk matches and exposes the expected entities."""
    quirked = zigpy_device_from_v2_quirk(manufacturer, "TS0601")
    ep = quirked.endpoints[1]

    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)
    assert ep.on_off is not None
    assert ep.power is not None

    entry = DEVICE_REGISTRY.match_entry(quirked)
    suffixes = {
        metadata.resolved_unique_id_suffix
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    }
    assert suffixes == {
        "mode",
        "sustain_time",
        "down_movement",
        "up_movement",
        "auto_calibration",
    }


@pytest.mark.parametrize(
    "msg,cluster_name,attr_name,value",
    # All frames captured from a Sygonix SY-6811314 (_TZE284_chcnj5st)
    [
        (b"\x09\xde\x02\x00\x0d\x01\x01\x00\x01\x01", "on_off", "on_off", True),
        (b"\x09\xdf\x02\x00\x0e\x01\x01\x00\x01\x00", "on_off", "on_off", False),
        (
            b"\x09\x0a\x02\x00\x38\x02\x04\x00\x01\x01",
            "tuya_manufacturer",
            "mode",
            FingerBotModeCZF02.SWITCH,
        ),
        (
            b"\x09\x0b\x02\x00\x39\x03\x02\x00\x04\x00\x00\x00\x03",  # 0.3 s
            "tuya_manufacturer",
            "sustain_time",
            300,
        ),
        (
            b"\x09\x0d\x02\x00\x3b\x05\x02\x00\x04\x00\x00\x00\x1e",
            "tuya_manufacturer",
            "down_movement",
            30,
        ),
        (
            b"\x09\x0c\x02\x00\x3a\x06\x02\x00\x04\x00\x00\x00\x02",
            "tuya_manufacturer",
            "up_movement",
            2,
        ),
        (
            b"\x09\x0e\x02\x00\x3c\x08\x02\x00\x04\x00\x00\x00\x64",  # 100 %
            "power",
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.name,
            200,
        ),
    ],
)
async def test_czf02_state_report(
    zigpy_device_from_v2_quirk, msg, cluster_name, attr_name, value
):
    """Test Tuya datapoint reports are mapped to the correct attributes."""
    quirked = zigpy_device_from_v2_quirk("_TZE284_chcnj5st", "TS0601")
    ep = quirked.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer
    cluster = getattr(ep, cluster_name)
    listener = ClusterListener(cluster)

    hdr, data = tuya_cluster.deserialize(msg)
    status = tuya_cluster.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert listener.attribute_updates[-1] == (
        cluster.attributes_by_name[attr_name].id,
        value,
    )


@pytest.mark.parametrize(
    "command_id,expected_dp_data",
    [
        (OnOff.ServerCommandDefs.on.id, b"\x01\x01\x00\x01\x01"),
        (OnOff.ServerCommandDefs.off.id, b"\x01\x01\x00\x01\x00"),
    ],
)
async def test_czf02_on_off(zigpy_device_from_v2_quirk, command_id, expected_dp_data):
    """Test on/off commands are sent with set_data, which the device acts on."""
    quirked = zigpy_device_from_v2_quirk("_TZE284_chcnj5st", "TS0601")
    ep = quirked.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        await ep.on_off.command(command_id)
        await wait_for_zigpy_tasks()

    m1.assert_called_once()
    assert m1.call_args.kwargs["command_id"] == TUYA_SET_DATA
    assert m1.call_args.kwargs["data"].endswith(expected_dp_data)


@pytest.mark.parametrize(
    "attributes,expected_dp_data",
    [
        ({"mode": FingerBotModeCZF02.SWITCH}, b"\x02\x04\x00\x01\x01"),
        ({"sustain_time": 300}, b"\x03\x02\x00\x04\x00\x00\x00\x03"),
        ({"sustain_time": 1500}, b"\x03\x02\x00\x04\x00\x00\x00\x0f"),
        ({"sustain_time": 10000}, b"\x03\x02\x00\x04\x00\x00\x00\x64"),
        ({"down_movement": 25}, b"\x05\x02\x00\x04\x00\x00\x00\x19"),
        ({"up_movement": 4}, b"\x06\x02\x00\x04\x00\x00\x00\x04"),
        ({"auto_calibration": True}, b"\x65\x01\x00\x01\x01"),
    ],
)
async def test_czf02_write_attributes(
    zigpy_device_from_v2_quirk, attributes, expected_dp_data
):
    """Test writing attributes sends the correct Tuya datapoints."""
    quirked = zigpy_device_from_v2_quirk("_TZE284_chcnj5st", "TS0601")
    tuya_cluster = quirked.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        (status,) = await tuya_cluster.write_attributes(attributes)
        await wait_for_zigpy_tasks()

    assert status == [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    m1.assert_called_once()
    assert m1.call_args.kwargs["command_id"] == TUYA_SET_DATA
    assert m1.call_args.kwargs["data"].endswith(expected_dp_data)


ON_REPORT = b"\x09\xde\x02\x00\x0d\x01\x01\x00\x01\x01"


@pytest.mark.parametrize(
    "mode,expected_on_off",
    [
        (FingerBotModeCZF02.BUTTON, False),
        (FingerBotModeCZF02.SWITCH, True),
        (None, True),
    ],
)
async def test_czf02_button_mode_resets_on_off(
    zigpy_device_from_v2_quirk, mode, expected_on_off
):
    """Test the switch turns off again after a press in button mode only."""
    quirked = zigpy_device_from_v2_quirk("_TZE284_chcnj5st", "TS0601")
    ep = quirked.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer
    assert isinstance(ep.on_off, FingerBotCZF02OnOff)

    if mode is not None:
        tuya_cluster.update_attribute("mode", mode)

    with mock.patch.object(FingerBotCZF02OnOff, "reset_margin_s", 0.01):
        hdr, data = tuya_cluster.deserialize(ON_REPORT)
        tuya_cluster.handle_get_data(data.data)
        assert ep.on_off.get("on_off") == 1

        await asyncio.sleep(0.05)

    assert ep.on_off.get("on_off") == expected_on_off


async def test_czf02_button_mode_reset_waits_for_sustain_time(
    zigpy_device_from_v2_quirk,
):
    """Test the reset in button mode waits for the press to finish."""
    quirked = zigpy_device_from_v2_quirk("_TZE284_chcnj5st", "TS0601")
    ep = quirked.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer
    tuya_cluster.update_attribute("mode", FingerBotModeCZF02.BUTTON)
    tuya_cluster.update_attribute("sustain_time", 300)

    with mock.patch.object(FingerBotCZF02OnOff, "reset_margin_s", 0):
        ep.on_off.update_attribute(OnOff.AttributeDefs.on_off.name, True)

        await asyncio.sleep(0.1)
        assert ep.on_off.get("on_off") == 1

        await asyncio.sleep(0.3)
        assert ep.on_off.get("on_off") == 0


async def test_czf02_button_mode_resets_after_on_command(zigpy_device_from_v2_quirk):
    """Test turning on from HA in button mode turns the switch off again."""
    quirked = zigpy_device_from_v2_quirk("_TZE284_chcnj5st", "TS0601")
    ep = quirked.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer
    tuya_cluster.update_attribute("mode", FingerBotModeCZF02.BUTTON)

    with (
        mock.patch.object(FingerBotCZF02OnOff, "reset_margin_s", 0.01),
        mock.patch.object(
            tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
        ),
    ):
        await ep.on_off.command(OnOff.ServerCommandDefs.on.id)
        await wait_for_zigpy_tasks()
        assert ep.on_off.get("on_off") == 1

        await asyncio.sleep(0.05)

    assert ep.on_off.get("on_off") == 0
