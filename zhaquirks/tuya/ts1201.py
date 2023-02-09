"""Tuya TS1201 IR blaster."""

import logging
import base64
from typing import Any, List, Optional, Union, Tuple

from zigpy.profiles import zha
from zigpy.profiles.zha import DeviceType
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PowerConfiguration,
    Time,
    Groups,
    Scenes,
    OnOff,
)

from zigpy.zdo.types import NodeDescriptor

from zhaquirks.const import (
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_PRESS,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    ON,
    OUTPUT_CLUSTERS,
    PARAMS,
    PROFILE_ID,
    SHORT_PRESS,
    TURN_ON,
)


class Bytes(bytes):
    """Bytes serializable class."""

    def serialize(self):
        """Serialize Bytes."""
        return self

    @classmethod
    def deserialize(cls, data):
        """Deserialize Bytes."""
        return cls(data), b""


class ZosungIRControl(CustomCluster):
    """Zosung IR Control Cluster (0xE004)."""

    name = "Zosung IR Control Cluster"
    cluster_id = 0xE004
    ep_attribute = "zosung_ircontrol"

    attributes = {}

    server_commands = {
        0x00: foundation.ZCLCommandDef(
            "data",
            schema={"data": Bytes},
            is_reply=False,
            is_manufacturer_specific=True,
        ),
        0x01: foundation.ZCLCommandDef(
            "IRLearn",
            schema={"on_off": t.Bool},
            is_reply=False,
            is_manufacturer_specific=True,
        ),
        0x02: foundation.ZCLCommandDef(
            "IRSend",
            schema={"code": t.CharacterString},
            is_reply=False,
            is_manufacturer_specific=True,
        ),
    }

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle a cluster request."""
        self.debug(
            "%s: handle_cluster_request - Command: %s Data: %s Data.type: %s",
            self.name,
            hdr.command_id,
            args,
            type(args),
        )
        #        self.debug("self.endpoint.in_clusters: %s", self.endpoint.in_clusters)
        self.debug("self.command: %s", self.command)
        for d in args:
            self.debug("d: %s", d)

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
        **kwargs: Any,
    ):
        """Override the default Cluster command."""
        self.debug("Receive command with args: %s and kwargs %s", args, kwargs)
        if command_id == 1:
            if kwargs["on_off"]:
                new_args = {Bytes(b'{"study":0}')}
            else:
                new_args = {Bytes(b'{"study":1}')}
            return await super().command(
                0x00,
                *new_args,
                manufacturer=manufacturer,
                expect_reply=False,
                tsn=tsn,
            )
        elif command_id == 2:
            irMsg = f'{{"key_num":1,"delay":300,"key1":{{"num":1,"freq":38000,"type":1,"key_code":"{kwargs["code"]}"}}}}'
            self.debug("irMsg to send: %s", irMsg)
            seq = self.endpoint.device.nextSeq()
            self.endpoint.device.ir_msg_to_send = {seq: irMsg}
            self.create_catching_task(
                self.endpoint.zosung_irtransmit.command(
                    0x00,
                    seq=seq,
                    length=len(irMsg),
                    unk1=0x00000000,
                    clusterid=0xE004,
                    unk2=0x01,
                    cmd=0x02,
                    unk3=0x0000,
                    expect_reply=False,
                    tsn=tsn,
                )
            )
        else:
            return await super().command(
                command_id,
                *args,
                manufacturer=manufacturer,
                expect_reply=expect_reply,
                tsn=tsn,
            )


class ZosungIRTransmit(CustomCluster):
    """Zosung IR Transmit Cluster (0xED00)."""

    name = "Zosung IR Control Cluster"
    cluster_id = 0xED00
    ep_attribute = "zosung_irtransmit"

    current_position = 0
    msg_length = 0
    ir_msg = []

    attributes = {}
    client_commands = {
        0x03: foundation.ZCLCommandDef(
            "resp_ir_frame_03",
            schema={
                "zero": t.uint8_t,
                "seq": t.uint16_t,
                "position": t.uint32_t,
                "msgpart": t.LVBytes,
                "msgpartcrc": t.uint8_t,
            },
            is_reply=True,
            is_manufacturer_specific=False,
        ),
        0x05: foundation.ZCLCommandDef(
            "resp_ir_frame_05",
            schema={
                "seq": t.uint16_t,
                "zero": t.uint16_t,
            },
            is_reply=False,
            is_manufacturer_specific=True,
        ),
    }
    server_commands = {
        0x00: foundation.ZCLCommandDef(
            "receive_ir_frame_00",
            schema={
                "seq": t.uint16_t,
                "length": t.uint32_t,
                "unk1": t.uint32_t,
                "clusterid": t.uint16_t,
                "unk2": t.uint8_t,
                "cmd": t.uint8_t,
                "unk3": t.uint16_t,
            },
            is_reply=False,
            is_manufacturer_specific=True,
        ),
        0x01: foundation.ZCLCommandDef(
            "receive_ir_frame_01",
            schema={
                "zero": t.uint8_t,
                "seq": t.uint16_t,
                "length": t.uint32_t,
                "unk1": t.uint32_t,
                "clusterid": t.uint16_t,
                "unk2": t.uint8_t,
                "cmd": t.uint8_t,
                "unk3": t.uint16_t,
            },
            is_reply=False,
            is_manufacturer_specific=True,
        ),
        0x02: foundation.ZCLCommandDef(
            "receive_ir_frame_02",
            schema={
                "seq": t.uint16_t,
                "position": t.uint32_t,
                "maxlen": t.uint8_t,
            },
            is_reply=False,
            is_manufacturer_specific=True,
        ),
        0x03: foundation.ZCLCommandDef(
            "receive_ir_frame_03",
            schema={
                "zero": t.uint8_t,
                "seq": t.uint16_t,
                "position": t.uint32_t,
                "msgpart": t.LVBytes,
                "msgpartcrc": t.uint8_t,
            },
            is_reply=True,
            is_manufacturer_specific=False,
        ),
        0x04: foundation.ZCLCommandDef(
            "receive_ir_frame_04",
            schema={
                "zero0": t.uint8_t,
                "seq": t.uint16_t,
                "zero1": t.uint16_t,
            },
            is_reply=False,
            is_manufacturer_specific=True,
        ),
        0x05: foundation.ZCLCommandDef(
            "receive_ir_frame_05",
            schema={
                "seq": t.uint16_t,
                "zero": t.uint16_t,
            },
            is_reply=False,
            is_manufacturer_specific=True,
        ),
    }

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle a cluster request."""
        self.debug(
            "%s: handle_cluster_request - Command: %s Data: %s Data.type: %s",
            self.name,
            hdr.command_id,
            args,
            type(args),
        )

        for d in args:
            self.debug("d: %s", d)
        if hdr.command_id == 0x00:
            self.debug("hdr.command_id == 0x00")

            self.current_position = 0
            self.ir_msg.clear()
            self.msg_length = args.length

            new_args_01 = {
                "zero": 0,
                "seq": args.seq,
                "length": args.length,
                "unk1": args.unk1,
                "clusterid": args.clusterid,
                "unk2": args.unk2,
                "cmd": args.cmd,
                "unk3": args.unk3,
            }
            self.create_catching_task(
                super().command(0x01, **new_args_01, expect_reply=False)
            )

            new_args_02 = {"seq": args.seq, "position": 0, "maxlen": 0x38}
            self.create_catching_task(
                super().command(0x02, **new_args_02, expect_reply=False)
            )
        elif hdr.command_id == 0x01:
            self.debug("IR-Message-Code01 received, sequence: %s", args.seq)
            self.debug("msg to send: %s", self.endpoint.device.ir_msg_to_send[args.seq])
        elif hdr.command_id == 0x02:
            position = args.position
            seq = args.seq
            maxlen = args.maxlen
            irmsg = self.endpoint.device.ir_msg_to_send[seq]
#            msgpart = irmsg[position : position + 0x32]
            msgpart = irmsg[position : position + maxlen]
            calculated_crc = 0
            for x in msgpart:
                calculated_crc = (calculated_crc + ord(x)) % 0x100
            self.debug(
                "hdr.command_id == 0x02 ; msgcrc=%s ; position=%s ; msgpart=%s",
                calculated_crc,
                position,
                msgpart,
            )
            new_args_03 = {
                "zero": 0,
                "seq": seq,
                "position": position,
                "msgpart": msgpart.encode("utf-8"),
                "msgpartcrc": calculated_crc,
            }
            self.create_catching_task(
                super().command(0x03, **new_args_03, expect_reply=False)
            )
        elif hdr.command_id == 0x03:
            msg_part_crc = args.msgpartcrc
            calculated_crc = 0
            for x in args.msgpart:
                calculated_crc = (calculated_crc + x) % 0x100
            self.debug(
                "hdr.command_id == 0x03 ; msgcrc=%s ; calculated_crc=%s ; position=%s",
                msg_part_crc,
                calculated_crc,
                args.position,
            )
            self.ir_msg[args.position :] = args.msgpart
            if args.position + len(args.msgpart) < self.msg_length:
                new_args_02 = {
                    "seq": args.seq,
                    "position": args.position + len(args.msgpart),
                    "maxlen": 0x38,
                }
                self.create_catching_task(
                    super().command(0x02, **new_args_02, expect_reply=False)
                )
            else:
                self.debug("Ir message totally received.")
                new_args_04 = {"zero0": 0, "seq": args.seq, "zero1": 0}
                self.create_catching_task(
                    super().command(0x04, **new_args_04, expect_reply=False)
                )
        elif hdr.command_id == 0x04:
            seq = args.seq
            self.debug("Command 0x04: IRCode has been successfuly sent. (seq:%s)", seq)
            new_args_05 = {"seq": seq, "zero": 0}
            self.create_catching_task(
                super().command(0x05, **new_args_05, expect_reply=False)
            )
        elif hdr.command_id == 0x05:
            self.info(
                "Command 0x05: Ir message really totally received: %s",
                base64.b64encode(bytes(self.ir_msg)),
            )
            self.debug("Stopping learning mode on device.")
            self.create_catching_task(
                self.endpoint.zosung_ircontrol.command(
                    0x01, on_off=False, expect_reply=False
                )
            )
        else:
            self.debug("hdr.command_id: %s", hdr.command_id)


class ZosungIRBlaster(CustomDevice):
    """Zosung IR Blaster."""

    seq = -1
    ir_msg_to_send = {}

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.seq = 0
        super().__init__(*args, **kwargs)

    def nextSeq(self):
        self.seq = (self.seq + 1) % 0x10000
        return self.seq

    signature = {
        # "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        # input_clusters=[0x0000, 0x0001, 0x0003, 0x0004, 0x0005, 0x0006,
        #                 0xe004, 0xed00]
        # output_clusters=[0x000a, 0x0019]
        #  <SimpleDescriptor endpoint=1, profile=260, device_type=61440
        #  device_version=1
        #  input_clusters=[0, 1, 3, 4, 5, 6, 57348, 60672]
        #  output_clusters=[10, 25]>
        MODELS_INFO: [
            ("_TZ3290_ot6ewjvmejq5ekhl", "TS1201"),
            ("_TZ3290_7v1k4vufotpowp9z", "TS1201"),
            ("_TZ3290_acv1iuslxi3shaaj", "TS1201"),
            ("_TZ3290_j37rooaxrcdcqo5n", "TS1201"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0xF000,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    ZosungIRTransmit.cluster_id,
                    ZosungIRControl.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    PowerConfiguration.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    ZosungIRTransmit,
                    ZosungIRControl,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    PowerConfiguration.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = {
        (BUTTON, ON): {
            COMMAND: 0,
            CLUSTER_ID: 0xE004,
            ENDPOINT_ID: 1,
            PARAMS: {
                "data": b'{"study":0}',
            },
        },
    }
