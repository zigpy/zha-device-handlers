"""Custom ZHA Quirk for Tuya TS0601 _TZE200_seq9cm6u Pressure/Occupancy Mat."""

from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaPowerConfigurationCluster

(
    TuyaQuirkBuilder("_TZE200_seq9cm6u", "TS0601")
    .applies_to(
        b_input_clusters=[0x0000, 0xEF00],
        b_output_clusters=[0x000A, 0x0019],
    )
    .tuya_dp(
        dp_id=1,
        ep_attribute=OccupancySensing.ep_attribute,
        attribute_name="occupancy",
        converter=lambda x: not x,
    )
    .tuya_dp(
        dp_id=4,
        ep_attribute=TuyaPowerConfigurationCluster.ep_attribute,
        attribute_name="battery_percentage_remaining",
    )
    .adds(OccupancySensing)
    .adds(TuyaPowerConfigurationCluster)
    .add_to_registry()
)
