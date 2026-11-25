"""Custom cluster base for quirks.

`CustomCluster` is the primitive every custom cluster subclasses (in both legacy
and builder quirks). It is a plain `zigpy.zcl.Cluster` that skips the global
cluster registry and can serve constant attribute values without a device
round-trip.
"""

from __future__ import annotations

import logging
import typing

from zigpy.typing import UNDEFINED, UndefinedType
import zigpy.zcl
from zigpy.zcl import foundation

_LOGGER = logging.getLogger(__name__)
_REPORTED_KEYS: set[tuple[type, ConstantAttributeKey]] = set()

type ConstantAttributeKey = int | str | foundation.ZCLAttributeDef


class CustomCluster(zigpy.zcl.Cluster):
    """Custom cluster implementation for quirks."""

    _skip_registry = True
    # Keys are attribute IDs, attribute names or attribute definitions of this cluster.
    # An ID matches every attribute with that ID, regardless of its manufacturer code.
    # A name or definition only matches that one attribute, which is what separates a
    # manufacturer-specific attribute from a standard one with the same ID.
    _CONSTANT_ATTRIBUTES: dict[ConstantAttributeKey, typing.Any] | None = None

    def _get_constant_attribute(
        self,
        attrid: int,
        attr_def: foundation.ZCLAttributeDef | None,
    ) -> tuple[bool, typing.Any]:
        """Return `(True, value)` if the attribute has a constant value."""
        for key, value in (self._CONSTANT_ATTRIBUTES or {}).items():
            if isinstance(key, int):
                matches = key == attrid
            else:
                try:
                    key_def = self.find_attribute(key)

                    if (
                        isinstance(key, foundation.ZCLAttributeDef)
                        and key.id != key_def.id
                    ):
                        raise KeyError(key.name)  # noqa: TRY301

                    matches = attr_def is not None and key_def.name == attr_def.name
                except KeyError:
                    # Don't break every read of the cluster over a bad key
                    if (type(self), key) not in _REPORTED_KEYS:
                        _REPORTED_KEYS.add((type(self), key))
                        _LOGGER.error(
                            "Ignoring constant attribute %s, not an attribute of %s",
                            getattr(key, "name", key),
                            type(self).__name__,
                        )
                    continue

            if matches:
                return True, value

        return False, None

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
        constant_defs: set[foundation.ZCLAttributeDef] = set()

        for attribute in attributes:
            try:
                attr_def = self.find_attribute(
                    attribute, manufacturer_code=manufacturer
                )
            except KeyError:
                # Let zigpy handle unknown attributes
                attrs_to_read.append(attribute)
                continue

            found, value = self._get_constant_attribute(attr_def.id, attr_def)

            if not found:
                attrs_to_read.append(attribute)
                continue

            if attr_def in constant_defs:
                raise ValueError(
                    f"Cannot read the same attribute twice in the same call: {attr_def}"
                )

            constant_defs.add(attr_def)
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
        found, value = self._get_constant_attribute(attr_def.id, attr_def)

        if found:
            return value

        return super().get(key, default)

    def is_attribute_unsupported(
        self, attr: int | str | foundation.ZCLAttributeDef
    ) -> bool:
        """Return whether an attribute is unsupported."""
        # Constant attributes are always supported, even if the device was marked as
        # not supporting them before the quirk was applied
        if self._CONSTANT_ATTRIBUTES:
            attr_def = self.find_attribute(attr)

            if self._get_constant_attribute(attr_def.id, attr_def)[0]:
                return False

        return super().is_attribute_unsupported(attr)

    async def apply_custom_configuration(self, *args, **kwargs):
        """Apply custom configuration; overridden by clusters that need it."""
