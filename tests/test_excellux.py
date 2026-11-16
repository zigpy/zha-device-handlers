"""Tests for Excellux quirks."""

from unittest import mock

import pytest
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

import zhaquirks
from zhaquirks.excellux.ntcht01 import (
    Ntcht01RelativeHumidity,
    Ntcht01TemperatureMeasurement,
)
from zhaquirks.tuya import TuyaCommand, TuyaData, TuyaDatapointData
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()


def send_ntcht01_datapoints(device, datapoints: list[tuple[int, int]]) -> None:
    """Deliver a Tuya datapoint report to the device."""
    device.endpoints[1].tuya_manufacturer.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=1,
            datapoints=[
                TuyaDatapointData(dp, TuyaData(value)) for dp, value in datapoints
            ],
        )
    )


def send_standard_report(
    device,
    cluster,
    attrid: int,
    attr_type: foundation.DataTypeId,
    value,
    *,
    disable_default_response: bool = True,
) -> None:
    """Deliver a standard Report_Attributes frame from the device."""
    hdr = foundation.ZCLHeader.general(
        tsn=1,
        command_id=foundation.GeneralCommand.Report_Attributes,
        direction=foundation.Direction.Server_to_Client,
    )
    hdr.frame_control = hdr.frame_control.replace(
        disable_default_response=disable_default_response
    )
    command = foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Report_Attributes
    ].schema(
        attribute_reports=[
            foundation.Attribute(
                attrid=attrid,
                value=foundation.TypeValue(type=attr_type, value=value),
            )
        ]
    )
    device.packet_received(
        t.ZigbeePacket(
            profile_id=zha.PROFILE_ID,
            cluster_id=cluster.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(hdr.serialize() + command.serialize()),
        )
    )


def test_ntcht01_clusters(zigpy_device_from_v2_quirk):
    """Test that the quirk is applied and creates the expected clusters."""
    device = zigpy_device_from_v2_quirk("Excellux", "NTCHT01")
    ep = device.endpoints[1]

    assert isinstance(ep.basic, Basic)
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)
    assert isinstance(ep.temperature, Ntcht01TemperatureMeasurement)
    assert isinstance(ep.humidity, Ntcht01RelativeHumidity)
    assert isinstance(ep.power, PowerConfiguration)


@pytest.mark.parametrize("manuf,model", [("Excellux", "NTCHT02"), ("Excellux", "NTCHT03")])
def test_ntcht01_whitelabels(zigpy_device_from_v2_quirk, manuf, model):
    """Test that the white-label variants match the same quirk."""
    device = zigpy_device_from_v2_quirk(manuf, model)
    ep = device.endpoints[1]

    assert isinstance(ep.temperature, Ntcht01TemperatureMeasurement)
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)


def test_ntcht01_temperature_dp_mapping(zigpy_device_from_v2_quirk):
    """Test that the body reading (dp 5) feeds the main sensor and the probe
    reading (dp 1) feeds the probe sensor, each with its own scale."""
    device = zigpy_device_from_v2_quirk("Excellux", "NTCHT01")
    ep = device.endpoints[1]

    send_ntcht01_datapoints(
        device,
        [
            (1, 243),  # probe, tenths of a degree -> 24.3 C
            (5, 2500),  # body, hundredths of a degree -> 25.00 C
            (118, 4500),  # humidity, hundredths of a percent -> 45.00 %
            (4, 87),  # battery -> 87 %
        ],
    )

    # Main temperature comes from the body datapoint (dp 5, hundredths)
    assert ep.temperature.get("measured_value") == 2500
    # Probe temperature comes from the probe datapoint (dp 1, tenths)
    assert ep.tuya_manufacturer.get("probe_temperature") == 243
    assert ep.humidity.get("measured_value") == 4500
    assert ep.power.get("battery_percentage_remaining") == 174


def test_ntcht01_negative_temperatures(zigpy_device_from_v2_quirk):
    """Test that sub-zero readings survive on both temperature paths."""
    device = zigpy_device_from_v2_quirk("Excellux", "NTCHT01")
    ep = device.endpoints[1]

    send_ntcht01_datapoints(device, [(1, -31), (5, -310)])  # -3.1 C, -3.10 C

    assert ep.temperature.get("measured_value") == -310
    assert ep.tuya_manufacturer.get("probe_temperature") == -31


async def test_ntcht01_ignores_standard_reports(zigpy_device_from_v2_quirk):
    """Test that the device's periodic raw 0x0402/0x0405 reports (wrong scale)
    cannot overwrite the datapoint-fed values."""
    device = zigpy_device_from_v2_quirk("Excellux", "NTCHT01")
    ep = device.endpoints[1]

    send_ntcht01_datapoints(device, [(5, 2500), (118, 4500)])
    assert ep.temperature.get("measured_value") == 2500
    assert ep.humidity.get("measured_value") == 4500

    # The raw report carries the probe reading in tenths (243 == 24.3 C);
    # interpreted by the standard clusters it would display 2.43 C
    send_standard_report(
        device,
        ep.temperature,
        TemperatureMeasurement.AttributeDefs.measured_value.id,
        foundation.DataTypeId.int16,
        t.int16s(243),
    )
    send_standard_report(
        device,
        ep.humidity,
        RelativeHumidity.AttributeDefs.measured_value.id,
        foundation.DataTypeId.uint16,
        t.uint16_t(243),
    )

    assert ep.temperature.get("measured_value") == 2500
    assert ep.humidity.get("measured_value") == 4500

    # The next datapoint report still updates the values
    send_ntcht01_datapoints(device, [(5, 2430), (118, 4400)])
    assert ep.temperature.get("measured_value") == 2430
    assert ep.humidity.get("measured_value") == 4400


async def test_ntcht01_ignored_report_gets_default_response(zigpy_device_from_v2_quirk):
    """Test that a dropped standard report is still answered when requested."""
    device = zigpy_device_from_v2_quirk("Excellux", "NTCHT01")
    ep = device.endpoints[1]
    temp_cluster = ep.temperature
    measured_value_id = TemperatureMeasurement.AttributeDefs.measured_value.id

    with mock.patch.object(temp_cluster, "send_default_rsp") as mock_rsp:
        send_standard_report(
            device,
            temp_cluster,
            measured_value_id,
            foundation.DataTypeId.int16,
            t.int16s(243),
            disable_default_response=False,
        )
        assert mock_rsp.call_count == 1
        assert mock_rsp.call_args.args[0].command_id == (
            foundation.GeneralCommand.Report_Attributes
        )

        send_standard_report(
            device,
            temp_cluster,
            measured_value_id,
            foundation.DataTypeId.int16,
            t.int16s(243),
            disable_default_response=True,
        )
        assert mock_rsp.call_count == 1
