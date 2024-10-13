"""Sonoff SWV - Zigbee smart water valve."""

import typing

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ValveState(t.enum8):
    """Water valve state."""

    Water_Shortage = 1
    Water_Leakage = 2


class EwelinkCluster(CustomCluster):
    """Ewelink specific cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        water_supply_state = ZCLAttributeDef(
            id=0x500C,
            type=bool,
        )

        valve_leak_state = ZCLAttributeDef(
            id=0x500C,
            type=bool,
        )

    @property
    def _is_manuf_specific(self):
        return False

    def get(self, key: int | str, default: typing.Any | None = None) -> typing.Any:
        """Map binary sensors onto bits of shared attribute."""

        value = super().get(key, default)
        match key:
            case self.AttributeDefs.water_supply_state.name:
                return value & ValveState.Water_Shortage
            case self.AttributeDefs.valve_leak_state.name:
                return value & ValveState.Water_Leakage
        raise ValueError(f"Unknown attribute {key}")


(
    QuirkBuilder("SONOFF", "SWV")
    .replaces(EwelinkCluster)
    .binary_sensor(
        EwelinkCluster.AttributeDefs.water_supply_state.name,
        EwelinkCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        translation_key="water_supply",
        fallback_name="Water supply status",
    )
    .binary_sensor(
        EwelinkCluster.AttributeDefs.valve_leak_state.name,
        EwelinkCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        translation_key="valve_leak",
        fallback_name="Valve leak status",
    )
    .add_to_registry()
)
