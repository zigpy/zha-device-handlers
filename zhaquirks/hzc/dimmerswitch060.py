"""Quirk for Repenic Ltd. dimmer (e.g. HZC Smart Dimmer D060-ZG)."""
import re
from zigpy import types as t
from zigpy.zcl import foundation
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl



class OutEdge(t.enum8):
    TrailingEdge = 0
    LeadingEdge = 1
class HzcLevelControl(CustomCluster, LevelControl):
    name = "HzcLevelControl"
    manufacturer_id_override = None
    attributes = LevelControl.attributes.copy()
    attributes.update(
        {
            0xA004: ("boost", t.uint8_t, False),
            0xB000: ("out_edge", OutEdge, False)
        }
    )


class ModeType(list, metaclass=t.KwargTypeMeta):
    _item_type = t.uint8_t
    _length = 6

    _getitem_kwargs = {"item_type": None, "length": None}

    def getStr(self):
        arr = list(self)
        chunks = []
        current_chunk = []
        current_type = None  #'digit' 或 'space'
        for c in arr:
            if c == ' ':
                if current_type == 'space':
                    current_chunk.append(c)
                else:
                    if current_chunk:
                        chunks.append(''.join(current_chunk))
                        current_chunk = []
                    current_type = 'space'
                    current_chunk.append(c)
            else:
                if current_type == 'digit':
                    current_chunk.append(c)
                else:
                    if current_chunk:
                        chunks.append(''.join(current_chunk))
                        current_chunk = []
                    current_type = 'digit'
                    current_chunk.append(c)

        #
        if current_chunk:
            chunks.append(''.join(current_chunk))

        result = ''.join(chunks)
        return result
    """General data"""
    def serialize(self) -> bytes:
        assert self._length is not None
        res = self.getStr()
        res = re.split("\s+", res)
        if len(res) != 6:
            raise ValueError(
                f"Invalid length for {res}: expected {6}, got {len(res)}"
            )
        # 1 17 45 255 00 00
        res = b"".join([self._item_type(i).serialize() for i in res])
        return res



class WorkModeCluster(CustomCluster):
    cluster_id = 0xE003
    name = "WorkModeCluster"
    attributes = {
        0x0000: ("sleep_mode", t.CharacterString, False),
        0x0001: ("wakeup_mode", t.CharacterString, False),
        0x0002: ("night_mode", t.CharacterString, False),
    }

    server_commands = {
        0x0000: foundation.ZCLCommandDef(
            "SetSleepMode",
            {
                "sleep_mode": ModeType,
            },
            False,
        ),
        0x0001: foundation.ZCLCommandDef(
            "SetWakeUpMode",
            {
                "wakeup_mode": ModeType,
            },
            False,
        ),
        0x0002: foundation.ZCLCommandDef(
            "SetNightMode",
            {
                "night_mode": ModeType,
            },
            False,
        ),
    }

class WorkProgramCluster(CustomCluster):
    cluster_id = 0xE002
    name = "WorkProgramCluster"
    attributes = {
        0x0000: ("week1", t.CharacterString, False),
        0x0001: ("week2", t.CharacterString, False),
        0x0002: ("week3", t.CharacterString, False),
        0x0003: ("week4", t.CharacterString, False),
        0x0004: ("week5", t.CharacterString, False),
        0x0005: ("week6", t.CharacterString, False),
        0x0006: ("week7", t.CharacterString, False),
    }

    server_commands = {
        # 01
        0x0000: foundation.ZCLCommandDef(
            "SetWeek1",
            {
                "week1": ModeType,
            },
            False,
        ),
        0x0001: foundation.ZCLCommandDef(
            "SetWeek2",
            {
                "week2": ModeType,
            },
            False,
        ),
        0x0002: foundation.ZCLCommandDef(
            "SetWeek3",
            {
                "week3": ModeType,
            },
            False,
        ),
        0x0003: foundation.ZCLCommandDef(
            "SetWeek4",
            {
                "week4": ModeType,
            },
            False,
        ),
        0x0004: foundation.ZCLCommandDef(
            "SetWeek5",
            {
                "week5": ModeType,
            },
            False,
        ),
        0x0005: foundation.ZCLCommandDef(
            "SetWeek6",
            {
                "week6": ModeType,
            },
            False,
        ),
        0x0006: foundation.ZCLCommandDef(
            "SetWeek7",
            {
                "week7": ModeType,
            },
            False,
        ),
    }


(
    QuirkBuilder("Repenic Ltd.", "Dimmer Switch-PDZG")
    .replace_cluster_occurrences(HzcLevelControl, replace_client_instances=False)
    .adds(WorkModeCluster)
    .adds(WorkProgramCluster)
    .add_to_registry()
)
