"""Module to handle quirks of the King of Fans MR101Z ceiling fan receiver.

The King of Fans ceiling fan receiver does not generate default replies. This
module overrides all server commands that do not have a mandatory reply to not
expect replies at all.
"""

from __future__ import annotations

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.hvac import Fan

from zhaquirks import NoReplyMixin
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MANUFACTURER,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


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


class CeilingFan(CustomDevice):
    """Ceiling Fan Device."""

    signature = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 14,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Fan.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
        MANUFACTURER: "King Of Fans,  Inc.",
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    KofBasic,
                    KofIdentify,
                    KofGroups,
                    KofScenes,
                    KofOnOff,
                    KofLevelControl,
                    Fan,
                ],
                OUTPUT_CLUSTERS: [Identify, Ota],
            }
        }
    }
