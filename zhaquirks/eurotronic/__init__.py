"""Eurotronic devices."""

import logging
from typing import Any, Final

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.clusters import CustomCluster

EUROTRONIC = "Eurotronic"

THERMOSTAT_CHANNEL = "thermostat"

MANUFACTURER = 0x1037  # 4151

OCCUPIED_HEATING_SETPOINT_ATTR = 0x0012
CTRL_SEQ_OF_OPER_ATTR = 0x001B
SYSTEM_MODE_ATTR = 0x001C

TRV_MODE_ATTR = 0x4000
SET_VALVE_POS_ATTR = 0x4001
ERRORS_ATTR = 0x4002
CURRENT_TEMP_SETPOINT_ATTR = 0x4003
HOST_FLAGS_ATTR = 0x4008


# Host Flags
# unknown (defaults to 1)       = 0b00000001 # 1
MIRROR_SCREEN_FLAG = 0b00000010  # 2
BOOST_FLAG = 0b00000100  # 4
# unknown                       = 0b00001000 # 8
CLR_OFF_MODE_FLAG = 0b00010000  # 16
SET_OFF_MODE_FLAG = 0b00100000  # 32, reported back as 16
# unknown                       = 0b01000000 # 64
CHILD_LOCK_FLAG = 0b10000000  # 128


_LOGGER = logging.getLogger(__name__)


class ThermostatCluster(CustomCluster, Thermostat):
    """Thermostat cluster."""

    _CONSTANT_ATTRIBUTES = {
        CTRL_SEQ_OF_OPER_ATTR: Thermostat.ControlSequenceOfOperation.Heating_Only,
        SYSTEM_MODE_ATTR: Thermostat.SystemMode.Heat,
    }

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        trv_mode: Final = ZCLAttributeDef(
            id=TRV_MODE_ATTR, type=t.enum8, is_manufacturer_specific=True
        )
        set_valve_position: Final = ZCLAttributeDef(
            id=SET_VALVE_POS_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )
        errors: Final = ZCLAttributeDef(
            id=ERRORS_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )
        current_temperature_setpoint: Final = ZCLAttributeDef(
            id=CURRENT_TEMP_SETPOINT_ATTR, type=t.int16s, is_manufacturer_specific=True
        )
        host_flags: Final = ZCLAttributeDef(
            id=HOST_FLAGS_ATTR, type=t.uint24_t, is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid, value):
        _LOGGER.debug("update attribute %04x to %s... ", attrid, value)

        if attrid == CURRENT_TEMP_SETPOINT_ATTR:
            super()._update_attribute(OCCUPIED_HEATING_SETPOINT_ATTR, value)
        elif attrid == HOST_FLAGS_ATTR:
            if value & CLR_OFF_MODE_FLAG == CLR_OFF_MODE_FLAG:
                super()._update_attribute(SYSTEM_MODE_ATTR, 0x0)
                _LOGGER.debug("set system_mode to [off ]")
            else:
                super()._update_attribute(SYSTEM_MODE_ATTR, 0x4)
                _LOGGER.debug("set system_mode to [heat]")

        _LOGGER.debug("update attribute %04x to %s... [ ok ]", attrid, value)
        super()._update_attribute(attrid, value)

    async def read_attributes_raw(
        self, attributes: list[int], manufacturer: int | None = None, **kwargs
    ) -> foundation.ReadAttributesResponse | foundation.DefaultResponse:
        """Serve `occupied_heating_setpoint` from `current_temperature_setpoint`."""
        if OCCUPIED_HEATING_SETPOINT_ATTR not in attributes:
            return await super().read_attributes_raw(
                attributes, manufacturer=manufacturer, **kwargs
            )

        records: list[foundation.ReadAttributeRecord] = []

        # The thermostat reports the wrong value for the standard attribute, the
        # manufacturer-specific one holds the real setpoint
        rsp = await super().read_attributes_raw(
            [CURRENT_TEMP_SETPOINT_ATTR], manufacturer=MANUFACTURER, **kwargs
        )
        assert isinstance(rsp, foundation.ReadAttributesResponse)

        for record in rsp.status_records:
            record.attrid = OCCUPIED_HEATING_SETPOINT_ATTR
            records.append(record)

        remaining = [a for a in attributes if a != OCCUPIED_HEATING_SETPOINT_ATTR]

        if remaining:
            rsp = await super().read_attributes_raw(
                remaining, manufacturer=manufacturer, **kwargs
            )
            assert isinstance(rsp, foundation.ReadAttributesResponse)
            records.extend(rsp.status_records)

        return foundation.ReadAttributesResponse(status_records=records)

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Override wrong writes to thermostat attributes."""
        if "system_mode" in attributes:
            host_flags = self._attr_cache.get(HOST_FLAGS_ATTR, 1)
            _LOGGER.debug("current host_flags: %s", host_flags)

            if attributes.get("system_mode") == 0x0:
                return await super().write_attributes(
                    {"host_flags": host_flags | SET_OFF_MODE_FLAG},
                    manufacturer=MANUFACTURER,
                )
            if attributes.get("system_mode") == 0x4:
                return await super().write_attributes(
                    {"host_flags": host_flags | CLR_OFF_MODE_FLAG},
                    manufacturer=MANUFACTURER,
                )

        return await super().write_attributes(attributes, **kwargs)
