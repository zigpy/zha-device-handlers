"""Tests for Third Reality quirks."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import MultistateInput
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.thirdreality.button import MultistateInputCluster
import zhaquirks.thirdreality.night_light
import zhaquirks.thirdreality.three_button
import zhaquirks.thirdreality.zha_scale_quirk
from zhaquirks.thirdreality.zha_scale_quirk import ThirdRealityScaleCluster

zhaquirks.setup()


@pytest.mark.parametrize("quirk", (zhaquirks.thirdreality.night_light.Nightlight,))
async def test_third_reality_nightlight(zigpy_device_from_quirk, quirk):
    """Test Third Reality night light forwarding motion attribute to IasZone cluster."""

    device = zigpy_device_from_quirk(quirk)

    ias_zone_cluster = device.endpoints[1].ias_zone
    ias_zone_listener = ClusterListener(ias_zone_cluster)

    ias_zone_status_id = IasZone.AttributeDefs.zone_status.id

    third_reality_cluster = device.endpoints[1].in_clusters[0xFC00]

    # 0x0002 is also used on manufacturer specific cluster for motion events
    third_reality_cluster.update_attribute(0x0002, IasZone.ZoneStatus.Alarm_1)

    assert len(ias_zone_listener.attribute_updates) == 1
    assert ias_zone_listener.attribute_updates[0][0] == ias_zone_status_id
    assert ias_zone_listener.attribute_updates[0][1] == IasZone.ZoneStatus.Alarm_1

    # turn off motion alarm
    third_reality_cluster.update_attribute(0x0002, 0)

    assert len(ias_zone_listener.attribute_updates) == 2
    assert ias_zone_listener.attribute_updates[1][0] == ias_zone_status_id
    assert ias_zone_listener.attribute_updates[1][1] == 0


@pytest.mark.parametrize(
    ("attr_value", "expected_action"),
    [
        (1, "single"),  # 1 corresponds to single click
        (2, "double"),  # 2 corresponds to double click
        (0, "hold"),  # 0 corresponds to hold
        (255, "release"),  # 255 corresponds to release
    ],
)
@pytest.mark.parametrize(
    ("manufacturer", "model"),
    [("Third Reality, Inc", "3RSB22BZ")],
)
async def test_third_reality_button_v2(
    zigpy_device_from_v2_quirk, manufacturer, model, attr_value, expected_action
):
    """Test Third Reality button event conversion and triggering functionality."""
    device = zigpy_device_from_v2_quirk(manufacturer, model)
    multistate_cluster = device.endpoints[1].in_clusters[
        MultistateInputCluster.cluster_id
    ]

    # Create mock listener and register it with the cluster
    listener = mock.MagicMock()
    multistate_cluster.add_listener(listener)

    multistate_cluster.update_attribute(
        0x0055, attr_value
    )  # 1 corresponds to single click
    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args_list[0] == mock.call(
        expected_action, {"value": attr_value}
    )


@pytest.mark.parametrize(
    ("endpoint_id", "attr_value", "expected_action"),
    [
        (1, 1, "single"),
        (2, 2, "double"),
        (3, 0, "hold"),
    ],
)
async def test_third_reality_three_button_v2_events(
    zigpy_device_from_v2_quirk, endpoint_id, attr_value, expected_action
):
    """Test Third Reality three-button event conversion on all button endpoints."""
    device = zigpy_device_from_v2_quirk(
        "Third Reality, Inc",
        "3RSB01085Z",
        cluster_ids={
            1: {MultistateInput.cluster_id: ClusterType.Server},
            2: {MultistateInput.cluster_id: ClusterType.Server},
            3: {MultistateInput.cluster_id: ClusterType.Server},
        },
    )
    multistate_cluster = device.endpoints[endpoint_id].in_clusters[
        MultistateInput.cluster_id
    ]

    listener = mock.MagicMock()
    multistate_cluster.add_listener(listener)

    multistate_cluster.update_attribute(0x0055, attr_value)
    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args_list[0] == mock.call(
        expected_action, {"value": attr_value}
    )


async def test_third_reality_three_button_v2_ignores_unknown_press_type(
    zigpy_device_from_v2_quirk,
):
    """Test unsupported button press values do not emit events."""
    device = zigpy_device_from_v2_quirk(
        "Third Reality, Inc",
        "3RSB01085Z",
        cluster_ids={
            1: {MultistateInput.cluster_id: ClusterType.Server},
            2: {MultistateInput.cluster_id: ClusterType.Server},
            3: {MultistateInput.cluster_id: ClusterType.Server},
        },
    )
    multistate_cluster = device.endpoints[1].in_clusters[MultistateInput.cluster_id]

    listener = mock.MagicMock()
    multistate_cluster.add_listener(listener)

    multistate_cluster.update_attribute(0x0055, 42)
    assert listener.zha_send_event.call_count == 0


# ---------------------------------------------------------------------------
# Third Reality Kitchen Scale (3RKS030Z) tests
# ---------------------------------------------------------------------------

SCALE_CLUSTER_ID = ThirdRealityScaleCluster.cluster_id  # 0xFF0C
ATTR_SCALE_VAL = ThirdRealityScaleCluster.AttributeDefs.SCALE_VAL.id  # 0x0001
ATTR_DISPLAY_VAL = ThirdRealityScaleCluster.AttributeDefs.DISPLAY_VAL.id  # 0x0002
ATTR_PRIVATE_STATUS = ThirdRealityScaleCluster.AttributeDefs.PRIVATE_STATUS.id  # 0x0003
ATTR_PRIVATE_UNIT = ThirdRealityScaleCluster.AttributeDefs.PRIVATE_UNIT.id  # 0x0004
ATTR_TARGET_VAL = ThirdRealityScaleCluster.AttributeDefs.TARGET_VAL.id  # 0x0005


@pytest.fixture
def scale_device(zigpy_device_from_v2_quirk):
    """Return a quirked 3RKS030Z device."""
    return zigpy_device_from_v2_quirk("Third Reality, Inc", "3RKS030Z")


@pytest.fixture
def scale_cluster(scale_device):
    """Return the ThirdRealityScaleCluster from the quirked device."""
    return scale_device.endpoints[1].in_clusters[SCALE_CLUSTER_ID]


# --- Quirk registration ---


async def test_scale_quirk_registers_custom_cluster(scale_cluster):
    """Quirk must replace the standard cluster with ThirdRealityScaleCluster."""
    assert isinstance(scale_cluster, ThirdRealityScaleCluster)


# --- Attribute definitions ---


async def test_scale_cluster_has_expected_attributes(scale_cluster):
    """Cluster must expose exactly the five defined attributes."""
    expected = {
        "SCALE_VAL",
        "DISPLAY_VAL",
        "PRIVATE_STATUS",
        "PRIVATE_UNIT",
        "TARGET_VAL",
    }
    actual = {attr.name for attr in ThirdRealityScaleCluster.attributes.values()}
    assert actual == expected


# --- _update_attribute: gram mode (default) ---


async def test_scale_update_display_val_gram_mode_passthrough(scale_cluster):
    """DISPLAY_VAL in gram mode (unit=0) must store the raw integer value."""
    listener = ClusterListener(scale_cluster)
    scale_cluster._update_attribute(ATTR_DISPLAY_VAL, 500)
    assert listener.attribute_updates[-1] == (ATTR_DISPLAY_VAL, 500)


async def test_scale_update_scale_val_passthrough(scale_cluster):
    """SCALE_VAL is always stored as-is regardless of unit mode."""
    listener = ClusterListener(scale_cluster)
    scale_cluster._update_attribute(ATTR_SCALE_VAL, 250)
    assert listener.attribute_updates[-1] == (ATTR_SCALE_VAL, 250)


async def test_scale_update_private_status_passthrough(scale_cluster):
    """PRIVATE_STATUS is stored as-is."""
    listener = ClusterListener(scale_cluster)
    scale_cluster._update_attribute(ATTR_PRIVATE_STATUS, 1)
    assert listener.attribute_updates[-1] == (ATTR_PRIVATE_STATUS, 1)


# --- _update_attribute: unit switching ---


async def test_scale_update_private_unit_sets_current_unit(scale_cluster):
    """Writing PRIVATE_UNIT must update the internal _current_unit tracker."""
    scale_cluster._update_attribute(ATTR_PRIVATE_UNIT, 1)
    assert scale_cluster._current_unit == 1


async def test_scale_update_private_unit_stores_value(scale_cluster):
    """Writing PRIVATE_UNIT must also persist the value via super()."""
    listener = ClusterListener(scale_cluster)
    scale_cluster._update_attribute(ATTR_PRIVATE_UNIT, 1)
    assert listener.attribute_updates[-1] == (ATTR_PRIVATE_UNIT, 1)


# --- _update_attribute: lb:oz conversion ---


@pytest.mark.parametrize(
    ("raw_value", "expected_str"),
    [
        (0, "0lb 0.0oz"),  # zero
        (160, "1lb 0.0oz"),  # exactly 1 lb
        (247, "1lb 8.7oz"),  # 1 lb 8.7 oz (original docstring example)
        (320, "2lb 0.0oz"),  # exactly 2 lb
        (165, "1lb 0.5oz"),  # fractional oz
        (16, "0lb 1.6oz"),  # less than 1 lb
    ],
)
async def test_scale_display_val_lb_oz_conversion(
    scale_cluster, raw_value, expected_str
):
    """DISPLAY_VAL in lb:oz mode must be formatted as '{lb}lb {oz:.1f}oz'."""
    # Switch to lb:oz mode first
    scale_cluster._update_attribute(ATTR_PRIVATE_UNIT, 1)
    listener = ClusterListener(scale_cluster)
    scale_cluster._update_attribute(ATTR_DISPLAY_VAL, raw_value)
    assert listener.attribute_updates[-1] == (ATTR_DISPLAY_VAL, expected_str)


async def test_scale_display_val_switches_back_to_gram_mode(scale_cluster):
    """After switching back to gram mode (unit=0) DISPLAY_VAL must store raw int again."""
    # Enable lb:oz mode
    scale_cluster._update_attribute(ATTR_PRIVATE_UNIT, 1)
    # Switch back to gram mode
    scale_cluster._update_attribute(ATTR_PRIVATE_UNIT, 0)
    listener = ClusterListener(scale_cluster)
    scale_cluster._update_attribute(ATTR_DISPLAY_VAL, 300)
    assert listener.attribute_updates[-1] == (ATTR_DISPLAY_VAL, 300)
