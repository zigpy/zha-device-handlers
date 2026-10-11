"""Tests for the Muller nativ radiator quirk."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import WriteAttributesStatusRecord

import zhaquirks
from zhaquirks.muller.nativ import (
    MULLER_MANUFACTURER_ID,
    NATIV_MODEL,
    PRESENCE_DETECTION_ATTR_ID,
    NativThermostatCluster,
)

zhaquirks.setup()

#: `model_identifier` payload captured from a Noirot Lavaroc, length byte
#: stripped. Pins the padding independently of how the quirk builds it.
MODEL_IDENTIFIER_PAYLOAD = bytes.fromhex(
    "696e747569737261646961746f722020202020202020202020202020202020"
)


def test_model_matches_the_payload_sent_by_the_radiator():
    """The quirk must match the padded model byte for byte."""
    assert MODEL_IDENTIFIER_PAYLOAD.decode() == NATIV_MODEL


@pytest.mark.parametrize("model", [NATIV_MODEL, NATIV_MODEL.strip()])
def test_nativ_quirk_applies_without_manufacturer_name(
    zigpy_device_from_v2_quirk, model
):
    """The radiators report no manufacturer name, so the model alone must match."""
    device = zigpy_device_from_v2_quirk(None, model)

    assert isinstance(device.endpoints[1].thermostat, NativThermostatCluster)


async def test_presence_detection_write_is_manufacturer_specific(
    zigpy_device_from_v2_quirk,
):
    """0xFC00 is rejected by the radiator unless the header carries 0x122E."""
    device = zigpy_device_from_v2_quirk(None, NATIV_MODEL)
    thermostat = device.endpoints[1].thermostat
    thermostat._write_attributes = mock.AsyncMock(
        side_effect=lambda attrs, **kw: [
            [WriteAttributesStatusRecord(foundation.Status.SUCCESS) for _ in attrs],
            [],
        ]
    )

    await thermostat.write_attributes({"presence_detection": 1})

    records, kwargs = (
        thermostat._write_attributes.await_args.args[0],
        thermostat._write_attributes.await_args.kwargs,
    )
    assert kwargs["manufacturer"] == MULLER_MANUFACTURER_ID
    assert records[0].attrid == PRESENCE_DETECTION_ATTR_ID
    assert records[0].value.value == 1


async def test_standard_attribute_write_stays_unmanufactured(
    zigpy_device_from_v2_quirk,
):
    """Adding the custom attribute must not taint the standard setpoints."""
    device = zigpy_device_from_v2_quirk(None, NATIV_MODEL)
    thermostat = device.endpoints[1].thermostat
    thermostat._write_attributes = mock.AsyncMock(
        side_effect=lambda attrs, **kw: [
            [WriteAttributesStatusRecord(foundation.Status.SUCCESS) for _ in attrs],
            [],
        ]
    )

    await thermostat.write_attributes({"unoccupied_heating_setpoint": 1600})

    records, kwargs = (
        thermostat._write_attributes.await_args.args[0],
        thermostat._write_attributes.await_args.kwargs,
    )
    assert kwargs["manufacturer"] is None
    assert records[0].attrid == Thermostat.AttributeDefs.unoccupied_heating_setpoint.id
    assert records[0].value.value == 1600
