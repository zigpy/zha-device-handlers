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
        success: dict[typing.Any, typing.Any] = {}
        failure: dict[typing.Any, typing.Any] = {}
        attrs_to_read: dict[
            int | str | foundation.ZCLAttributeDef, foundation.ZCLAttributeDef
        ] = {}
        seen_defs: set[foundation.ZCLAttributeDef] = set()

        for attribute in attributes:
            # Unknown attributes raise a `KeyError`, like in zigpy
            attr_def = self.find_attribute(attribute, manufacturer_code=manufacturer)

            if attr_def in seen_defs:
                raise ValueError(
                    f"Cannot read the same attribute twice in the same call: {attr_def}"
                )

            seen_defs.add(attr_def)

            if (
                self._CONSTANT_ATTRIBUTES is None
                or attr_def.id not in self._CONSTANT_ATTRIBUTES
            ):
                attrs_to_read[attribute] = attr_def
                continue

            value = self._CONSTANT_ATTRIBUTES[attr_def.id]
            success[attribute] = value if value is None else attr_def.type(value)

        if attrs_to_read:
            read_success, read_failure = await self._read_non_constant_attributes(
                attrs_to_read,
                allow_cache=allow_cache,
                only_cache=only_cache,
                manufacturer=manufacturer,
                **kwargs,
            )
            success.update(read_success)
            failure.update(read_failure)

        return success, failure

    async def _read_non_constant_attributes(
        self,
        attributes: dict[
            int | str | foundation.ZCLAttributeDef, foundation.ZCLAttributeDef
        ],
        *,
        allow_cache: bool,
        only_cache: bool,
        manufacturer: int | UndefinedType | None,
        **kwargs,
    ) -> typing.Any:
        """Read attributes not in `_CONSTANT_ATTRIBUTES`, from the device by default.

        `attributes` maps each requested key to its resolved attribute definition.
        """
        return await super().read_attributes(
            list(attributes),
            allow_cache=allow_cache,
            only_cache=only_cache,
            manufacturer=manufacturer,
            **kwargs,
        )

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
