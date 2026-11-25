"""Quirk for the Aqara Power Plug H2 EU (RGB), SP-P05D, model lumi.plug.aeu005.

Three problems are fixed:

1. Power is shown 10x too low.
   The plug reports ElectricalMeasurement.active_power (0x050B) in whole
   watts, but advertises ac_power_divisor (0x0605) = 10. ZHA divides the
   reading by 10, so a ~1000 W heater shows up as ~100 W. The quirk pins
   ac_power_multiplier and ac_power_divisor to 1.

2. Energy (kWh) never updates.
   The plug does not send attribute reports at all (it rejects the reporting
   configuration and pushes nothing on 0xFCC0); it only answers reads. ZHA
   already polls active_power every 30 s for this device, but nothing reads
   Metering.current_summ_delivered (0x0000), so the energy sensor keeps the
   value it read at startup. The value itself is correct when read
   (multiplier 1, divisor 1000 -> kWh). The quirk reads it right after a
   power poll, at most once per SUMMATION_REFRESH_INTERVAL seconds.

3. Energy (kWh) occasionally drops to 0.
   Every few hours a read of current_summ_delivered comes back as 0, and the
   next read returns the real counter again. The energy sensor is
   total_increasing, so Home Assistant treats each 0 as a meter reset and
   counts the whole counter again when it comes back (a plug at ~30 kWh
   added ~120 kWh to one day's statistics). The quirk ignores a 0 once a
   non-zero value is known; the counter never legitimately returns to 0
   while the device stays paired.

Verified on firmware 0x00000015:
- heater switched on: grid import rose by ~1055 W; the plug reported raw
  active_power 997 (shown as 99.7 W without the quirk, 997 W with it);
- current_summ_delivered read 2014 -> 2413 over ~25 min at ~982 W
  (0.399 kWh, expected ~0.41 kWh).

Note: the device identifies as manufacturer "Aqara" (not "LUMI"), so the
existing Xiaomi/LUMI quirks do not match it.
"""

from __future__ import annotations

import asyncio
import logging
import time

from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster

_LOGGER = logging.getLogger(__name__)

SUMMATION_REFRESH_INTERVAL = 60  # seconds


class AqaraH2PlugElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """ElectricalMeasurement with corrected scaling and energy refresh."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 1,
    }

    def __init__(self, *args, **kwargs):
        """Initialize the cluster."""
        super().__init__(*args, **kwargs)
        self._last_summation_refresh: float | None = None
        self._summation_task: asyncio.Task | None = None

    def _update_attribute(self, attrid, value):
        """Refresh the energy counter after an active_power update."""
        super()._update_attribute(attrid, value)

        if attrid != ElectricalMeasurement.AttributeDefs.active_power.id:
            return
        if self._summation_task is not None and not self._summation_task.done():
            return

        now = time.monotonic()
        if (
            self._last_summation_refresh is not None
            and now - self._last_summation_refresh < SUMMATION_REFRESH_INTERVAL
        ):
            return

        self._last_summation_refresh = now
        self._summation_task = asyncio.get_running_loop().create_task(
            self._refresh_summation()
        )

    async def _refresh_summation(self) -> None:
        """Read current_summ_delivered from the Metering cluster."""
        try:
            await self.endpoint.smartenergy_metering.read_attributes(
                [Metering.AttributeDefs.current_summ_delivered.id]
            )
        except Exception as exc:  # noqa: BLE001 - never break the device on a poll
            _LOGGER.debug("Failed to refresh current_summ_delivered: %s", exc)


class AqaraH2PlugMetering(CustomCluster, Metering):
    """Metering that drops spurious zero readings of the energy counter."""

    def _update_attribute(self, attrid, value):
        """Ignore a current_summ_delivered of 0 once a non-zero value is known."""
        if attrid == Metering.AttributeDefs.current_summ_delivered.id and not value:
            previous = self._attr_cache.get(attrid)
            if previous:
                _LOGGER.debug(
                    "Ignoring spurious current_summ_delivered=0 (last value %s)",
                    previous,
                )
                return
        super()._update_attribute(attrid, value)


(
    QuirkBuilder("Aqara", "lumi.plug.aeu005")
    .replaces(AqaraH2PlugElectricalMeasurement)
    .replaces(AqaraH2PlugMetering)
    .add_to_registry()
)
