"""Tuya MCU comunications."""
from typing import Dict, Optional, Union

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff

from zhaquirks import Bus
from zhaquirks.tuya import (
    ATTR_ON_OFF,
    TUYA_MCU_COMMAND,
    TUYA_SET_DATA,
    Data,
    DPToAttributeMapping,
    TuyaCommand,
    TuyaData,
    TuyaDPType,
    TuyaLocalCluster,
    TuyaNewManufCluster,
)


class TuyaMCUCluster(TuyaNewManufCluster):
    """Manufacturer specific cluster for sending Tuya MCU commands."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.command_bus = Bus()
        self.endpoint.device.command_bus.add_listener(
            self
        )  # Cluster for endpoint: 1 (listen MCU commands)

    def tuya_mcu_command(
        self, command: TuyaCommand, endpoint_id: int, attribute_name: str
    ):
        """Tuya MCU command listener. Only endpoint:1 must listen to MCU commands."""

        self.debug("tuya_mcu_command: %s", command)
        cluster_dp = self.get_dp_from_cluster(endpoint_id, attribute_name)
        if cluster_dp:
            command.dp = cluster_dp

            self.create_catching_task(
                self.command(TUYA_SET_DATA, command, expect_reply=True)
            )

    def get_dp_from_cluster(
        self, endpoint_id: int, attribute_name: str
    ) -> Optional[int]:
        """Search for the DP in dp_to_attribute."""

        for dp, dp_mapping in self.dp_to_attribute.items():
            if (attribute_name == dp_mapping.attribute_name) and (
                endpoint_id in [dp_mapping.endpoint_id, self.endpoint.endpoint_id]
            ):
                self.debug("get_dp_from_cluster --> found DP: %s", dp)
                return dp
        return None


class TuyaAttributesCluster(TuyaMCUCluster, TuyaLocalCluster):
    """Manufacturer specific cluster for Tuya converting attributes <-> commands."""

    def read_attributes(
        self, attributes, allow_cache=False, only_cache=False, manufacturer=None
    ):
        """Ignore remote reads as the "get_data" command doesn't seem to do anything."""

        self.debug("read_attributes --> attrs: %s", attributes)
        return super().read_attributes(
            attributes, allow_cache=True, only_cache=True, manufacturer=manufacturer
        )

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer attributes writing to the set_data tuya command."""

        records = self._write_attr_records(attributes)

        for record in records:

            self.debug("write_attributes --> record: %s", record)

            cmd_payload = TuyaCommand()
            cmd_payload.status = 0
            cmd_payload.tsn = self.endpoint.device.application.get_sequence()
            cmd_payload.data = TuyaData()
            # TODO: get TuyaDPType from record.value.type
            cmd_payload.data.dp_type = TuyaDPType.ENUM
            cmd_payload.data.function = 0
            cmd_payload.data.raw = t.LVBytes.deserialize([1, record.value.value])[0]

            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cmd_payload,
                self.endpoint.endpoint_id,
                self.attributes[record.attrid][0],
            )

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


class TuyaOnOff(OnOff, TuyaLocalCluster):
    """Tuya MCU OnOff cluster."""

    attributes = {
        ATTR_ON_OFF: ("on_off", t.Bool),
    }

    async def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default Cluster command."""

        self.debug(
            "Sending Tuya Cluster Command... Cluster Command is %x, Arguments are %s",
            command_id,
            args,
        )

        # (off, on)
        if command_id in (0x0000, 0x0001):
            cmd_payload = TuyaCommand()
            cmd_payload.status = 0
            # cmd_payload.tsn = tsn if tsn else self.endpoint.device.application.get_sequence()
            cmd_payload.tsn = 0
            cmd_payload.data = TuyaData()
            cmd_payload.data.dp_type = TuyaDPType.BOOL
            cmd_payload.data.function = 0
            cmd_payload.data.raw = t.LVBytes.deserialize([1, command_id])[0]

            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cmd_payload,
                self.endpoint.endpoint_id,
                "on_off",
            )
            return foundation.Status.SUCCESS

        self.warning("ERROR: unsupported command_id: %s", command_id)
        return foundation.Status.UNSUP_CLUSTER_COMMAND


class TuyaOnOffManufCluster(TuyaMCUCluster):
    """Tuya with On/Off data points."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
        ),
        2: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=2,
        ),
        3: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=3,
        ),
        4: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=4,
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        3: "_dp_2_attr_update",
        4: "_dp_2_attr_update",
    }


class TuyaLevelControl(LevelControl, TuyaLocalCluster):
    """Tuya MCU Level cluster for dimmable device."""

    attributes = {0x0000: ("current_level", t.uint8_t)}

    async def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default Cluster command."""
        self.debug(
            "Sending Tuya Cluster Command.. Cluster Command is %x, Arguments are %s",
            command_id,
            args,
        )
        # (move_to_level, move, move_to_level_with_on_off)
        if command_id in (0x0000, 0x0001, 0x0004):
            cmd_payload = TuyaCommand()
            cmd_payload.status = 0
            # cmd_payload.tsn = tsn if tsn else self.endpoint.device.application.get_sequence()
            cmd_payload.tsn = 0
            cmd_payload.data = TuyaData()
            cmd_payload.data.dp_type = TuyaDPType.ENUM
            cmd_payload.data.function = 0

            brightness = (args[0] * 1000) // 255
            val = Data.from_value(t.uint32_t(brightness))
            cmd_payload.data.raw = t.LVBytes.deserialize(val)[0]

            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cmd_payload,
                self.endpoint.endpoint_id,
                "current_level",
            )
            return foundation.Status.SUCCESS

        self.warning("ERROR: unsupported command_id: %s", command_id)
        return foundation.Status.UNSUP_CLUSTER_COMMAND


class TuyaLevelControlManufCluster(TuyaMCUCluster):
    """Tuya with Level Control data points."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
        ),
        2: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "current_level",
        ),
        7: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=2,
        ),
        8: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "current_level",
            endpoint_id=2,
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        7: "_dp_2_attr_update",
        8: "_dp_2_attr_update",
    }
