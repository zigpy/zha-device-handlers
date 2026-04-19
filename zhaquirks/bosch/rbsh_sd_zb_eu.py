"""Device handler for Bosch RBSH-SD-ZB-EU (aka BSD-2) smoke detector + indoor siren.

The BSD-2 sends standard IAS Zone status notifications for smoke and tamper,
but the two "manually sound the alarm" features - smoke test and
burglar-alarm siren - are exposed over the IAS Zone (0x0500) cluster via a
Bosch manufacturer-specific ``control_alarm`` command (id 0x80), not via
any ZCL-standard attribute or command. The device accepts

    control_alarm(alarm_mode, alarm_timeout)

with manufacturer code ``0x1209`` (Robert Bosch GmbH), where ``alarm_mode``
selects smoke (``0x00``) or burglar (``0x01``) and ``alarm_timeout`` is a
timeout in seconds (``0x00`` stops, ``0xF0`` = 240 s is what the Bosch
firmware and zigbee2mqtt use for "arm").

Because Home Assistant drives switches via writes to ZCL attributes, this
quirk surfaces *synthetic* manufacturer-specific attributes on the IAS
Zone cluster and translates writes to them into ``control_alarm`` frames.
The attributes do not exist on the wire; their values live only in the
zigpy cluster cache and are primed to ``0`` when the cluster is
constructed. That gives HA four ordinary switch entities per detector:

    switch.<device>_manual_smoke_alarm       unicast arm - this device only
    switch.<device>_manual_burglar_alarm     unicast arm - this device only
    switch.<device>_broadcast_smoke_alarm    mesh-wide arm - every BSD-2
    switch.<device>_broadcast_burglar_alarm  mesh-wide arm - every BSD-2

The ``manual_*`` switches send a normal unicast ``control_alarm`` to the
specific device. The ``broadcast_*`` switches emit the same frame as a
Zigbee broadcast (destination ``0xFFFF`` / endpoint ``0xFF``) reaching
every BSD-2 on the mesh, including sleepy battery-powered ones, matching
zigbee2mqtt's ``broadcast_alarms`` feature. Because Bosch's firmware and
herdsman send the broadcast twice with a 4-second gap so sleepy detectors
that miss the first packet still arm on the second, so does this quirk.

Semantics:

* ``True`` -> ``control_alarm(mode, 240)``; ``False`` -> ``control_alarm(mode, 0)``.
* The hardware can only run one alarm mode at a time, so arming smoke
  flips the burglar sibling off in the cache (and vice versa) without a
  second command.
* Broadcast switches additionally synchronize their cached state across
  every live ``BoschIasZoneCluster`` instance on the controller, so
  flipping the switch on one BSD-2 is reflected on the other four (HA
  tracks the mesh-wide state, not per-device intent, for broadcasts).
* The device does not report alarm state back, so all switch state is
  purely local; it will go stale if the 240 s auto-stop on the device
  fires without the user flipping the switch off. Flipping it off in HA
  re-syncs by sending ``control_alarm(mode, 0)``.

Reference implementation (zigbee-herdsman-converters):
    https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/src/devices/bosch.ts
"""

from __future__ import annotations

import asyncio
from typing import Any, Final
import weakref

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import ZCLAttributeDef, ZCLCommandDef

BOSCH_MANUFACTURER_CODE = 0x1209

# IAS Zone command id of the Bosch "control_alarm" manufacturer-specific command.
CONTROL_ALARM_CMD_ID = 0x80

# Synthetic manufacturer-specific IAS Zone attribute ids backing the HA switches.
# These attributes do not exist on the wire; they are cache-only handles that
# the quirk translates into control_alarm commands in ``write_attributes``.
MANUAL_SMOKE_ALARM_ATTR_ID = 0xF000
MANUAL_BURGLAR_ALARM_ATTR_ID = 0xF001
BROADCAST_SMOKE_ALARM_ATTR_ID = 0xF002
BROADCAST_BURGLAR_ALARM_ATTR_ID = 0xF003

# Timeout value (in seconds) the Bosch firmware and zigbee2mqtt use when
# arming the siren; writing 0 stops a running alarm.
ALARM_TIMEOUT_SECONDS = 240

# Sleepy end-device broadcasts are routinely lost; Bosch's firmware and
# zigbee2mqtt's boschSmokeAlarmExtend emit every broadcast twice with a 4 s
# gap so BSD-2s that miss the first packet still arm on the second.
INTER_BROADCAST_DELAY_S = 4.0

# Frame constants for the broadcast path.
HA_PROFILE_ID = 0x0104
BROADCAST_SRC_ENDPOINT = 1
BROADCAST_DST_ENDPOINT = 0xFF
BROADCAST_RADIUS = 30

_MANUAL_ATTR_IDS: Final = frozenset(
    {MANUAL_SMOKE_ALARM_ATTR_ID, MANUAL_BURGLAR_ALARM_ATTR_ID}
)
_BROADCAST_ATTR_IDS: Final = frozenset(
    {BROADCAST_SMOKE_ALARM_ATTR_ID, BROADCAST_BURGLAR_ALARM_ATTR_ID}
)
_SYNTHETIC_ATTR_IDS: Final = _MANUAL_ATTR_IDS | _BROADCAST_ATTR_IDS

# Each synthetic attribute is paired with its opposite on the same device
# (smoke <-> burglar, unicast <-> unicast and broadcast <-> broadcast).
_SIBLING_ATTR_ID: Final[dict[int, int]] = {
    MANUAL_SMOKE_ALARM_ATTR_ID: MANUAL_BURGLAR_ALARM_ATTR_ID,
    MANUAL_BURGLAR_ALARM_ATTR_ID: MANUAL_SMOKE_ALARM_ATTR_ID,
    BROADCAST_SMOKE_ALARM_ATTR_ID: BROADCAST_BURGLAR_ALARM_ATTR_ID,
    BROADCAST_BURGLAR_ALARM_ATTR_ID: BROADCAST_SMOKE_ALARM_ATTR_ID,
}

# Which on-wire alarm_mode each synthetic attribute maps to.
_ATTR_ID_TO_ALARM_MODE: Final[dict[int, int]] = {
    MANUAL_SMOKE_ALARM_ATTR_ID: 0x00,
    MANUAL_BURGLAR_ALARM_ATTR_ID: 0x01,
    BROADCAST_SMOKE_ALARM_ATTR_ID: 0x00,
    BROADCAST_BURGLAR_ALARM_ATTR_ID: 0x01,
}

# Weak set of all live ``BoschIasZoneCluster`` instances so a broadcast
# write on one detector can mirror its cached state onto every other BSD-2.
_LIVE_CLUSTERS: weakref.WeakSet[BoschIasZoneCluster] = weakref.WeakSet()


class BoschAlarmMode(t.enum8):
    """Alarm mode selector for the Bosch control_alarm command."""

    Smoke = 0x00
    Burglar = 0x01


class BoschIasZoneCluster(CustomCluster, IasZone):
    """IAS Zone cluster with Bosch's manual-alarm command + unicast/broadcast switches."""

    class AttributeDefs(IasZone.AttributeDefs):
        """Bosch manufacturer-specific synthetic attributes backing the HA switches."""

        manual_smoke_alarm: Final = ZCLAttributeDef(
            id=MANUAL_SMOKE_ALARM_ATTR_ID,
            type=t.Bool,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
            access="rw",
        )

        manual_burglar_alarm: Final = ZCLAttributeDef(
            id=MANUAL_BURGLAR_ALARM_ATTR_ID,
            type=t.Bool,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
            access="rw",
        )

        broadcast_smoke_alarm: Final = ZCLAttributeDef(
            id=BROADCAST_SMOKE_ALARM_ATTR_ID,
            type=t.Bool,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
            access="rw",
        )

        broadcast_burglar_alarm: Final = ZCLAttributeDef(
            id=BROADCAST_BURGLAR_ALARM_ATTR_ID,
            type=t.Bool,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
            access="rw",
        )

    class ServerCommandDefs(IasZone.ServerCommandDefs):
        """Bosch manufacturer-specific IAS Zone commands."""

        control_alarm: Final = ZCLCommandDef(
            id=CONTROL_ALARM_CMD_ID,
            schema={
                "alarm_mode": BoschAlarmMode,
                "alarm_timeout": t.uint8_t,
            },
            is_manufacturer_specific=True,
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Prime the synthetic attribute cache so every switch defaults to off."""
        super().__init__(*args, **kwargs)
        _LIVE_CLUSTERS.add(self)
        for attr_id in _SYNTHETIC_ATTR_IDS:
            self._update_attribute(attr_id, 0)

    def _resolve_synthetic_attr_id(self, attr: Any) -> int | None:
        """Return the synthetic attribute id for ``attr`` (name / id / def), or None."""
        if isinstance(attr, ZCLAttributeDef):
            attr_id = attr.id
        elif isinstance(attr, str):
            attr_def = self.attributes_by_name.get(attr)
            attr_id = attr_def.id if attr_def else None
        else:
            try:
                attr_id = int(attr)
            except (TypeError, ValueError):
                attr_id = None
        if attr_id in _SYNTHETIC_ATTR_IDS:
            return attr_id
        return None

    async def _broadcast_control_alarm(self, alarm_mode: int, timeout: int) -> None:
        """Emit a single ``control_alarm`` frame as a mesh-wide Zigbee broadcast."""
        app = self.endpoint.device.application
        tsn = app.get_sequence()
        header = foundation.ZCLHeader(
            frame_control=foundation.FrameControl(
                frame_type=foundation.FrameType.CLUSTER_COMMAND,
                is_manufacturer_specific=True,
                direction=foundation.Direction.Client_to_Server,
                disable_default_response=True,
                reserved=0,
            ),
            manufacturer=BOSCH_MANUFACTURER_CODE,
            tsn=tsn,
            command_id=CONTROL_ALARM_CMD_ID,
        )
        data = header.serialize() + bytes([alarm_mode & 0xFF, timeout & 0xFF])
        await app.broadcast(
            profile=HA_PROFILE_ID,
            cluster=IasZone.cluster_id,
            src_ep=BROADCAST_SRC_ENDPOINT,
            dst_ep=BROADCAST_DST_ENDPOINT,
            grpid=0,
            radius=BROADCAST_RADIUS,
            sequence=tsn,
            data=data,
            broadcast_address=t.BroadcastAddress.ALL_DEVICES,
        )

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        manufacturer: int | None = None,
        **kwargs: Any,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Route writes of synthetic attrs to unicast or broadcast control_alarm frames."""
        remaining: dict[str | int | ZCLAttributeDef, Any] = {}
        synthetic_writes: list[tuple[int, bool]] = []

        for attr, value in attributes.items():
            synth_id = self._resolve_synthetic_attr_id(attr)
            if synth_id is None:
                remaining[attr] = value
            else:
                synthetic_writes.append((synth_id, bool(int(value))))

        for attr_id, on in synthetic_writes:
            alarm_mode = BoschAlarmMode(_ATTR_ID_TO_ALARM_MODE[attr_id])
            alarm_timeout = ALARM_TIMEOUT_SECONDS if on else 0

            if attr_id in _BROADCAST_ATTR_IDS:
                # Send twice 4 s apart to match Bosch firmware / z2m so sleepy
                # BSD-2s that miss the first broadcast still pick up the second.
                await self._broadcast_control_alarm(alarm_mode, alarm_timeout)
                await asyncio.sleep(INTER_BROADCAST_DELAY_S)
                await self._broadcast_control_alarm(alarm_mode, alarm_timeout)
                _sync_broadcast_state_across_mesh(attr_id, 1 if on else 0)
            else:
                await self.control_alarm(alarm_mode, alarm_timeout)
                self._update_attribute(attr_id, 1 if on else 0)
                if on:
                    self._update_attribute(_SIBLING_ATTR_ID[attr_id], 0)

        if remaining:
            return await super().write_attributes(
                remaining, manufacturer=manufacturer, **kwargs
            )
        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


def _sync_broadcast_state_across_mesh(attr_id: int, value: int) -> None:
    """Mirror the broadcast attr value onto every live ``BoschIasZoneCluster``.

    The BSD-2 firmware can only run one alarm mode at a time. Arming one
    broadcast flavour therefore implicitly stops the other across the whole
    mesh, and a stop for one flavour leaves the other's cached state alone.
    """
    sibling = _SIBLING_ATTR_ID[attr_id]
    for cluster in list(_LIVE_CLUSTERS):
        cluster._update_attribute(attr_id, value)
        if value:
            cluster._update_attribute(sibling, 0)


(
    QuirkBuilder("Bosch", "RBSH-SD-ZB-EU")
    .applies_to("BOSCH", "RBSH-SD-ZB-EU")
    .replaces(BoschIasZoneCluster)
    .switch(
        attribute_name=BoschIasZoneCluster.AttributeDefs.manual_smoke_alarm.name,
        cluster_id=BoschIasZoneCluster.cluster_id,
        translation_key="manual_smoke_alarm",
        fallback_name="Manual smoke alarm",
    )
    .switch(
        attribute_name=BoschIasZoneCluster.AttributeDefs.manual_burglar_alarm.name,
        cluster_id=BoschIasZoneCluster.cluster_id,
        translation_key="manual_burglar_alarm",
        fallback_name="Manual burglar alarm",
    )
    .switch(
        attribute_name=BoschIasZoneCluster.AttributeDefs.broadcast_smoke_alarm.name,
        cluster_id=BoschIasZoneCluster.cluster_id,
        translation_key="broadcast_smoke_alarm",
        fallback_name="Broadcast smoke alarm",
    )
    .switch(
        attribute_name=BoschIasZoneCluster.AttributeDefs.broadcast_burglar_alarm.name,
        cluster_id=BoschIasZoneCluster.cluster_id,
        translation_key="broadcast_burglar_alarm",
        fallback_name="Broadcast burglar alarm",
    )
    .add_to_registry()
)
