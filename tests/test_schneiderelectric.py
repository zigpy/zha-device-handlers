"""Tests for Schneider Electric devices."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
import zhaquirks.schneiderelectric.outlet
import zhaquirks.schneiderelectric.shutters

zhaquirks.setup()


def test_1gang_shutter_1_signature(assert_signature_matches_quirk):
    """Test signature."""
    signature = {
        "node_descriptor": (
            "NodeDescriptor(logical_type=<LogicalType.Router: 1>, "
            "complex_descriptor_available=0, user_descriptor_available=0, reserved=0, "
            "aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, "
            "mac_capability_flags=<MACCapabilityFlags.FullFunctionDevice|MainsPowered"
            "|RxOnWhenIdle|AllocateAddress: 142>, manufacturer_code=4190, "
            "maximum_buffer_size=82, maximum_incoming_transfer_size=82, "
            "server_mask=10752, maximum_outgoing_transfer_size=82, "
            "descriptor_capability_field=<DescriptorCapability.NONE: 0>, "
            "*allocate_address=True, *is_alternate_pan_coordinator=False, "
            "*is_coordinator=False, *is_end_device=False, "
            "*is_full_function_device=True, *is_mains_powered=True, "
            "*is_receiver_on_when_idle=True, *is_router=True, "
            "*is_security_capable=False)"
        ),
        "endpoints": {
            "5": {
                "profile_id": 0x0104,
                "device_type": "0x0202",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0102",
                    "0x0b05",
                ],
                "out_clusters": ["0x0019"],
            },
            "21": {
                "profile_id": 0x0104,
                "device_type": "0x0104",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0b05",
                    "0xff17",
                ],
                "out_clusters": [
                    "0x0003",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x0019",
                    "0x0102",
                ],
            },
        },
        "manufacturer": "Schneider Electric",
        "model": "1GANG/SHUTTER/1",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(
        zhaquirks.schneiderelectric.shutters.OneGangShutter1, signature
    )


async def test_1gang_shutter_1_go_to_lift_percentage_cmd(zigpy_device_from_quirk):
    """Asserts that the go_to_lift_percentage command inverts the percentage value."""

    device = zigpy_device_from_quirk(
        zhaquirks.schneiderelectric.shutters.OneGangShutter1
    )
    window_covering_cluster = device.endpoints[5].window_covering

    p = mock.patch.object(window_covering_cluster, "request", mock.AsyncMock())
    with p as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        await window_covering_cluster.go_to_lift_percentage(58)

        assert request_mock.call_count == 1
        assert request_mock.call_args[0][1] == (
            WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
        )
        assert request_mock.call_args[0][3] == 42  # 100 - 58


async def test_1gang_shutter_1_unpatched_cmd(zigpy_device_from_quirk):
    """Asserts that unpatched ZCL commands keep working."""

    device = zigpy_device_from_quirk(
        zhaquirks.schneiderelectric.shutters.OneGangShutter1
    )
    window_covering_cluster = device.endpoints[5].window_covering

    p = mock.patch.object(window_covering_cluster, "request", mock.AsyncMock())
    with p as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        await window_covering_cluster.up_open()

        assert request_mock.call_count == 1
        assert request_mock.call_args[0][1] == (
            WindowCovering.ServerCommandDefs.up_open.id
        )


async def test_1gang_shutter_1_lift_percentage_updates(zigpy_device_from_quirk):
    """Asserts that updates to the ``current_position_lift_percentage`` attribute.

    (e.g., by the device) invert the reported percentage value.
    """

    device = zigpy_device_from_quirk(
        zhaquirks.schneiderelectric.shutters.OneGangShutter1
    )
    window_covering_cluster = device.endpoints[5].window_covering
    cluster_listener = ClusterListener(window_covering_cluster)

    window_covering_cluster.update_attribute(
        WindowCovering.AttributeDefs.current_position_lift_percentage.id,
        77,
    )

    assert len(cluster_listener.attribute_updates) == 1
    assert cluster_listener.attribute_updates[0] == (
        WindowCovering.AttributeDefs.current_position_lift_percentage.id,
        23,  # 100 - 77
    )
    assert len(cluster_listener.cluster_commands) == 0


@pytest.mark.parametrize("quirk", (zhaquirks.schneiderelectric.outlet.SocketOutlet,))
async def test_schneider_device_temp(zigpy_device_from_quirk, quirk):
    """Test that instant demand is divided by 1000."""
    device = zigpy_device_from_quirk(quirk)

    metering_cluster = device.endpoints[6].smartenergy_metering
    metering_listener = ClusterListener(metering_cluster)
    instantaneous_demand_attr_id = Metering.AttributeDefs.instantaneous_demand.id
    summation_delivered_attr_id = Metering.AttributeDefs.current_summ_delivered.id

    # verify instant demand is divided by 1000
    metering_cluster.update_attribute(instantaneous_demand_attr_id, 25000)
    assert len(metering_listener.attribute_updates) == 1
    assert metering_listener.attribute_updates[0][0] == instantaneous_demand_attr_id
    assert metering_listener.attribute_updates[0][1] == 25  # divided by 1000

    # verify other attributes are not modified
    metering_cluster.update_attribute(summation_delivered_attr_id, 25)
    assert len(metering_listener.attribute_updates) == 2
    assert metering_listener.attribute_updates[1][0] == summation_delivered_attr_id
    assert metering_listener.attribute_updates[1][1] == 25  # not modified
