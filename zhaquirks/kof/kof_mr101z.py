"""Module to handle quirks of the King of Fans MR101Z ceiling fan receiver.

The King of Fans ceiling fan receiver does not generate default replies. This
module overrides all server commands that do not have a mandatory reply to not
expect replies at all.
"""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Scenes,
)

from zhaquirks import NoReplyMixin


class KofBasic(NoReplyMixin, CustomCluster, Basic):
    """KOF Basic Cluster."""

    void_input_commands = {
        Basic.commands_by_name["reset_fact_default"].id,
    }


class KofIdentify(NoReplyMixin, CustomCluster, Identify):
    """KOF Identify Cluster."""

    void_input_commands = {
        Identify.commands_by_name["identify"].id,
        Identify.commands_by_name["trigger_effect"].id,
    }


class KofGroups(NoReplyMixin, CustomCluster, Groups):
    """KOF Group Cluster."""

    # Remove All Groups, Add Group If Identifying
    void_input_commands = {
        Groups.commands_by_name["remove_all"].id,
        Groups.commands_by_name["add_if_identifying"].id,
    }


class KofScenes(NoReplyMixin, CustomCluster, Scenes):
    """KOF Scene Cluster."""

    void_input_commands = {Scenes.commands_by_name["recall"].id}


class KofOnOff(NoReplyMixin, CustomCluster, OnOff):
    """KOF On Off Cluster."""

    void_input_commands = {cmd.id for cmd in OnOff.commands_by_name.values()}


class KofLevelControl(NoReplyMixin, CustomCluster, LevelControl):
    """KOF Level Control Cluster."""

    void_input_commands = {cmd.id for cmd in LevelControl.commands_by_name.values()}


(
    # The manufacturer has two spaces in its name
    QuirkBuilder("King Of Fans,  Inc.", "MR101Z")
    # TODO: add support for wildcard matching in `applies_to`
    .applies_to("King Of Fans,  Inc.", "HDC52EastwindFan")
    .applies_to("King Of Fans,  Inc.", "HBUniversalCFRemote")
    .replaces_endpoint(
        endpoint_id=1, device_type=zha.DeviceType.DIMMABLE_LIGHT
    )  # was 257
    .replaces(KofBasic)
    .replaces(KofIdentify)
    .replaces(KofGroups)
    .replaces(KofScenes)
    .replaces(KofOnOff)
    .replaces(KofLevelControl)
    .add_to_registry()
)
