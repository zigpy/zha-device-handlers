"""Custom cluster base for quirks.

`CustomCluster` is the primitive every custom cluster subclasses (in both legacy
and builder quirks). It is a plain `zigpy.zcl.Cluster` that skips the global
cluster registry and can serve constant attribute values without a device
round-trip.
"""

from __future__ import annotations

import typing

from zigpy.typing import UNDEFINED, UndefinedType
import zigpy.zcl
from zigpy.zcl import foundation


class CustomCluster(zigpy.zcl.Cluster):
    """Custom cluster implementation for quirks."""

    _skip_registry = True
    _CONSTANT_ATTRIBUTES: dict[int, typing.Any] | None = None

    async def read_attributes(
        self,
        attributes: list[int | str | foundation.ZCLAttributeDef],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> typing.Any:
        """Read attributes, serving `_CONSTANT_ATTRIBUTES` without caching them.

        Constant values are defined by the quirk, not reported by the device, so
        they are kept out of the attribute cache. Otherwise, they would be persisted
        to the database as if the device reported them, and would outlive the quirk.
        """
        if not self._CONSTANT_ATTRIBUTES:
            return await super().read_attributes(
                attributes,
                allow_cache=allow_cache,
                only_cache=only_cache,
                manufacturer=manufacturer,
                **kwargs,
            )

        success: dict[typing.Any, typing.Any] = {}
        failure: dict[typing.Any, typing.Any] = {}
        attrs_to_read: list[int | str | foundation.ZCLAttributeDef] = []

        for attribute in attributes:
            try:
                attr_def = self.find_attribute(
                    attribute, manufacturer_code=manufacturer
                )
            except KeyError:
                # Let zigpy handle unknown attributes
                attrs_to_read.append(attribute)
                continue

            if attr_def.id not in self._CONSTANT_ATTRIBUTES:
                attrs_to_read.append(attribute)
                continue

            value = self._CONSTANT_ATTRIBUTES[attr_def.id]
            success[attribute] = value if value is None else attr_def.type(value)

        if attrs_to_read:
            read_success, read_failure = await super().read_attributes(
                attrs_to_read,
                allow_cache=allow_cache,
                only_cache=only_cache,
                manufacturer=manufacturer,
                **kwargs,
            )
            success.update(read_success)
            failure.update(read_failure)

        return success, failure

    def get(self, key: int | str, default: typing.Any | None = None) -> typing.Any:
        """Get cached attribute."""

        try:
            attr_def = self.find_attribute(key)
        except KeyError:
            return super().get(key, default)

        # Ensure we check the constant attributes dictionary first, since their values
        # will not be in the attribute cache but can be read immediately.
        if (
            self._CONSTANT_ATTRIBUTES is not None
            and attr_def.id in self._CONSTANT_ATTRIBUTES
        ):
            return self._CONSTANT_ATTRIBUTES[attr_def.id]

        return super().get(key, default)

    def is_attribute_unsupported(
        self, attr: int | str | foundation.ZCLAttributeDef
    ) -> bool:
        """Return whether an attribute is unsupported."""
        # Constant attributes are always supported, even if the device was marked as
        # not supporting them before the quirk was applied
        if self._CONSTANT_ATTRIBUTES and (
            self.find_attribute(attr).id in self._CONSTANT_ATTRIBUTES
        ):
            return False

        return super().is_attribute_unsupported(attr)

    async def apply_custom_configuration(self, *args, **kwargs):
        """Apply custom configuration; overridden by clusters that need it."""
