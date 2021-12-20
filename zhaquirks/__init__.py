"""Quirks implementations for the ZHA component of Homeassistant."""
import asyncio
import importlib
import logging
import pathlib
import pkgutil
from typing import Any, Dict, List, Optional, Union

import zigpy.device
import zigpy.endpoint
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.util import ListenableMixin
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.security import IasZone
from zigpy.zdo import types as zdotypes

from zhaquirks.const import (
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    CLUSTER_COMMAND,
    COMMAND_ATTRIBUTE_UPDATED,
    CUSTOM_QUIRKS_PATH,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MANUFACTURER,
    MODEL,
    MODELS_INFO,
    MOTION_EVENT,
    NODE_DESCRIPTOR,
    OFF,
    ON,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    UNKNOWN,
    VALUE,
    ZHA_SEND_EVENT,
    ZONE_STATE,
)

_LOGGER = logging.getLogger(__name__)
OCCUPANCY_STATE = 0
OCCUPANCY_EVENT = "occupancy_event"


class Bus(ListenableMixin):
    """Event bus implementation."""

    def __init__(self, *args, **kwargs):
        """Init event bus."""
        super().__init__(*args, **kwargs)
        self._listeners = {}


class LocalDataCluster(CustomCluster):
    """Cluster meant to prevent remote calls."""

    _CONSTANT_ATTRIBUTES = {}

    async def bind(self):
        """Prevent bind."""
        return (foundation.Status.SUCCESS,)

    async def unbind(self):
        """Prevent unbind."""
        return (foundation.Status.SUCCESS,)

    async def _configure_reporting(self, *args, **kwargs):  # pylint: disable=W0221
        """Prevent remote configure reporting."""
        return (foundation.ConfigureReportingResponse.deserialize(b"\x00")[0],)

    async def read_attributes_raw(self, attributes, manufacturer=None):
        """Prevent remote reads."""
        records = [
            foundation.ReadAttributeRecord(
                attr, foundation.Status.UNSUPPORTED_ATTRIBUTE, foundation.TypeValue()
            )
            for attr in attributes
        ]
        for record in records:
            if record.attrid in self._CONSTANT_ATTRIBUTES:
                record.value.value = self._CONSTANT_ATTRIBUTES[record.attrid]
            else:
                record.value.value = self._attr_cache.get(record.attrid)
            if record.value.value is not None:
                record.status = foundation.Status.SUCCESS
        return (records,)

    async def write_attributes(self, attributes, manufacturer=None):
        """Prevent remote writes."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attridx[attrid]
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)
        return ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)


class EventableCluster(CustomCluster):
    """Cluster that generates events."""

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Send cluster requests as events."""
        if (
            self.server_commands is not None
            and self.server_commands.get(hdr.command_id) is not None
        ):
            self.listener_event(
                ZHA_SEND_EVENT,
                self.server_commands.get(hdr.command_id, (hdr.command_id))[0],
                args,
            )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        self.listener_event(
            ZHA_SEND_EVENT,
            COMMAND_ATTRIBUTE_UPDATED,
            {
                ATTRIBUTE_ID: attrid,
                ATTRIBUTE_NAME: self.attributes.get(attrid, [UNKNOWN])[0],
                VALUE: value,
            },
        )


class GroupBoundCluster(CustomCluster):
    """Cluster that can only bind to a group instead of direct to hub.

    Binding this cluster results in binding to a group that the coordinator
    is a member of.
    """

    COORDINATOR_GROUP_ID = 0x30  # Group id with only coordinator as a member

    async def bind(self):
        """Bind cluster to a group."""
        # Ensure coordinator is a member of the group
        application = self._endpoint.device.application
        coordinator = application.get_device(application.ieee)
        await coordinator.add_to_group(
            self.COORDINATOR_GROUP_ID,
            name="Coordinator Group - Created by ZHAQuirks",
        )

        # Bind cluster to group
        dstaddr = zdotypes.MultiAddress()
        dstaddr.addrmode = 1
        dstaddr.nwk = self.COORDINATOR_GROUP_ID
        dstaddr.endpoint = self._endpoint.endpoint_id
        return await self._endpoint.device.zdo.Bind_req(
            self._endpoint.device.ieee,
            self._endpoint.endpoint_id,
            self.cluster_id,
            dstaddr,
        )


class DoublingPowerConfigurationCluster(CustomCluster, PowerConfiguration):
    """PowerConfiguration cluster implementation.

    This implementation doubles battery pct remaining for non standard devices
    that don't follow the reporting spec.
    """

    cluster_id = PowerConfiguration.cluster_id
    BATTERY_PERCENTAGE_REMAINING = 0x0021

    def _update_attribute(self, attrid, value):
        if attrid == self.BATTERY_PERCENTAGE_REMAINING:
            value = value * 2
        super()._update_attribute(attrid, value)


class PowerConfigurationCluster(CustomCluster, PowerConfiguration):
    """Common use power configuration cluster."""

    cluster_id = PowerConfiguration.cluster_id
    BATTERY_VOLTAGE_ATTR = 0x0020
    BATTERY_PERCENTAGE_REMAINING = 0x0021
    MIN_VOLTS = 1.5  # old 2.1
    MAX_VOLTS = 2.8  # old 3.2

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.BATTERY_VOLTAGE_ATTR and value not in (0, 255):
            super()._update_attribute(
                self.BATTERY_PERCENTAGE_REMAINING,
                self._calculate_battery_percentage(value),
            )

    def _calculate_battery_percentage(self, raw_value):
        volts = raw_value / 10
        volts = max(volts, self.MIN_VOLTS)
        volts = min(volts, self.MAX_VOLTS)

        percent = round(
            ((volts - self.MIN_VOLTS) / (self.MAX_VOLTS - self.MIN_VOLTS)) * 200
        )

        self.debug(
            "Voltage [RAW]:%s [Max]:%s [Min]:%s, Battery Percent: %s",
            raw_value,
            self.MAX_VOLTS,
            self.MIN_VOLTS,
            percent / 2,
        )

        return percent


class _Motion(CustomCluster, IasZone):
    """Self reset Motion cluster."""

    reset_s: int = 30

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._loop = asyncio.get_running_loop()
        self._timer_handle = None

    def _turn_off(self):
        self._timer_handle = None
        _LOGGER.debug("%s - Resetting motion sensor", self.endpoint.device.ieee)
        self.listener_event(CLUSTER_COMMAND, 253, ZONE_STATE, [OFF, 0, 0, 0])
        self._update_attribute(ZONE_STATE, OFF)


class MotionWithReset(_Motion):
    """Self reset Motion cluster.

    Optionally send event over device bus.
    """

    send_occupancy_event: bool = False

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle the cluster command."""
        if hdr.command_id == ZONE_STATE:
            if self._timer_handle:
                self._timer_handle.cancel()
            self._timer_handle = self._loop.call_later(self.reset_s, self._turn_off)
            if self.send_occupancy_event:
                self.endpoint.device.occupancy_bus.listener_event(OCCUPANCY_EVENT)


class MotionOnEvent(_Motion):
    """Motion based on received events from occupancy."""

    reset_s: int = 120

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.motion_bus.add_listener(self)

    def motion_event(self):
        """Motion event."""
        super().listener_event(CLUSTER_COMMAND, 254, ZONE_STATE, [ON, 0, 0, 0])
        self._update_attribute(ZONE_STATE, ON)

        _LOGGER.debug("%s - Received motion event message", self.endpoint.device.ieee)

        if self._timer_handle:
            self._timer_handle.cancel()

        self._timer_handle = self._loop.call_later(self.reset_s, self._turn_off)


class _Occupancy(CustomCluster, OccupancySensing):
    """Self reset Occupancy cluster."""

    reset_s: int = 600

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._timer_handle = None
        self._loop = asyncio.get_running_loop()

    def _turn_off(self):
        self._timer_handle = None
        self._update_attribute(OCCUPANCY_STATE, OFF)


class OccupancyOnEvent(_Occupancy):
    """Self reset occupancy from bus."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.occupancy_bus.add_listener(self)

    def occupancy_event(self):
        """Occupancy event."""
        self._update_attribute(OCCUPANCY_STATE, ON)

        if self._timer_handle:
            self._timer_handle.cancel()

        self._timer_handle = self._loop.call_later(self.reset_s, self._turn_off)


class OccupancyWithReset(_Occupancy):
    """Self reset Occupancy cluster and send event on motion bus."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)

        if attrid == OCCUPANCY_STATE and value == ON:
            if self._timer_handle:
                self._timer_handle.cancel()
            self.endpoint.device.motion_bus.listener_event(MOTION_EVENT)
            self._timer_handle = self._loop.call_later(self.reset_s, self._turn_off)


class QuickInitDevice(CustomDevice):
    """Devices with quick initialization from quirk signature."""

    signature: Optional[Dict[str, Any]] = None

    @classmethod
    def from_signature(
        cls, device: zigpy.device.Device, model: Optional[str] = None
    ) -> zigpy.device.Device:
        """Update device accordingly to quirk signature."""

        assert isinstance(cls.signature, dict)
        if model is None:
            model = cls.signature[MODEL]
        manufacturer = cls.signature.get(MANUFACTURER)
        if manufacturer is None:
            manufacturer = cls.signature[MODELS_INFO][0][0]

        device.node_desc = cls.signature[NODE_DESCRIPTOR]

        endpoints = cls.signature[ENDPOINTS]
        for ep_id, ep_data in endpoints.items():
            endpoint = device.add_endpoint(ep_id)
            endpoint.profile_id = ep_data[PROFILE_ID]
            endpoint.device_type = ep_data[DEVICE_TYPE]
            for cluster_id in ep_data[INPUT_CLUSTERS]:
                cluster = endpoint.add_input_cluster(cluster_id)
                if cluster.ep_attribute == "basic":
                    manuf_attr_id = cluster.attridx[MANUFACTURER]
                    cluster._update_attribute(  # pylint: disable=W0212
                        manuf_attr_id, manufacturer
                    )
                    cluster._update_attribute(  # pylint: disable=W0212
                        cluster.attridx[MODEL], model
                    )
            for cluster_id in ep_data[OUTPUT_CLUSTERS]:
                endpoint.add_output_cluster(cluster_id)
            endpoint.status = zigpy.endpoint.Status.ZDO_INIT

        device.status = zigpy.device.Status.ENDPOINTS_INIT
        device.manufacturer = manufacturer
        device.model = model

        return device


class DeviceMonitor(Bus):
    """Device Monitor to perform actions on device initialization or removal."""

    def __init__(self, device):
        """Init the device, monitoring application for initialization."""
        super().__init__()
        self._device = device
        self._device.application.add_listener(self)

        if self._device.status == zigpy.device.Status.ENDPOINTS_INIT:
            loop = asyncio.get_running_loop()
            self.initialized_event = loop.call_soon(
                self.device_initialized, self._device
            )

    def device_initialized(self, device):
        """Application callback handler for device initialization."""
        if device != self._device:
            return

        self.listener_event("device_initialized")

    def device_removed(self, device):
        """Application callback handler for device removed."""
        if device != self._device:
            return

        if self.initialized_event:
            self.initialized_event.cancel()

        self.listener_event("device_removed")


class PolledCluster(CustomCluster):
    """PolledCluster Class to periodically poll cluster attributes."""

    DEFAULT_FREQUENCY = 60
    POLL_ATTRIBUTES = tuple()

    def __init__(self, *args, **kwargs):
        """Initialize the cluster."""
        super().__init__(*args, **kwargs)
        self._device_monitor = DeviceMonitor(self.endpoint.device)
        self._device_monitor.add_listener(self)
        self._timer_handles = {}
        self._poll_tasks = {}
        self._poll_attribs = tuple(self.attridx[a] for a in self.POLL_ATTRIBUTES)
        self._poll_freq = {a: self.DEFAULT_FREQUENCY for a in self._poll_attribs}
        self._loop = asyncio.get_running_loop()

    def device_initialized(self):
        """Device monitor callback handler for device initialization."""
        self._stop_polling_timers()
        self._start_polling_timers()

    def device_removed(self):
        """Device monitor callback handler for device removed."""
        self._stop_polling_timers()

    def _attr_frequency(self, attrid):
        return self._poll_freq.get(attrid, self.DEFAULT_FREQUENCY)

    def _get_update_frequencies(self):
        return set(self._poll_freq.values())

    def _attribs_by_frequency(self, frequency):
        return [a for a, freq in self._poll_freq.items() if freq == frequency]

    def _has_frequency_timer_running(self, frequency):
        same_frequency_attrs = self._attribs_by_frequency(frequency)
        return any(a in self._timer_handles for a in same_frequency_attrs)

    def _start_polling_timers(self):
        assert not self._timer_handles

        for freq in self._get_update_frequencies():
            self._start_polling_timers_by_frequency(freq)

    def _start_polling_timers_by_frequency(self, freq):
        if self._has_frequency_timer_running(freq):
            return

        attribs = self._attribs_by_frequency(freq)
        timer = self._loop.call_later(freq, self._queue_poll_attribs, attribs, freq)
        self._timer_handles.update({a: timer for a in attribs})

    def _stop_polling_timers(self):
        for timer in self._timer_handles.values():
            timer.cancel()
        self._timer_handles = {}

        for task in self._poll_tasks.values():
            task.cancel()
        self._poll_tasks = {}

    async def _poll_attribs_async(self, attribs, freq):
        cancelled = False
        try:
            await self.read_attributes(attribs)
        except asyncio.CancelledError:
            cancelled = True
        except asyncio.TimeoutError:
            _LOGGER.warn(
                "Timed out while polling device %s attributes %s",
                self.endpoint.device.ieee,
                attribs,
            )
        except Exception:
            _LOGGER.exception(
                "Failed to poll device %s attributes", self.endpoint.device.ieee
            )
        finally:
            self._poll_tasks.update({a: None for a in attribs})
            if not cancelled:
                self._start_polling_timers_by_frequency(freq)

    def _queue_poll_attribs(self, attribs, freq):
        attribs_to_poll = []
        for attrid in attribs:
            if self._timer_handles.pop(attrid, None) and not self._poll_tasks.get(
                attrid
            ):
                attribs_to_poll.append(attrid)

        if attribs_to_poll:
            task = self._loop.create_task(
                self._poll_attribs_async(attribs_to_poll, freq)
            )
            self._poll_tasks.update({a: task for a in attribs_to_poll})

    def _configure_reporting(self, args, manufacturer=None):
        """Configure reporting."""
        frequencies = set()
        for arg in [a for a in args if a.attrid in self._poll_attribs]:
            self._skip_update(arg.attrid, restart=False)
            frequency = min(
                max(arg.min_interval, self.DEFAULT_FREQUENCY), arg.max_interval
            )
            for freq in self._get_update_frequencies():
                if freq >= arg.min_interval and freq <= arg.max_interval:
                    frequency = freq
                    break
            self._poll_freq[arg.attrid] = frequency
            frequencies.add(frequency)

        for frequency in frequencies:
            self._start_polling_timers_by_frequency(frequency)

        return super()._configure_reporting(args, manufacturer=manufacturer)

    def _skip_update(self, attrid, restart=True):
        timer = self._timer_handles.pop(attrid, None)
        if not timer:
            return

        attr_frequency = self._attr_frequency(attrid)
        if not self._has_frequency_timer_running(attr_frequency):
            timer.cancel()

            if restart:
                self._start_polling_timers_by_frequency(attr_frequency)

    def _update_attribute(self, attrid, value):
        if attrid in self._poll_attribs:
            self._skip_update(attrid)

        super()._update_attribute(attrid, value)


def setup(config: Optional[Dict[str, Any]] = None) -> None:
    """Register all quirks with zigpy, including optional custom quirks."""

    # Import all quirks in the `zhaquirks` package first
    for importer, modname, ispkg in pkgutil.walk_packages(
        path=__path__,
        prefix=__name__ + ".",
    ):
        _LOGGER.debug("Loading quirks module %s", modname)
        importlib.import_module(modname)

    # Treat the custom quirk path (e.g. `/config/custom_quirks/`) itself as a module
    if config and config.get(CUSTOM_QUIRKS_PATH):
        path = pathlib.Path(config[CUSTOM_QUIRKS_PATH])
        _LOGGER.debug("Loading custom quirks from %s", path)

        for importer, modname, ispkg in pkgutil.walk_packages(path=[str(path)]):
            _LOGGER.debug("Loading custom quirks module %s", modname)
            importer.find_module(modname).load_module(modname)
