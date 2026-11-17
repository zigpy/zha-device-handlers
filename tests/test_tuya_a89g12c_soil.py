"""Functional test for the A89G12C Arteco soil sensor quirk.

Loads the quirk, applies it to a simulated device matching the real
device signature, feeds it synthetic Tuya datapoint reports, and checks
that soil_moisture / illuminance / soil_conductivity decode correctly and
that the duplicate RelativeHumidity cluster is removed.
"""

from zha.quirks import DEVICE_REGISTRY
from zha.units import UnitOfConductivity

from zhaquirks.tuya import TuyaCommand, TuyaData, TuyaDatapointData
import zhaquirks.tuya.tuya_a89g12c_soil  # noqa: F401  (registers the quirk)


def test_quirk_matches_removes_humidity_and_decodes_datapoints(
    zigpy_device_from_v2_quirk,
):
    """Check that the quirk removes RelativeHumidity and decodes datapoints.

    Applying the quirk should remove the duplicate humidity cluster and
    correctly decode soil_moisture / illuminance / soil_conductivity from
    their Tuya datapoints.
    """
    device = zigpy_device_from_v2_quirk(
        "A89G12C",
        "Arteco",
        endpoint_ids=[1],
        cluster_ids={
            1: {
                0x0001: 0,  # Power config
                0x0003: 0,  # Identify
                0x0402: 0,  # Temperature
                0x0405: 0,  # Relative humidity - duplicates soil moisture, must be removed
                0xEF00: 0,  # Tuya MCU cluster
            }
        },
    )

    ep = device.endpoints[1]
    assert 0x0405 not in ep.in_clusters, (
        "RelativeHumidity cluster should have been removed"
    )
    assert 0x0402 in ep.in_clusters, "Temperature cluster should stay untouched"
    assert 0x0001 in ep.in_clusters, "Power (battery) cluster should stay untouched"

    tuya_cluster = ep.in_clusters[0xEF00]

    cmd = TuyaCommand(
        status=0,
        tsn=1,
        datapoints=[
            TuyaDatapointData(3, TuyaData(42)),  # soil_moisture
            TuyaDatapointData(102, TuyaData(850)),  # illuminance
            TuyaDatapointData(112, TuyaData(1200)),  # soil_conductivity
        ],
    )
    tuya_cluster.handle_get_data(cmd)

    assert tuya_cluster.get("soil_moisture") == 42
    assert tuya_cluster.get("illuminance") == 850
    assert tuya_cluster.get("soil_conductivity") == 1200


def test_soil_conductivity_has_device_class_and_correct_unit():
    """Regression test for the plant-monitor picker issue.

    HA's plant integrations (Plant Monitor / homeassistant-plant) filter
    candidate sensors by device_class, and validate the reported unit
    against the device_class's allowed units. Both must be set correctly
    or the entity silently won't show up as selectable.
    """
    matches = [
        q
        for q in DEVICE_REGISTRY
        if any(
            m.manufacturer == "A89G12C" and m.model == "Arteco"
            for m in q.device_match.applies_to
        )
    ]
    assert matches, "quirk not found in registry"
    quirk_def = matches[0].zha_device_factory.quirk_definition

    ec_meta = next(
        m
        for m in quirk_def.entity_metadata
        if getattr(m, "attribute_name", None) == "soil_conductivity"
    )
    assert ec_meta.device_class is not None, "soil_conductivity is missing device_class"
    assert ec_meta.device_class.value == "conductivity"
    assert ec_meta.unit == UnitOfConductivity.MICROSIEMENS_PER_CM
