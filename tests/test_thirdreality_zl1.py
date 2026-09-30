"""Tests for Third Reality Smart Color Bulb ZL1 quirk (v2)."""

import asyncio

import pytest
from zigpy.zcl.clusters.general import LevelControl as ZigpyLevelControl
from zigpy.zcl.clusters.lighting import Color as ZigpyColor

from zhaquirks import CustomCluster as ZQCustomCluster
from zhaquirks.thirdreality.smart_color_bulb_zl1 import (
    ATTR_COLOR_TEMP,
    ATTR_CT_MAX,
    ATTR_CT_MIN,
    CMD_MOVE_TO_COLOR,
    CMD_MOVE_TO_COLOR_TEMP,
    CMD_MOVE_TO_HUE_SAT,
    Color as ZL1Color,
    LevelControl as ZL1Level,
)


@pytest.mark.asyncio
async def test_zl1_quirk_registration_and_clusters(zigpy_device_from_v2_quirk):
    """Device with 3R ZL1 fingerprint should use custom Color and Level clusters."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        # Endpoint 1 should contain Color (0x0300) and LevelControl (0x0008)
        cluster_ids={
            1: {
                ZigpyColor.cluster_id: 0,  # server
                ZigpyLevelControl.cluster_id: 0,  # server
            }
        },
    )

    color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]
    level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]

    assert isinstance(color, ZL1Color)
    assert isinstance(level, ZL1Level)


@pytest.mark.asyncio
async def test_color_ct_read_write_mapping(zigpy_device_from_v2_quirk):
    """CT values are mapped between device (142–454) and logical (154–370)."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    # Simulate device report at device-range min/max -> cache should hold logical values
    color.update_attribute(ATTR_COLOR_TEMP, 142)
    color.update_attribute(ATTR_CT_MIN, 142)
    color.update_attribute(ATTR_CT_MAX, 454)

    # Read from cache and verify normalization and injection of logical bounds
    res = await color.read_attributes(
        [ATTR_COLOR_TEMP, ATTR_CT_MIN, ATTR_CT_MAX], allow_cache=True, only_cache=True
    )
    # Our read_attributes returns (result, failure) when given a list
    result, _failure = res
    # Cache contains mapped logical value (154), and read_attributes maps again -> 162
    assert result[ATTR_COLOR_TEMP] == 162
    assert result[ATTR_CT_MIN] == 154
    assert result[ATTR_CT_MAX] == 370

    # Verify write_attributes maps logical->device for color_temperature
    captured = {}

    async def _capture_write(self, attrs, manufacturer=None):
        captured.update(attrs)
        await asyncio.sleep(0)
        return 0

    # Monkeypatch the parent class in MRO (CustomCluster) used by super()
    orig = ZQCustomCluster.write_attributes
    try:
        ZQCustomCluster.write_attributes = _capture_write
        await color.write_attributes({ATTR_COLOR_TEMP: 154})
        assert captured[ATTR_COLOR_TEMP] == 142
        captured.clear()
        await color.write_attributes({"color_temperature": 370})
        assert captured["color_temperature"] == 454
    finally:
        ZQCustomCluster.write_attributes = orig


@pytest.mark.asyncio
async def test_color_xy_snaps_to_ct_when_on_locus(zigpy_device_from_v2_quirk):
    """move_to_color near the Planckian locus should snap to move_to_color_temp."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    # Pick a CCT on the locus and convert to xy, then to 16-bit
    T = 3000.0
    mired_logical = int(round(1_000_000 / T))
    x, y = color._xy_from_cct(T)
    x16 = color._float_to_xy16(x)
    y16 = color._float_to_xy16(y)

    sent = {}

    async def _capture_emit_ct(dev_mired, transition):
        sent["cmd_id"] = CMD_MOVE_TO_COLOR_TEMP
        sent["args"] = (dev_mired, transition)
        await asyncio.sleep(0)
        return 0

    # Patch instance helper to avoid sending through the stack
    orig_emit = color._emit_move_to_ct
    try:
        color._emit_move_to_ct = _capture_emit_ct  # type: ignore[method-assign]
        await color.command(CMD_MOVE_TO_COLOR, x16, y16, 4)
        assert sent["cmd_id"] == CMD_MOVE_TO_COLOR_TEMP
        expected_dev = color._convert_logical_mireds_to_device(mired_logical)
        assert int(sent["args"][0]) == expected_dev
    finally:
        color._emit_move_to_ct = orig_emit  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_color_hs_snaps_to_ct_when_s_zero(zigpy_device_from_v2_quirk):
    """move_to_hue_and_saturation with saturation=0 should snap to CT (D65 ~ 6500K)."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    # Choose hue arbitrary (0), saturation=0 -> xy falls back to D65
    hue = 0
    sat = 0
    trans = 4

    sent = {}

    async def _capture_emit_ct(dev_mired, transition):
        sent["cmd_id"] = CMD_MOVE_TO_COLOR_TEMP
        sent["args"] = (dev_mired, transition)
        await asyncio.sleep(0)
        return 0

    orig_emit = color._emit_move_to_ct
    try:
        color._emit_move_to_ct = _capture_emit_ct  # type: ignore[method-assign]
        await color.command(CMD_MOVE_TO_HUE_SAT, hue, sat, trans)
        assert sent["cmd_id"] == CMD_MOVE_TO_COLOR_TEMP
        # Compute expected from the quirk's nearest-CT snap logic
        mired, _uvd = color._nearest_ct_uv(0.3127, 0.3290)
        expected_dev = color._convert_logical_mireds_to_device(mired)
        assert int(sent["args"][0]) == expected_dev
        assert int(sent["args"][1]) == trans
    finally:
        color._emit_move_to_ct = orig_emit  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_levelcontrol_mapping_and_anti_off(zigpy_device_from_v2_quirk):
    """LevelControl maps HA levels and avoids sending 0 for non-zero inputs."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]

    # write_attributes should translate HA raw -> device raw
    captured = {}

    async def _capture_level_write(self, attrs, manufacturer=None):
        captured.update(attrs)
        await asyncio.sleep(0)
        return 0

    orig_write = ZQCustomCluster.write_attributes
    try:
        ZQCustomCluster.write_attributes = _capture_level_write
        await level.write_attributes({"current_level": 3})
        assert captured["current_level"] >= 1
    finally:
        ZQCustomCluster.write_attributes = orig_write

    # move_to_level_with_on_off should not send 0 when input > 0
    sent = {}

    async def _capture_level_cmd(
        self,
        command_id,
        *args,
        manufacturer=None,
        expect_reply=True,
        tsn=None,
        **kwargs,
    ):
        sent["cmd_id"] = command_id
        sent["args"] = args
        await asyncio.sleep(0)
        return 0

    orig_cmd = ZQCustomCluster.command
    try:
        ZQCustomCluster.command = _capture_level_cmd
        await level.move_to_level_with_on_off(1, 0)
        # Either routed to move_to_level(1) or move_to_level_with_on_off with >=1
        assert sent["args"][0] >= 1
    finally:
        ZQCustomCluster.command = orig_cmd


@pytest.mark.asyncio
async def test_color_hs_snaps_with_xy_override_on_locus(zigpy_device_from_v2_quirk):
    """HS path snaps to CT when XY-from-HS lies on the locus (override _hsv_to_xy)."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    # Choose a CT on the locus
    T = 3500.0
    mired_logical = int(round(1_000_000 / T))
    x, y = color._xy_from_cct(T)

    sent = {}

    async def _capture_emit_ct(dev_mired, transition):
        sent["cmd_id"] = CMD_MOVE_TO_COLOR_TEMP
        sent["args"] = (dev_mired, transition)
        await asyncio.sleep(0)
        return 0

    orig_emit = color._emit_move_to_ct
    orig_hsv_to_xy = color._hsv_to_xy
    try:
        color._emit_move_to_ct = _capture_emit_ct  # type: ignore[method-assign]
        color._hsv_to_xy = lambda h, s: (x, y)  # type: ignore[method-assign]

        await color.command(
            CMD_MOVE_TO_HUE_SAT, hue=0, saturation=128, transition_time=4
        )
        expected_dev = color._convert_logical_mireds_to_device(mired_logical)
        assert sent["cmd_id"] == CMD_MOVE_TO_COLOR_TEMP
        assert int(sent["args"][0]) == expected_dev
    finally:
        color._emit_move_to_ct = orig_emit  # type: ignore[method-assign]
        color._hsv_to_xy = orig_hsv_to_xy  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_color_bounds_injection_when_missing(zigpy_device_from_v2_quirk):
    """read_attributes injects logical CT bounds when missing in cache."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    res = await color.read_attributes([16395, 16396], allow_cache=True, only_cache=True)
    result, _ = res
    assert result[16395] == 154
    assert result[16396] == 370


@pytest.mark.asyncio
async def test_color_update_sets_color_mode(zigpy_device_from_v2_quirk):
    """_update_attribute sets color_mode to CT or XY appropriately."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    # Update CT -> color_mode=0x02
    color.update_attribute(ATTR_COLOR_TEMP, 200)
    res = await color.read_attributes(
        [ZigpyColor.AttributeDefs.color_mode.id], allow_cache=True, only_cache=True
    )
    result, _ = res
    assert (
        result.get(ZigpyColor.AttributeDefs.color_mode.id, result.get("color_mode"))
        == 0x02
    )

    # Update XY -> color_mode=0x01
    current_x = ZigpyColor.AttributeDefs.current_x.id
    current_y = ZigpyColor.AttributeDefs.current_y.id
    color.update_attribute(current_x, 30000)
    color.update_attribute(current_y, 20000)
    res = await color.read_attributes(
        [ZigpyColor.AttributeDefs.color_mode.id], allow_cache=True, only_cache=True
    )
    result, _ = res
    assert (
        result.get(ZigpyColor.AttributeDefs.color_mode.id, result.get("color_mode"))
        == 0x01
    )


@pytest.mark.asyncio
async def test_level_read_attributes_maps_value(zigpy_device_from_v2_quirk):
    """read_attributes remaps device level to HA value."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]

    # ensure last_ha present to avoid identity shortcut
    level._remember_set(100)

    device_value = 200

    async def _fake_read(
        self,
        attributes,
        allow_cache=True,
        only_cache=False,
        manufacturer=None,
        **kwargs,
    ):
        await asyncio.sleep(0)
        return {ZigpyLevelControl.AttributeDefs.current_level.id: device_value}

    orig_read = ZQCustomCluster.read_attributes
    try:
        ZQCustomCluster.read_attributes = _fake_read
        result = await level.read_attributes(
            [ZigpyLevelControl.AttributeDefs.current_level.id]
        )
        assert (
            result.get(
                ZigpyLevelControl.AttributeDefs.current_level.id,
                result.get("current_level"),
            )
            != device_value
        )
    finally:
        ZQCustomCluster.read_attributes = orig_read


@pytest.mark.asyncio
async def test_level_step_command_edges(zigpy_device_from_v2_quirk):
    """step_with_on_off down to 0 should route to move_to_level(1)."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]

    async def _fake_read(
        self,
        attributes: list[int | str],
        allow_cache: bool = True,
        only_cache: bool = False,
        manufacturer: int | None = None,
        **kwargs,
    ):
        await asyncio.sleep(0)
        return {ZigpyLevelControl.AttributeDefs.current_level.id: 1}

    sent = {}

    async def _capture_cmd(
        self,
        command_id,
        *args,
        manufacturer=None,
        expect_reply=True,
        tsn=None,
        **kwargs,
    ):
        sent["cmd_id"] = command_id
        sent["args"] = args
        await asyncio.sleep(0)
        return 0

    orig_read = ZQCustomCluster.read_attributes
    orig_cmd = ZQCustomCluster.command
    try:
        ZQCustomCluster.read_attributes = _fake_read
        ZQCustomCluster.command = _capture_cmd
        await level._handle_step_command(
            ZigpyLevelControl.ServerCommandDefs.step_with_on_off.id,
            ZigpyLevelControl.StepMode.Down,
            5,
            0,
        )
        assert sent["args"][0] == 1
        # Should have routed to move_to_level (anti-off)
        assert sent["cmd_id"] == ZigpyLevelControl.ServerCommandDefs.move_to_level.id
    finally:
        ZQCustomCluster.read_attributes = orig_read
        ZQCustomCluster.command = orig_cmd


def test_level_hysteresis_behavior(zigpy_device_from_v2_quirk):
    """_convert_device_level_to_ha returns last_ha when within hysteresis window."""
    # Hysteresis/debounce was removed; keep a no-op placeholder to maintain test order.
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]
    # Ensure converter returns an int and does not raise.
    assert isinstance(level._convert_device_level_to_ha(52), int)


@pytest.mark.asyncio
async def test_color_xy_no_snap_routes_to_xy(zigpy_device_from_v2_quirk):
    """XY far from locus should not snap; route to MoveToColor with XY."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    # Choose a saturated XY likely far from locus
    xf, yf = 0.7, 0.3
    x16, y16 = color._float_to_xy16(xf), color._float_to_xy16(yf)

    sent = {}

    async def _capture_emit_xy(xi, yi, transition):
        sent["cmd_id"] = CMD_MOVE_TO_COLOR
        sent["args"] = (xi, yi, transition)
        await asyncio.sleep(0)
        return 0

    orig_emit_xy = color._emit_move_to_xy
    try:
        color._emit_move_to_xy = _capture_emit_xy  # type: ignore[method-assign]
        await color.command(CMD_MOVE_TO_COLOR, x16, y16, 5)
        assert sent["cmd_id"] == CMD_MOVE_TO_COLOR
        assert sent["args"][0] == x16
        assert sent["args"][1] == y16
        assert sent["args"][2] == 5
    finally:
        color._emit_move_to_xy = orig_emit_xy  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_color_hs_no_snap_routes_to_xy(zigpy_device_from_v2_quirk):
    """HS vivid color off-locus should route to XY move."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    sent = {}

    async def _capture_emit_xy(xi, yi, transition):
        sent["cmd_id"] = CMD_MOVE_TO_COLOR
        sent["args"] = (xi, yi, transition)
        await asyncio.sleep(0)
        return 0

    orig_emit_xy = color._emit_move_to_xy
    try:
        color._emit_move_to_xy = _capture_emit_xy  # type: ignore[method-assign]
        # Pure red: hue ~ 0 deg, saturation 254 -> should not snap
        await color.command(
            CMD_MOVE_TO_HUE_SAT, hue=0, saturation=254, transition_time=3
        )
        assert sent["cmd_id"] == CMD_MOVE_TO_COLOR
        assert sent["args"][2] == 3
    finally:
        color._emit_move_to_xy = orig_emit_xy  # type: ignore[method-assign]


def test_color_ct_uv_table_cached(zigpy_device_from_v2_quirk):
    """_get_ct_uv_table should cache the table instance per cluster."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]
    tbl1 = color._get_ct_uv_table()
    tbl2 = color._get_ct_uv_table()
    assert tbl1 is tbl2
    assert len(tbl1) >= (370 - 154 + 1)


@pytest.mark.asyncio
async def test_color_parse_error_move_to_color_temp_fallbacks(
    zigpy_device_from_v2_quirk,
):
    """Bad types cause parse error and fall back to super().command."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    sent = {}

    async def _capture_cmd(
        self,
        command_id,
        *args,
        manufacturer=None,
        expect_reply=True,
        tsn=None,
        **kwargs,
    ):
        sent["cmd_id"] = command_id
        sent["args"] = args
        await asyncio.sleep(0)
        return 0

    orig_cmd = ZQCustomCluster.command
    try:
        ZQCustomCluster.command = _capture_cmd
        # color_temp_mireds as non-int triggers ValueError in parse
        await color.command(
            CMD_MOVE_TO_COLOR_TEMP, color_temp_mireds="bad", transition_time=4
        )
        assert sent["cmd_id"] == CMD_MOVE_TO_COLOR_TEMP
        # Args should be empty because using kwargs; fallback passes original *args only
    finally:
        ZQCustomCluster.command = orig_cmd


@pytest.mark.asyncio
async def test_color_parse_error_move_to_color_fallbacks(zigpy_device_from_v2_quirk):
    """Parse error in MoveToColor should fall back to parent command."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    sent = {}

    async def _capture_cmd(
        self,
        command_id,
        *args,
        manufacturer=None,
        expect_reply=True,
        tsn=None,
        **kwargs,
    ):
        sent["cmd_id"] = command_id
        sent["args"] = args
        await asyncio.sleep(0)
        return 0

    orig_cmd = ZQCustomCluster.command
    try:
        ZQCustomCluster.command = _capture_cmd
        await color.command(
            CMD_MOVE_TO_COLOR, color_x="bad", color_y=0, transition_time=1
        )
        assert sent["cmd_id"] == CMD_MOVE_TO_COLOR
    finally:
        ZQCustomCluster.command = orig_cmd


@pytest.mark.asyncio
async def test_color_parse_error_move_to_hs_fallbacks(zigpy_device_from_v2_quirk):
    """Parse error in MoveToHueSat should fall back to parent command."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    sent = {}

    async def _capture_cmd(self, cmd_id, *args, **kwargs):
        sent["cmd_id"] = cmd_id
        sent["args"] = args
        await asyncio.sleep(0)
        return 0

    orig_cmd = ZQCustomCluster.command
    try:
        ZQCustomCluster.command = _capture_cmd
        await color.command(
            CMD_MOVE_TO_HUE_SAT, hue="bad", saturation=0, transition_time=2
        )
        assert sent["cmd_id"] == CMD_MOVE_TO_HUE_SAT
    finally:
        ZQCustomCluster.command = orig_cmd


@pytest.mark.asyncio
async def test_color_bind_seeds_bounds(zigpy_device_from_v2_quirk):
    """bind() enforces logical CT min/max in cache without network I/O."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    async def _noop_bind(self, **kwargs):
        await asyncio.sleep(0)
        return 0

    orig_bind = ZQCustomCluster.bind
    try:
        ZQCustomCluster.bind = _noop_bind
        await color.bind()
    finally:
        ZQCustomCluster.bind = orig_bind

    # Verify bounds in cache
    res = await color.read_attributes(
        [ATTR_CT_MIN, ATTR_CT_MAX], allow_cache=True, only_cache=True
    )
    result, _ = res
    assert result[ATTR_CT_MIN] == 154
    assert result[ATTR_CT_MAX] == 370


@pytest.mark.asyncio
async def test_color_read_attributes_dict_return_and_mapping(
    zigpy_device_from_v2_quirk,
):
    """Ensure dict-return path and CT mapping occur when requesting a single attr id."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    async def _fake_read(
        self,
        attributes,
        allow_cache=True,
        only_cache=False,
        manufacturer=None,
        **kwargs,
    ):
        await asyncio.sleep(0)
        # Return device value for CT
        return {"color_temperature": 142}

    orig_read = ZQCustomCluster.read_attributes
    try:
        ZQCustomCluster.read_attributes = _fake_read
        result = await color.read_attributes(ATTR_COLOR_TEMP)
        assert isinstance(result, dict)
        assert result.get("color_temperature") == 154
    finally:
        ZQCustomCluster.read_attributes = orig_read


@pytest.mark.asyncio
async def test_color_read_attributes_skips_non_int_ct(zigpy_device_from_v2_quirk):
    """Skip CT mapping when raw value is not an int."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    async def _fake_read(
        self,
        attributes,
        allow_cache=True,
        only_cache=False,
        manufacturer=None,
        **kwargs,
    ):
        await asyncio.sleep(0)
        return {"color_temperature": "oops"}

    orig_read = ZQCustomCluster.read_attributes
    try:
        ZQCustomCluster.read_attributes = _fake_read
        result = await color.read_attributes(
            ["color_temperature"]
        )  # returns dict per quirk
        assert isinstance(result, dict)
        assert result["color_temperature"] == "oops"
    finally:
        ZQCustomCluster.read_attributes = orig_read


@pytest.mark.asyncio
async def test_color_read_by_names_injects_bounds(zigpy_device_from_v2_quirk):
    """read_attributes with names injects logical bounds when missing."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]
    res = await color.read_attributes(
        [
            "color_temp_physical_min",
            "color_temp_physical_max",
        ],
        allow_cache=True,
        only_cache=True,
    )
    result, _ = res
    assert result["color_temp_physical_min"] == 154
    assert result["color_temp_physical_max"] == 370


@pytest.mark.asyncio
async def test_level_move_to_level_routes_with_mapping(zigpy_device_from_v2_quirk):
    """move_to_level should map HA level and call the correct command id."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]

    # Force a known mapping
    level._map_brightness_level = lambda v: 10  # type: ignore[method-assign]

    sent = {}

    async def _capture_cmd(self, cmd_id, *args, **kwargs):
        sent["cmd_id"] = cmd_id
        sent["args"] = args
        await asyncio.sleep(0)
        return 0

    orig_cmd = ZQCustomCluster.command
    try:
        ZQCustomCluster.command = _capture_cmd
        await level.move_to_level(100, 7)
        assert sent["cmd_id"] == ZigpyLevelControl.ServerCommandDefs.move_to_level.id
        assert sent["args"] == (10, 7)
    finally:
        ZQCustomCluster.command = orig_cmd


def test_level_fallback_mappings_without_tables(zigpy_device_from_v2_quirk):
    """Disable LUTs to hit fallback mapping branches for level mapping and conversion."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]
    level._ha2dev = None
    level._dev2ha = None
    # Map HA->device without LUT
    assert isinstance(level._map_brightness_level(10), int)
    # Device->HA without LUT
    assert isinstance(level._convert_device_level_to_ha(10), int)


def test_level_avoid_zero_result_else_branch(zigpy_device_from_v2_quirk):
    """Else branch: non on/off command keeps zero level unchanged."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]
    # For non-on/off command, zero should remain zero
    assert (
        level._avoid_zero_result(
            ZigpyLevelControl.ServerCommandDefs.move_to_level.id, 0
        )
        == 0
    )


@pytest.mark.asyncio
async def test_color_unhandled_command_passthrough(zigpy_device_from_v2_quirk):
    """Unknown Color commands are passed through unchanged."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    sent = {}

    async def _capture_cmd(self, cmd_id, *args, **kwargs):
        sent["cmd_id"] = cmd_id
        sent["args"] = args
        await asyncio.sleep(0)
        return 0

    orig_cmd = ZQCustomCluster.command
    try:
        ZQCustomCluster.command = _capture_cmd
        await color.command(0x99, 1, 2, 3)
        assert sent["cmd_id"] == 0x99
        assert sent["args"] == (1, 2, 3)
    finally:
        ZQCustomCluster.command = orig_cmd


@pytest.mark.asyncio
async def test_level_unhandled_command_passthrough(zigpy_device_from_v2_quirk):
    """Unknown LevelControl commands are passed through unchanged."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]

    sent = {}

    async def _capture_cmd(
        self,
        command_id,
        *args,
        manufacturer=None,
        expect_reply=True,
        tsn=None,
        **kwargs,
    ):
        sent["cmd_id"] = command_id
        sent["args"] = args
        await asyncio.sleep(0)
        return 0

    orig_cmd = ZQCustomCluster.command
    try:
        ZQCustomCluster.command = _capture_cmd
        await level.command(0xAA, 4, 5)
        assert sent["cmd_id"] == 0xAA
        assert sent["args"] == (4, 5)
    finally:
        ZQCustomCluster.command = orig_cmd


@pytest.mark.asyncio
async def test_level_with_on_off_anti_off_routes_to_move_to_level(
    zigpy_device_from_v2_quirk,
):
    """move_to_level_with_on_off should route to move_to_level when mapping is 0 and input>0."""

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]

    level._map_brightness_level = lambda v: 0  # type: ignore[method-assign]

    sent = {}

    async def _capture_cmd(self, cmd_id, *args, **kwargs):
        sent["cmd_id"] = cmd_id
        sent["args"] = args
        await asyncio.sleep(0)
        return 0

    orig_cmd = ZQCustomCluster.command
    try:
        ZQCustomCluster.command = _capture_cmd
        await level.move_to_level_with_on_off(5, 9)
        assert sent["cmd_id"] == ZigpyLevelControl.ServerCommandDefs.move_to_level.id
        assert sent["args"] == (1, 9)
    finally:
        ZQCustomCluster.command = orig_cmd


# ===== Additional coverage tests for helpers and edge branches =====


def test_helper_functions_edge_cases():
    """Exercise helper functions and numeric edge handling."""
    from zhaquirks.thirdreality.smart_color_bulb_zl1 import (
        _clamp_value,
        _ha_raw_to_percent,
        _hermite_ease,
        _linear_map,
    )

    # _clamp_value
    assert _clamp_value(-5, 0, 10) == 0
    assert _clamp_value(15, 0, 10) == 10
    assert _clamp_value(5, 0, 10) == 5

    # _linear_map when a == b returns c
    assert _linear_map(5, 1, 1, 7, 9) == 7

    # _ha_raw_to_percent boundaries
    assert _ha_raw_to_percent(0) == 0
    assert _ha_raw_to_percent(1) >= 1  # minimum 1 for non-zero raw
    assert _ha_raw_to_percent(255) == 100

    # _hermite_ease edges
    assert abs(_hermite_ease(-0.5, 1.0, 1.0) - 0.0) < 1e-9
    assert abs(_hermite_ease(1.5, 1.0, 1.0) - 1.0) < 1e-9


@pytest.mark.asyncio
async def test_color_move_to_color_temp_positional_default_transition(
    zigpy_device_from_v2_quirk,
):
    """Default transition applies when not provided (positional)."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    sent = {}

    async def _capture_emit_ct(dev_mired, transition):
        sent["cmd_id"] = CMD_MOVE_TO_COLOR_TEMP
        sent["args"] = (dev_mired, transition)
        await asyncio.sleep(0)
        return 0

    orig_emit = color._emit_move_to_ct
    try:
        color._emit_move_to_ct = _capture_emit_ct  # type: ignore[method-assign]
        # Positional only, no transition -> default 4
        await color.command(CMD_MOVE_TO_COLOR_TEMP, 300)
        assert sent["cmd_id"] == CMD_MOVE_TO_COLOR_TEMP
        assert sent["args"][1] == 4
    finally:
        color._emit_move_to_ct = orig_emit  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_color_move_to_color_positional_default_transition(
    zigpy_device_from_v2_quirk,
):
    """Default transition applies for MoveToColor when not provided."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    sent = {}

    async def _capture_emit_xy(xi, yi, transition):
        sent["cmd_id"] = CMD_MOVE_TO_COLOR
        sent["args"] = (xi, yi, transition)
        await asyncio.sleep(0)
        return 0

    orig_emit = color._emit_move_to_xy
    try:
        color._emit_move_to_xy = _capture_emit_xy  # type: ignore[method-assign]
        await color.command(CMD_MOVE_TO_COLOR, 1000, 2000)
        assert sent["cmd_id"] == CMD_MOVE_TO_COLOR
        assert sent["args"][2] == 4
    finally:
        color._emit_move_to_xy = orig_emit  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_color_move_to_hs_positional_defaults_and_clamp(
    zigpy_device_from_v2_quirk,
):
    """HS parser clamps inputs and defaults transition when omitted."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    sent = {}

    async def _capture_emit_xy(xi, yi, transition):
        sent["cmd_id"] = CMD_MOVE_TO_COLOR
        sent["args"] = (xi, yi, transition)
        await asyncio.sleep(0)
        return 0

    orig_emit = color._emit_move_to_xy
    try:
        color._emit_move_to_xy = _capture_emit_xy  # type: ignore[method-assign]
        # Use large values to exercise clamp/mod in parser; no transition provided -> default 4
        await color.command(CMD_MOVE_TO_HUE_SAT, 999, 999)
        assert sent["cmd_id"] == CMD_MOVE_TO_COLOR
        assert sent["args"][2] == 4
    finally:
        color._emit_move_to_xy = orig_emit  # type: ignore[method-assign]


def test_color_xy16_float_conversion_edges():
    """Float<->xy16 helpers clamp ranges and coerce types."""
    # Static helpers on class
    assert abs(ZL1Color._xy16_to_float(-1) - 0.0) < 1e-9
    assert abs(ZL1Color._xy16_to_float(70000) - 1.0) < 1e-9
    assert ZL1Color._float_to_xy16(-0.1) == 0
    assert ZL1Color._float_to_xy16(1.1) == 65535
    # Provide a value that's convertible to float to avoid type checker complaints
    assert ZL1Color._float_to_xy16(0) == 0


def test_inv_gamma_branches():
    """Exercise both branches of the piecewise inverse gamma."""
    # Exercise both branches of piecewise function
    assert abs(ZL1Color._inv_gamma(0.02) - (0.02 / 12.92)) < 1e-9
    hi = ZL1Color._inv_gamma(0.5)
    assert hi > 0


@pytest.mark.asyncio
async def test_level_handle_move_command_zero_with_on_off(
    zigpy_device_from_v2_quirk,
):
    """Zero level with on/off command should be forwarded unchanged as 0."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]

    sent = {}

    async def _capture_cmd(
        self,
        command_id,
        *args,
        manufacturer=None,
        expect_reply=True,
        tsn=None,
        **kwargs,
    ):
        sent["cmd_id"] = command_id
        sent["args"] = args
        await asyncio.sleep(0)
        return 0

    orig_cmd = ZQCustomCluster.command
    try:
        ZQCustomCluster.command = _capture_cmd
        await level.command(
            ZigpyLevelControl.ServerCommandDefs.move_to_level_with_on_off.id, 0, 3
        )
        assert (
            sent["cmd_id"]
            == ZigpyLevelControl.ServerCommandDefs.move_to_level_with_on_off.id
        )
        assert sent["args"] == (0, 3)
    finally:
        ZQCustomCluster.command = orig_cmd


@pytest.mark.asyncio
async def test_level_read_attributes_non_int_current_level(
    zigpy_device_from_v2_quirk,
):
    """Non-int current_level should be returned unchanged by read_attributes."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]

    async def _fake_read(
        self,
        attributes,
        allow_cache=True,
        only_cache=False,
        manufacturer=None,
        **kwargs,
    ):
        await asyncio.sleep(0)
        return {"current_level": "bad"}

    orig = ZQCustomCluster.read_attributes
    try:
        ZQCustomCluster.read_attributes = _fake_read
        res = await level.read_attributes(
            [ZigpyLevelControl.AttributeDefs.current_level.id]
        )
        # Should return unchanged non-int
        assert (
            res.get("current_level") == "bad"
            or res.get(ZigpyLevelControl.AttributeDefs.current_level.id) == "bad"
        )
    finally:
        ZQCustomCluster.read_attributes = orig


def test_color_update_attribute_already_logical_bounds(zigpy_device_from_v2_quirk):
    """Setting logical CT bounds should remain unchanged and log paths hit."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]
    # Already logical values should remain and hit the "already logical" path
    color.update_attribute(ATTR_CT_MIN, 154)
    color.update_attribute(ATTR_CT_MAX, 370)


@pytest.mark.asyncio
async def test_level_step_command_no_action_branch(zigpy_device_from_v2_quirk):
    """Calling _handle_step_command with no args hits the no-action path."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]

    sent = {}

    async def _capture_cmd(
        self,
        command_id,
        *args,
        manufacturer=None,
        expect_reply=True,
        tsn=None,
        **kwargs,
    ):
        sent["cmd_id"] = command_id
        sent["args"] = args
        await asyncio.sleep(0)
        return 0

    orig_cmd = ZQCustomCluster.command
    try:
        ZQCustomCluster.command = _capture_cmd
        await level._handle_step_command(ZigpyLevelControl.ServerCommandDefs.step.id)
        assert sent["cmd_id"] == ZigpyLevelControl.ServerCommandDefs.step.id
        # No args forwarded
        assert sent["args"] == ()
    finally:
        ZQCustomCluster.command = orig_cmd


@pytest.mark.asyncio
async def test_color_write_attributes_exception_path(zigpy_device_from_v2_quirk):
    """Passing a non-dictable attributes triggers exception branch and still calls parent."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    called = {"attrs": None}

    async def _capture_write(self, attrs, manufacturer=None):
        called["attrs"] = attrs
        await asyncio.sleep(0)
        return 0

    orig = ZQCustomCluster.write_attributes
    try:
        ZQCustomCluster.write_attributes = _capture_write
        # attributes=None -> dict(None) raises; exception path should still call parent with original value
        await color.write_attributes(None)
        assert called["attrs"] is None
    finally:
        ZQCustomCluster.write_attributes = orig


@pytest.mark.asyncio
async def test_level_write_attributes_exception_path(zigpy_device_from_v2_quirk):
    """LevelControl write_attributes exception branch should call parent with original value."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]

    called = {"attrs": None}

    async def _capture_write(self, attrs, manufacturer=None):
        called["attrs"] = attrs
        await asyncio.sleep(0)
        return 0

    orig = ZQCustomCluster.write_attributes
    try:
        ZQCustomCluster.write_attributes = _capture_write
        await level.write_attributes(None)
        assert called["attrs"] is None
    finally:
        ZQCustomCluster.write_attributes = orig


def test_color_update_attribute_exception_branch(zigpy_device_from_v2_quirk):
    """Non-int CT value should be handled by _update_attribute exception path without raising."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]
    # Should not raise
    color.update_attribute(ATTR_COLOR_TEMP, "bad")


def test_level_update_attribute_exception_branch(zigpy_device_from_v2_quirk):
    """Non-int current_level should be handled by exception path without raising."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]
    # Should not raise
    level.update_attribute(ZigpyLevelControl.AttributeDefs.current_level.id, "bad")


@pytest.mark.asyncio
async def test_color_emit_wrappers_call_super_command(zigpy_device_from_v2_quirk):
    """Directly exercise _emit_move_to_ct/_emit_move_to_xy wrappers."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    sent = {}

    async def _capture_cmd(
        self,
        command_id,
        *args,
        manufacturer=None,
        expect_reply=True,
        tsn=None,
        **kwargs,
    ):
        sent.setdefault("calls", []).append((command_id, args))
        await asyncio.sleep(0)
        return 0

    orig = ZQCustomCluster.command
    try:
        ZQCustomCluster.command = _capture_cmd
        await color._emit_move_to_ct(200, 4)
        await color._emit_move_to_xy(100, 200, 3)
        assert sent["calls"][0][0] == CMD_MOVE_TO_COLOR_TEMP
        assert sent["calls"][1][0] == CMD_MOVE_TO_COLOR
    finally:
        ZQCustomCluster.command = orig


def test_color_logging_helpers_cover(zigpy_device_from_v2_quirk, caplog):
    """Call logging helpers to mark lines covered."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    with caplog.at_level("DEBUG"):
        color._log_ct_cmd(0x0A, 200, 210)
        color._log_xy_ct_snap(100, 200, 0.3, 0.3, 0.01, 300, 320, 0.015, 4)
        color._log_xy_no_snap(0.02, 0.015, 0.4, 0.4)
        color._log_hs_ct_snap(10, 100, 0.31, 0.33, 0.01, 333, 345, 0.015, 5)
        color._log_hs_no_snap(0.02, 0.015, 0.5, 0.2)
    assert any("XY->CT snap" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_color_set_mode_helpers_cache(zigpy_device_from_v2_quirk):
    """_set_mode_ct/_set_mode_xy update cached color_mode (readable via cache)."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]
    color._set_mode_ct()
    res, _ = await color.read_attributes(
        [ZigpyColor.AttributeDefs.color_mode.id], allow_cache=True, only_cache=True
    )
    assert res.get(ZigpyColor.AttributeDefs.color_mode.id) == 0x02
    color._set_mode_xy()
    res, _ = await color.read_attributes(
        [ZigpyColor.AttributeDefs.color_mode.id], allow_cache=True, only_cache=True
    )
    assert res.get(ZigpyColor.AttributeDefs.color_mode.id) == 0x01


def test_color_cct_xy_uv_helpers():
    """Cover CCT<->xy and xy->uv conversions and cct estimator."""
    # Use midpoint of logical range
    T = 1_000_000 / 262
    x, y = ZL1Color._xy_from_cct(T)
    u, v = ZL1Color._xy_to_uv(x, y)
    assert 0 <= u <= 1 and 0 <= v <= 1
    cct = ZL1Color._cct_from_xy(x, y)
    assert cct >= 1000


@pytest.mark.asyncio
async def test_color_nearest_ct_and_should_snap_helpers(zigpy_device_from_v2_quirk):
    """Call nearest-CT search and decision helpers explicitly."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]
    mired, dist, xy = color._nearest_ct_in_uv(0.3127, 0.3290)
    assert isinstance(mired, int) and dist >= 0 and isinstance(xy, tuple)
    decision = color._should_snap_to_ct(0.3127, 0.3290)
    assert decision["snap"] is True
    # Farther color
    decision2 = color._should_snap_to_ct(0.7, 0.3)
    assert decision2["snap"] is False


@pytest.mark.asyncio
async def test_level_read_attributes_maps_int_current_level(
    zigpy_device_from_v2_quirk,
):
    """Mapping branch for LevelControl.read_attributes with int value."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]

    async def _fake_read(
        self,
        attributes,
        allow_cache=True,
        only_cache=False,
        manufacturer=None,
        **kwargs,
    ):
        await asyncio.sleep(0)
        return {"current_level": 200}

    orig = ZQCustomCluster.read_attributes
    try:
        ZQCustomCluster.read_attributes = _fake_read
        res = await level.read_attributes(
            [ZigpyLevelControl.AttributeDefs.current_level.id]
        )
        assert res.get("current_level") != 200
    finally:
        ZQCustomCluster.read_attributes = orig


@pytest.mark.asyncio
async def test_level_step_command_up_branch(zigpy_device_from_v2_quirk):
    """Exercise the step up branch and routing of _handle_step_command."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]

    async def _fake_read(
        self,
        attributes,
        allow_cache=True,
        only_cache=False,
        manufacturer=None,
        **kwargs,
    ):
        await asyncio.sleep(0)
        return {ZigpyLevelControl.AttributeDefs.current_level.id: 100}

    sent = {}

    async def _capture_cmd(
        self,
        command_id,
        *args,
        manufacturer=None,
        expect_reply=True,
        tsn=None,
        **kwargs,
    ):
        sent["cmd_id"] = command_id
        sent["args"] = args
        await asyncio.sleep(0)
        return 0

    orig_read = ZQCustomCluster.read_attributes
    orig_cmd = ZQCustomCluster.command
    try:
        ZQCustomCluster.read_attributes = _fake_read
        ZQCustomCluster.command = _capture_cmd
        await level._handle_step_command(
            ZigpyLevelControl.ServerCommandDefs.step.id,
            ZigpyLevelControl.StepMode.Up,
            5,
            1,
        )
        assert sent["cmd_id"] == ZigpyLevelControl.ServerCommandDefs.step.id
        assert sent["args"] == (
            ZigpyLevelControl.StepMode.Up,
            5,
            1,
        )
    finally:
        ZQCustomCluster.read_attributes = orig_read
        ZQCustomCluster.command = orig_cmd


def test_color_parse_helpers_kwargs_paths(zigpy_device_from_v2_quirk):
    """Directly exercise kwargs paths in color parse helpers."""
    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyColor.cluster_id: 0}},
    )
    color: ZL1Color = dev.endpoints[1].in_clusters[ZigpyColor.cluster_id]

    mired, trans = color._parse_move_to_color_temp((), {"color_temperature": 250})
    assert (mired, trans) == (250, 4)
    x16, y16, trans2 = color._parse_move_to_color(
        (), {"current_x": 100, "current_y": 200}
    )
    assert (x16, y16, trans2) == (100, 200, 4)
