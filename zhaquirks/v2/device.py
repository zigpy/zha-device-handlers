"""The ZHA device used by declarative (QuirkBuilder) quirks."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

import zigpy.device

# `discovery` must be imported before `zha.zigbee.device`: the platform modules
# it loads participate in an import cycle with the device module and cannot be
# loaded while `zha.zigbee.device` is only partially initialized.
from zha.application import discovery  # noqa: F401
from zha.application.platforms import BaseEntity
from zha.zigbee.device import Device

from zhaquirks.v2.discovery import discover_quirks_v2_entities
from zhaquirks.v2.metadata import QuirkDefinition

if TYPE_CHECKING:
    from zha.application.gateway import Gateway


class QuirkV2Device(Device):
    """Base ZHA device for QuirkBuilder."""

    def __init__(
        self,
        zigpy_device: zigpy.device.Device,
        gateway: Gateway,
        *,
        quirk_definition: QuirkDefinition,
    ) -> None:
        """Initialize the quirk device."""
        self._quirk_definition = quirk_definition
        super().__init__(zigpy_device, gateway)

    @property
    def quirk_metadata(self) -> QuirkDefinition:
        """Return the ZHA-level quirk metadata for this device."""
        return self._quirk_definition

    def discover_entities(self) -> Iterator[BaseEntity]:
        """Yield the default entities plus the quirk's exposed v2 entities."""
        yield from super().discover_entities()
        yield from discover_quirks_v2_entities(self)
