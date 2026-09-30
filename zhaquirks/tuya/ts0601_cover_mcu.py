"""Tuya MCU based cover and blinds."""

from __future__ import annotations

from typing import Any

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic, GreenPowerProxy, Groups, Ota, Scenes, Time

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TUYA_MCU_COMMAND, TuyaLocalCluster, TuyaWindowCover
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaClusterData, TuyaMCUCluster


class TuyaCoverCommand(t.enum8):
    """Tuya cover commands."""

    OPEN = 0x00
    STOP = 0x01
    CLOSE = 0x02


class ZclCoverCommand(t.enum8):
    """ZCL cover commands."""

    OPEN = 0x00
    CLOSE = 0x01
    STOP = 0x02


TUYA_TO_ZCL_COVER_COMMAND = {
    ZclCoverCommand.OPEN: TuyaCoverCommand.OPEN,
    ZclCoverCommand.CLOSE: TuyaCoverCommand.CLOSE,
    ZclCoverCommand.STOP: TuyaCoverCommand.STOP,
}


class TuyaMCUWindowCovering(WindowCovering, TuyaLocalCluster):
    """Tuya MCU WindowCovering cluster."""

    attributes = WindowCovering.attributes.copy()
    attributes.update(
        {
            # 0: open, 1: stop, 2: close
            0xF000: ("curtain_switch", t.enum8, True),
            # 0: calibration started, 1: calibration finished
            0xF001: ("accurate_calibration", t.enum8, True),
            # 0: default, 1: reverse
            0xF002: ("motor_steering", t.enum8, True),
            # 30 to 9000 (units of 0.1 seconds)
            0xF003: ("travel", t.uint16_t, True),
        }
    )

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ):
        """Override the default Cluster command."""

        self.debug(
            "Sending Tuya Cluster Command. Cluster Command is %x, Arguments are %s",
            command_id,
            args,
        )

        # up_open, down_close, stop
        if command_id in (0x0000, 0x0001, 0x0002):
            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_name=self.ep_attribute,
                cluster_attr="curtain_switch",
                attr_value=TUYA_TO_ZCL_COVER_COMMAND[command_id],
                expect_reply=expect_reply,
                manufacturer=None,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

        # go_to_lift_percentage
        if command_id == 0x0005:
            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_name=self.ep_attribute,
                cluster_attr="current_position_lift_percentage",
                attr_value=args[0],
                expect_reply=expect_reply,
                manufacturer=None,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

        self.warning("Unsupported command_id: %s", command_id)
        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND)


class TuyaMCUWindowCoverManufCluster(TuyaMCUCluster):
    """Tuya MCU cluster with WindowCover data points."""

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaMCUWindowCovering.ep_attribute,
            "curtain_switch",
        ),
        2: DPToAttributeMapping(
            TuyaMCUWindowCovering.ep_attribute,
            "current_position_lift_percentage",
        ),
        3: DPToAttributeMapping(
            TuyaMCUWindowCovering.ep_attribute,
            "current_position_lift_percentage",
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        3: "_dp_2_attr_update",
    }


class TuyaMCUCover0601(TuyaWindowCover):
    """Tuya MCU blind controller with GreenPowerProxy."""

    signature = {
        MODELS_INFO: [
            ("_TZE200_rmymn92d", "TS0601"),
            ("_TZE200_r0jdjrvi", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaMCUWindowCoverManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaMCUWindowCoverManufCluster,
                    TuyaMCUWindowCovering,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
