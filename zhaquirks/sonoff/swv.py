"""Sonoff SWV - Zigbee smart water valve."""

import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.builder import BinarySensorDeviceClass, QuirkBuilder, ReportingConfig
from zhaquirks.clusters import CustomCluster


class ValveState(t.enum8):
    """Water valve state."""

    Normal = 0
    Water_Shortage = 1
    Water_Leakage = 2
    Water_Shortage_And_Leakage = 3


class SonoffSWVTimerCluster(LocalDataCluster):
    """Local cluster for the Sonoff SWV watering timer."""

    cluster_id = 0xFC12

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        watering_duration = ZCLAttributeDef(
            id=0x0000,
            type=t.uint16_t,
            manufacturer_code=None,
        )

    async def start_timed_watering(self) -> None:
        """Start timed watering using the configured duration."""
        duration = self.get(self.AttributeDefs.watering_duration.id)

        if duration is None:
            raise ValueError("Watering duration is not configured.")

        on_off_cluster = self.endpoint.in_clusters[OnOff.cluster_id]

        await on_off_cluster.start_timed_watering(duration)


class SonoffSWVOnOffCluster(OnOff, CustomCluster):
    """Custom OnOff cluster for the Sonoff SWV."""

    async def start_timed_watering(self, duration: int) -> None:
        """Start watering for the specified duration in seconds."""
        if not 1 <= duration <= 0xFFFE:
            raise ValueError("Watering duration must be between 1 and 65534 seconds")

        await self.on_with_timed_off(
            on_off_control=OnOff.OnOffControl(0),
            on_time=duration,
            off_wait_time=0,
        )


class CustomSonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        water_valve_state = ZCLAttributeDef(
            id=0x500C,
            type=ValveState,
            manufacturer_code=None,
        )

        auto_close_water_shortage = ZCLAttributeDef(
            id=0x5011,
            type=t.uint16_t,
            manufacturer_code=None,
        )


(
    QuirkBuilder("SONOFF", "SWV")
    .replaces(CustomSonoffCluster)
    .replaces(SonoffSWVOnOffCluster)
    .adds(SonoffSWVTimerCluster)
    .number(
        SonoffSWVTimerCluster.AttributeDefs.watering_duration.name,
        SonoffSWVTimerCluster.cluster_id,
        min_value=1,
        max_value=0xFFFE,
        step=1,
        unit="s",
        translation_key="watering_duration",
        fallback_name="Timed watering duration",
    )
    .command_button(
        "start_timed_watering",
        SonoffSWVTimerCluster.cluster_id,
        translation_key="start_timed_watering",
        fallback_name="Start timed watering",
    )
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        device_class=BinarySensorDeviceClass.MOISTURE,
        attribute_converter=lambda x: x & ValveState.Water_Leakage,
        unique_id_suffix="water_leak_status",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="water_leak",
        fallback_name="Water leak",
    )
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_converter=lambda x: x & ValveState.Water_Shortage,
        unique_id_suffix="water_supply_status",
        translation_key="water_supply",
        fallback_name="Water supply",
    )
    .switch(
        CustomSonoffCluster.AttributeDefs.auto_close_water_shortage.name,
        CustomSonoffCluster.cluster_id,
        off_value=0,
        on_value=30,
        translation_key="water_shortage_auto_close",
        fallback_name="Water shortage auto-close",
    )
    .add_to_registry()
)
