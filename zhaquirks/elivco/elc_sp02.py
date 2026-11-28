"""Elivco ELC-SP02 smart plug with power monitoring."""

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
)
from zhaquirks.clusters import CustomCluster


class ElivcoElectricalMeasurementCluster(CustomCluster):
    """Elivco custom cluster for electrical measurements.

    Uses eWeLink firmware cluster 0xFC11.
    """

    cluster_id = 0xFC11
    name = "Elivco Electrical Measurement"
    ep_attribute = "elivco_electrical_measurement"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # Current in milliamps (mA)
        current = ZCLAttributeDef(
            id=0x7004,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        # Voltage in millivolts (mV)
        voltage = ZCLAttributeDef(
            id=0x7005,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        # Power in milliwatts (mW)
        power = ZCLAttributeDef(
            id=0x7006,
            type=t.uint32_t,
            manufacturer_code=None,
        )


(
    QuirkBuilder("eWeLink", "CK-BL702-SWP-01(7020)")
    .replaces(ElivcoElectricalMeasurementCluster, endpoint_id=1)
    .sensor(
        attribute_name=ElivcoElectricalMeasurementCluster.AttributeDefs.voltage.name,
        cluster_id=ElivcoElectricalMeasurementCluster.cluster_id,
        divisor=1000,  # Convert mV to V
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        reporting_config=ReportingConfig(
            min_interval=10,
            max_interval=300,
            reportable_change=100,  # 0.1V
        ),
        fallback_name="Voltage",
    )
    .sensor(
        attribute_name=ElivcoElectricalMeasurementCluster.AttributeDefs.current.name,
        cluster_id=ElivcoElectricalMeasurementCluster.cluster_id,
        divisor=1000,  # Convert mA to A
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricCurrent.AMPERE,
        reporting_config=ReportingConfig(
            min_interval=10,
            max_interval=300,
            reportable_change=10,  # 0.01A
        ),
        fallback_name="Current",
    )
    .sensor(
        attribute_name=ElivcoElectricalMeasurementCluster.AttributeDefs.power.name,
        cluster_id=ElivcoElectricalMeasurementCluster.cluster_id,
        divisor=1000,  # Convert mW to W
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.WATT,
        reporting_config=ReportingConfig(
            min_interval=10,
            max_interval=300,
            reportable_change=100,  # 0.1W
        ),
        fallback_name="Power",
    )
    .add_to_registry()
)
