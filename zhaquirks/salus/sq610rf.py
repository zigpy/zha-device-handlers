"""ZHA quirk for the Salus SQ610RFNH Quantum thermostat (Computime, mfr 0x1078).

Built with the zha-device-handlers **v2 QuirkBuilder** pattern
(https://github.com/zigpy/zha-device-handlers, .github/copilot-instructions.md).

Status: grounded in decrypted over-the-air captures of the device joining BOTH
a stock ZHA coordinator (where it fails) and a native Salus system -- a CO10RF
gold-reference AND a real SQ610RF<->KL08RF pairing (where it succeeds). See
`sniffer/captures/` and `sniffer/salus_fc00_protocol_reference.txt`.

What the sniff established
--------------------------
* Device signature (ZHA diagnostics + sniff): manufacturer "SALUS",
  model "SQ610RFNH", node-descriptor manufacturer_code 0x1078 ("Computime"),
  a SLEEPY end device on endpoint 9, profile 0x0104, device_type THERMOSTAT.
  It has NO standard hvacThermostat (0x0201); heating control lives in the
  proprietary manufacturer clusters 0xFC00 and 0xFC09.
* Root cause of "stuck in pairing / LED keeps blinking":
  During commissioning the device repeatedly sends a manufacturer-specific
  ZCL command **0x10 on cluster 0xFC00** (mfr 0x1078, payload `ff 42 ff 3f
  00 00 00`) to the coordinator's endpoint 1 and waits for a manufacturer
  reply. Stock ZHA only APS-acks it and never sends an application reply, so
  after ~2 s the device broadcasts Permit-Join requests and RE-ASSOCIATES,
  looping forever (observed 52x). The fc00 bind itself IS set up by ZHA, so
  binding is not the problem -- the missing application reply is.

The fix (from the native captures)
----------------------------------
The controller answers the device's fc00 cmd 0x10 with **cmd 0x81**:
    dev  -> ctrl   cmd 0x10  payload ff42ff3f000000
    ctrl -> dev    cmd 0x81  payload 2b00a5a6d631030d01ffffffff3000   <-- unsticks it
This quirk makes ZHA send exactly that 0x81 reply (verified: the reply body
serializes byte-for-byte to the captured payload) plus the identity/OTA/bind
replies below.

Status update (native SQ610RF<->KL08RF pairing captured 2026-07-02)
-------------------------------------------------------------------
* The full wiring-centre bind (0x16/0x86, 0x18/0x88, 0x14/0x84) is now confirmed
  byte-for-byte against a REAL KL08RF (capture_kl08rf_pair_ch25.pcap); the replies
  this quirk sends match it. The on-screen "control box" number and "zone" map to
  the leading byte and the zone byte, and are echoed back dynamically.
* **0x81 BYTE 0 IS THE DEVICE'S ASSIGNED SLOT, not a session token** (decoded
  2026-09-11 from a full network rebuild -- capture_salus_rebuild_ch15.pcap, and
  see salus_kl08rf.py, where getting this wrong cost two days). On first contact
  the coordinator ASSIGNS it; the device echoes its own slot thereafter. The
  range encodes the device class: **thermostats 0x2b..**, wiring centres
  0x01..0x09. Six native thermostats took 2b 2c 2d 2e 2f 30 in pairing order.
  So the 0x2b this quirk sends is a VALID THERMOSTAT SLOT -- which is precisely
  why the thermostat side has always worked, and why handing that same 0x2b to a
  wiring centre did not. If a second SQ610RF is ever run against this quirk
  simultaneously, give it a distinct slot (0x2c, ...).
* The remaining 0x81 bytes are NOT validated: earlier ZHA deploys used the
  gold-ref a5/a8 + a6:d6:31 and the device accepted them. Bytes 2-3 are a
  little-endian counter and 4-5 a per-session constant.
* The round-2 gate: the device only sets its 0x10 byte-2 to 0x01 (which unlocks
  the 0x16 stage) once it detects a ROUTER neighbour advertising via NWK Link
  Status -- i.e. a wiring centre / any router must be present. On a bare ZHA
  coordinator with no routers it stays 0xff and the device never reaches 0x16.
* COMMISSIONING CONFIRMED WORKING on ZHA with a router present (2026-07-04). A
  45-min decrypted ch20 sniff (scratchpad/battery_long_ch20.pcap) shows the device
  (short 0xe178) fully commissioned and OPERATIONAL: it is a child of mains router
  0xea41 (a4:6d:d4:ff:fe:51:25:81), completed the wiring-centre bind, and steadily
  unicasts fc00 0x12 operational reports to coordinator endpoint 8 (the wiring-
  centre EP) -- APS-acked, with NO re-commissioning 0x10 loop, no 0x11 time flood,
  no 0x25, and no 0xa9 distress. So the quirk's commissioning replies work end-to-
  end once a mains router is in radio range (this resolves the earlier "TEST on a
  net with routers" note). Reporting cadence: prompt (within seconds) on a setpoint
  change, plus a FIXED ~10.25 min (615 s) steady-state 0x12 heartbeat even when
  nothing changes (a timer, not a threshold) -- so HA gets a fresh temperature at
  least every ~10 min. The sleepy device MAC-polls its parent every 7.0 s.
  See sniffer/salus_fc00_protocol_reference.txt for the full timing breakdown.
* CONTROL (writing a setpoint) is still unknown: in a local Salus system nothing
  writes setpoints over the air, so the write command was never captured. Remote
  control DOES exist, but only via the UGE600 gateway's LOCAL HTTP/LAN API
  (the `pyit600` client, `POST /deviceid/read` etc.) -- an off-Zigbee path a zigpy
  quirk cannot use. A gateway `readall` datamodel dump (GitHub issue #1524) is
  decoded in sniffer/salus_uge600_datamodel_map.txt; it independently confirms our
  /100 temp/setpoint scaling and the no-battery finding. But the
  0x12 operational report IS decoded (dev->wc: `02 01 <demand> <zone> 00 ff
  00 00 00 00 00 ff <measured x100 LE> <setpoint x100 LE> f4 01`) -- enough for a
  read-only temperature/setpoint entity once the device commissions.
* Schedule settings (type + per-day programs) are 100% LOCAL to the device --
  never transmitted, not readable, not writable (mapped 2026-07-03, see
  sniffer/salus_schedule_map.txt). Disabling the schedule emits fc09 attr
  0x0000 = 2 (manual/permanent) and a 0x12 with the setpoint reverted to the
  stored manual value; enabling is silent apart from a normal setpoint report.
"""

import datetime
import time
from typing import Final

import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic, Ota
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityType,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster

SALUS = "SALUS"
SALUS_MODEL = "SQ610RFNH"
# The base (non-NH) model reports Basic modelId "SQ610RF" -- seen in the 2020
# zigbee2mqtt interview log and the UGE600 gateway datamodel (GitHub issue #1524,
# sniffer/salus_uge600_datamodel_map.txt). Same Computime 0x1078 family; the fc00
# commissioning grammar this quirk answers is identical (only firmware-dependent
# payload bytes differ, which the quirk does not depend on). Matched too so a base
# SQ610RF gets the same commissioning fix; unverified on real base hardware.
SALUS_MODEL_BASE = "SQ610RF"
COMPUTIME = 0x1078  # manufacturer CODE (node descriptor / mfr-specific fc00 frames)
# Manufacturer NAME string. Our SQ610RFNH unit reports Basic manufacturerName
# "SALUS", but the Salus/Computime ecosystem more often reports the raw
# "Computime": zhaquirks matches the SP600/SPE600 plugs as (Computime, ...)
# (zhaquirks/salus/__init__.py), and the KL08RF wiring centre and its Cosmo
# CFK8L white-label both report "Computime" (z2m issues #3354/#15208). So the
# base SQ610RF (and other firmware) may report "Computime" rather than "SALUS";
# we match BOTH manufacturers for the SQ610 models below to be robust. This is
# safe -- the model strings are specific, so adding the manufacturer cannot
# over-match another device.
COMPUTIME_MFR = "Computime"
THERMOSTAT_EP = 9

# EXPERIMENT (2026-09-10) -- override the control-box index in the 0x86 reply
# instead of echoing the box the thermostat asked for. Set to None for normal
# behaviour (echo), or an int to force a specific index.
#
# Why (historical -- the underlying problem is SOLVED, see salus_kl08rf.py): a
# short press of the KL08RF's Pair button showed NO zone LEDs, because our quirk
# had assigned it slot 0x2b -- not a valid control box. The thermostat asks for
# box 0x01, so the KL08RF answered every bind
# `0x88 01ff0000000000` -- status 01, "that isn't me". An unassigned address is
# most likely stored as ZERO, which nothing has ever asked for.
#
# This also settles a second untested question: whether the thermostat uses OUR
# box byte in its follow-up 0x18, or its own on-screen selection. Every capture
# we have -- native and ZHA -- used 0x01 on both sides, so the two are
# indistinguishable until they differ.
#
# Reading the result:
# RESULT (tested on hardware 2026-09-10, capture_kl08rf_box00_ch20.pcap): the
# thermostat VALIDATES that our 0x86 echoes back the box index it asked for. With
# a forced 0x00 it rejected every attempt outright -- screen showed "Control box
# not exist NN" for NN = 01/02/09 -- and sent **NO 0x18 at all** (count: 0). So
# the box index CANNOT be redirected from here, and "unassigned == box 0" is not
# testable this way (the thermostat screen only offers 01..09 anyway).
# Left in place, disabled, because the knob is useful if a future capture shows a
# wiring centre legitimately answering to a different index.
FORCE_WC_BOX: int | None = None
# The endpoint a Salus wiring centre (KL08RF and its white-labels) serves from --
# confirmed as its SOLE endpoint by a live ZHA interview (2026-09-10). Used to
# recognise a real wiring centre on the network in _find_wiring_centre().
WC_EP = 8

# Toggle the fc00 cmd-0x10 -> 0x81 commissioning auto-reply.
ENABLE_FC00_COMMISSION_REPLY = True

# Auto-sync the device clock to Home Assistant's local time (same fc00 0x11 the
# "Set clock to HA time" button sends). Fires off the device's OWN incoming traffic
# -- so on the first contact after a (re)join or HA restart, then at most once every
# TIME_SYNC_INTERVAL_S, riding the ~10 min 0x12 heartbeat. No background timers.
# Keeps the SQ610RF's internal clock (and its local schedule) correct on ZHA with no
# Salus gateway. Set False to disable and drive the clock only from the button.
ENABLE_TIME_AUTO_SYNC = True
TIME_SYNC_INTERVAL_S = 24 * 60 * 60  # once a day

# Model string the device expects to read back from its "coordinator" during
# commissioning -- this is the model a native Salus CO10RF reports (captured
# verbatim). See SalusBasic below for why this lives on the *device* quirk.
SALUS_COORD_MODEL = "SAL6DC1"

# --- fc00 commissioning replies, from the native captures ---
#
# The 0x81 reply body is `2b 00 <state> a6 d6 31 03 0d 01 ff ff ff ff 30 00`.
# The device does the 0x10->0x81 exchange twice; the controller advances the
# <state> byte between rounds. Captured values (dev 0x10 -> ctrl 0x81):
#     round 1: 0x10 `ff42ff3f000000` -> 0x81 `2b00 a5 a6d6...`
#     round 2: 0x10 `2b42013f000000` -> 0x81 `2b00 a8 a6d6...`
# In round 1 the device's request starts with 0xff; in round 2 it echoes our
# session token 0x2b (the first byte of the 0x81 reply). So: request byte0 0xff
# => state 0xa5 (first contact), otherwise => state 0xa8 (advance). Replying 0xa5
# to *both* rounds leaves the device stuck emitting 0xa9 heartbeats and it never
# advances to 0x16 (observed in capture_basicfix_ch20.pcap).
#
# The reply byte 0 (token) is only *chosen* by us (0x2b) on first contact; on
# every later round we ECHO the device's request byte0 back, matching the native
# coordinator. The ch25 recon (salus-native-net-map) shows commissioned devices
# periodically re-running 0x10/0x81 with rolling tokens (2c..31) and the
# coordinator answering `<tok> 00 <state> ...`. On the join path this is
# byte-identical to always sending 0x2b (round 2's request byte0 *is* 0x2b);
# only the periodic session-refresh replies change.
FC00_0X81_STATE_FIRST = 0xA5
FC00_0X81_STATE_NEXT = 0xA8
FC00_0X81_TAIL = bytes.fromhex("a6d631030d01ffffffff3000")
# Token we pick on first contact (request byte0 == 0xff); on later rounds the
# device supplies a rolling token which we echo back (see _fc00_reply_for).
FC00_0X81_DEFAULT_TOKEN = 0x2B

# After the 0x81 rounds the device asks (0x16) which wiring centre to bind to,
# then binds a zone via 0x18/0x14. A native KL08RF wiring centre answers -- captured
# byte-for-byte from a real SQ610RF<->KL08RF pairing (capture_kl08rf_pair_ch25.pcap):
#     dev 0x16 `01`               -> wc 0x86 `01 5fb1`         (box 01 -> wc 0xb15f, LE)
#     dev 0x18 `01 06 0000ff0000` -> wc 0x88 `00ff0000000000`
#     dev 0x14 `00 06`            -> wc 0x84 `00 06 00`        (zone 06 ack)
# where the leading 0x01 = the on-screen "control box" number and 0x06 = the "zone".
#
# 0x86 points the device at a wiring centre, and we answer it in one of two ways
# (see _find_wiring_centre):
#   * A REAL wiring centre is on the ZHA network (a KL08RF joined via
#     salus_kl08rf.py -- verified working 2026-09-10): point the device at ITS
#     short address. The thermostat then sends 0x18/0x14 straight to that device's
#     endpoint 8 and the REAL hardware answers 0x88/0x84 -- our handlers below
#     never fire. This is the only arrangement in which the wiring centre's
#     hardwired zone relay actually switches, because the relay is driven from the
#     demand bit in the 0x12 reports the thermostat sends it.
#   * NO real wiring centre: fall back to being one ourselves -- 0x86 points at the
#     coordinator (0x0000) and our own 0x88/0x84 handlers complete the bind. This
#     commissions the thermostat and yields live temperature/setpoint entities, but
#     nothing can ever call for heat. This was the only behaviour before 2026-09-10.
#
# These replies land on this same cluster because zigpy routes incoming requests by
# the sender's endpoint (see SalusBasic). 0x88's body is constant on-air (the zone is
# only in the request); 0x86 and 0x84 are built dynamically in _fc00_reply_for.
FC00_0X88_REPLY = bytes.fromhex("00ff0000000000")


def payload_bytes(args) -> bytes:
    """Raw body of an incoming fc00 command, whichever shape zigpy hands us.

    zigpy picks its command table from the ZCL DIRECTION bit: Server_to_Client
    (FCF 0x1d) resolves against client_commands, Client_to_Server (FCF 0x15)
    against server_commands. An id missing from the table it picks is handed
    back as RAW BYTES with no `.data` attribute -- silently, with no error.

    This bit us hard on the KL08RF (2026-09-10): Salus points its two device
    classes in OPPOSITE directions, that quirk declared its commands on one
    table only, and so every payload arrived empty. Nothing logged; the handler
    just took its "no payload" branch forever.

    The SQ610RF sends 0x1d, so it lands in client_commands and works today.
    This helper exists so a frame arriving the other way degrades visibly
    rather than silently. See salus_kl08rf.payload_bytes -- same contract.
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


# --- setpoint-WRITE reverse-engineering: CLOSED (conclusive), 3 rounds 2026-07-03..08 ---
# CONCLUSION: there is NO coordinator-reachable over-air setpoint write on this device.
# The 07-03 closure was reached with a framing BUG (every fuzz frame went out
# Client->Server, ZCL FCF 0x05 -- the direction the device ignores; verified in
# capture_setpoint_write_ch20.pcap). Round 3 (07-08) fixed that: the hardware-validated
# 0x11 time write proved the device acts on coordinator fc00 frames only with the native
# Server->Client framing (FCF 0x1d, _send_fc00_reply). We re-ran the setpoint matrix
# through the CORRECT 0x1d framing (temporary probe command 0x31, since removed;
# capture_setpoint_probe3_ch20.pcap) and the setpoint STILL never moved:
#   * fc00 0x12, 0x13 (18-byte 0x12-report echo, SETPOINT spliced in) -> ignored.
#   * fc00 0x02 (both report-echo AND bare 2-byte centi-degC LE)      -> ignored.
#   * fc00 0x03, 0x04, 0x08, 0x0c (bare 2-byte centi-degC LE)         -> ignored.
#     (All confirmed on-air as FCF 0x1d; device sent no reply, setpoint held 26.00 C.)
# Corroborating: no native capture -- including capture_kl08rf_setpoint_ch25.pcap,
# recorded WHILE a setpoint was changed -- contains ANY inbound fc00 command to a
# thermostat other than commissioning (0x10/0x81), keepalive (0x37) and reports (0x12).
# The thermostat is the setpoint master; remote control exists only via the UGE600
# gateway's local HTTP API (pyit600; sniffer/salus_uge600_datamodel_map.txt, issue
# #1524), which is off-Zigbee and unreachable from a quirk. => setpoint stays read-only.
# Round 1+2 (0x05-framed) extras still on record: 0x0201 is a stub (OccupiedHeating/
# SystemMode -> Unsupported Attribute 0x86, SetpointRaiseLower -> Unsupported Cluster
# 0xc3); DANGER -- fc00 0x20 -> 0xa9 distress, **0x40 -> NWK Leave (device RESET/LEAVE,
# never send it)**, 0x80/0xe0 high band untested/unsafe. To re-open, re-add the 0x31
# probe (git history 2026-07-08) and sweep the high band deliberately, or capture a
# real UGE600 gateway setting a setpoint over-air.


class SalusFC00Cluster(CustomCluster):
    """Salus/Computime proprietary commissioning/control cluster 0xFC00.

    The SQ610RFNH sends manufacturer command 0x10 during commissioning and
    re-associates forever unless the coordinator answers with command 0x81.
    Decoded handshake (mfr 0x1078), device<->controller:
        dev  0x10  ->  ctrl 0x81   (commissioning accept -- the critical one)
        dev  0x16  ->  ctrl 0x86   (which wiring centre)
        dev  0x18  ->  ctrl 0x88   (zone bind)
        dev  0x14  ->  ctrl 0x84   (zone bind confirm)
    Reply command id is always 0x80 | low-nibble of the request.

    Post-commissioning the device also pushes status commands with no reply:
        dev  0x12              operational report (temp/setpoint/heat-demand)
        dev  0x25              firmware update-check (HA "update" click; no OTA)
    """

    cluster_id = 0xFC00
    ep_attribute = "salus_fc00"
    name = "Salus Manufacturer FC00"
    manufacturer_id_override = COMPUTIME

    # Monotonic timestamp of the last auto-sync clock push (None = never). Per-device
    # instance state; reset on HA restart so the clock is re-synced on first contact.
    _last_time_sync: float | None = None

    class AttributeDefs(BaseAttributeDefs):
        """Synthetic attributes populated locally from the 0x12 report.

        The device has no readable fc00 attributes -- it pushes state via the
        manufacturer command 0x12. We parse that report and `update_attribute`
        these so the v2 builder can surface them as sensors. They are read-only
        from cache (never read over-air), so access is "r", not reportable.
        """

        local_temperature: Final = ZCLAttributeDef(
            id=0x0000, type=t.int16s, access="r", manufacturer_code=COMPUTIME
        )
        # Device setpoint limits (from the UGE600 gateway datamodel, issue #1524):
        # MinHeatSetpoint 5.00 C .. MaxHeatSetpoint 35.00 C -- the intended range for
        # a future .number() setpoint entity, IF an over-air write command is ever
        # found (currently CLOSED). See sniffer/salus_uge600_datamodel_map.txt.
        occupied_heating_setpoint: Final = ZCLAttributeDef(
            id=0x0001, type=t.int16s, access="r", manufacturer_code=COMPUTIME
        )
        # The device's own heat-demand bit, byte 2 of the 0x12 report (01 = calling
        # for heat, 00 = satisfied; verified against measured-vs-setpoint across six
        # native thermostats -- this is what the KL08RF switches its zone relays on).
        # Surfaced as a "running" binary sensor (on = heating, off = idle).
        # Synthetic/cache-only, like the two above.
        running_state: Final = ZCLAttributeDef(
            id=0x0002, type=t.Bool, access="r", manufacturer_code=COMPUTIME
        )
        # Device clock, decoded from the fc00 0x11 date/time-change broadcast the
        # thermostat emits when its Date/Time (or DST) is edited on-screen (see
        # _handle_time_announce and the "SOLVED" section of sniffer/salus_time_map.txt).
        # Raw value = u32 LE = the device's LOCAL wall-clock, in SECONDS since the ZCL
        # epoch 2000-01-01 00:00:00. No timezone is transmitted, so this is naive local
        # time, NOT an absolute UTC timestamp. Synthetic/cache-only, like the above.
        device_time: Final = ZCLAttributeDef(
            id=0x0003, type=t.uint32_t, access="r", manufacturer_code=COMPUTIME
        )
        # DST flag carried in the same 0x11 (bytes 4-5: 03 01 = on, 02 00 = off).
        dst_active: Final = ZCLAttributeDef(
            id=0x0004, type=t.Bool, access="r", manufacturer_code=COMPUTIME
        )

    class ClientCommandDefs(BaseCommandDefs):
        """Manufacturer commands the device sends during commissioning.

        Registered so zigpy deserializes them (schema _RawPayload) and routes
        them to handle_cluster_request. The 0x8x replies are also declared for
        documentation; the quirk builds and sends those frames manually.
        """

        report: Final = ZCLCommandDef(
            id=0x12, schema=_RawPayload, is_manufacturer_specific=True
        )
        # Broadcast (NWK 0xffff) whenever the user edits the device's Date/Time or DST
        # on-screen. Body carries the absolute clock; decoded in _handle_time_announce.
        # Registered so zigpy deserializes/routes it to handle_cluster_request.
        time_announce_request: Final = ZCLCommandDef(
            id=0x11, schema=_RawPayload, is_manufacturer_specific=True
        )
        # Emitted when Home Assistant / ZHA triggers a firmware "update" on the
        # device. Salus does NOT use standard Zigbee OTA (cluster 0x0019) for the
        # SQ610RF: the device first reads the coordinator's Basic ZCL Version, then
        # sends this fc00 0x25 with a single payload byte (0x00 = "update check /
        # no update / idle"). The native controller only APS-acks it, so we accept
        # it and send no ZCL reply. See sniffer/salus_ota_map.txt (ADDENDUM).
        update_check_request: Final = ZCLCommandDef(
            id=0x25, schema=_RawPayload, is_manufacturer_specific=True
        )
        commission_request: Final = ZCLCommandDef(
            id=0x10, schema=_RawPayload, is_manufacturer_specific=True
        )
        bind_confirm_request: Final = ZCLCommandDef(
            id=0x14, schema=_RawPayload, is_manufacturer_specific=True
        )
        wiring_centre_request: Final = ZCLCommandDef(
            id=0x16, schema=_RawPayload, is_manufacturer_specific=True
        )
        bind_request: Final = ZCLCommandDef(
            id=0x18, schema=_RawPayload, is_manufacturer_specific=True
        )
        commission_response: Final = ZCLCommandDef(
            id=0x81, schema=_RawPayload, is_manufacturer_specific=True
        )
        bind_confirm_response: Final = ZCLCommandDef(
            id=0x84, schema=_RawPayload, is_manufacturer_specific=True
        )
        wiring_centre_response: Final = ZCLCommandDef(
            id=0x86, schema=_RawPayload, is_manufacturer_specific=True
        )
        bind_response: Final = ZCLCommandDef(
            id=0x88, schema=_RawPayload, is_manufacturer_specific=True
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Synthetic command backing the "Set clock to HA time" button.

        It never goes on-air as this id: command() intercepts it and instead emits
        the real fc00 0x11 time-announce (server->client, mfr 0x1078) to the device --
        the same frame a native thermostat broadcasts when its clock is edited. Id
        0x30 is unused by the real Salus protocol (only 0x10/0x14/0x16/0x18/0x25 seen).
        """

        set_clock_to_ha_time: Final = ZCLCommandDef(
            id=0x30, schema={}, is_manufacturer_specific=True
        )

    # ZCL/Zigbee time epoch (2000-01-01) -- the base for the 0x11 u32 timestamp.
    _ZCL_EPOCH = datetime.datetime(2000, 1, 1)

    async def command(self, command_id, *args, **kwargs):
        """Intercept the synthetic set-clock button; pass everything else through.

        The "Set clock to HA time" button calls this with command 0x30. We do NOT
        send 0x30 on-air; instead we emit a real fc00 0x11 carrying Home Assistant's
        current local time, then return a synthetic success so the button reports done.
        """
        if command_id == self.ServerCommandDefs.set_clock_to_ha_time.id:
            await self._set_clock_to_now()
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)
        return await super().command(command_id, *args, **kwargs)

    def _maybe_auto_sync(self) -> None:
        """Push the clock to HA time on first contact, then once per interval.

        Called from handle_cluster_request on every incoming device command, so it
        rides the device's own traffic (join handshake + ~10 min 0x12 heartbeat)
        instead of a background timer. Self-throttled to TIME_SYNC_INTERVAL_S; the
        timestamp is stamped BEFORE the async send so a burst of frames can't queue
        multiple pushes. Reset on HA restart (instance state) -> re-syncs on restart.
        """
        if not ENABLE_TIME_AUTO_SYNC:
            return
        now = time.monotonic()
        if (
            self._last_time_sync is not None
            and (now - self._last_time_sync) < TIME_SYNC_INTERVAL_S
        ):
            return
        self._last_time_sync = now
        self.create_catching_task(self._set_clock_to_now())

    async def _set_clock_to_now(self) -> None:
        """Emit an fc00 0x11 setting the device clock to HA's current local time.

        Body mirrors what a native thermostat sends on a clock edit (decoded in
        _handle_time_announce; sniffer/salus_time_map.txt "SOLVED"):
            <u32 LE: local time, seconds since 2000-01-01> <DST b4><DST b5> 0x0d
        Sent as a server->client fc00 frame (FCF 0x1d, mfr 0x1078) via the same path
        the commissioning replies use. EXPERIMENTAL: whether the device honours a
        coordinator-originated 0x11 is being validated on real hardware.
        """
        lt = time.localtime()
        now_local = datetime.datetime(
            lt.tm_year, lt.tm_mon, lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec
        )
        secs = int((now_local - self._ZCL_EPOCH).total_seconds())
        dst_on = lt.tm_isdst > 0
        body = (
            secs.to_bytes(4, "little")
            + (b"\x03\x01" if dst_on else b"\x02\x00")
            + b"\x0d"
        )
        tsn = self.endpoint.device.application.get_sequence()
        self.debug(
            "fc00 0x11 SET device clock -> %s (secs_since_2000=%s, DST=%s) body=%s",
            now_local.isoformat(sep=" "),
            secs,
            "on" if dst_on else "off",
            body.hex(),
        )
        await self._send_fc00_reply(tsn, 0x11, body)

    def handle_cluster_request(
        self, hdr: foundation.ZCLHeader, args, *, dst_addressing=None
    ):
        # Any incoming device traffic (join 0x10 handshake, ~10 min 0x12 heartbeat,
        # etc.) is a chance to keep the clock synced; _maybe_auto_sync self-throttles.
        self._maybe_auto_sync()

        if hdr.command_id == 0x12:
            # Operational report -> update local temp/setpoint attributes. The
            # native wiring centre only APS-acks 0x12 (no ZCL reply), so we return
            # here without letting zigpy emit a Default Response.
            req = payload_bytes(args)
            self._handle_report(req)
            return

        if hdr.command_id == 0x11:
            # Date/time-change broadcast -> decode + cache the device clock. Sent
            # NWK-broadcast with disable-default-response; the native gateway never
            # answers it (verified natively, 2026-07), so we cache and return with no
            # ZCL reply. Other units on a native mesh set THEIR clocks from this same
            # broadcast -- that is the whole time-sync mechanism (salus_time_map.txt).
            req = payload_bytes(args)
            self._handle_time_announce(req)
            return

        if hdr.command_id == 0x25:
            # HA/ZHA "firmware update" -> device's proprietary update-check command
            # (payload byte 0x00 = no update). Salus has no standard-OTA update path;
            # the native controller only APS-acks this, so we accept it and reply
            # nothing. Returning here keeps the device joined (it sets
            # disable-default-response, so no ZCL reply is expected either way).
            return

        if ENABLE_FC00_COMMISSION_REPLY:
            reply = self._fc00_reply_for(hdr, args)
            if reply is not None:
                reply_cmd, body = reply
                # Return early so zigpy does not also emit a ZCL Default Response.
                self.create_catching_task(
                    self._send_fc00_reply(hdr.tsn, reply_cmd, body)
                )
                return

        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

    def _handle_report(self, req: bytes) -> None:
        """Parse a Salus fc00 0x12 operational report and cache its fields.

        Layout (18 bytes), decoded from captures (sniffer/salus_schedule_map.txt):
            02 01 <demand> <zone> 00 ff 00 00 00 00 00 ff
            <measured x100 LE> <setpoint x100 LE> f4 01
        e.g. `0201010600ff0000000000ffd009540bf401` -> demand 01 (heating), zone 6,
        measured 25.12 C (0x09d0), setpoint 29.00 C (0x0b54). Values are
        centi-degrees; the sensors divide by 100.
        """
        if len(req) < 16:
            return
        measured = int.from_bytes(req[12:14], "little")
        setpoint = int.from_bytes(req[14:16], "little")
        self.update_attribute(self.AttributeDefs.local_temperature.id, measured)
        self.update_attribute(self.AttributeDefs.occupied_heating_setpoint.id, setpoint)
        self.update_attribute(
            self.AttributeDefs.running_state.id, t.Bool(bool(req[2]))
        )

    def _handle_time_announce(self, req: bytes) -> None:
        """Decode a Salus fc00 0x11 date/time-change broadcast and cache the clock.

        Body (7 bytes), decoded and verified 4/4 against on-screen edits captured on
        the native ch25 net (see the "SOLVED" section of sniffer/salus_time_map.txt):
            <u32 LE: local time, seconds since 2000-01-01> <b4> <b5> 0d
        The DST flag is bytes 4-5: 0x03 0x01 = DST on, 0x02 0x00 = off. b3 is simply
        the current most-significant byte of the u32 (it looked "constant" only because
        every captured sample fell within ~1 day). e.g. `5897de3103010d` ->
        0x31de9758 = 2026-07-06 16:42:00 local, DST on.
        """
        if len(req) < 6:
            return
        secs_since_2000 = int.from_bytes(req[0:4], "little")
        dst_on = req[4] == 0x03  # 0x03/0x01 = DST on; 0x02/0x00 = off
        # Human-readable form for the log only (naive local wall time; see docstring).
        local = datetime.datetime(2000, 1, 1) + datetime.timedelta(seconds=secs_since_2000)
        self.debug(
            "fc00 0x11 date/time-change: device clock -> %s (secs_since_2000=%s, DST=%s)",
            local.isoformat(sep=" "),
            secs_since_2000,
            "on" if dst_on else "off",
        )
        self.update_attribute(self.AttributeDefs.device_time.id, secs_since_2000)
        self.update_attribute(self.AttributeDefs.dst_active.id, t.Bool(dst_on))

    def _find_wiring_centre(self):
        """Short address of a real Salus wiring centre on this network, or None.

        Identified by SIGNATURE rather than by IEEE or a hardcoded short address:
        a device (not the coordinator) exposing fc00 on endpoint 8. That is the
        KL08RF's sole endpoint, confirmed by a live ZHA interview, and it is what
        distinguishes a wiring centre from the thermostats (endpoint 9) and from
        every non-Salus device. Matching on the signature means white-labels (Cosmo
        CFK8L, ...) and a replacement unit work with no code change, and a rejoin
        that hands the KL08RF a new short address is picked up automatically --
        which a hardcoded address would not survive.

        Returns None if the lookup is unavailable or no wiring centre is present,
        and the caller then falls back to emulating one at the coordinator.
        """
        try:
            devices = self.endpoint.device.application.devices
        except AttributeError:
            return None
        for dev in devices.values():
            nwk = getattr(dev, "nwk", None)
            if not nwk:  # skips the coordinator (0x0000) and unset addresses
                continue
            ep = dev.endpoints.get(WC_EP)
            if ep is None:
                continue
            if 0xFC00 in ep.in_clusters or 0xFC00 in ep.out_clusters:
                return int(nwk)
        return None

    def _fc00_reply_for(self, hdr, args):
        """Return (reply_command_id, body_bytes) for a device fc00 command."""
        cmd = hdr.command_id
        req = payload_bytes(args)
        if cmd == 0x10:
            # First contact (request starts 0xff): we pick the session token and
            # reply state 0xa5. Later rounds: echo the device's rolling token
            # (byte 0 of its request, matching the native coordinator) and reply
            # state 0xa8. Token and state advance together off the same test.
            first = not req or req[0] == 0xFF
            token = FC00_0X81_DEFAULT_TOKEN if first else req[0]
            state = FC00_0X81_STATE_FIRST if first else FC00_0X81_STATE_NEXT
            return 0x81, bytes([token, 0x00, state]) + FC00_0X81_TAIL
        if cmd == 0x16:
            # 0x86 = <control-box index><wiring-centre short addr, LE>. Prefer a
            # REAL wiring centre on the network; fall back to the coordinator and
            # emulate one ourselves. Echo the box the device asked for (req[0]);
            # default 0x01 if absent.
            box = req[0] if req else 0x01
            if FORCE_WC_BOX is not None and FORCE_WC_BOX != box:
                self.debug(
                    "fc00 0x16: device asked for control box 0x%02x, "
                    "answering with FORCED box 0x%02x (experiment)",
                    box,
                    FORCE_WC_BOX,
                )
                box = FORCE_WC_BOX
            wc_nwk = self._find_wiring_centre()
            if wc_nwk is None:
                self.debug(
                    "fc00 0x16: no wiring centre on the network -- pointing the "
                    "device at the coordinator (0x0000) and emulating one. The "
                    "zone relay CANNOT switch in this mode."
                )
                wc_nwk = 0x0000
            else:
                self.debug(
                    "fc00 0x16: pointing the device at real wiring centre 0x%04x",
                    wc_nwk,
                )
            return 0x86, bytes([box]) + wc_nwk.to_bytes(2, "little")
        if cmd == 0x18:
            # 0x88 body is constant on-air (zone lives in the 0x18 request, not here).
            return 0x88, FC00_0X88_REPLY
        if cmd == 0x14:
            # 0x84 = 00 <zone> 00 -- echo the zone the device chose (req[1]);
            # default zone 0x06 if the request is unexpectedly short.
            zone = req[1] if len(req) >= 2 else 0x06
            return 0x84, bytes([0x00, zone, 0x00])
        return None

    async def _send_fc00_reply(self, tsn, command_id, body):
        """Emit a Salus fc00 reply with the exact on-air framing the CO10RF uses.

        Salus is non-standard: it tags the reply direction Server->Client (so the
        on-air ZCL frame control is 0x1d), which zigpy's high-level reply() cannot
        produce from a server cluster -- so we build the frame directly.
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


class SalusOta(CustomCluster, Ota):
    """Device OTA cluster that mimics the CO10RF's non-OTA reply.

    The device sends an OTA `Query Next Image Request` (cluster 0x0019) during
    commissioning. A native CO10RF is not an OTA server, so it answers with a
    plain ZCL **Default Response, status Invalid Field (0x85)**; ~1 s later the
    device advances to the second 0x10 round and the wiring-centre bind. Stock
    ZHA instead answers as a real OTA server (`Query Next Image Response,
    No Image Available`), after which the device stalls and never advances
    (observed in capture_wcemul_ch20.pcap: it goes silent after the OTA reply).

    This request is dispatched onto the device's own EP9 OTA cluster via the
    same sender-endpoint routing described in SalusBasic, so we can answer it
    here. We reply with the CO10RF's Default Response instead of letting zigpy's
    OTA server logic run.
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


class SalusBasic(CustomCluster, Basic):
    """Device Basic cluster that answers the post-0x81 coordinator-identity check.

    After the fc00 0x10->0x81 handshake the SQ610RFNH reads **Basic Model
    Identifier (0x0005)** from what it believes is the coordinator (it sends the
    read to coordinator EP1) and refuses to stay joined unless the answer is a
    Salus controller model string. A native CO10RF answers "SAL6DC1"; a stock
    ZHA coordinator answers "Unsupported Attribute (0x86)", so the device sends
    NWK Leave (rejoin=False) ~0.1 s later and resets (confirmed by decrypted
    captures: verify_ch20.pcap vs capture_salus_goldref_ch25.pcap).

    Why this fix lives on the *device* quirk and not a coordinator quirk:
    zigpy processes an incoming request on the *sender's* device object and
    dispatches it by the sender's endpoint (`packet.src_ep`), not the addressed
    destination endpoint (see zigpy `application.packet_received` ->
    `Device.packet_received` -> `Device._find_zcl_cluster`). So the device's read
    of the coordinator's model is actually answered by *this* device's own
    Basic cluster on endpoint 9 (the on-air reply carries source endpoint 9, not
    the coordinator's endpoint 1 -- exactly what the capture shows). zigpy builds
    that reply from `handle_read_attribute_<name>()`, ignoring the attribute
    cache, so we override the method here to return the expected Salus model.
    """

    def handle_read_attribute_model(self) -> t.CharacterString:
        # MUST be a zigpy string type, not a bare `str`: zigpy 2.x serializes the
        # read-attributes reply by calling `.serialize()` on the value, which a
        # plain str lacks ("'str' object has no attribute 'serialize'"). (A bare
        # str worked on zigpy 1.5.1, where the value was coerced -- not on 2.x.)
        return t.CharacterString(SALUS_COORD_MODEL)


class SalusFC09Cluster(CustomCluster):
    """Salus/Computime proprietary cluster 0xFC09.

    Low-frequency gateway config/status channel (dev EP9 <-> coord EP1); on the
    native CO10RF it carries mode/config sync (standard profile-wide Report
    Attributes, attr 0x0000). The only value ever observed for attr 0x0000 is 2,
    reported when entering manual/permanent hold (incl. disabling the schedule);
    schedule/standby transitions never report. This lines up with the UGE600
    gateway datamodel's `HoldType` field (also 2 = permanent/manual hold; issue
    #1524, sniffer/salus_uge600_datamodel_map.txt), so a schedule-running device
    likely reports a different, as-yet-uncaptured value here. No entity is built,
    but the attribute is declared so it can be read manually from the HA "Manage
    Zigbee device" UI (untested whether an active read returns a distinct value
    while a schedule is running -- the device is sleepy, so the read is delivered
    on its next ~7 s poll).
    """

    cluster_id = 0xFC09
    ep_attribute = "salus_fc09"
    name = "Salus Manufacturer FC09"
    manufacturer_id_override = COMPUTIME

    class AttributeDefs(BaseAttributeDefs):
        operating_mode: Final = ZCLAttributeDef(
            id=0x0000, type=t.uint8_t, access="rp", manufacturer_code=COMPUTIME
        )


# --- battery-level reverse-engineering: CLOSED (no over-air source), 2026-07-04 ---
# The SQ610RFNH is a battery-powered sleepy end device (node descriptor
# power_source = "Battery or Unknown"), but it exposes NO battery level over
# Zigbee -- proven from every angle (decrypted ch20 + native ch25 captures):
#   * It does NOT advertise a standard PowerConfiguration cluster (0x0001) on its
#     only endpoint (EP9). We ADDED one as a probe and it was rejected: reads of
#     BatteryVoltage(0x0020)/BatteryPercentageRemaining(0x0021) return None and
#     ZHA reconfigure gets UNSUP_CLUSTER_COMMAND -- the device has no 0x0001.
#   * On ZHA the device transmits ONLY the fc00 0x12 operational report (prompt on
#     a setpoint change + a ~10.25 min heartbeat; a 45-min sniff caught 7). Its
#     18-byte body is fully accounted for
#     (02 01 [demand][zone] 00ff0000000000ff [meas LE][set LE] f4 01) -- no byte
#     tracks battery. No fc09 battery attribute exists either.
#   * The device sends NO cluster-0x0001 frame in ANY native KL08RF/CO10RF capture
#     -- so it doesn't report battery even to its own gateway. (A 20.5% report seen
#     once on ch20 was an UNRELATED device 0x1e9a on EP1, 7.1 V -- not the Salus.)
#   * The UGE600 gateway's own `readall` datamodel (issue #1524, decoded in
#     sniffer/salus_uge600_datamodel_map.txt) likewise contains NO battery field for
#     this device -- so even the gateway path has no battery source to surface.
# Root cause: like setpoint-write/schedule/mode, battery is only surfaced via the
# native UGE600 gateway's proprietary path, which rejects our reads and which we
# cannot reference. => NO battery entity is possible. Do not re-add a 0x0001
# cluster. (Only remaining theoretical option: a multi-week battery-drain diff of
# fc00/fc09 traffic to spot a slow-moving byte -- deferred, very low confidence.)


# --- v2 registration -------------------------------------------------------
# Match on manufacturer/model and swap in the Salus custom clusters. The device's
# other clusters (Identify/Time/Diagnostic) are left untouched -- a full, faithful
# cluster set gives the best "stays joined" behaviour (a minimal-interview trim was
# tested and made no difference). The 0x10 byte-2 gate flips to 0x01 only once the
# device sees a ROUTER neighbour via NWK Link Status; with a mains router in range
# the device now commissions FULLY and reports operationally on ZHA -- confirmed
# 2026-07-04, see the "COMMISSIONING CONFIRMED WORKING" note in the module docstring.
(
    QuirkBuilder(SALUS, SALUS_MODEL)
    # Also apply to the base (non-NH) SQ610RF -- same 0x1078 family / fc00 grammar.
    .applies_to(SALUS, SALUS_MODEL_BASE)
    # ...and under manufacturer "Computime", which this ecosystem reports at
    # least as often as "SALUS" (see COMPUTIME_MFR above): covers a base SQ610RF
    # or a firmware revision that reports the raw Computime vendor string.
    .applies_to(COMPUTIME_MFR, SALUS_MODEL)
    .applies_to(COMPUTIME_MFR, SALUS_MODEL_BASE)
    .replaces(SalusBasic, endpoint_id=THERMOSTAT_EP)
    .replaces(SalusFC09Cluster, endpoint_id=THERMOSTAT_EP)
    .replaces(SalusOta, endpoint_id=THERMOSTAT_EP, cluster_type=ClusterType.Client)
    # fc00 is present as BOTH an input and an output cluster -- replace both.
    .replace_cluster_occurrences(SalusFC00Cluster)
    # Read-only entities populated from the fc00 0x12 operational report. (Setpoint
    # is read-only for now: the setpoint-WRITE command is not yet known -- once it is,
    # this becomes a .number()/climate.)
    .sensor(
        attribute_name=SalusFC00Cluster.AttributeDefs.local_temperature.name,
        cluster_id=SalusFC00Cluster.cluster_id,
        endpoint_id=THERMOSTAT_EP,
        divisor=100,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        fallback_name="Temperature",
    )
    .sensor(
        attribute_name=SalusFC00Cluster.AttributeDefs.occupied_heating_setpoint.name,
        cluster_id=SalusFC00Cluster.cluster_id,
        endpoint_id=THERMOSTAT_EP,
        divisor=100,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="heating_setpoint",
        fallback_name="Setpoint",
    )
    # Heating/idle indicator from the device's own authoritative heat-demand byte
    # (byte 2 of the 0x12 report; see _handle_report) -- NOT derived from
    # measured<setpoint. Confirmed against the 45-min ch20 capture (2026-07-04):
    # demand=1 while calling for heat, 0 once satisfied. Stands in for the climate
    # hvac_action, which we can't offer as a real climate entity because the
    # device's only Thermostat cluster (0x0201) is a non-functional stub.
    .binary_sensor(
        attribute_name=SalusFC00Cluster.AttributeDefs.running_state.name,
        cluster_id=SalusFC00Cluster.cluster_id,
        endpoint_id=THERMOSTAT_EP,
        device_class=BinarySensorDeviceClass.RUNNING,
        fallback_name="Heating",
    )
    # Device clock + DST, decoded from the fc00 0x11 broadcast the thermostat emits
    # when its Date/Time is edited on-screen (see _handle_time_announce). DIAGNOSTIC:
    # device_time is raw seconds since 2000-01-01 in the device's LOCAL wall time -- no
    # timezone is transmitted, so it is deliberately NOT presented as an absolute
    # timestamp. Only populated after the device sends a 0x11 (i.e. after a clock edit);
    # blank until then. Representation is intentionally faithful/minimal -- easy to
    # reshape (e.g. a template datetime) once verified on real hardware.
    .sensor(
        attribute_name=SalusFC00Cluster.AttributeDefs.device_time.name,
        cluster_id=SalusFC00Cluster.cluster_id,
        endpoint_id=THERMOSTAT_EP,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="device_time",
        fallback_name="Device clock (seconds since 2000)",
    )
    .binary_sensor(
        attribute_name=SalusFC00Cluster.AttributeDefs.dst_active.name,
        cluster_id=SalusFC00Cluster.cluster_id,
        endpoint_id=THERMOSTAT_EP,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="dst_active",
        fallback_name="Daylight saving",
    )
    # EXPERIMENTAL write path: a button that pushes HA's current local time to the
    # device as an fc00 0x11 (see SalusFC00Cluster._set_clock_to_now). On a native
    # mesh this is how one thermostat sets every other unit's clock; here it lets ZHA
    # keep the SQ610RF's internal clock (and thus its local schedule) correct with no
    # Salus gateway. Whether the device honours a coordinator-sent 0x11 is being
    # validated on hardware -- safe until pressed; a wrong clock is undone by editing
    # the time on the thermostat screen.
    .command_button(
        SalusFC00Cluster.ServerCommandDefs.set_clock_to_ha_time.name,
        SalusFC00Cluster.cluster_id,
        endpoint_id=THERMOSTAT_EP,
        translation_key="set_clock_to_ha_time",
        fallback_name="Set clock to HA time",
    )
    .add_to_registry()
)
