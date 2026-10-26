"""Custom cluster base for quirks.

`CustomCluster` is the primitive every custom cluster subclasses (in both legacy
and builder quirks). It is a plain `zigpy.zcl.Cluster` that skips the global
cluster registry and can serve constant attribute values without a device
round-trip.
"""

from __future__ import annotations

import logging
import typing

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

    def _find_constant_attribute(
        self, attrid: int, manufacturer: int | None
    ) -> foundation.ZCLAttributeDef | None:
        """Find the definition a read of `attrid` with `manufacturer` refers to."""
        # Only definition and name keys need it, and resolving can emit warnings
        if all(isinstance(key, int) for key in self._CONSTANT_ATTRIBUTES or ()):
            return None

        for kwargs in ({"manufacturer_code": manufacturer}, {}):
            try:
                return self.find_attribute(attrid, **kwargs)
            except KeyError:
                continue

        return None

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

    async def read_attributes_raw(
        self, attributes: list[int], manufacturer: int | None = None, **kwargs
    ):
        """Read attributes, serving `_CONSTANT_ATTRIBUTES` from the quirk locally."""
        if not self._CONSTANT_ATTRIBUTES:
            return await super().read_attributes_raw(
                attributes, manufacturer=manufacturer, **kwargs
            )

        succeeded = []
        attrs_to_read = []

        for attr in attributes:
            found, value = self._get_constant_attribute(
                attr, self._find_constant_attribute(attr, manufacturer)
            )

            if found:
                succeeded.append(
                    foundation.ReadAttributeRecord(
                        attrid=attr,
                        status=foundation.Status.SUCCESS,
                        value=foundation.TypeValue(type=None, value=value),
                    )
                )
            else:
                attrs_to_read.append(attr)

        if not attrs_to_read:
            return [succeeded]

        results = await super().read_attributes_raw(
            attrs_to_read, manufacturer=manufacturer, **kwargs
        )
        if not isinstance(results[0], list):
            for attrid in attrs_to_read:
                succeeded.append(  # noqa: PERF401
                    foundation.ReadAttributeRecord(
                        attrid,
                        results[0],
                        foundation.TypeValue(),
                    )
                )
        else:
            succeeded.extend(results[0])
        return [succeeded]

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

    async def apply_custom_configuration(self, *args, **kwargs):
        """Apply custom configuration; overridden by clusters that need it."""
