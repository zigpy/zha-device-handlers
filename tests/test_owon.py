"""Test units for Owon units."""

import pytest
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks
from zhaquirks.const import ENDPOINTS, INPUT_CLUSTERS
from zhaquirks.owon.pc321 import (
    ELECTRICAL_MEASUREMENT_CONSTANT_ATTRIBUTES,
    METERING_CONSTANT_ATTRIBUTES,
    Owon_PC321,
    OwonElectricalMeasurementPhaseA,
    OwonElectricalMeasurementPhaseB,
    OwonElectricalMeasurementPhaseC,
    OwonManufacturerSpecific,
    OwonMeteringPhaseA,
    OwonMeteringPhaseB,
    OwonMeteringPhaseC,
)

zhaquirks.setup()


def test_pc321_signature(assert_signature_matches_quirk):
    """Test Owon_PC321 cover signature is matched to its quirk."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.FullFunctionDevice|MainsPowered|RxOnWhenIdle|AllocateAddress: 142>, manufacturer_code=4412, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 0x0104,
                "device_type": "0x000d",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0702",
                ],
                "out_clusters": ["0x0003"],
            }
        },
        "manufacturer": "OWON Technology Inc.",
        "model": "PC321",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(Owon_PC321, signature)


BUS_NAMES = [
    "energy_consumption_ph_a_bus",
    "energy_consumption_ph_b_bus",
    "energy_consumption_ph_c_bus",
    "total_energy_consumption_bus",
    "active_power_bus",
    "active_power_ph_b_bus",
    "active_power_ph_c_bus",
    "total_active_power_bus",
    "reactive_power_bus",
    "reactive_power_ph_b_bus",
    "reactive_power_ph_c_bus",
    "total_reactive_power_bus",
    "rms_voltage_bus",
    "rms_voltage_ph_b_bus",
    "rms_voltage_ph_c_bus",
    "active_current_bus",
    "active_current_ph_b_bus",
    "active_current_ph_c_bus",
    "instantaneous_active_current_bus",
    "reactive_energy_consumption_ph_a_bus",
    "reactive_energy_consumption_ph_b_bus",
    "reactive_energy_consumption_ph_c_bus",
    "total_reactive_energy_consumption_bus",
    "ac_frequency_bus",
    "leakage_current_bus",
]


@pytest.mark.parametrize("quirk", (zhaquirks.owon.pc321.Owon_PC321,))
def test_pc321_replacement(zigpy_device_from_quirk, quirk):
    """Test that the quirk has appropriate replacement endpoints."""
    device = zigpy_device_from_quirk(quirk)
    assert device.replacement is not None

    # check that the replacement first endpoint has ManufacturerSpecificCluster
    assert quirk.replacement[ENDPOINTS][1][INPUT_CLUSTERS].pop().cluster_id == 0xFD32

    # check that quirk has necessary buses
    for bus in BUS_NAMES:
        assert isinstance(device.__dict__[bus], zhaquirks.Bus)

    for endpoint_id, endpoint in quirk.replacement[ENDPOINTS].items():
        if endpoint_id == 1:
            continue
        for cluster in endpoint[INPUT_CLUSTERS]:
            # must expose only Metering or ElectricalMeasurement subclasses
            assert issubclass(cluster, Metering) or issubclass(
                cluster, ElectricalMeasurement
            )


def test_ManufacturerSpecific_cluster():
    """Test Manufacturer specific cluster has necessary functions."""

    for fn in BUS_NAMES:
        assert callable(
            getattr(OwonManufacturerSpecific, fn.replace("_bus", "_reported"))
        )


def test_ElectricalMeasurement_clusters():
    """Test ElectricalMeasurement cluster has necessary functions."""

    assert (
        OwonElectricalMeasurementPhaseA._CONSTANT_ATTRIBUTES
        == ELECTRICAL_MEASUREMENT_CONSTANT_ATTRIBUTES
    )
    assert (
        OwonElectricalMeasurementPhaseB._CONSTANT_ATTRIBUTES
        == ELECTRICAL_MEASUREMENT_CONSTANT_ATTRIBUTES
    )
    assert (
        OwonElectricalMeasurementPhaseC._CONSTANT_ATTRIBUTES
        == ELECTRICAL_MEASUREMENT_CONSTANT_ATTRIBUTES
    )
    assert callable(OwonElectricalMeasurementPhaseA.rms_voltage_reported)
    assert callable(OwonElectricalMeasurementPhaseA.active_power_reported)
    assert callable(OwonElectricalMeasurementPhaseB.rms_voltage_ph_b_reported)
    assert callable(OwonElectricalMeasurementPhaseB.active_power_ph_b_reported)
    assert callable(OwonElectricalMeasurementPhaseC.rms_voltage_ph_c_reported)
    assert callable(OwonElectricalMeasurementPhaseC.active_power_ph_c_reported)


def test_Metering_clusters():
    """Test Metering cluster has necessary functions."""

    assert OwonMeteringPhaseA._CONSTANT_ATTRIBUTES == METERING_CONSTANT_ATTRIBUTES
    assert OwonMeteringPhaseB._CONSTANT_ATTRIBUTES == METERING_CONSTANT_ATTRIBUTES
    assert OwonMeteringPhaseC._CONSTANT_ATTRIBUTES == METERING_CONSTANT_ATTRIBUTES
    assert callable(OwonMeteringPhaseA.energy_consumption_ph_a_reported)
    assert callable(OwonMeteringPhaseA.active_power_reported)
    assert callable(OwonMeteringPhaseB.energy_consumption_ph_b_reported)
    assert callable(OwonMeteringPhaseB.active_power_ph_b_reported)
    assert callable(OwonMeteringPhaseC.energy_consumption_ph_c_reported)
    assert callable(OwonMeteringPhaseC.active_power_ph_c_reported)
