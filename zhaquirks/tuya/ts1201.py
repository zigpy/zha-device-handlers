"""Tuya TS1201 IR blaster.

Heavily inspired by work from @mak-42
https://github.com/Koenkk/zigbee-herdsman-converters/blob/9d5e7b902479582581615cbfac3148d66d4c675c/lib/zosung.js
"""

import base64
import logging
from typing import Any, Final, Optional, Union

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import BaseAttributeDefs, BaseCommandDefs, foundation
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

_LOGGER = logging.getLogger(__name__)


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

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        last_learned_ir_code: Final = foundation.ZCLAttributeDef(
            id=0x0000, type=t.CharacterString, access="r", mandatory=True
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        data: Final = foundation.ZCLCommandDef(
            id=0x00,
            schema={"data": Bytes},
            direction=foundation.Direction.Server_to_Client,
            is_manufacturer_specific=True,
        )
        IRLearn: Final = foundation.ZCLCommandDef(
            id=0x01,
            schema={"on_off": t.Bool},
            direction=foundation.Direction.Server_to_Client,
            is_manufacturer_specific=True,
        )
        IRSend: Final = foundation.ZCLCommandDef(
            id=0x02,
            schema={"code": t.CharacterString},
            direction=foundation.Direction.Server_to_Client,
            is_manufacturer_specific=True,
        )

    async def read_attributes(
        self, attributes, allow_cache=False, only_cache=False, manufacturer=None
    ):
        """Read attributes ZCL foundation command."""
        if (
            self.AttributeDefs.last_learned_ir_code.id in attributes
            or "last_learned_ir_code" in attributes
        ):
            return {0: self.endpoint.device.last_learned_ir_code}, {}
        else:
            return {}, {0: foundation.Status.UNSUPPORTED_ATTRIBUTE}

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
        **kwargs: Any,
    ):
        """Override the default cluster command."""
        if command_id == self.ServerCommandDefs.IRLearn.id:
            if kwargs["on_off"]:
                cmd_args = {Bytes(b'{"study":0}')}
            else:
                cmd_args = {Bytes(b'{"study":1}')}
            return await super().command(
                0x00,
                *cmd_args,
                manufacturer=manufacturer,
                expect_reply=True,
                tsn=tsn,
            )
        elif command_id == self.ServerCommandDefs.IRSend.id:
            ir_msg = (
                f'{{"key_num":1,"delay":300,"key1":'
                f'{{"num":1,"freq":38000,"type":1,"key_code":"{kwargs["code"]}"}}}}'
            )
            _LOGGER.debug(
                "Sending IR code: %s to %s", ir_msg, self.endpoint.device.ieee
            )
            seq = self.endpoint.device.next_seq()
            self.endpoint.device.ir_msg_to_send = {seq: ir_msg}
            self.create_catching_task(
                self.endpoint.zosung_irtransmit.command(
                    0x00,
                    seq=seq,
                    length=len(ir_msg),
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

    name = "Zosung IR Transmit Cluster"
    cluster_id = 0xED00
    ep_attribute = "zosung_irtransmit"

    current_position = 0
    msg_length = 0
    ir_msg = []

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        receive_ir_frame_00: Final = foundation.ZCLCommandDef(
            id=0x00,
            schema={
                "seq": t.uint16_t,
                "length": t.uint32_t,
                "unk1": t.uint32_t,
                "clusterid": t.uint16_t,
                "unk2": t.uint8_t,
                "cmd": t.uint8_t,
                "unk3": t.uint16_t,
            },
            direction=foundation.Direction.Server_to_Client,
            is_manufacturer_specific=True,
        )
        receive_ir_frame_01: Final = foundation.ZCLCommandDef(
            id=0x01,
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
            direction=foundation.Direction.Server_to_Client,
            is_manufacturer_specific=True,
        )
        receive_ir_frame_02: Final = foundation.ZCLCommandDef(
            id=0x02,
            schema={
                "seq": t.uint16_t,
                "position": t.uint32_t,
                "maxlen": t.uint8_t,
            },
            direction=foundation.Direction.Server_to_Client,
            is_manufacturer_specific=True,
        )
        receive_ir_frame_03: Final = foundation.ZCLCommandDef(
            id=0x03,
            schema={
                "zero": t.uint8_t,
                "seq": t.uint16_t,
                "position": t.uint32_t,
                "msgpart": t.LVBytes,
                "msgpartcrc": t.uint8_t,
            },
            direction=foundation.Direction.Client_to_Server,
            is_manufacturer_specific=False,
        )
        receive_ir_frame_04: Final = foundation.ZCLCommandDef(
            id=0x04,
            schema={
                "zero0": t.uint8_t,
                "seq": t.uint16_t,
                "zero1": t.uint16_t,
            },
            direction=foundation.Direction.Server_to_Client,
            is_manufacturer_specific=True,
        )
        receive_ir_frame_05: Final = foundation.ZCLCommandDef(
            id=0x05,
            schema={
                "seq": t.uint16_t,
                "zero": t.uint16_t,
            },
            direction=foundation.Direction.Server_to_Client,
            is_manufacturer_specific=True,
        )

    class ClientCommandDefs(BaseCommandDefs):
        """Client command definitions."""

        resp_ir_frame_03: Final = foundation.ZCLCommandDef(
            id=0x03,
            schema={
                "zero": t.uint8_t,
                "seq": t.uint16_t,
                "position": t.uint32_t,
                "msgpart": t.LVBytes,
                "msgpartcrc": t.uint8_t,
            },
            direction=foundation.Direction.Client_to_Server,
            is_manufacturer_specific=False,
        )
        resp_ir_frame_05: Final = foundation.ZCLCommandDef(
            id=0x05,
            schema={
                "seq": t.uint16_t,
                "zero": t.uint16_t,
            },
            direction=foundation.Direction.Server_to_Client,
            is_manufacturer_specific=True,
        )

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle a cluster request."""

        # send default response to avoid repeated zcl frame from device
        if not hdr.frame_control.disable_default_response:
            _LOGGER.debug("Sending default response to %s", self.endpoint.device.ieee)
            self.send_default_rsp(hdr, status=foundation.Status.SUCCESS)

        if hdr.command_id == self.ServerCommandDefs.receive_ir_frame_00.id:
            _LOGGER.debug("Received IR frame 0x00 from %s", self.endpoint.device.ieee)

            self.current_position = 0
            self.ir_msg.clear()
            self.msg_length = args.length

            cmd_01_args = {
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
                super().command(0x01, **cmd_01_args, expect_reply=True)
            )
            cmd_02_args = {"seq": args.seq, "position": 0, "maxlen": 0x38}
            self.create_catching_task(
                super().command(0x02, **cmd_02_args, expect_reply=True)
            )
        elif hdr.command_id == self.ServerCommandDefs.receive_ir_frame_01.id:
            _LOGGER.debug(
                "IR-Message-Code01 received, sequence: %s, from %s",
                args.seq,
                self.endpoint.device.ieee,
            )
            _LOGGER.debug(
                "Message to send: %s, to %s",
                self.endpoint.device.ir_msg_to_send[args.seq],
                self.endpoint.device.ieee,
            )
        elif hdr.command_id == self.ServerCommandDefs.receive_ir_frame_02.id:
            position = args.position
            seq = args.seq
            maxlen = args.maxlen
            irmsg = self.endpoint.device.ir_msg_to_send[seq]
            msgpart = irmsg[position : position + maxlen]
            calculated_crc = 0
            for x in msgpart:
                calculated_crc = (calculated_crc + ord(x)) % 0x100
            _LOGGER.debug(
                "Received IR frame 0x02 from %s, msgsrc: %s, position: %s, msgpart: %s",
                self.endpoint.device.ieee,
                calculated_crc,
                position,
                msgpart,
            )
            cmd_03_args = {
                "zero": 0,
                "seq": seq,
                "position": position,
                "msgpart": msgpart.encode("utf-8"),
                "msgpartcrc": calculated_crc,
            }
            self.create_catching_task(
                super().command(0x03, **cmd_03_args, expect_reply=True)
            )
        elif hdr.command_id == self.ServerCommandDefs.receive_ir_frame_03.id:
            msg_part_crc = args.msgpartcrc
            calculated_crc = 0
            for x in args.msgpart:
                calculated_crc = (calculated_crc + x) % 0x100
            _LOGGER.debug(
                "Received IR frame 0x03 from %s, msgcrc: %s, "
                "calculated_crc: %s, position: %s",
                self.endpoint.device.ieee,
                msg_part_crc,
                calculated_crc,
                args.position,
            )
            self.ir_msg[args.position :] = args.msgpart
            if args.position + len(args.msgpart) < self.msg_length:
                cmd_02_args = {
                    "seq": args.seq,
                    "position": args.position + len(args.msgpart),
                    "maxlen": 0x38,
                }
                self.create_catching_task(
                    super().command(0x02, **cmd_02_args, expect_reply=False)
                )
            else:
                _LOGGER.debug(
                    "IR message completely received from %s", self.endpoint.device.ieee
                )
                cmd_04_args = {"zero0": 0, "seq": args.seq, "zero1": 0}
                self.create_catching_task(
                    super().command(0x04, **cmd_04_args, expect_reply=False)
                )
        elif hdr.command_id == self.ServerCommandDefs.receive_ir_frame_04.id:
            seq = args.seq
            _LOGGER.debug(
                "IR code has been sent to %s (seq:%s)", self.endpoint.device.ieee, seq
            )
            cmd_05_args = {"seq": seq, "zero": 0}
            self.create_catching_task(
                super().command(0x05, **cmd_05_args, expect_reply=False)
            )
        elif hdr.command_id == self.ServerCommandDefs.receive_ir_frame_05.id:
            self.endpoint.device.last_learned_ir_code = base64.b64encode(
                bytes(self.ir_msg)
            ).decode()
            _LOGGER.info(
                "IR message really totally received: %s, from %s",
                self.endpoint.device.last_learned_ir_code,
                self.endpoint.device.ieee,
            )
            _LOGGER.debug(
                "Stopping learning mode on device %s", self.endpoint.device.ieee
            )
            self.create_catching_task(
                self.endpoint.zosung_ircontrol.command(
                    0x01, on_off=False, expect_reply=False
                )
            )
        else:
            _LOGGER.debug(
                "Unhandled command: %s, from %s",
                hdr.command_id,
                self.endpoint.device.ieee,
            )


class ZosungIRBlaster(CustomDevice):
    """Zosung IR Blaster."""

    seq = -1
    ir_msg_to_send = {}
    last_learned_ir_code = t.CharacterString("")

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.seq = 0
        super().__init__(*args, **kwargs)

    def next_seq(self):
        """Next local sequence."""
        self.seq = (self.seq + 1) % 0x10000
        return self.seq

    signature = {
        # "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>,
        # complex_descriptor_available=0, user_descriptor_available=0, reserved=0,
        # aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>,
        # mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>,
        # manufacturer_code=4098, maximum_buffer_size=82,
        # maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82,
        # descriptor_capability_field=<DescriptorCapability.NONE: 0>,
        # *allocate_address=True, *is_alternate_pan_coordinator=False,
        # *is_coordinator=False, *is_end_device=True, *is_full_function_device=False,
        # *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False,
        # *is_security_capable=False)",
        # input_clusters=[0x0000, 0x0001, 0x0003, 0x0004, 0x0005, 0x0006,
        #                 0xe004, 0xed00]
        # output_clusters=[0x000a, 0x0019]
        #  <SimpleDescriptor endpoint=1, profile=260, device_type=61440
        #  device_version=1
        #  input_clusters=[0, 1, 3, 4, 5, 6, 57348, 60672]
        #  output_clusters=[10, 25]>
        MODELS_INFO: [
            ("_TZ3290_ot6ewjvmejq5ekhl", "TS1201"),
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


class ZosungIRBlaster_ZS06(ZosungIRBlaster):
    """Zosung IR Blaster ZS06."""

    signature = {
        #  <SimpleDescriptor endpoint=1, profile=260, device_type=61440
        #  device_version=1
        #  input_clusters=[0, 3, 4, 5, 6, 57348, 60672]
        #  output_clusters=[10, 25]>
        #  <SimpleDescriptor endpoint=242, profile=41440, device_type=97
        #  device_version=1
        #  input_clusters=[]
        #  output_clusters=[33]>
        MODELS_INFO: [
            ("_TZ3290_7v1k4vufotpowp9z", "TS1201"),
            ("_TZ3290_acv1iuslxi3shaaj", "TS1201"),
            ("_TZ3290_gnl5a6a5xvql7c2a", "TS1201"),
            ("_TZ3290_rlkmy85q4pzoxobl", "TS1201"),
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
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
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
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }
