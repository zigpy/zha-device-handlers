"""Test for HOBEIAN ZG-303Z soil sensor."""

from unittest.mock import MagicMock

import pytest
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.measurement import (
    RelativeHumidity,
    SoilMoisture,
    TemperatureMeasurement,
)

from zhaquirks.tuya import TuyaData, TuyaDatapointData, TuyaDPType
from zhaquirks.tuya.ts0601_soil import (
    HobeianMcuCluster,
    HobeianRelativeHumidity,
    HobeianSoilMoisture,
    HobeianZG303Z,
)


def test_signature(assert_signature_matches_quirk):
    """Test signature."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0302",
                "in_clusters": [
                    "0x0000",
                    "0x0001",
                    "0x0003",
                    "0x0402",
                    "0x0405",
                    "0xef00",
                ],
                "out_clusters": ["0x0003"],
            }
        },
        "manufacturer": "HOBEIAN",
        "model": "ZG-303Z",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(HobeianZG303Z, signature)


@pytest.mark.parametrize(
    "dp, attribute_name, value, expected, endpoint_id, cluster, cluster_id",
    [
        (
            3,
            "measured_value",
            50,
            5000,
            2,
            HobeianSoilMoisture,
            SoilMoisture.cluster_id,
        ),
        (
            5,
            "measured_value",
            25,
            250,
            1,
            TemperatureMeasurement,
            TemperatureMeasurement.cluster_id,
        ),
        (
            15,
            "battery_percentage_remaining",
            95,
            95,
            1,
            PowerConfiguration,
            PowerConfiguration.cluster_id,
        ),
        (
            109,
            "measured_value",
            60,
            6000,
            3,
            HobeianRelativeHumidity,
            RelativeHumidity.cluster_id,
        ),
    ],
)
async def test_mcu_cluster(
    dp, attribute_name, value, expected, endpoint_id, cluster, cluster_id
):
    """Test Tuya MCU cluster."""
    endpoint_mock = MagicMock()
    endpoint_mock.in_clusters = {}
    mcu_cluster = HobeianMcuCluster(endpoint_mock)
    mcu_cluster.endpoint.device.endpoints = {
        1: endpoint_mock,
        2: MagicMock(),
        3: MagicMock(),
    }

    mock_cluster = MagicMock()
    if endpoint_id == 1:
        mcu_cluster.endpoint.device.endpoints[endpoint_id].in_clusters[cluster_id] = (
            mock_cluster
        )
        setattr(
            mcu_cluster.endpoint.device.endpoints[endpoint_id],
            cluster.ep_attribute,
            mock_cluster,
        )
    else:
        mcu_cluster.endpoint.device.endpoints[endpoint_id].in_clusters = {
            cluster_id: mock_cluster
        }
        setattr(
            mcu_cluster.endpoint.device.endpoints[endpoint_id],
            cluster.ep_attribute,
            mock_cluster,
        )

    # Create TuyaDatapointData object
    tuya_data = TuyaData()
    tuya_data.dp_type = TuyaDPType.VALUE
    tuya_data.payload = value
    datapoint = TuyaDatapointData()
    datapoint.dp = dp
    datapoint.data = tuya_data

    # Call the method to test
    mcu_cluster._dp_2_attr_update(datapoint)

    # Assert that the attribute was updated
    mock_cluster.update_attribute.assert_called_once_with(attribute_name, expected)
