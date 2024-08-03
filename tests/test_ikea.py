"""Tests for Ikea Starkvind quirks."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, PowerConfiguration
from zigpy.zcl.clusters.measurement import PM25

from tests.common import ClusterListener
import zhaquirks
import zhaquirks.ikea.starkvind
from zhaquirks.ikea.starkvind import IkeaAirpurifier

zhaquirks.setup()


def test_ikea_starkvind(assert_signature_matches_quirk):
    """Test new 'STARKVIND Air purifier table' signature is matched to its quirk."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4476, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0007",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0202",
                    "0xfc57",
                    "0xfc7d",
                ],
                "out_clusters": ["0x0019", "0x0400", "0x042a"],
            },
            "242": {
                "profile_id": 41440,
                "device_type": "0x0061",
                "in_clusters": [],
                "out_clusters": ["0x0021"],
            },
        },
        "manufacturer": "IKEA of Sweden",
        "model": "STARKVIND Air purifier",
        "class": "ikea.starkvind.IkeaSTARKVIND",
    }

    assert_signature_matches_quirk(zhaquirks.ikea.starkvind.IkeaSTARKVIND, signature)


def test_ikea_starkvind_v2(assert_signature_matches_quirk):
    """Test new 'STARKVIND Air purifier table' signature is matched to its quirk."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4476, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0007",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0202",
                    "0xfc57",
                    "0xfc7c",
                    "0xfc7d",
                ],
                "out_clusters": ["0x0019", "0x0400", "0x042a"],
            },
            "242": {
                "profile_id": 41440,
                "device_type": "0x0061",
                "in_clusters": [],
                "out_clusters": ["0x0021"],
            },
        },
        "manufacturer": "IKEA of Sweden",
        "model": "STARKVIND Air purifier table",
        "class": "ikea.starkvind.IkeaSTARKVIND_v2",
    }

    assert_signature_matches_quirk(zhaquirks.ikea.starkvind.IkeaSTARKVIND_v2, signature)


@pytest.mark.parametrize("attribute", ["fan_speed", "fan_mode"])
@pytest.mark.parametrize(
    "value,expected",
    [
        (0, 0),  # off
        (1, 1),  # auto
        (10, 2),
        (20, 4),
        (50, 10),
    ],
)
async def test_fan_speed_mode_update(
    zigpy_device_from_quirk, attribute, value, expected
):
    """Test reading the fan speed and mode."""

    starkvind_device = zigpy_device_from_quirk(zhaquirks.ikea.starkvind.IkeaSTARKVIND)
    assert starkvind_device.model == "STARKVIND Air purifier"

    ikea_cluster = starkvind_device.endpoints[1].in_clusters[
        zhaquirks.ikea.starkvind.IkeaAirpurifier.cluster_id
    ]
    ikea_listener = ClusterListener(ikea_cluster)

    attr_id = getattr(IkeaAirpurifier.AttributeDefs, attribute).id

    ikea_cluster.update_attribute(attr_id, value)
    assert len(ikea_listener.attribute_updates) == 1
    assert ikea_listener.attribute_updates[0] == (attr_id, expected)


async def test_pm25_cluster_read(zigpy_device_from_quirk):
    """Test reading from PM25 cluster."""

    starkvind_device = zigpy_device_from_quirk(zhaquirks.ikea.starkvind.IkeaSTARKVIND)
    assert starkvind_device.model == "STARKVIND Air purifier"

    pm25_cluster = starkvind_device.endpoints[1].in_clusters[PM25.cluster_id]
    ikea_cluster = starkvind_device.endpoints[1].in_clusters[
        zhaquirks.ikea.starkvind.IkeaAirpurifier.cluster_id
    ]

    # Mock the read attribute to on the IkeaAirpurifier cluster
    # to always return 6 for anything.
    def mock_read(attributes, manufacturer=None):
        records = [
            foundation.ReadAttributeRecord(
                attr, foundation.Status.SUCCESS, foundation.TypeValue(None, 6)
            )
            for attr in attributes
        ]
        return (records,)

    patch_ikeacluster_read = mock.patch.object(
        ikea_cluster, "_read_attributes", mock.AsyncMock(side_effect=mock_read)
    )
    with patch_ikeacluster_read:
        # Reading "measured_value" should read the "air_quality_25pm" value from
        # the IkeaAirpurifier cluster
        success, fail = await pm25_cluster.read_attributes(["measured_value"])
        assert success
        assert 6 in success.values()
        assert not fail

        # Same call with allow_cache=True; a bug previously prevented this from working
        success, fail = await pm25_cluster.read_attributes(
            ["measured_value"], allow_cache=True
        )
        assert success
        assert 6 in success.values()
        assert not fail


@mock.patch("zigpy.zcl.Cluster.bind", mock.AsyncMock())
@pytest.mark.parametrize(
    "firmware, pct_device, pct_correct, expected_pct_updates, expect_log_warning",
    (
        ("1.0.024", 50, 100, 2, False),  # old firmware, doubling
        ("2.3.075", 50, 100, 2, False),  # old firmware, doubling
        ("2.4.5", 50, 50, 1, False),  # new firmware, no doubling
        ("3.0.0", 50, 50, 1, False),  # new firmware, no doubling
        ("24.4.5", 50, 50, 1, False),  # new firmware, no doubling
        ("invalid_fw_string_1", 50, 50, 1, False),  # treated as new, no doubling
        ("invalid.fw.string.2", 50, 50, 1, True),  # treated as new, no doubling + log
        ("", 50, 50, 1, False),  # treated as new fw, no doubling
    ),
)
async def test_double_power_config_firmware(
    caplog,
    zigpy_device_from_quirk,
    firmware,
    pct_device,
    pct_correct,
    expected_pct_updates,
    expect_log_warning,
):
    """Test battery percentage remaining is doubled for old firmware."""

    device = zigpy_device_from_quirk(zhaquirks.ikea.fivebtnremote.IkeaTradfriRemote1)

    basic_cluster = device.endpoints[1].basic
    ClusterListener(basic_cluster)
    sw_build_id = Basic.AttributeDefs.sw_build_id.id

    power_cluster = device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)
    battery_pct_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    # fake read response for attributes: return plug_read argument for all attributes
    def mock_read(attributes, manufacturer=None):
        records = [
            foundation.ReadAttributeRecord(
                attr, foundation.Status.SUCCESS, foundation.TypeValue(None, firmware)
            )
            for attr in attributes
        ]
        return (records,)

    p1 = mock.patch.object(power_cluster, "create_catching_task")
    p2 = mock.patch.object(
        basic_cluster, "_read_attributes", mock.AsyncMock(side_effect=mock_read)
    )

    with p1 as mock_task, p2 as request_mock:
        # update battery percentage with no firmware in attr cache, check pct not doubled for now
        power_cluster.update_attribute(battery_pct_id, pct_device)
        assert len(power_listener.attribute_updates) == 1
        assert power_listener.attribute_updates[0] == (battery_pct_id, pct_device)

        # but also check that sw_build_id read is requested in the background for next update
        assert mock_task.call_count == 1
        await mock_task.call_args[0][0]  # await coroutine to read attribute
        assert request_mock.call_count == 1  # verify request to read sw_build_id
        assert request_mock.mock_calls[0][1][0][0] == sw_build_id

        # battery pct might be updated again when the attribute read returned new firmware, check pct not doubled then
        # if firmware turned out to be old or still unknown, do not update battery pct again, as we doubled it already
        assert len(power_listener.attribute_updates) == expected_pct_updates
        if expected_pct_updates > 2:
            assert power_listener.attribute_updates[1] == (battery_pct_id, pct_correct)

        # reset mocks for testing when sw_build_id is known next
        mock_task.reset_mock()
        request_mock.reset_mock()
        power_listener = ClusterListener(power_cluster)

        # update battery percentage with firmware in attr cache, check pct doubled if needed
        basic_cluster.update_attribute(sw_build_id, firmware)
        power_cluster.update_attribute(battery_pct_id, pct_device)
        assert len(power_listener.attribute_updates) == 1
        assert power_listener.attribute_updates[0] == (battery_pct_id, pct_correct)

        # check no attribute reads were requested when sw_build_id is known
        assert mock_task.call_count == 0
        assert request_mock.call_count == 0

        # make sure a call to bind() always reads sw_build_id (e.g. on join or to refresh when repaired/reconfigured)
        await power_cluster.bind()
        assert request_mock.call_count == 1
        assert request_mock.mock_calls[0][1][0][0] == sw_build_id

        # check log output if we expect a warning
        if expect_log_warning:
            assert f"sw_build_id is not a number: {firmware} for device" in caplog.text
