"""Tests for the Eurotronic Spirit Zigbee thermostat quirk."""

from unittest import mock

import zigpy.types as t
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import (
    Attribute,
    ReadAttributeRecord,
    ReadAttributesResponse,
    Status,
    TypeValue,
    WriteAttributesResponseSchema,
    WriteAttributesStatusRecord,
)

import zhaquirks
from zhaquirks.eurotronic import (
    CLR_OFF_MODE_FLAG,
    CURRENT_TEMP_SETPOINT_ATTR,
    HOST_FLAGS_ATTR,
    MANUFACTURER,
    OCCUPIED_HEATING_SETPOINT_ATTR,
    SET_OFF_MODE_FLAG,
)
from zhaquirks.eurotronic.spzb0001 import SPZB0001

zhaquirks.setup()


async def test_occupied_heating_setpoint_read(zigpy_device_from_quirk):
    """The standard setpoint is served from the manufacturer-specific attribute."""
    cluster = zigpy_device_from_quirk(SPZB0001).endpoints[1].thermostat

    read = mock.AsyncMock(
        return_value=ReadAttributesResponse(
            status_records=[
                ReadAttributeRecord(
                    attrid=CURRENT_TEMP_SETPOINT_ATTR,
                    status=Status.SUCCESS,
                    value=TypeValue(
                        type=cluster.AttributeDefs.current_temperature_setpoint.zcl_type,
                        value=2150,
                    ),
                )
            ]
        )
    )

    with mock.patch.object(cluster, "_read_attributes", read):
        success, _ = await cluster.read_attributes([OCCUPIED_HEATING_SETPOINT_ATTR])

    assert read.mock_calls == [
        mock.call([t.uint16_t(CURRENT_TEMP_SETPOINT_ATTR)], manufacturer=MANUFACTURER)
    ]
    assert success == {OCCUPIED_HEATING_SETPOINT_ATTR: 2150}


async def test_ctrl_sequence_of_oper_is_constant(zigpy_device_from_quirk):
    """The control sequence is answered locally without a device round-trip."""
    cluster = zigpy_device_from_quirk(SPZB0001).endpoints[1].thermostat

    read = mock.AsyncMock()

    with mock.patch.object(cluster, "_read_attributes", read):
        success, _ = await cluster.read_attributes(["ctrl_sequence_of_oper"])

    assert read.mock_calls == []
    assert success == {
        "ctrl_sequence_of_oper": Thermostat.ControlSequenceOfOperation.Heating_Only
    }


async def test_host_flags_off_bit_sets_system_mode(zigpy_device_from_quirk):
    """A host_flags report with the off bit set turns system_mode off."""
    cluster = zigpy_device_from_quirk(SPZB0001).endpoints[1].thermostat

    cluster.update_attribute(HOST_FLAGS_ATTR, CLR_OFF_MODE_FLAG | 1)
    assert cluster.get("system_mode") == Thermostat.SystemMode.Off

    cluster.update_attribute(HOST_FLAGS_ATTR, 1)
    assert cluster.get("system_mode") == Thermostat.SystemMode.Heat


async def test_system_mode_write_sets_host_flags(zigpy_device_from_quirk):
    """Writing system_mode sets the matching host_flags bit instead."""
    cluster = zigpy_device_from_quirk(SPZB0001).endpoints[1].thermostat
    cluster.update_attribute(HOST_FLAGS_ATTR, 1)

    write = mock.AsyncMock(
        return_value=WriteAttributesResponseSchema(
            status_records=[WriteAttributesStatusRecord(Status.SUCCESS)]
        )
    )

    with mock.patch.object(cluster, "_write_attributes", write):
        await cluster.write_attributes({"system_mode": Thermostat.SystemMode.Off})

    assert write.mock_calls == [
        mock.call(
            [
                Attribute(
                    HOST_FLAGS_ATTR,
                    TypeValue(
                        type=cluster.AttributeDefs.host_flags.zcl_type,
                        value=t.uint24_t(1 | SET_OFF_MODE_FLAG),
                    ),
                )
            ],
            manufacturer=MANUFACTURER,
        )
    ]
