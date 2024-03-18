"""Quirks for Sonoff devices."""
from __future__ import annotations

from typing import Any, Final

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.types.basic import enum_factory
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    Direction,
    GeneralCommand,
    ZCLAttributeDef,
    ZCLHeader,
)

WWAH_CLUSTER_ID = 0xFC57


class DisplayUnit(enum_factory(t.uint16_t)):
    Celsius = 0
    Fahrenheit = 1


class SonoffClusterFC11(CustomCluster):
    """Sonoff custom cluster."""

    DisplayUnit: Final = DisplayUnit

    cluster_id = 0xFC11
    name = "SonoffClusterFC11"

    class AttributeDefs(BaseAttributeDefs):
        high_temperature_threshold: Final = ZCLAttributeDef(
            id=0x0003, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        low_temperature_threshold: Final = ZCLAttributeDef(
            id=0x0004, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        low_humidity_threshold: Final = ZCLAttributeDef(
            id=0x0005, type=t.uint16_t, access="rwp", is_manufacturer_specific=True
        )
        high_humidity_threshold: Final = ZCLAttributeDef(
            id=0x0006, type=t.uint16_t, access="rwp", is_manufacturer_specific=True
        )
        display_unit: Final = ZCLAttributeDef(
            id=0x0007, type=DisplayUnit, access="rwp", is_manufacturer_specific=True
        )
        unknown_fffd: Final = ZCLAttributeDef(
            id=0xFFFD, type=t.uint16_t, access="rwp", is_manufacturer_specific=True
        )

    def _create_request(
        self,
        *,
        general: bool,
        command_id: GeneralCommand | int,
        schema: dict | t.Struct,
        manufacturer: int | None = None,
        tsn: int | None = None,
        disable_default_response: bool,
        direction: Direction,
        # Schema args and kwargs
        args: tuple[Any, ...],
        kwargs: Any,
    ) -> tuple[ZCLHeader, bytes]:
        """Override all request to disable manufacturer."""
        return super()._create_request(
            general=general,
            command_id=command_id,
            schema=schema,
            manufacturer=ZCLHeader.NO_MANUFACTURER_ID,
            tsn=tsn,
            disable_default_response=disable_default_response,
            direction=direction,
            args=args,
            kwargs=kwargs,
        )
