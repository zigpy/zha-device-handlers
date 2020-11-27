"""Eurotronic devices."""

import logging

from zigpy.quirks import CustomCluster
import zigpy.types as types
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

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

    manufacturer_attributes = {
        TRV_MODE_ATTR: ("trv_mode", types.enum8),
        SET_VALVE_POS_ATTR: ("set_valve_position", types.uint8_t),
        ERRORS_ATTR: ("errors", types.uint8_t),
        CURRENT_TEMP_SETPOINT_ATTR: ("current_temperature_setpoint", types.int16s),
        HOST_FLAGS_ATTR: ("host_flags", types.uint24_t),
    }

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

    async def read_attributes_raw(self, attributes, manufacturer=None):
        """Override wrong attribute reports from the thermostat."""
        success = []
        error = []

        if CTRL_SEQ_OF_OPER_ATTR in attributes:
            rar = foundation.ReadAttributeRecord(
                CTRL_SEQ_OF_OPER_ATTR, foundation.Status.SUCCESS, foundation.TypeValue()
            )
            rar.value.value = 0x2
            success.append(rar)

        if SYSTEM_MODE_ATTR in attributes:
            rar = foundation.ReadAttributeRecord(
                SYSTEM_MODE_ATTR, foundation.Status.SUCCESS, foundation.TypeValue()
            )
            rar.value.value = 0x4
            success.append(rar)

        if OCCUPIED_HEATING_SETPOINT_ATTR in attributes:

            _LOGGER.debug("intercepting OCC_HS")

            values = await super().read_attributes_raw(
                [CURRENT_TEMP_SETPOINT_ATTR], manufacturer=MANUFACTURER
            )

            if len(values) == 2:
                current_temp_setpoint = values[1][0]
                current_temp_setpoint.attrid = OCCUPIED_HEATING_SETPOINT_ATTR

                error.extend(values[1])
            else:
                current_temp_setpoint = values[0][0]
                current_temp_setpoint.attrid = OCCUPIED_HEATING_SETPOINT_ATTR

                success.extend(values[0])

        attributes = list(
            filter(
                lambda x: x
                not in (
                    CTRL_SEQ_OF_OPER_ATTR,
                    SYSTEM_MODE_ATTR,
                    OCCUPIED_HEATING_SETPOINT_ATTR,
                ),
                attributes,
            )
        )

        if attributes:
            values = await super().read_attributes_raw(attributes, manufacturer)

            success.extend(values[0])

            if len(values) == 2:
                error.extend(values[1])

        return success, error

    def write_attributes(self, attributes, manufacturer=None):
        """Override wrong writes to thermostat attributes."""
        if "system_mode" in attributes:

            host_flags = self._attr_cache.get(HOST_FLAGS_ATTR, 1)
            _LOGGER.debug("current host_flags: %s", host_flags)

            if attributes.get("system_mode") == 0x0:
                return super().write_attributes(
                    {"host_flags": host_flags | SET_OFF_MODE_FLAG}, MANUFACTURER
                )
            if attributes.get("system_mode") == 0x4:
                return super().write_attributes(
                    {"host_flags": host_flags | CLR_OFF_MODE_FLAG}, MANUFACTURER
                )

        return super().write_attributes(attributes, manufacturer)
