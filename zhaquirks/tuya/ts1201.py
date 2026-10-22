"""Tuya TS1201 IR blaster.

Heavily inspired by work from @mak-42
https://github.com/Koenkk/zigbee-herdsman-converters/blob/9d5e7b902479582581615cbfac3148d66d4c675c/lib/zosung.js
"""

import asyncio
import base64
import json
import logging
from typing import Any, Final, NamedTuple, Union

from zigpy.profiles import zgp, zha
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

from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legacy import CustomDevice

_LOGGER = logging.getLogger(__name__)

DEFAULT_IR_FREQUENCY: Final = 38000
IR_MSG_PART_MAX_LENGTH: Final = 0x38
# Seconds to wait for the device to confirm it has the whole IR message to send.
IR_SEND_TIMEOUT: Final = 10


def ir_msg_part_crc(msg_part: bytes) -> int:
    """Return the checksum the device uses for an IR message part."""
    return sum(msg_part) % 0x100


def ir_msg_for_code(
    code: str, freq: int = DEFAULT_IR_FREQUENCY, repeats: int = 0
) -> bytes:
    """Return the message the device expects for sending an IR code."""
    return json.dumps(
        {
            "key_num": 1,
            "delay": 300,
            # The device counts transmissions in total, not repeats.
            "key1": {"num": 1 + repeats, "freq": freq, "type": 1, "key_code": code},
        },
        separators=(",", ":"),
    ).encode()


class PendingIRSend(NamedTuple):
    """An IR message the device is fetching from us."""

    seq: int
    msg: bytes
    sent: asyncio.Future[None]


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
            schema={"data": t.Bytes},
            manufacturer_code=None,
        )
        IRLearn: Final = foundation.ZCLCommandDef(
            id=0x01,
            schema={"on_off": t.Bool},
            manufacturer_code=None,
        )
        IRSend: Final = foundation.ZCLCommandDef(
            id=0x02,
            schema={
                "code": t.CharacterString,
                "freq?": t.uint32_t,
                "repeats?": t.uint8_t,
            },
            manufacturer_code=None,
        )

    async def read_attributes(
        self,
        attributes: list[int | str | foundation.ZCLAttributeDef],
        **kwargs,
    ) -> Any:
        """Serve the last learned IR code, which only exists on our side."""
        learned_ir_code = self.AttributeDefs.last_learned_ir_code
        success: dict[Any, Any] = {}
        failure: dict[Any, foundation.Status] = {}
        for attribute in attributes:
            if attribute in (learned_ir_code.id, learned_ir_code.name, learned_ir_code):
                success[learned_ir_code.id] = self.endpoint.device.last_learned_ir_code
            else:
                failure[attribute] = foundation.Status.UNSUPPORTED_ATTRIBUTE
        return success, failure

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args,
        manufacturer: Union[int, t.uint16_t] | None = None,
        expect_reply: bool = True,
        tsn: Union[int, t.uint8_t] | None = None,
        **kwargs: Any,
    ):
        """Override the default cluster command."""
        if command_id == self.ServerCommandDefs.IRLearn.id:
            # The device reads "study" backwards: 0 starts learning, 1 stops it.
            study = b'{"study":0}' if kwargs["on_off"] else b'{"study":1}'
            return await super().command(
                self.ServerCommandDefs.data.id,
                t.Bytes(study),
                manufacturer=manufacturer,
                expect_reply=True,
                tsn=tsn,
            )
        elif command_id == self.ServerCommandDefs.IRSend.id:
            ir_msg = ir_msg_for_code(
                kwargs["code"],
                freq=kwargs.get("freq") or DEFAULT_IR_FREQUENCY,
                repeats=kwargs.get("repeats") or 0,
            )
            _LOGGER.debug(
                "Sending IR code: %s to %s", ir_msg, self.endpoint.device.ieee
            )
            await self.endpoint.zosung_irtransmit.send_ir_msg(ir_msg, tsn=tsn)
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)
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
            manufacturer_code=None,
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
            manufacturer_code=None,
        )
        receive_ir_frame_02: Final = foundation.ZCLCommandDef(
            id=0x02,
            schema={
                "seq": t.uint16_t,
                "position": t.uint32_t,
                "maxlen": t.uint8_t,
            },
            manufacturer_code=None,
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
        )
        receive_ir_frame_04: Final = foundation.ZCLCommandDef(
            id=0x04,
            schema={
                "zero0": t.uint8_t,
                "seq": t.uint16_t,
                "zero1": t.uint16_t,
            },
            manufacturer_code=None,
        )
        receive_ir_frame_05: Final = foundation.ZCLCommandDef(
            id=0x05,
            schema={
                "seq": t.uint16_t,
                "zero": t.uint16_t,
            },
            manufacturer_code=None,
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
        )
        resp_ir_frame_05: Final = foundation.ZCLCommandDef(
            id=0x05,
            schema={
                "seq": t.uint16_t,
                "zero": t.uint16_t,
            },
            manufacturer_code=None,
        )

    def __init__(self, *args, **kwargs):
        """Init cluster and its per-instance learn and send state."""
        super().__init__(*args, **kwargs)
        self.current_position = 0
        self.msg_length = 0
        self.ir_msg: list[int] = []
        self.seq = 0
        # The ZS06 handles one transfer at a time, so each send waits its turn.
        self.send_lock = asyncio.Lock()
        self.pending_send: PendingIRSend | None = None

    async def send_ir_msg(
        self, ir_msg: bytes, *, tsn: int | t.uint8_t | None = None
    ) -> None:
        """Send an IR message and wait until the device confirms it has all of it."""
        async with self.send_lock:
            self.seq = (self.seq + 1) % 0x10000
            sent = asyncio.get_running_loop().create_future()
            self.pending_send = PendingIRSend(self.seq, ir_msg, sent)
            try:
                await super().command(
                    self.ServerCommandDefs.receive_ir_frame_00.id,
                    seq=self.seq,
                    length=len(ir_msg),
                    unk1=0x00000000,
                    clusterid=ZosungIRControl.cluster_id,
                    unk2=0x01,
                    cmd=ZosungIRControl.ServerCommandDefs.IRSend.id,
                    unk3=0x0000,
                    expect_reply=False,
                    tsn=tsn,
                )
                async with asyncio.timeout(IR_SEND_TIMEOUT):
                    await sent
            except TimeoutError:
                _LOGGER.warning(
                    "IR code was not confirmed by %s (seq: %s)",
                    self.endpoint.device.ieee,
                    self.seq,
                )
                raise
            finally:
                self.pending_send = None

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
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
                super().command(
                    self.ServerCommandDefs.receive_ir_frame_01.id,
                    **cmd_01_args,
                    expect_reply=True,
                )
            )
            cmd_02_args = {
                "seq": args.seq,
                "position": 0,
                "maxlen": IR_MSG_PART_MAX_LENGTH,
            }
            self.create_catching_task(
                super().command(
                    self.ServerCommandDefs.receive_ir_frame_02.id,
                    **cmd_02_args,
                    expect_reply=True,
                )
            )
        elif hdr.command_id == self.ServerCommandDefs.receive_ir_frame_01.id:
            _LOGGER.debug(
                "IR-Message-Code01 received, sequence: %s, from %s",
                args.seq,
                self.endpoint.device.ieee,
            )
            _LOGGER.debug(
                "Message to send: %s, to %s",
                self.pending_send,
                self.endpoint.device.ieee,
            )
        elif hdr.command_id == self.ServerCommandDefs.receive_ir_frame_02.id:
            position = args.position
            seq = args.seq
            maxlen = args.maxlen
            pending = self.pending_send
            if pending is None or pending.seq != seq:
                # The device is asking for a message we no longer have, so the IR code
                # it belongs to will never be transmitted.
                _LOGGER.warning(
                    "Cannot send IR code to %s: no pending message for seq %s",
                    self.endpoint.device.ieee,
                    seq,
                )
                return
            msgpart = pending.msg[position : position + maxlen]
            calculated_crc = ir_msg_part_crc(msgpart)
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
                "msgpart": msgpart,
                "msgpartcrc": calculated_crc,
            }
            self.create_catching_task(
                super().command(
                    self.ServerCommandDefs.receive_ir_frame_03.id,
                    **cmd_03_args,
                    expect_reply=True,
                )
            )
        elif hdr.command_id == self.ServerCommandDefs.receive_ir_frame_03.id:
            msg_part_crc = args.msgpartcrc
            calculated_crc = ir_msg_part_crc(args.msgpart)
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
                    "maxlen": IR_MSG_PART_MAX_LENGTH,
                }
                self.create_catching_task(
                    super().command(
                        self.ServerCommandDefs.receive_ir_frame_02.id,
                        **cmd_02_args,
                        expect_reply=False,
                    )
                )
            else:
                _LOGGER.debug(
                    "IR message completely received from %s", self.endpoint.device.ieee
                )
                cmd_04_args = {"zero0": 0, "seq": args.seq, "zero1": 0}
                self.create_catching_task(
                    super().command(
                        self.ServerCommandDefs.receive_ir_frame_04.id,
                        **cmd_04_args,
                        expect_reply=False,
                    )
                )
        elif hdr.command_id == self.ServerCommandDefs.receive_ir_frame_04.id:
            seq = args.seq
            pending = self.pending_send
            if pending is None or pending.seq != seq:
                _LOGGER.debug(
                    "IR frame 0x04 from %s for unknown seq %s",
                    self.endpoint.device.ieee,
                    seq,
                )
            else:
                _LOGGER.debug(
                    "IR code has been sent to %s (seq:%s)",
                    self.endpoint.device.ieee,
                    seq,
                )
                if not pending.sent.done():
                    pending.sent.set_result(None)
            # Confirm an unknown seq too: it may be a repeat of a frame 0x04 whose
            # confirmation was lost.
            cmd_05_args = {"seq": seq, "zero": 0}
            self.create_catching_task(
                super().command(
                    self.ServerCommandDefs.receive_ir_frame_05.id,
                    **cmd_05_args,
                    expect_reply=False,
                )
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
                    ZosungIRControl.ServerCommandDefs.IRLearn.id,
                    on_off=False,
                    expect_reply=False,
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

    last_learned_ir_code = t.CharacterString("")

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
            ("_TZ3290_u9xac5rv", "TS1201"),
            ("_TZ3290_yyax9ajf", "TS1201"),
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
            ("_TZ3290_nba3knpsarkawgnt", "TS1201"),
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
