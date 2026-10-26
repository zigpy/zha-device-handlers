"""Custom cluster base for quirks.

`CustomCluster` is the primitive every custom cluster subclasses (in both legacy
and builder quirks). It is a plain `zigpy.zcl.Cluster` that skips the global
cluster registry and can serve constant attribute values without a device
round-trip.
"""

from __future__ import annotations

import typing

import zigpy.zcl
from zigpy.zcl import foundation


class CustomCluster(zigpy.zcl.Cluster):
    """Custom cluster implementation for quirks."""

    _skip_registry = True
    _CONSTANT_ATTRIBUTES: dict[int, typing.Any] | None = None

    async def read_attributes_raw(
        self, attributes: list[int], manufacturer: int | None = None, **kwargs
    ):
        """Read attributes, serving `_CONSTANT_ATTRIBUTES` from the quirk locally."""
        if not self._CONSTANT_ATTRIBUTES:
            return await super().read_attributes_raw(
                attributes, manufacturer=manufacturer, **kwargs
            )

        succeeded = [
            foundation.ReadAttributeRecord(
                attrid=attr,
                status=foundation.Status.SUCCESS,
                value=foundation.TypeValue(
                    type=None,
                    value=self._CONSTANT_ATTRIBUTES[attr],
                ),
            )
            for attr in attributes
            if attr in self._CONSTANT_ATTRIBUTES
        ]

        attrs_to_read = [
            attr for attr in attributes if attr not in self._CONSTANT_ATTRIBUTES
        ]

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
        if (
            self._CONSTANT_ATTRIBUTES is not None
            and attr_def.id in self._CONSTANT_ATTRIBUTES
        ):
            return self._CONSTANT_ATTRIBUTES[attr_def.id]

        return super().get(key, default)

    async def apply_custom_configuration(self, *args, **kwargs):
        """Apply custom configuration; overridden by clusters that need it."""
