"""Device handler for Tuya TS0202 PIR motion sensors.

Some cheap Tuya TS0202 clones (``_TZ3000_bsvqrxru`` / HW500A is the reference
hardware here) expose only an IAS Zone server endpoint and need two small
tweaks before Home Assistant renders a useful motion entity:

1. The device never reports its ``zone_type``, so without a quirk ZHA defaults
   the generated binary_sensor to ``device_class: opening`` (contact switch).
   The quirk pins ``zone_type = Motion_Sensor`` so the entity materialises as
   ``device_class: motion`` without waiting for a ``read_attributes``
   roundtrip.

2. These firmwares need the "Tuya spell" (a read of Basic cluster attributes
   ``0x0004, 0x0000, 0x0001, 0x0005, 0x0007, 0xFFFE``) before they'll emit ZCL
   traffic at all. The PIR front-end keeps blinking its red LED locally on
   motion but the radio stays silent until the spell is cast. ``TuyaQuirkBuilder
   .tuya_enchantment()`` handles that at device init.

On top of that we auto-reset ``zone_status`` after a configurable client-side
timeout. The HW500A firmware has a hard-coded ~65 second internal keep_time
that cannot be changed over Zigbee (the ``_TZ3000_bsvqrxru`` fingerprint
intentionally has no ``keep_time`` exposed in zigbee2mqtt for that reason),
so exposing a writable ``motion_timeout`` Number entity is the only knob we
can realistically offer. The same auto-clear also covers firmwares that forget
to send a "no motion" status change altogether - z2m's
``fz.ias_occupancy_alarm_1_with_timeout`` does the equivalent on that side.

The quirk also swaps the stock Power cluster for
``TuyaPowerConfigurationCluster2AAA`` (these units run off 2x AAA) and removes
the vestigial OnOff client cluster that ZHA would otherwise turn into a second,
permanently-off binary_sensor.
"""

from __future__ import annotations

from typing import Any, Final

from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant import UnitOfTime
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import MotionWithReset
from zhaquirks.tuya import TuyaPowerConfigurationCluster2AAA
from zhaquirks.tuya.builder import TuyaQuirkBuilder

#: Quirk-local attribute id used to expose the writable auto-clear timer.
#: Sits in the 0xFFxx reserved range so it cannot collide with any real
#: IAS Zone attribute the device might grow in a future firmware.
MOTION_TIMEOUT_ATTR_ID: Final = 0xFFF0

DEFAULT_MOTION_TIMEOUT_S: Final = 90
MIN_MOTION_TIMEOUT_S: Final = 5
MAX_MOTION_TIMEOUT_S: Final = 900

#: Bits that indicate "motion present" in a zone_status report.
#: Alarm_2 is included because some TS0202 firmwares use it alongside Alarm_1.
ALARM_BITS: Final = IasZone.ZoneStatus.Alarm_1 | IasZone.ZoneStatus.Alarm_2


class TS0202MotionCluster(MotionWithReset):
    """IAS Zone cluster for TS0202 HW500A-family PIR motion sensors.

    Adds three things on top of the base ``MotionWithReset``:

    * Pins ``zone_type = Motion_Sensor`` so the binary_sensor renders as
      ``device_class: motion`` without waiting for the device to answer.
    * Schedules the auto-clear timer for *both* ``zone_status_change_notification``
      commands (inherited from ``MotionWithReset``) and ``zone_status``
      attribute reports, since these TS0202 clones mix the two paths across
      firmware revisions.
    * Exposes a synthetic, writable ``motion_timeout`` attribute (seconds)
      that backs a Number entity. Writing it updates the auto-clear timer
      live; no Zigbee frames are sent to the device since this firmware has
      no runtime-configurable keep_time.
    """

    class AttributeDefs(IasZone.AttributeDefs):
        """Extend IAS Zone attrs with a quirk-local ``motion_timeout``."""

        motion_timeout: Final = foundation.ZCLAttributeDef(
            id=MOTION_TIMEOUT_ATTR_ID,
            type=t.uint16_t,
            is_manufacturer_specific=False,
        )

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Motion_Sensor,
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        super().__init__(*args, **kwargs)
        self.reset_s: int = DEFAULT_MOTION_TIMEOUT_S
        self._update_attribute(MOTION_TIMEOUT_ATTR_ID, DEFAULT_MOTION_TIMEOUT_S)

    def _update_attribute(self, attrid: int | t.uint16_t, value: Any) -> None:
        """Schedule auto-clear on zone_status reports that carry an alarm bit.

        ``MotionWithReset.handle_cluster_request`` already covers the command
        path (``zone_status_change_notification``). This override covers the
        attribute-report path so we don't care which of the two a given
        firmware chooses to emit.
        """
        if (
            attrid == IasZone.AttributeDefs.zone_status.id
            and isinstance(value, int)
            and value & ALARM_BITS
        ):
            if self._timer_handle:
                self._timer_handle.cancel()
            self._timer_handle = self._loop.call_later(self.reset_s, self._turn_off)
        super()._update_attribute(attrid, value)

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer: int | None = None,
    ) -> list:
        """Intercept writes to the synthetic ``motion_timeout`` attribute.

        The Number entity calls ``write_attributes({"motion_timeout": N})``.
        Since the firmware has no runtime-configurable keep_time, we keep the
        value quirk-local: clamp + cache + use it on the next motion event.
        Any other attribute writes fall through to the device unchanged.
        """
        local: dict[str | int, Any] = {}
        remote: dict[str | int, Any] = {}
        for key, value in attributes.items():
            if self._is_motion_timeout_key(key):
                local[key] = value
            else:
                remote[key] = value

        for value in local.values():
            clamped = max(
                MIN_MOTION_TIMEOUT_S,
                min(MAX_MOTION_TIMEOUT_S, int(value)),
            )
            self.reset_s = clamped
            self._update_attribute(MOTION_TIMEOUT_ATTR_ID, clamped)
            self.debug(
                "%s - motion_timeout set to %ss (was request for %s)",
                self.endpoint.device.ieee,
                clamped,
                value,
            )

        if remote:
            return await super().write_attributes(remote, manufacturer=manufacturer)

        return [
            [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
        ]

    @staticmethod
    def _is_motion_timeout_key(key: str | int | foundation.ZCLAttributeDef) -> bool:
        """Return True if ``key`` targets the synthetic motion_timeout attr."""
        if isinstance(key, foundation.ZCLAttributeDef):
            return key.id == MOTION_TIMEOUT_ATTR_ID
        if isinstance(key, str):
            return key == "motion_timeout"
        try:
            return int(key) == MOTION_TIMEOUT_ATTR_ID
        except (TypeError, ValueError):
            return False


(
    TuyaQuirkBuilder("_TZ3000_bsvqrxru", "TS0202")
    .replaces(TS0202MotionCluster)
    .replaces(TuyaPowerConfigurationCluster2AAA)
    .removes(cluster_id=OnOff.cluster_id, cluster_type=ClusterType.Client)
    .number(
        attribute_name=TS0202MotionCluster.AttributeDefs.motion_timeout.name,
        cluster_id=IasZone.cluster_id,
        min_value=MIN_MOTION_TIMEOUT_S,
        max_value=MAX_MOTION_TIMEOUT_S,
        step=5,
        unit=UnitOfTime.SECONDS,
        entity_type=EntityType.CONFIG,
        translation_key="motion_timeout",
        fallback_name="Motion clear timeout",
    )
    .tuya_enchantment()
    .skip_configuration()
    .add_to_registry()
)
