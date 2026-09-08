"""Candeo rotary dimmer switches."""

from typing import Final

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import Identify, LevelControl, OnOff, Ota
from zigpy.zcl.foundation import (
    BaseCommandDefs,
    DataTypeId,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.builder import QuirkBuilder
from zhaquirks.candeo import CANDEO
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_CONTINUED_ROTATING,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_PRESS,
    COMMAND_RELEASE,
    COMMAND_STARTED_ROTATING,
    COMMAND_STOPPED_ROTATING,
    CONTINUED_ROTATING,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LEFT,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    RIGHT,
    ROTARY_KNOB,
    SHORT_PRESS,
    STARTED_ROTATING,
    STOPPED_ROTATING,
)


class CandeoRemoteDirection(t.enum8):
    """Candeo Remote Direction."""

    Right = 0x00
    Left = 0x01


class CandeoRemoteLiteEP2Functionality(t.enum8):
    """Candeo remote lite EP2 functionality enum."""

    disabled = False
    enabled = True


class CandeoOnOffRemoteCluster(OnOff, CustomCluster):
    """Candeo OnOff Remote Cluster."""

    class ServerCommandDefs(BaseCommandDefs):
        """overwrite ServerCommandDefs."""

        double: Final = ZCLCommandDef(
            id=0x00,
            schema={},
        )
        press: Final = ZCLCommandDef(
            id=0x01,
            schema={},
        )
        hold: Final = ZCLCommandDef(
            id=0x02,
            schema={},
        )
        release: Final = ZCLCommandDef(
            id=0x03,
            schema={},
        )


class CandeoLevelControlRemoteCluster(LevelControl, CustomCluster):
    """Candeo LevelControl Remote Cluster."""

    class ServerCommandDefs(BaseCommandDefs):
        """overwrite ServerCommandDefs."""

        started_rotating: Final = ZCLCommandDef(
            id=0x05,
            schema={"direction": CandeoRemoteDirection},
        )
        continued_rotating: Final = ZCLCommandDef(
            id=0x06,
            schema={"direction": CandeoRemoteDirection},
        )
        stopped_rotating: Final = ZCLCommandDef(
            id=0x03,
            schema={},
        )


class CandeoOnOffRemoteLiteEP2FunctionalityCluster(OnOff, CustomCluster):
    """Candeo OnOff Remote Lite EP2 Functionality Cluster."""

    class AttributeDefs(OnOff.AttributeDefs):
        """Attribute Definitions."""

        rem_lite_ep2_functionality = ZCLAttributeDef(
            id=0x8000,
            type=CandeoRemoteLiteEP2Functionality,
            zcl_type=DataTypeId.bool_,
            access="rw",
        )

    _VALID_ATTRIBUTES = {
        AttributeDefs.rem_lite_ep2_functionality.id,
    }


class CandeoOnOffRemoteLiteCluster(OnOff, CustomCluster):
    """Candeo OnOff Remote Lite Cluster."""

    class ServerCommandDefs(BaseCommandDefs):
        """overwrite ServerCommandDefs."""

        double: Final = ZCLCommandDef(
            id=0x00,
            schema={},
        )
        hold: Final = ZCLCommandDef(
            id=0x02,
            schema={},
        )
        release: Final = ZCLCommandDef(
            id=0x03,
            schema={},
        )


remote_lite_quirk = (
    QuirkBuilder()
    .replaces(
        CandeoOnOffRemoteLiteEP2FunctionalityCluster,
        endpoint_id=1,
    )
    .replaces(
        CandeoOnOffRemoteLiteCluster,
        endpoint_id=2,
        cluster_type=ClusterType.Client,
    )
    .removes(
        OnOff.cluster_id,
        endpoint_id=3,
    )
    .enum(
        attribute_name=CandeoOnOffRemoteLiteEP2FunctionalityCluster.AttributeDefs.rem_lite_ep2_functionality.name,
        cluster_id=CandeoOnOffRemoteLiteEP2FunctionalityCluster.cluster_id,
        endpoint_id=1,
        translation_key="rem_lite_ep2_functionality",
        fallback_name="Extra button commands",
        enum_class=CandeoRemoteLiteEP2Functionality,
    )
    .device_automation_triggers(
        {
            (DOUBLE_PRESS, ROTARY_KNOB): {
                COMMAND: COMMAND_DOUBLE,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            (LONG_PRESS, ROTARY_KNOB): {
                COMMAND: COMMAND_HOLD,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            (LONG_RELEASE, ROTARY_KNOB): {
                COMMAND: COMMAND_RELEASE,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
        }
    )
)

remote_quirk = (
    QuirkBuilder()
    .replaces(
        CandeoOnOffRemoteCluster,
        endpoint_id=2,
        cluster_type=ClusterType.Client,
    )
    .replaces(
        CandeoLevelControlRemoteCluster,
        endpoint_id=2,
        cluster_type=ClusterType.Client,
    )
    .device_automation_triggers(
        {
            (SHORT_PRESS, ROTARY_KNOB): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            (DOUBLE_PRESS, ROTARY_KNOB): {
                COMMAND: COMMAND_DOUBLE,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            (LONG_PRESS, ROTARY_KNOB): {
                COMMAND: COMMAND_HOLD,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            (LONG_RELEASE, ROTARY_KNOB): {
                COMMAND: COMMAND_RELEASE,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 2,
            },
            (STARTED_ROTATING, LEFT): {
                COMMAND: COMMAND_STARTED_ROTATING,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"direction": 1},
            },
            (CONTINUED_ROTATING, LEFT): {
                COMMAND: COMMAND_CONTINUED_ROTATING,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"direction": 1},
            },
            (STARTED_ROTATING, RIGHT): {
                COMMAND: COMMAND_STARTED_ROTATING,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"direction": 0},
            },
            (CONTINUED_ROTATING, RIGHT): {
                COMMAND: COMMAND_CONTINUED_ROTATING,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
                PARAMS: {"direction": 0},
            },
            (STOPPED_ROTATING, ROTARY_KNOB): {
                COMMAND: COMMAND_STOPPED_ROTATING,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 2,
            },
        }
    )
)

(
    QuirkBuilder(CANDEO, "C-ZB-RD1")
    .applies_to(CANDEO, "C-ZB-RD1P-DIM")
    .removes(Ota.cluster_id)
    .add_to_registry()
)

(
    remote_lite_quirk.clone()
    .applies_to(CANDEO, "C-ZB-RD1Pv2-DIM")
    .removes(Ota.cluster_id)
    .add_to_registry()
)

(
    remote_quirk.clone()
    .applies_to(CANDEO, "C-ZB-RD1P-REM")
    .applies_to(CANDEO, "C-ZB-RD1Pv2-REM")
    .removes(Identify.cluster_id, endpoint_id=1)
    .removes(Identify.cluster_id, endpoint_id=2)
    .removes(Ota.cluster_id)
    .add_to_registry()
)

(
    remote_quirk.clone()
    .applies_to(CANDEO, "C-ZB-RD1P-DPM")
    .applies_to(CANDEO, "C-ZB-RD1Pv2-DPM")
    .removes(Ota.cluster_id)
    .add_to_registry()
)
