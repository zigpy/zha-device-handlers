"""Quirks v1 device registry (moved out of zigpy)."""

from __future__ import annotations

from collections import defaultdict, deque
import inspect
import itertools
import logging
import pathlib
from typing import TYPE_CHECKING

from zigpy.const import QUIRKS_REPO_URL, SIG_MANUFACTURER, SIG_MODEL, SIG_MODELS_INFO
from zigpy.util import deprecated

from zhaquirks.device import BaseCustomDevice
import zhaquirks.legacy

if TYPE_CHECKING:
    from zigpy.device import Device

    from zhaquirks.legacy import CustomDevice

_LOGGER = logging.getLogger(__name__)


class LegacyDeviceRegistry:
    """Device registry for quirks v1."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the registry."""
        self._registry_v1: dict[
            str | None, dict[str | None, deque[type[CustomDevice]]]
        ] = defaultdict(lambda: defaultdict(deque))

    def purge_custom_quirks(self, custom_quirks_root: pathlib.Path) -> None:
        """Remove quirks loaded from the custom quirks directory."""
        # If zhaquirks aren't being used, we can't tell if a quirk is custom or not
        for model_registry in self._registry_v1.values():
            for quirks in model_registry.values():
                to_remove = []

                for quirk in quirks:
                    module = inspect.getmodule(quirk)
                    assert module is not None  # All quirks should have modules

                    quirk_module = pathlib.Path(module.__file__)

                    if quirk_module.is_relative_to(custom_quirks_root):
                        to_remove.append(quirk)

                for quirk in to_remove:
                    _LOGGER.debug("Removing stale custom v1 quirk: %s", quirk)
                    quirks.remove(quirk)

    def add_to_registry(self, custom_device: type[CustomDevice]) -> None:
        """Add a device to the registry."""
        models_info = custom_device.signature.get(SIG_MODELS_INFO)
        if models_info:
            for manuf, model in models_info:
                if custom_device not in self.registry_v1[manuf][model]:
                    self.registry_v1[manuf][model].appendleft(custom_device)
        else:
            manufacturer = custom_device.signature.get(SIG_MANUFACTURER)
            model = custom_device.signature.get(SIG_MODEL)
            if custom_device not in self.registry_v1[manufacturer][model]:
                self.registry_v1[manufacturer][model].appendleft(custom_device)

    def remove(self, custom_device: type[CustomDevice]) -> None:
        """Remove a device from the registry."""
        models_info = custom_device.signature.get(SIG_MODELS_INFO)
        if models_info:
            for manuf, model in models_info:
                self.registry_v1[manuf][model].remove(custom_device)
        else:
            manufacturer = custom_device.signature.get(SIG_MANUFACTURER)
            model = custom_device.signature.get(SIG_MODEL)
            self.registry_v1[manufacturer][model].remove(custom_device)

    def get_device(self, device: Device) -> CustomDevice | Device:
        """Get a CustomDevice object, if one is available."""
        if isinstance(device, BaseCustomDevice):
            return device

        _LOGGER.debug(
            "Checking quirks for %s %s (%s)",
            device.manufacturer,
            device.model,
            device.ieee,
        )

        for candidate in itertools.chain(
            self.registry_v1[device.manufacturer][device.model],
            self.registry_v1[device.manufacturer][None],
            self.registry_v1[None][device.model],
            self.registry_v1[None][None],
        ):
            matcher = zhaquirks.legacy.signature_matches(candidate.signature)
            _LOGGER.debug("Considering %s", candidate)

            if not matcher(device):
                continue

            _LOGGER.debug(
                "Found custom device replacement for %s: %s", device.ieee, candidate
            )

            try:
                return candidate(device._application, device.ieee, device.nwk, device)
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    (
                        "Failed to load quirk for %r: %r\n"
                        "This is a bug. Please report it here: %s"
                    ),
                    device,
                    candidate,
                    QUIRKS_REPO_URL,
                )
                return device

        # If none match, return the original device
        return device

    @property
    @deprecated("The `registry` property is deprecated, use `registry_v1` instead.")
    def registry(self) -> dict[str | None, dict[str | None, deque[type[CustomDevice]]]]:
        """Return the v1 registry."""
        return self._registry_v1

    @property
    def registry_v1(
        self,
    ) -> dict[str | None, dict[str | None, deque[type[CustomDevice]]]]:
        """Return the v1 registry."""
        return self._registry_v1

    def __contains__(self, device: type[CustomDevice]) -> bool:
        """Check if a device is in the registry."""
        manufacturer, model = device.signature.get(
            SIG_MODELS_INFO,
            [
                (
                    device.signature.get(SIG_MANUFACTURER),
                    device.signature.get(SIG_MODEL),
                )
            ],
        )[0]
        return device in itertools.chain(
            self.registry_v1[manufacturer][model],
            self.registry_v1[manufacturer][None],
            self.registry_v1[None][None],
        )
