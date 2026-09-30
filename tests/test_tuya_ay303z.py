"""Tests for the AOYAN AY-303Z Tuya soil sensor."""

from unittest import mock

from zha.quirks import DEVICE_REGISTRY
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic, Identify, PowerConfiguration
from zigpy.zcl.clusters.measurement import (
    RelativeHumidity,
    SoilMoisture,
    TemperatureMeasurement,
)

from tests.common import wait_for_zigpy_tasks
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.tuya import TUYA_CLUSTER_ID, TuyaCommand, TuyaData, TuyaDatapointData
from zhaquirks.tuya.builder import TuyaSoilMoisture
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.tuya_sensor import AY303ZRelativeHumidity, TuyaTempUnitConvert

AY303Z_MANUFACTURER = "AOYAN  "
AY303Z_MODEL = "AY-303Z"
AY303Z_CLUSTERS = {
    1: {
        Basic.cluster_id: ClusterType.Server,
        Identify.cluster_id: ClusterType.Server,
        PowerConfiguration.cluster_id: ClusterType.Server,
        TemperatureMeasurement.cluster_id: ClusterType.Server,
        RelativeHumidity.cluster_id: ClusterType.Server,
        TUYA_CLUSTER_ID: ClusterType.Server,
    }
}


def _make_ay303z(zigpy_device_from_v2_quirk, manufacturer=AY303Z_MANUFACTURER):
    """Create an AY-303Z from its stock device signature."""
    return zigpy_device_from_v2_quirk(
        manufacturer,
        AY303Z_MODEL,
        cluster_ids=AY303Z_CLUSTERS,
    )


def test_ay303z_match_and_clusters(zigpy_device_from_v2_quirk) -> None:
    """Test matching the stock signature and applying cluster replacements."""
    device = _make_ay303z(zigpy_device_from_v2_quirk)
    assert isinstance(device, CustomZigpyDevice)

    endpoint = device.endpoints[1]
    assert isinstance(endpoint.tuya_manufacturer, TuyaMCUCluster)
    assert isinstance(endpoint.temperature, TemperatureMeasurement)
    assert isinstance(endpoint.power, PowerConfiguration)
    assert isinstance(endpoint.humidity, AY303ZRelativeHumidity)
    assert isinstance(endpoint.soil_moisture, TuyaSoilMoisture)

    unpadded = _make_ay303z(zigpy_device_from_v2_quirk, manufacturer="AOYAN")
    assert not isinstance(unpadded, CustomZigpyDevice)


def test_ay303z_datapoints(zigpy_device_from_v2_quirk) -> None:
    """Test measurement, warning, and configuration datapoint mappings."""
    device = _make_ay303z(zigpy_device_from_v2_quirk)
    endpoint = device.endpoints[1]
    endpoint.tuya_manufacturer.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=1,
            datapoints=[
                TuyaDatapointData(3, TuyaData(42)),
                TuyaDatapointData(5, TuyaData(235)),
                TuyaDatapointData(9, TuyaData(TuyaTempUnitConvert.Fahrenheit)),
                TuyaDatapointData(15, TuyaData(87)),
                TuyaDatapointData(102, TuyaData(-4)),
                TuyaDatapointData(104, TuyaData(-5)),
                TuyaDatapointData(105, TuyaData(3)),
                TuyaDatapointData(106, TuyaData(True)),
                TuyaDatapointData(109, TuyaData(61)),
                TuyaDatapointData(110, TuyaData(20)),
                TuyaDatapointData(111, TuyaData(300)),
                TuyaDatapointData(112, TuyaData(600)),
            ],
        )
    )

    assert endpoint.soil_moisture.get("measured_value") == 4200
    assert endpoint.temperature.get("measured_value") == 2350
    assert endpoint.power.get("battery_percentage_remaining") == 174
    assert endpoint.humidity.get("measured_value") == 6100

    tuya = endpoint.tuya_manufacturer
    assert tuya.get("temperature_unit") == TuyaTempUnitConvert.Fahrenheit
    assert tuya.get("soil_calibration") == -4
    assert tuya.get("temperature_calibration") == -5
    assert tuya.get("humidity_calibration") == 3
    assert bool(tuya.get("dry")) is True
    assert tuya.get("soil_warning") == 20
    assert tuya.get("temperature_sampling") == 300
    assert tuya.get("soil_sampling") == 600


def test_ay303z_native_humidity_report_ignored(zigpy_device_from_v2_quirk) -> None:
    """Test a native soil-like humidity report cannot overwrite DP109."""
    device = _make_ay303z(zigpy_device_from_v2_quirk)
    endpoint = device.endpoints[1]
    endpoint.tuya_manufacturer.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=1,
            datapoints=[TuyaDatapointData(109, TuyaData(61))],
        )
    )
    assert endpoint.humidity.get("measured_value") == 6100

    hdr = foundation.ZCLHeader.general(
        tsn=2,
        command_id=foundation.GeneralCommand.Report_Attributes,
        direction=foundation.Direction.Server_to_Client,
    )
    hdr = hdr.replace(
        frame_control=hdr.frame_control.replace(disable_default_response=False)
    )
    report = foundation.Attribute(
        attrid=RelativeHumidity.AttributeDefs.measured_value.id,
        value=foundation.TypeValue(type=t.uint16_t, value=t.uint16_t(4200)),
    )
    args = foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Report_Attributes
    ].schema([report])

    with mock.patch.object(endpoint.humidity, "send_default_rsp") as default_rsp:
        endpoint.humidity.handle_cluster_general_request(hdr, args)

    assert endpoint.humidity.get("measured_value") == 6100
    default_rsp.assert_called_once_with(hdr, foundation.Status.SUCCESS)


async def test_ay303z_humidity_delegates_general_requests(
    zigpy_device_from_v2_quirk,
) -> None:
    """Test ordinary general requests are delegated to the parent cluster."""
    device = _make_ay303z(zigpy_device_from_v2_quirk)
    humidity = device.endpoints[1].humidity
    hdr = foundation.ZCLHeader.general(
        tsn=3,
        command_id=foundation.GeneralCommand.Read_Attributes,
        direction=foundation.Direction.Client_to_Server,
    )
    args = foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Read_Attributes
    ].schema(attribute_ids=[RelativeHumidity.AttributeDefs.measured_value.id])

    with mock.patch.object(
        humidity, "read_attributes_rsp", new=mock.AsyncMock()
    ) as read_attributes_rsp:
        humidity.handle_cluster_general_request(hdr, args)
        await wait_for_zigpy_tasks()

    read_attributes_rsp.assert_awaited_once()
    records = read_attributes_rsp.await_args.args[0]
    assert records == [
        foundation.ReadAttributeRecord(
            attrid=RelativeHumidity.AttributeDefs.measured_value.id,
            status=foundation.Status.UNSUPPORTED_ATTRIBUTE,
        )
    ]


def test_ay303z_entity_metadata(zigpy_device_from_v2_quirk) -> None:
    """Test all Tuya-backed entities are declared exactly once."""
    device = _make_ay303z(zigpy_device_from_v2_quirk)
    entry = DEVICE_REGISTRY.match_entry(device)
    assert entry is not None

    metadata = entry.zha_device_factory.quirk_definition.entity_metadata
    assert [entity.attribute_name for entity in metadata] == [
        "dry",
        "temperature_unit",
        "temperature_calibration",
        "humidity_calibration",
        "soil_calibration",
        "temperature_sampling",
        "soil_sampling",
        "soil_warning",
    ]

    endpoint = device.endpoints[1]
    assert list(endpoint.in_clusters).count(RelativeHumidity.cluster_id) == 1
    assert list(endpoint.in_clusters).count(SoilMoisture.cluster_id) == 1
