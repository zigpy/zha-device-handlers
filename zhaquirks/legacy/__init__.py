"""Quirks v1 system (legacy, slated for removal).

The subclass-based `CustomDevice` registration system: a quirk subclasses
`CustomDevice` with a `signature`/`replacement` dict and is auto-registered.
The clone machinery (`BaseCustomDevice`) and cluster primitive (`CustomCluster`)
it builds on are not legacy and live in `zhaquirks.device`/`zhaquirks.clusters`.
"""

from __future__ import annotations

import logging
import typing
from typing import Any

from zigpy.const import (  # noqa: F401
    SIG_ENDPOINTS,
    SIG_EP_INPUT,
    SIG_EP_OUTPUT,
    SIG_EP_PROFILE,
    SIG_EP_TYPE,
    SIG_MANUFACTURER,
    SIG_MODEL,
    SIG_MODELS_INFO,
    SIG_NODE_DESC,
    SIG_SKIP_CONFIG,
)
import zigpy.device

from zhaquirks.device import BaseCustomDevice
from zhaquirks.legacy.registry import LegacyDeviceRegistry

_LOGGER = logging.getLogger(__name__)

DEVICE_REGISTRY = LegacyDeviceRegistry()
PENDING_LEGACY_QUIRKS: list[type[CustomDevice]] = []

_uninitialized_device_message_handlers = []


def get_device(
    device: zigpy.device.Device, registry: LegacyDeviceRegistry | None = None
) -> zigpy.device.Device:
    """Get a CustomDevice object, if one is available."""
    if registry is None:
        return DEVICE_REGISTRY.get_device(device)

    return registry.get_device(device)


def get_quirk_list(
    manufacturer: str, model: str, registry: LegacyDeviceRegistry | None = None
):
    """Get the Quirk list for a given manufacturer and model."""
    if registry is None:
        return DEVICE_REGISTRY.registry_v1[manufacturer][model]

    return registry.registry_v1[manufacturer][model]


def register_uninitialized_device_message_handler(handler: typing.Callable) -> None:
    """Register an handler for messages received by uninitialized devices.

    each handler is passed same parameters as
    zigpy.application.ControllerApplication.handle_message
    """
    if handler not in _uninitialized_device_message_handlers:
        _uninitialized_device_message_handlers.append(handler)


class CustomDevice(BaseCustomDevice):
    """Implementation of a quirks v1 custom device."""

    signature: dict[str, Any] | None = None

    def __init_subclass__(cls) -> None:
        """Register a quirk subclass that defines a signature."""
        if getattr(cls, "signature", None) is not None:
            DEVICE_REGISTRY.add_to_registry(cls)
            PENDING_LEGACY_QUIRKS.append(cls)


FilterType = typing.Callable[[zigpy.device.Device], bool]


def signature_matches(
    signature: dict[str, Any],
) -> FilterType:
    """Return True if device matches signature."""

    def _match(a: dict | typing.Iterable, b: dict | typing.Iterable) -> bool:
        return set(a) == set(b)

    def _filter(device: zigpy.device.Device) -> bool:
        """Return True if device matches signature."""
        if device.model != signature.get(SIG_MODEL, device.model):
            _LOGGER.debug("Fail, because device model mismatch: '%s'", device.model)
            return False

        if device.manufacturer != signature.get(SIG_MANUFACTURER, device.manufacturer):
            _LOGGER.debug(
                "Fail, because device manufacturer mismatch: '%s'",
                device.manufacturer,
            )
            return False

        dev_ep = set(device.endpoints) - {0}

        sig = signature.get(SIG_ENDPOINTS)
        if sig is None:
            return False

        if not _match(sig, dev_ep):
            _LOGGER.debug(
                "Fail because endpoint list mismatch: %s %s",
                set(sig.keys()),
                dev_ep,
            )
            return False

        if not all(
            device[eid].profile_id
            == sig[eid].get(SIG_EP_PROFILE, device[eid].profile_id)
            for eid in sig
        ):
            _LOGGER.debug("Fail because profile_id mismatch on at least one endpoint")
            return False

        if not all(
            device[eid].device_type
            == sig[eid].get(SIG_EP_TYPE, device[eid].device_type)
            for eid in sig
        ):
            _LOGGER.debug("Fail because device_type mismatch on at least one endpoint")
            return False

        if not all(
            _match(device[eid].in_clusters, ep.get(SIG_EP_INPUT, []))
            for eid, ep in sig.items()
        ):
            _LOGGER.debug(
                "Fail because input cluster mismatch on at least one endpoint"
            )
            return False

        if not all(
            _match(device[eid].out_clusters, ep.get(SIG_EP_OUTPUT, []))
            for eid, ep in sig.items()
        ):
            _LOGGER.debug(
                "Fail because output cluster mismatch on at least one endpoint"
            )
            return False

        _LOGGER.debug(
            "Device matches filter signature - device ieee[%s]: filter signature[%s]",
            device.ieee,
            signature,
        )
        return True

    return _filter


def handle_message_from_uninitialized_sender(
    sender: zigpy.device.Device,
    profile: int,
    cluster: int,
    src_ep: int,
    dst_ep: int,
    message: bytes,
) -> None:
    """Process a message from an uninitialized sender."""
    for handler in _uninitialized_device_message_handlers:
        if handler(sender, profile, cluster, src_ep, dst_ep, message):
            break
