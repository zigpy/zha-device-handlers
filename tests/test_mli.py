"""Tests for the Müller Licht tint remote, Tuya variant (_TZ3000_bdbb0fon)."""

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Scenes
from zigpy.zcl.clusters.lighting import Color

import zhaquirks
from zhaquirks.mli.tint import TintRemoteTS1001

zhaquirks.setup()


def test_tint_ts1001_exposes_color_client_cluster(zigpy_device_from_quirk):
    """The Tuya variant must expose Color as a client cluster.

    The device sends move_to_color_temp/move_to_color but does not report the
    Color cluster in its output clusters; the quirk adds it so ZHA decodes the
    commands and emits zha_events.
    """
    device = zigpy_device_from_quirk(TintRemoteTS1001)

    assert Color.cluster_id in device.endpoints[1].out_clusters


def test_tint_ts1001_scene_write(zigpy_device_from_quirk):
    """A manufacturer-specific Basic 0x4005 write updates the scene attribute."""
    device = zigpy_device_from_quirk(TintRemoteTS1001)
    endpoint = device.endpoints[1]
    basic = endpoint.out_clusters[Basic.cluster_id]
    scenes = endpoint.out_clusters[Scenes.cluster_id]

    attribute = foundation.Attribute(
        attrid=0x4005,
        value=foundation.TypeValue(type=t.uint8_t, value=3),
    )
    args = foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Write_Attributes
    ].schema([attribute])

    basic.handle_cluster_general_request(
        foundation.ZCLHeader.general(1, foundation.GeneralCommand.Write_Attributes),
        args,
    )

    assert scenes.get(Scenes.AttributeDefs.current_scene.name) == 3
