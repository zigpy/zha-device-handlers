"""ZHA quirk for the Salus KL08RF 8-zone wiring centre (Computime, mfr 0x1078).

Built with the zha-device-handlers **v2 QuirkBuilder** pattern, as a companion
to `salus_sq610rf.py` (the SQ610RFNH thermostat quirk, confirmed working on
ZHA 2026-07-04).

STATUS: VERIFIED ON HARDWARE 2026-09-10/11. The KL08RF joins ZHA and stays --
3+ hours, zero NWK Leaves -- which is the failure both z2m reports hit. Its
interview matched the predicted signature exactly. The one thing that did NOT
work, and why, is decoded under THE SLOT ASSIGNMENT below; the fix is in this
file and is the single most important thing to understand about it.

What the native captures establish (facts)
------------------------------------------

* The KL08RF (native short 0xb15f, IEEE 00:1e:5e:09:09:03:dc:67, Computime
  OUI) is a mains-powered ZIGBEE ROUTER -- one of only two NWK Link Status
  originators on the native net (the other is the CO10RF coordinator).
* Its wiring-centre service lives on **endpoint 8**: thermostats address
  their fc00 0x12 operational reports and the 0x18/0x14 zone-bind requests to
  wc:ep8, and the KL08RF answers 0x88/0x84 from ep8.
* It runs its OWN gateway-facing fc00 session: a 0x10 -> 0x81 handshake
  followed by command **0x37** (payload `110000`), once per ~90 min -- the
  same Computime commissioning/keep-alive grammar the SQ610RF uses
  (reply = 0x80 | low-nibble(request), ZCL FCF 0x1d, mfr 0x1078).
* The 0x81 reply body is `[slot] 00 [counter x2 LE] [session const x2] 03 0d
  01 ff ff ff ff 30 00`. Byte 0 is the device's ASSIGNED SLOT, not a session
  token -- see THE SLOT ASSIGNMENT below. Bytes 2-5 are a counter plus a
  per-session constant and are NOT validated by devices.
* Heat demand / relays are HARDWIRED, never on-air: driving a zone to 28 C
  produced NO Zigbee demand command from the KL08RF (heat-demand capture).
  The KL08RF switches its zone relays from the demand bit it receives in the
  thermostats' 0x12 reports; it transmits nothing operational upstream.

=> There is NOTHING operational to read from the KL08RF over Zigbee, so this
quirk builds NO entities (ZHA still provides LQI/RSSI). Its whole job is:
keep the device joined by answering the Computime handshake, and LOG every
proprietary frame it sends for future decoding.

Confirmed by two independent ZHA-family interviews (z2m #3354 + #15208)
----------------------------------------------------------------------
This exact device shows up in two zigbee2mqtt reports -- as the Salus KL08RF
(Koenkk/zigbee-herdsman-converters#3354, 2021) and as its white-label the
Cosmo CFK8L / "CFKL8" 8-Zonen-Funk-Regelklemmleiste (Koenkk/zigbee2mqtt#15208,
2022). Both are DIFFERENT physical units than ours; the same reporter linked
them and called the CFK8L "a whitelabel of the Salus KL08RF". They confirm the
failure mode this quirk fixes and pin down the join signature.

WHITE-LABELS: the same hardware is sold as at least Salus KL08RF and Cosmo
CFK8L (CFKL8). All report identically over Zigbee (see below), so this one
quirk covers every rebrand -- there is no model string to tell them apart
anyway.

Full join signature (authoritative -- from the #15208 herdsman DB entry, whose
interview completed further than #3354's):
* node type ROUTER (mains); manufId 4216 = 0x1078 (Computime);
  powerSource "Unknown"; zclVersion 0; hwVersion 1 (#3354 saw hwVersion 197 --
  a firmware/label difference the quirk does not depend on).
* Basic manufacturerName "Computime" (NOT "SALUS") and NO ModelIdentifier
  (both reports log the model as 'undefined'). Our own SQ610RF thermostats
  report "SALUS"; this device's firmware still reports the raw Computime
  vendor. => we match on manufacturer + an endpoint-8 signature filter, never
  a model string (see the registration block).
* A SINGLE endpoint EP8: profile 0x0104, device_id 0x0000, in-clusters
  [0x0000 Basic, 0x0003 Identify, 0xFC00], out-clusters [0x0003 Identify,
  0x0019 OTA, 0xFC00]. So fc00 is present as BOTH input and output, OTA is an
  output cluster, and there is nothing operational (no on/off, no relay
  state). Matches our native-net finding that the wiring centre lives on EP8.
  (#3354's aborted interview only managed to read genBasic before the leave,
  which is why `.adds()` still guarantees fc00 defensively.)
* Both units sent the SAME raw manufacturer frame during pairing (z2m
  mislabels cluster 0xFC00 as "manuSpecificPhilips" in #3354 and
  "manuSpecificUbisysDeviceSetup" in #15208 -- both vendors squat on 0xFC00):
    #3354  : 15 78 10 28 10 ff 00 ff 22 03 18 20
    #15208 : 15 78 10 29 10 ff 00 ff 18 04 19 20
    = ZCL FCF 0x15 (cluster-specific, mfr-specific, client->server,
      disable-default-response), mfr 0x1078, command 0x10, payload byte0 0xff
      = FIRST CONTACT. (The trailing payload bytes differ per firmware/config;
      our handler keys only off byte0 == 0xff, so it answers both.)
  So the device opens with fc00 command 0x10 exactly like the SQ610RF -- our
  commission handler replies 0x81 assigning it wiring-centre slot 0x01.
* In BOTH reports z2m only APS-acked the 0x10 (no application reply) and the
  device LEFT the network seconds later, re-joining in a loop -- the exact
  "answer 0x10 with 0x81 or it re-pairs forever" failure this quirk fixes.
* Hardware teardown in #3354: the KL08RF drives its relays through a PCF8575
  I2C GPIO expander (local), and the CO10RF gateway is a Silicon Labs CP210x
  USB-UART bridge -- independent confirmation that the zone relays are
  switched locally, never commanded over Zigbee.

Why join it to ZHA at all
-------------------------
* It is a mains ROUTER: its NWK Link Status presence satisfies the SQ610RF's
  round-2 commissioning gate all by itself (no third-party router needed).
* Future goal: with a real KL08RF on the ZHA net, the SQ610RF quirk's 0x86
  reply could point thermostats at the KL08RF's short address instead of the
  coordinator -- then the hardwired zone relays would fire from real thermostat
  demand under ZHA. That is a cross-device change in salus_sq610rf.py and
  needs live hardware; explicitly OUT OF SCOPE here.

THE SLOT ASSIGNMENT -- the whole point of this file
---------------------------------------------------
Decoded 2026-09-11 by running a factory-reset CO10RF from a Mac USB port (it
adopts with no host attached) while sniffing the radio, then watching it
rebuild the entire network from zero (capture_salus_rebuild_ch15.pcap).

**fc00 0x81 byte 0 is the SLOT the coordinator assigns the device.** On first
contact (request byte0 0xff, only ever sent by a factory-reset unit) the
coordinator ASSIGNS it; the device echoes its own slot in every later 0x10.
The value range encodes the device class:

    wiring centres   0x01 .. 0x09    the "control box" numbers -- what the
                                     thermostat's 01..09 picker selects and
                                     what the KL08RF shows on its zone LEDs
    thermostats      0x2b ..         six native units took 2b 2c 2d 2e 2f 30

Evidence, all from hardware: the KL08RF took slot 01 on an empty coordinator
table and lit exactly one zone LED at zone 1; the six thermostats then took
2b..30 in pairing order; all eleven binds were ACCEPTED (0x88 byte0 = 00).
Corroborating: 0x37's payload byte0 is `0x10 | slot` (11 at box 1, 12 at box 2),
and a short press of Pair displays the slot on the zone LEDs.

WHAT WENT WRONG BEFORE, and why it matters to anyone editing this file: we
answered first contact with 0x2b, copied from the thermostat gold-ref. That
told the KL08RF "you are wiring centre 43" -- not a valid box. It therefore
displayed no address, never sent 0x37, and REFUSED every zone bind with
`0x88 01ff...` (status 01). Two days went into chasing state bytes, session
advance, control-box indices and ZCL discovery, all of which were downstream of
that one byte. If you change FC00_0X81_WC_SLOT, keep it in 1..9.

Answered assumptions (were open until 2026-09-10; kept for the record)
----------------------------------------------------------------------
1. Identity CONFIRMED at first interview: manufacturer "Computime", NO model
   string, mfr code 0x1078, sole endpoint EP8 with in [Basic, Identify, fc00]
   and out [Identify, OTA, fc00] -- exactly the #15208 signature. The
   manufacturer + endpoint-8 filter match is correct as written.
2. ANSWERED, AND IT WAS WRONG: the KL08RF runs NEITHER of the thermostat's
   post-handshake gates. It never reads our Basic ModelIdentifier (no SAL6DC1
   check) and never sends an OTA Query-Next-Image -- ZHA pushed it an Image
   Notify and it simply APS-acked and ignored it. SalusKL08Basic and
   SalusKL08Ota are therefore DEAD CODE for this device. They are kept because
   they cost nothing at runtime and the white-labels are untested.
3. The 0x37 keep-alive gets no application reply: holds in practice. Never seen
   to loop; on ZHA it was never sent at all, because the device was never
   properly commissioned (see above). Natively it follows 0x81 by 0.15 s.
4. fc00 on EP8 CONFIRMED (in+out). `.adds()` is kept anyway so an aborted
   interview still dispatches the incoming 0x10.

Other decoded fields
--------------------
* 0x88 byte 0 is a STATUS: 00 = bind accepted (0x84 follows), 01 = refused.
  It is NOT a control-box echo -- the same box index yields both values.
* 0x33 (thermostat -> coordinator, empty payload) appears only after a REFUSED
  bind; it looks like the thermostat reporting failure upstream. Never needed
  answering once the slot was right.
* The thermostat screen distinguishes the two failures: a 0x86 whose box index
  does not echo its request gives "Control box not exist NN" with no 0x18 at
  all; a refused 0x18 just returns it to the box/zone picker.

"""

from typing import Final

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Ota
from zigpy.zcl.foundation import BaseCommandDefs, ZCLCommandDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster

SALUS = "SALUS"
# The KL08RF reports Basic manufacturerName "Computime" and NO model string
# (z2m issues #3354 and #15208 agree). We match on manufacturer + an endpoint-8
# signature filter (see the registration block); "SALUS" is matched too in case
# a firmware variant rebrands the vendor as our SQ610RF thermostats do.
COMPUTIME_MFR = "Computime"
COMPUTIME = 0x1078  # manufacturer CODE (node descriptor / mfr-specific frames)
# The KL08RF's wiring-centre service endpoint, known from native on-air
# addressing (thermostat 0x12/0x18/0x14 frames target wc:ep8) and confirmed as
# the device's SOLE endpoint by both z2m reports (epList [8]).
WC_EP = 8

# Toggle the fc00 cmd-0x10 -> 0x81 commissioning auto-reply.
ENABLE_FC00_COMMISSION_REPLY = True

# Model string a Computime device expects to read back from its "coordinator"
# during commissioning -- what a native Salus CO10RF reports (captured
# verbatim during the SQ610RF work). Unverified whether the KL08RF runs this
# identity gate (assumption 2); harmless if it never reads it.
SALUS_COORD_MODEL = "SAL6DC1"

# --- fc00 0x81 reply: THE WIRING-CENTRE SLOT ASSIGNMENT ---
#
# Body layout (DECODED 2026-09-11, see the module docstring):
#     [slot] 00 [counter x2 LE] [session const x2] 03 0d 01 ff ff ff ff 30 00
#
# **Byte 0 is the node's SLOT -- the address the coordinator assigns it.** It is
# NOT a "session token", which is what this file (and salus_sq610rf.py) called it
# for months. On FIRST CONTACT (request byte0 0xff) the coordinator ASSIGNS the
# slot here; the device then echoes its own slot as byte0 of every later 0x10.
# The value range encodes the DEVICE CLASS:
#
#     wiring centres  0x01 .. 0x09   <- the "control box" numbers. This is what
#                                       the thermostat's on-screen 01..09 picker
#                                       selects, and what the KL08RF displays on
#                                       its zone LEDs (short-press Pair).
#     thermostats     0x2b ..        <- the six native units took 2b 2c 2d 2e 2f
#                                       30 in pairing order.
#
# Proven by watching a factory-reset CO10RF rebuild the whole network from zero
# (capture_salus_rebuild_ch15.pcap): the KL08RF took slot 01 on an empty table
# and lit exactly one zone LED, at zone 1; the six thermostats then took 2b..30
# in order; and all eleven subsequent binds were ACCEPTED (0x88 byte0 = 00),
# where every bind on ZHA the day before had been REFUSED (0x88 byte0 = 01).
#
# THE BUG THIS FIXES: we used to answer first contact with 0x2b -- copied from
# the thermostat gold-ref -- which told the KL08RF "you are wiring centre 43".
# Not a valid box, so it displayed no address, never went operational, and
# correctly refused every bind. Everything else we chased (state bytes, session
# advance, control-box indices, ZCL discovery) was downstream of that one byte.
FC00_0X81_WC_SLOT = 0x01  # 1..9; the control box number this unit will answer to

# Bytes 2-3 are a little-endian counter and 4-5 a per-session constant; neither
# is validated by the device. Observed running 8b39 -> 8c86 monotonically across
# one session while 3632 held constant. We send a fixed, captured pair.
FC00_0X81_TAIL = bytes.fromhex("4dd931030d01ffffffff3000")


def commission_reply_body(req: bytes) -> bytes:
    """Build the fc00 0x81 reply body for a KL08RF 0x10 request.

    On FIRST CONTACT (request byte0 0xff -- only ever seen from a
    factory-reset unit) we ASSIGN the wiring-centre slot. Afterwards the device
    echoes its own slot back to us in byte0 and we simply confirm it, which is
    what the native CO10RF does: its one captured reply to an established
    KL08RF was `01 00 fe 4dd931...` -- byte0 01 because that unit was box 1.
    """
    first = not req or req[0] == 0xFF
    slot = FC00_0X81_WC_SLOT if first else req[0]
    return bytes([slot, 0x00, 0xFE]) + FC00_0X81_TAIL


def payload_bytes(args) -> bytes:
    """Raw body of an incoming fc00 command, whichever shape zigpy hands us.

    zigpy picks its command table from the ZCL DIRECTION bit: Server_to_Client
    (FCF 0x1d) resolves against client_commands, Client_to_Server (FCF 0x15)
    against server_commands. An id missing from the table it picks comes back
    as RAW BYTES with no `.data` attribute -- silently, with no error logged.

    THE BUG (2026-09-10): Salus points its two device classes in OPPOSITE
    directions -- the SQ610RF thermostat sends 0x1d, the KL08RF sends 0x15 --
    and this file originally declared its commands under ClientCommandDefs
    only. So every KL08RF payload arrived EMPTY, the handler silently took its
    "no payload" branch, and each 0x81 answered an established session as if it
    were first contact. Nothing in the log said so. Fixed by declaring the ids
    on BOTH tables and extracting through here.
    """
    if args is None:
        return b""
    data = getattr(args, "data", None)
    if data is not None:
        return bytes(data)
    if isinstance(args, (bytes, bytearray)):
        return bytes(args)
    return b""


class _RawPayload(t.Struct):
    """A ZCL command body that is just raw bytes (Salus uses no ZCL typing)."""

    data: t.Bytes


class SalusKL08FC00Cluster(CustomCluster):
    """Salus/Computime proprietary cluster 0xFC00 -- KL08RF gateway session.

    On its native net the KL08RF periodically (~90 min) runs toward the
    gateway:
        kl08 0x10  ->  ctrl 0x81   (session handshake -- we must answer)
        kl08 0x37  ->  (APS-ack only observed; no app reply)
    The other declared commands (0x11 time-notify, 0x25 update-check, 0xa9
    distress) are known from the SQ610RF side of the same Computime family
    and are declared so zigpy deserializes and LOGS them instead of dropping
    them -- never yet observed from the KL08RF itself.
    """

    cluster_id = 0xFC00
    ep_attribute = "salus_fc00"
    name = "Salus Manufacturer FC00"
    manufacturer_id_override = COMPUTIME

    class ClientCommandDefs(BaseCommandDefs):
        """Manufacturer commands the KL08RF may send (schema: raw bytes)."""

        commission_request: Final = ZCLCommandDef(
            id=0x10, schema=_RawPayload, is_manufacturer_specific=True
        )
        # Family command: the SQ610RF broadcasts this on clock changes.
        time_notify: Final = ZCLCommandDef(
            id=0x11, schema=_RawPayload, is_manufacturer_specific=True
        )
        # Family command: proprietary firmware update-check (no standard OTA).
        update_check_request: Final = ZCLCommandDef(
            id=0x25, schema=_RawPayload, is_manufacturer_specific=True
        )
        # KL08RF keep-alive, payload `110000` observed once per ~90 min.
        keep_alive: Final = ZCLCommandDef(
            id=0x37, schema=_RawPayload, is_manufacturer_specific=True
        )
        # Family command: distress heartbeat while NOT commissioned.
        distress: Final = ZCLCommandDef(
            id=0xA9, schema=_RawPayload, is_manufacturer_specific=True
        )
        # Declared for documentation; the quirk builds this reply manually.
        commission_response: Final = ZCLCommandDef(
            id=0x81, schema=_RawPayload, is_manufacturer_specific=True
        )

    class ServerCommandDefs(BaseCommandDefs):
        """The SAME commands again, declared Client_to_Server.

        The KL08RF sends its requests with the ZCL direction bit CLEAR (on-air
        FCF 0x15 = Client_to_Server), unlike the SQ610RF thermostat which uses
        0x1d. zigpy chooses the command table from that bit, so ids present only
        under ClientCommandDefs are "unknown" for this device and its payloads
        arrive unparsed -- see payload_bytes() for the full story and the bug it
        caused. Declaring both sides makes zigpy parse the frames properly and
        log them by name instead of as "Unknown Command".
        """

        commission_request: Final = ZCLCommandDef(
            id=0x10, schema=_RawPayload, is_manufacturer_specific=True
        )
        time_notify: Final = ZCLCommandDef(
            id=0x11, schema=_RawPayload, is_manufacturer_specific=True
        )
        update_check_request: Final = ZCLCommandDef(
            id=0x25, schema=_RawPayload, is_manufacturer_specific=True
        )
        keep_alive: Final = ZCLCommandDef(
            id=0x37, schema=_RawPayload, is_manufacturer_specific=True
        )
        distress: Final = ZCLCommandDef(
            id=0xA9, schema=_RawPayload, is_manufacturer_specific=True
        )

    def handle_cluster_request(
        self, hdr: foundation.ZCLHeader, args, *, dst_addressing=None
    ):
        req = payload_bytes(args)

        if hdr.command_id == 0x10 and ENABLE_FC00_COMMISSION_REPLY:
            # Session handshake -> answer 0x81 (token echoed, state advanced).
            body = commission_reply_body(req)
            # WARNING level on purpose: HA's UI log view filters DEBUG out, and
            # this one line is the whole diagnostic during the session-state
            # investigation. Drop back to self.debug() once that is settled.
            # Kept at debug: the slot we assign (body byte 0) is the single
            # most useful thing in this log when a bind is refused.
            self.debug(
                "KL08RF fc00 0x10 payload=%s (len %d) -> 0x81 body=%s",
                req.hex() or "<EMPTY - payload not parsed!>",
                len(req),
                body.hex(),
            )
            self.create_catching_task(self._send_fc00_reply(hdr.tsn, 0x81, body))
            return

        if hdr.command_id == 0x37:
            # Keep-alive. Native capture is consistent with APS-ack only, so
            # we accept it silently (assumption 3 in the module docstring).
            # If the device re-sends this in a tight loop at test time, it
            # wants an app reply -- try 0xb7 per the reply grammar.
            self.debug(
                "KL08RF fc00 keep-alive 0x37, payload %s (accepted, no reply)",
                req.hex(),
            )
            return

        if hdr.command_id == 0xA9:
            # On the SQ610RF this heartbeat means "commissioning NOT complete".
            self.warning(
                "KL08RF fc00 0xa9 distress heartbeat, payload %s -- the device "
                "does not consider itself commissioned; check the 0x10/0x81 "
                "handshake in the debug log",
                req.hex(),
            )
            return

        # Anything else (0x11/0x25/other): accept silently and log the raw
        # payload -- future reverse-engineering material. The device sets
        # disable-default-response, so no ZCL reply is expected.
        self.debug(
            "KL08RF fc00 command 0x%02x, payload %s (accepted, no reply)",
            hdr.command_id,
            req.hex(),
        )

    async def _send_fc00_reply(self, tsn, command_id, body):
        """Emit a Salus fc00 reply with the exact on-air framing the CO10RF uses.

        Mirrors salus_sq610rf.py: Salus tags replies Server->Client with
        disable-default-response (on-air ZCL FCF 0x1d), which zigpy's
        high-level reply() cannot produce from a server cluster -- so the
        frame is built directly.
        """
        rhdr = foundation.ZCLHeader.cluster(
            tsn=tsn, command_id=command_id, manufacturer=COMPUTIME
        )
        rhdr = rhdr.replace(
            frame_control=rhdr.frame_control.replace(
                direction=foundation.Direction.Server_to_Client,
                disable_default_response=True,
            )
        )
        data = rhdr.serialize() + body
        await self.endpoint.reply(
            cluster=self.cluster_id,
            sequence=tsn,
            data=data,
            command_id=command_id,
        )


class SalusKL08Ota(CustomCluster, Ota):
    """OTA cluster that mimics the CO10RF's non-OTA reply (mirrors salus_sq610rf.py).

    IF the KL08RF probes OTA during its join (unverified -- assumption 2), a
    native Salus controller answers the `Query Next Image Request` with a
    plain ZCL Default Response, status Invalid Field (0x85) -- NOT an OTA
    image response. The SQ610RF stalls on stock ZHA's real OTA-server answer,
    so the same fix is preloaded here. Harmless if the KL08RF never asks.
    """

    def handle_cluster_request(self, hdr, args, *, dst_addressing=None):
        if (
            ENABLE_FC00_COMMISSION_REPLY
            and hdr.direction == foundation.Direction.Client_to_Server
            and hdr.command_id == self.ServerCommandDefs.query_next_image.id
        ):
            self.create_catching_task(self._send_ota_default_rsp(hdr.tsn))
            return
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

    async def _send_ota_default_rsp(self, tsn):
        rhdr = foundation.ZCLHeader.general(
            tsn=tsn,
            command_id=foundation.GeneralCommand.Default_Response,
            direction=foundation.Direction.Server_to_Client,
        )
        # Match the CO10RF exactly: it leaves disable-default-response clear.
        rhdr = rhdr.replace(
            frame_control=rhdr.frame_control.replace(disable_default_response=False)
        )
        body = foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(
            command_id=self.ServerCommandDefs.query_next_image.id,
            status=foundation.Status.INVALID_FIELD,
        )
        data = rhdr.serialize() + body.serialize()
        await self.endpoint.reply(
            cluster=self.cluster_id,
            sequence=tsn,
            data=data,
            command_id=foundation.GeneralCommand.Default_Response,
        )


class SalusKL08Basic(CustomCluster, Basic):
    """Basic cluster that answers the coordinator-identity check (mirrors
    salus_sq610rf.py).

    IF the KL08RF, like the SQ610RF, reads Basic ModelIdentifier from what it
    believes is the coordinator and gates on a Salus controller model string
    (unverified -- assumption 2), this answers "SAL6DC1". zigpy dispatches
    that incoming read on THIS device's own endpoint (by the sender's
    endpoint, see the long note in salus_sq610rf.py's SalusBasic), so the
    override lives here on the KL08RF quirk. Harmless if it never reads.
    """

    def handle_read_attribute_model(self) -> t.CharacterString:
        # Must be a zigpy string type (zigpy 2.x serializes via .serialize()).
        return t.CharacterString(SALUS_COORD_MODEL)


def _is_kl08rf(device) -> bool:
    """Signature guard for the manufacturer-only match.

    The KL08RF reports NO model string (issue #3354), so we cannot key on one
    and instead match manufacturer "Computime"/"SALUS" broadly. This filter
    narrows that to devices that actually look like the wiring centre: a device
    exposing endpoint 8 (its sole, wiring-centre endpoint). This is what
    distinguishes it from the SQ610RF thermostats in the same family, which
    live on endpoint 9 -- so this quirk will never grab a thermostat, and the
    thermostat quirk (keyed on model "SQ610RFNH") is checked first regardless.
    """
    return WC_EP in device.endpoints


# --- v2 registration -------------------------------------------------------
# Match on manufacturer + the endpoint-8 signature filter, because the KL08RF
# reports no model to key on (issue #3354). The builder ops are defensive by
# design (verified against zhaquirks 2.1.0: ops apply removes -> adds ->
# replaces -> occurrences, and all no-op with a warning on missing
# endpoints/clusters):
#   * .adds() pins fc00 + Basic onto EP8 -- the known wiring-centre endpoint --
#     so zigpy can dispatch frames the KL08RF sends FROM ep8 (zigpy routes
#     incoming requests by the sender's endpoint) EVEN THOUGH the interview may
#     not advertise fc00 there (issue #3354 saw only genBasic on EP8).
#   * replace_cluster_occurrences() then swaps in the custom clusters wherever
#     the real interview actually finds them (any endpoint, in or out).
# No entities: nothing operational is readable from the KL08RF over Zigbee.
(
    QuirkBuilder(COMPUTIME_MFR, None)
    # Cover a possible firmware rebrand to "SALUS" (as our thermostats report).
    .applies_to(SALUS, None)
    .filter(_is_kl08rf)
    .adds(SalusKL08FC00Cluster, endpoint_id=WC_EP)
    .adds(SalusKL08Basic, endpoint_id=WC_EP)
    .replace_cluster_occurrences(SalusKL08FC00Cluster)
    .replace_cluster_occurrences(SalusKL08Basic)
    .replace_cluster_occurrences(SalusKL08Ota)
    .add_to_registry()
)
