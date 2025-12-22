"""Quirk for Bosch RFDL-ZB-MS TriTech motion sensor.

This quirk adds a virtual occupancy cluster with configurable timeout
to ensure reliable motion clear events, addressing an issue where the
hardware IAS Zone cluster intermittently fails to send clear notifications.

https://github.com/zigpy/zha-device-handlers
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl import foundation

from zhaquirks import Bus, LocalDataCluster, PowerConfigurationCluster
from zhaquirks.bosch import BOSCH
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    MOTION_EVENT,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

_LOGGER = logging.getLogger(__name__)

MOTION_TIMEOUT_S = 120
STUCK_MOTION_THRESHOLD_S = (
    30  # If occupied longer than this when clear arrives, treat as new motion
)
MOTION_CLEAR_EVENT = "motion_clear"


class BoschPowerConfiguration(PowerConfigurationCluster):
    """Power configuration with voltage-to-percentage conversion for Bosch sensors."""

    MIN_VOLTS = 1.9  # Minimum voltage (0%)
    MAX_VOLTS = 3.0  # Maximum voltage (100%)


class BoschIasZone(CustomCluster, IasZone):
    """IAS Zone cluster that forwards motion events to the virtual occupancy cluster."""

    cluster_id = IasZone.cluster_id

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: None = None,
    ) -> None:
        """Handle zone status change notifications."""
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

        if hdr.command_id == 0:  # Zone status change notification
            zone_status = args[0] if args else 0
            alarm1 = bool(zone_status & 0x01)

            _LOGGER.debug(
                "Bosch RFDL-ZB-MS zone status: 0x%04X (motion=%s)",
                zone_status,
                alarm1,
            )

            if alarm1:
                self.endpoint.device.motion_bus.listener_event(MOTION_EVENT)
            else:
                # Clear event - let occupancy cluster decide if this is a stuck sensor reset
                self.endpoint.device.motion_bus.listener_event(MOTION_CLEAR_EVENT)


class BoschOccupancy(LocalDataCluster, OccupancySensing):
    """Virtual occupancy cluster with guaranteed timeout.

    Provides a software-based motion timeout that clears occupancy
    after MOTION_TIMEOUT_S seconds of no motion, regardless of whether
    the hardware sends a clear event.
    """

    cluster_id = OccupancySensing.cluster_id

    _CONSTANT_ATTRIBUTES = {
        0x0010: 0,  # PIR sensor type
    }

    def __init__(self, *args, **kwargs):
        """Initialize cluster and subscribe to motion bus."""
        super().__init__(*args, **kwargs)
        self._update_attribute(0x0000, 0)  # occupancy = unoccupied
        self.endpoint.device.motion_bus.add_listener(self)
        self._timer_handle = None
        self._occupied_since = None  # Track when we became occupied

    def motion_event(self):
        """Handle motion event - set occupied and start/reset timer."""
        _LOGGER.debug(
            "Bosch RFDL-ZB-MS: motion detected, starting %ds timer", MOTION_TIMEOUT_S
        )
        self._update_attribute(0x0000, 1)  # occupancy = occupied
        self._occupied_since = time.monotonic()

        if self._timer_handle:
            self._timer_handle.cancel()

        loop = asyncio.get_event_loop()
        self._timer_handle = loop.call_later(MOTION_TIMEOUT_S, self._clear_occupancy)

    def motion_clear(self):
        """Handle clear event from hardware.

        Treats clear as new motion in two scenarios:
        1. Not currently occupied - sensor was stuck, this clear indicates new activity
        2. Occupied for longer than STUCK_MOTION_THRESHOLD_S - sensor resetting due to new activity
        """
        if self._occupied_since is None:
            # Not currently occupied but got a clear - sensor was stuck in motion state
            # and is now resetting due to new activity. Treat as motion.
            _LOGGER.debug(
                "Bosch RFDL-ZB-MS: clear received while not occupied, treating as motion (stuck sensor reset)"
            )
            self.motion_event()
            return

        occupied_duration = time.monotonic() - self._occupied_since

        if occupied_duration >= STUCK_MOTION_THRESHOLD_S:
            _LOGGER.debug(
                "Bosch RFDL-ZB-MS: clear after %ds (>%ds threshold), treating as new motion",
                int(occupied_duration),
                STUCK_MOTION_THRESHOLD_S,
            )
            # Treat as new motion - reset the timer
            self.motion_event()
        else:
            _LOGGER.debug(
                "Bosch RFDL-ZB-MS: clear after %ds (<%ds threshold), ignoring (timer will handle)",
                int(occupied_duration),
                STUCK_MOTION_THRESHOLD_S,
            )
            # Let the software timer handle the clear

    def _clear_occupancy(self):
        """Clear occupancy after timeout."""
        _LOGGER.debug(
            "Bosch RFDL-ZB-MS: clearing occupancy after %ds timeout", MOTION_TIMEOUT_S
        )
        self._update_attribute(0x0000, 0)  # occupancy = unoccupied
        self._timer_handle = None
        self._occupied_since = None


class BoschRFDLZBMS(CustomDevice):
    """Bosch RFDL-ZB-MS RADION TriTech motion sensor."""

    def __init__(self, *args, **kwargs):
        """Initialize device with motion bus."""
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(BOSCH, "RFDL-ZB-MS")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0402,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0402,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    BoschPowerConfiguration,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    BoschIasZone,
                    Diagnostic.cluster_id,
                    BoschOccupancy,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }
