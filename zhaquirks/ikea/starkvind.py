"""Device handler for IKEA of Sweden STARKVIND Air purifier."""

from __future__ import annotations

from typing import Any, Final

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Fan
from zigpy.zcl.clusters.measurement import PM25
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    BinarySensorDeviceClass,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster
from zhaquirks.ikea import IKEA

# The device reports fan mode and fan speed in steps of five (10-50), which are
# scaled down to the 2-10 range ZHA's fan entity expects. 0 is off and 1 is auto.
FAN_STEP: Final = 5
FAN_RAW_MIN: Final = 10
FAN_RAW_MAX: Final = 50
FAN_MIN: Final = FAN_RAW_MIN // FAN_STEP  # 2
FAN_MAX: Final = FAN_RAW_MAX // FAN_STEP  # 10

# Report as soon as the value changes, and at least every 15 minutes.
REPORT_ON_CHANGE: Final = ReportingConfig(
    min_interval=0, max_interval=900, reportable_change=1
)
# Same, but for the counters that tick every minute: at most one report per 30s.
REPORT_THROTTLED: Final = ReportingConfig(
    min_interval=30, max_interval=900, reportable_change=1
)


class IkeaAirpurifier(CustomCluster):
    """Ikea Manufacturer Specific AirPurifier."""

    name: str = "Ikea Airpurifier"
    cluster_id: t.uint16_t = 0xFC7D  # 64637  0xFC7D control air purifier with manufacturer-specific attributes
    ep_attribute: str = "ikea_airpurifier"

    class AttributeDefs(BaseAttributeDefs):
        """Cluster attributes."""

        filter_run_time: Final = ZCLAttributeDef(
            id=0x0000, type=t.uint32_t, manufacturer_code=0x117C
        )
        replace_filter: Final = ZCLAttributeDef(
            id=0x0001, type=t.uint8_t, manufacturer_code=0x117C
        )
        filter_life_time: Final = ZCLAttributeDef(
            id=0x0002, type=t.uint32_t, manufacturer_code=0x117C
        )
        disable_led: Final = ZCLAttributeDef(
            id=0x0003, type=t.Bool, manufacturer_code=0x117C
        )
        # PM2.5 in µg/m³. 0xFFFF means the value is unavailable (device off),
        # which ZHA already surfaces as "unknown" for a uint16 attribute.
        air_quality_25pm: Final = ZCLAttributeDef(
            id=0x0004, type=t.uint16_t, manufacturer_code=0x117C
        )
        child_lock: Final = ZCLAttributeDef(
            id=0x0005, type=t.Bool, manufacturer_code=0x117C
        )
        fan_mode: Final = ZCLAttributeDef(
            id=0x0006, type=t.uint8_t, manufacturer_code=0x117C
        )  # fan mode (Off, Auto, fanspeed 10 - 50)  read/write
        fan_speed: Final = ZCLAttributeDef(
            id=0x0007, type=t.uint8_t, manufacturer_code=0x117C
        )  # current fan speed (only fan speed 10-50)
        device_run_time: Final = ZCLAttributeDef(
            id=0x0008, type=t.uint32_t, manufacturer_code=0x117C
        )

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Scale the reported fan mode and fan speed down to 2-10."""
        if (
            attrid in (self.AttributeDefs.fan_mode.id, self.AttributeDefs.fan_speed.id)
            and FAN_RAW_MIN <= value <= FAN_RAW_MAX
        ):
            value = value // FAN_STEP
        super()._update_attribute(attrid, value)

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Scale a written fan mode back up to the device's 10-50 range."""
        fan_mode_name = self.AttributeDefs.fan_mode.name
        fan_mode = attributes.get(fan_mode_name)
        if fan_mode is not None and FAN_MIN <= fan_mode <= FAN_MAX:
            attributes = {**attributes, fan_mode_name: fan_mode * FAN_STEP}
        return await super().write_attributes(attributes, **kwargs)


(
    QuirkBuilder(IKEA, "STARKVIND Air purifier")
    .applies_to(IKEA, "STARKVIND Air purifier table")
    # The device exposes a standard `Fan` cluster, but it is not implemented.
    # Fan control happens through the manufacturer specific cluster below.
    .removes(Fan.cluster_id)
    .replaces(IkeaAirpurifier)
    # PM2.5 is only reported on the manufacturer specific cluster. This quirk used
    # to mirror it onto a virtual `PM25` cluster, which made ZHA bind and configure
    # reporting for an attribute the device does not implement. The unique_id of
    # that sensor is preserved here so the entity survives the change.
    .sensor(
        attribute_name=IkeaAirpurifier.AttributeDefs.air_quality_25pm.name,
        cluster_id=IkeaAirpurifier.cluster_id,
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,
        unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        reporting_config=REPORT_ON_CHANGE,
        unique_id_suffix=str(PM25.cluster_id),
        fallback_name="PM2.5",
    )
    .binary_sensor(
        attribute_name=IkeaAirpurifier.AttributeDefs.replace_filter.name,
        cluster_id=IkeaAirpurifier.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        reporting_config=REPORT_ON_CHANGE,
        unique_id_suffix=f"{IkeaAirpurifier.cluster_id}-replace_filter",
        translation_key="replace_filter",
        fallback_name="Replace filter",
    )
    .sensor(
        attribute_name=IkeaAirpurifier.AttributeDefs.filter_run_time.name,
        cluster_id=IkeaAirpurifier.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        reporting_config=REPORT_THROTTLED,
        unique_id_suffix=f"{IkeaAirpurifier.cluster_id}-filter_run_time",
        translation_key="filter_run_time",
        fallback_name="Filter run time",
    )
    .sensor(
        attribute_name=IkeaAirpurifier.AttributeDefs.device_run_time.name,
        cluster_id=IkeaAirpurifier.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        reporting_config=REPORT_THROTTLED,
        unique_id_suffix=f"{IkeaAirpurifier.cluster_id}-device_run_time",
        translation_key="device_run_time",
        fallback_name="Device run time",
    )
    .number(
        attribute_name=IkeaAirpurifier.AttributeDefs.filter_life_time.name,
        cluster_id=IkeaAirpurifier.cluster_id,
        min_value=0,
        max_value=0xFFFFFFFF,
        unit=UnitOfTime.MINUTES,
        reporting_config=REPORT_THROTTLED,
        unique_id_suffix=f"{IkeaAirpurifier.cluster_id}-filter_life_time",
        translation_key="filter_life_time",
        fallback_name="Filter life time",
    )
    .switch(
        attribute_name=IkeaAirpurifier.AttributeDefs.child_lock.name,
        cluster_id=IkeaAirpurifier.cluster_id,
        reporting_config=REPORT_ON_CHANGE,
        unique_id_suffix=f"{IkeaAirpurifier.cluster_id}-child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .switch(
        attribute_name=IkeaAirpurifier.AttributeDefs.disable_led.name,
        cluster_id=IkeaAirpurifier.cluster_id,
        reporting_config=REPORT_ON_CHANGE,
        unique_id_suffix=f"{IkeaAirpurifier.cluster_id}-disable_led",
        translation_key="disable_led",
        fallback_name="Disable LED",
    )
    .add_to_registry()
)
