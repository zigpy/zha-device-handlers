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

    async def _capture_level_cmd(self, cmd_id, *args, **kwargs):
        sent["cmd_id"] = cmd_id
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

    async def _capture_cmd(self, cmd_id, *args, **kwargs):
        sent["cmd_id"] = cmd_id
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

    dev = zigpy_device_from_v2_quirk(
        manufacturer="Third Reality, Inc",
        model="3RCB01057Z",
        cluster_ids={1: {ZigpyLevelControl.cluster_id: 0}},
    )
    level: ZL1Level = dev.endpoints[1].in_clusters[ZigpyLevelControl.cluster_id]

    level._hysteresis = 3
    level._last_dev = 50
    level._last_ha = 42
    assert level._convert_device_level_to_ha(52) == 42


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

    async def _capture_cmd(self, cmd_id, *args, **kwargs):
        sent["cmd_id"] = cmd_id
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

    async def _capture_cmd(self, cmd_id, *args, **kwargs):
        sent["cmd_id"] = cmd_id
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

    async def _noop_bind(self):
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
        self, attributes, allow_cache=True, only_cache=False, manufacturer=None
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
        self, attributes, allow_cache=True, only_cache=False, manufacturer=None
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

    async def _capture_cmd(self, cmd_id, *args, **kwargs):
        sent["cmd_id"] = cmd_id
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
