"""Tests for Namron quirks."""

import zhaquirks
import zhaquirks.namron.namron_4512783

zhaquirks.setup()


def test_namron_4512783_signature(assert_signature_matches_quirk):
    """Test signature matching for Namron 4512783 floor heating thermostat."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4714, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0301",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0201",
                    "0x0204",
                    "0x0405",
                    "0x0702",
                    "0x0b04",
                    "0x1000",
                    "0xe002",
                ],
                "out_clusters": ["0x0003", "0x0019", "0x0406"],
            },
            "242": {
                "profile_id": 41440,
                "device_type": "0x0061",
                "in_clusters": [],
                "out_clusters": ["0x0021"],
            },
        },
        "manufacturer": "Namron AS",
        "model": "4512783",
        "class": "zhaquirks.namron.namron_4512783.NamronFloorHeating4512783",
    }
    assert_signature_matches_quirk(
        zhaquirks.namron.namron_4512783.NamronFloorHeating4512783, signature
    )


def test_namron_thermostat_cluster_attributes():
    """Test that the custom thermostat cluster has the expected manufacturer-specific attributes."""
    from zhaquirks.namron.namron_4512783 import (
        NamronOperationMode,
        NamronThermostatCluster,
    )

    # Verify manufacturer-specific attributes are defined
    assert hasattr(NamronThermostatCluster.AttributeDefs, "operation_mode")
    assert hasattr(NamronThermostatCluster.AttributeDefs, "regulator_percentage")

    # Verify attribute IDs
    assert NamronThermostatCluster.AttributeDefs.operation_mode.id == 0x8004
    assert NamronThermostatCluster.AttributeDefs.regulator_percentage.id == 0x801D

    # Verify attributes are marked as manufacturer-specific
    assert NamronThermostatCluster.AttributeDefs.operation_mode.is_manufacturer_specific
    assert NamronThermostatCluster.AttributeDefs.regulator_percentage.is_manufacturer_specific

    # Verify operation mode enum values
    assert NamronOperationMode.Thermostat == 0x00
    assert NamronOperationMode.Regulator == 0x06
