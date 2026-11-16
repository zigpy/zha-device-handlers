"""Tests for the Lidl Melinera HG06467 string lights quirk."""

import colorsys
from unittest import mock

import pytest
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color

from tests.common import wait_for_zigpy_tasks
from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.lidl.hg06467 import (
    EFFECT_NAMES,
    LightMode,
    MelineraColorCluster,
    MelineraLight,
    StringEffect,
    hs_to_xy,
    xy_to_hs,
)
from zhaquirks.tuya import TuyaCommand, TuyaDatapointData, TuyaNewManufCluster

zhaquirks.setup()


def _dev(zigpy_device_from_v2_quirk):
    """Create the string light with its native clusters."""
    return zigpy_device_from_v2_quirk(
        "_TZE200_s8gkrkxk",
        "TS0601",
        cluster_ids={
            1: {
                OnOff.cluster_id: ClusterType.Server,
                LevelControl.cluster_id: ClusterType.Server,
                Color.cluster_id: ClusterType.Server,
                TuyaNewManufCluster.cluster_id: ClusterType.Server,
            }
        },
    )


def _report(cluster, dp, value):
    cmd = TuyaCommand(status=0, tsn=1, datapoints=[TuyaDatapointData(dp, value)])
    assert cluster.handle_get_data(cmd) == foundation.Status.SUCCESS


def _sent(request_mock):
    """Decode (dp, payload) of every Tuya command sent."""
    out = []
    for call in request_mock.call_args_list:
        if call.kwargs["cluster"] != TuyaNewManufCluster.cluster_id:
            continue
        data = call.kwargs["data"]
        hdr, rest = foundation.ZCLHeader.deserialize(data)
        cmd, _ = TuyaCommand.deserialize(rest)
        for dpd in cmd.datapoints:
            out.append((dpd.dp, dpd.data.payload))
    return out


def ha_hs_to_xy(h, s):
    """Copy of homeassistant.util.color.color_hs_to_xy (no gamut)."""
    r, g, b = (round(c * 255) for c in colorsys.hsv_to_rgb(h / 360, s / 100, 1))
    R, G, B = (
        ((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.04045 else c / 255 / 12.92
        for c in (r, g, b)
    )
    X = R * 0.664511 + G * 0.154324 + B * 0.162028
    Y = R * 0.283881 + G * 0.668433 + B * 0.047685
    Z = R * 0.000088 + G * 0.072310 + B * 0.986039
    return round(X / (X + Y + Z), 3), round(Y / (X + Y + Z), 3)


@pytest.mark.parametrize(
    "hue,sat",
    [(0, 100), (30, 100), (60, 100), (120, 100), (200, 80), (300, 50), (15, 30)],
)
def test_color_round_trip_matches_ha(hue, sat):
    """HA color wheel hs -> xy -> device hs gives back the picked hue."""
    x, y = ha_hs_to_xy(hue, sat)
    dev_h, dev_s = xy_to_hs(x, y)
    hue_err = min(abs(dev_h - hue), 360 - abs(dev_h - hue))
    assert hue_err < 3
    assert abs(dev_s / 10 - sat) < 2.5
    # and back again
    x2, y2 = hs_to_xy(dev_h, dev_s)
    assert abs(x2 - x) < 0.004 and abs(y2 - y) < 0.004


async def test_reports(zigpy_device_from_v2_quirk):
    """Test datapoint reports update the ZCL state."""
    dev = _dev(zigpy_device_from_v2_quirk)
    ep = dev.endpoints[1]
    tuya = ep.tuya_manufacturer
    assert isinstance(ep.light_color, MelineraColorCluster)

    _report(tuya, 1, False)
    assert ep.on_off.get("on_off") == 0
    _report(tuya, 1, True)
    assert ep.on_off.get("on_off") == 1

    _report(tuya, 2, LightMode.Effect)
    assert tuya.get("light_mode") == LightMode.Effect
    _report(tuya, 2, LightMode.Color)
    assert tuya.get("light_mode") == LightMode.Color

    _report(tuya, 5, "007803e801f4")  # hue 120, sat 1000, bri 500
    x, y = ep.light_color.get("current_x"), ep.light_color.get("current_y")
    h, s = xy_to_hs(x / 65535, y / 65535)
    assert abs(h - 120) < 1 and s > 990
    assert ep.level.get("current_level") == 127

    _report(tuya, 6, "0a48ff000000ff00")  # fading, speed 48/64, red+green
    assert tuya.get("string_effect") == StringEffect.Fading
    assert tuya.get("effect_speed") == 75
    assert tuya.get("effect_palette") == "ff000000ff00"

    # white brightness is ignored in colour mode, used in white mode
    _report(tuya, 3, 1000)
    assert ep.level.get("current_level") == 127
    _report(tuya, 2, LightMode.White)
    _report(tuya, 3, 1000)
    assert ep.level.get("current_level") == 254

    # cached state is served for reads (device's own color cluster is stale)
    success, _ = await ep.light_color.read_attributes(["current_x"])
    assert success["current_x"] == x
    assert ep.light_color.get("color_temperature") is None


async def test_effect_and_speed(zigpy_device_from_v2_quirk):
    """Test effect, speed and light mode writes."""
    dev = _dev(zigpy_device_from_v2_quirk)
    ep = dev.endpoints[1]
    tuya = ep.tuya_manufacturer

    with mock.patch.object(
        tuya.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req:
        # not in effect mode: speed is only stored
        _report(tuya, 2, LightMode.Color)
        await tuya.write_attributes({"effect_speed": 100})
        await wait_for_zigpy_tasks()
        assert req.call_count == 0
        assert tuya.get("effect_speed") == 100

        # selecting an effect uses the stored speed (100% -> 64)
        await tuya.write_attributes({"string_effect": StringEffect.Twinkle})
        await wait_for_zigpy_tasks()
        assert _sent(req) == [(2, LightMode.Effect), (6, "0464")]
        # the device does not report the mode change itself
        assert tuya.get("light_mode") == LightMode.Effect

        # in effect mode the speed is sent at once, keeping effect and palette
        req.reset_mock()
        _report(tuya, 6, "0464ff0000")
        await tuya.write_attributes({"effect_speed": 25})
        await wait_for_zigpy_tasks()
        assert _sent(req) == [(2, LightMode.Effect), (6, "0416ff0000")]


async def test_color_commands(zigpy_device_from_v2_quirk):
    """Test xy and colour temperature commands."""
    dev = _dev(zigpy_device_from_v2_quirk)
    ep = dev.endpoints[1]
    tuya = ep.tuya_manufacturer
    ep.level.update_attribute("current_level", 254)

    with mock.patch.object(
        tuya.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req:
        x, y = ha_hs_to_xy(240, 100)  # pure blue picked in HA
        rsp = await ep.light_color.command(
            Color.ServerCommandDefs.move_to_color.id,
            round(x * 65535),
            round(y * 65535),
            0,
        )
        assert rsp.status == foundation.Status.SUCCESS
        sent = _sent(req)
        assert sent[0] == (2, LightMode.Color)
        dp, value = sent[1]
        assert dp == 5
        assert 237 <= int(value[0:4], 16) <= 243
        assert int(value[4:8], 16) >= 990
        assert value[8:12] == "03e8"
        assert tuya.get("light_mode") == LightMode.Color

        # brightness in colour mode keeps the colour
        req.reset_mock()
        await ep.level.command(LevelControl.ServerCommandDefs.move_to_level.id, 127, 0)
        dp, value = _sent(req)[0]
        assert dp == 5
        assert 237 <= int(value[0:4], 16) <= 243
        assert value[8:12] == "01f4"

        # white picked in HA uses the white mode
        req.reset_mock()
        x, y = ha_hs_to_xy(0, 0)
        await ep.light_color.command(
            Color.ServerCommandDefs.move_to_color.id,
            round(x * 65535),
            round(y * 65535),
            0,
        )
        assert _sent(req) == [(2, LightMode.White), (3, 500)]

        # brightness in white mode uses DP3
        req.reset_mock()
        await ep.level.command(LevelControl.ServerCommandDefs.move_to_level.id, 254, 0)
        assert _sent(req) == [(3, 1000)]

        # brightness in effect mode is only kept
        req.reset_mock()
        tuya.update_attribute("light_mode", LightMode.Effect)
        await ep.level.command(LevelControl.ServerCommandDefs.move_to_level.id, 100, 0)
        assert _sent(req) == []
        assert ep.level.get("current_level") == 100


async def test_light_entity_from_diagnostics():
    """Test the light offers the effects and no extra selects are created."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "tze200-s8gkrkxk-ts0601-0x00000046.json", DEVICE_REGISTRY
        )
        ieee = str(device.ieee)
        light = device.get_platform_entity(Platform.LIGHT, f"{ieee}-1")
        assert type(light) is MelineraLight
        assert light.effect_list == ["off", *EFFECT_NAMES.values()]
        assert light.supported_color_modes == {"xy"}
        assert light.effect == "off"

        platforms = {platform for platform, _ in device.platform_entities}
        assert Platform.SELECT not in platforms
        assert device.get_platform_entity(Platform.NUMBER, f"{ieee}-1-effect_speed")

        tuya = device.device.endpoints[1].tuya_manufacturer
        tuya.update_attribute("effect_speed", 100)
        with mock.patch.object(
            tuya.endpoint,
            "request",
            return_value=[0, foundation.Status.SUCCESS],
        ) as req:
            await light.async_turn_on(effect="Snow")
            await gateway.async_block_till_done()
            assert _sent(req) == [(2, LightMode.Effect), (6, "0164")]
            assert light.effect == "Snow"

            # picking a colour leaves the effect
            req.reset_mock()
            await light.async_turn_on(xy_color=ha_hs_to_xy(120, 100))
            await gateway.async_block_till_done()
            assert [dp for dp, _ in _sent(req)] == [2, 5]
            assert light.effect == "off"
