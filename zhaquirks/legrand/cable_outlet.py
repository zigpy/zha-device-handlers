"""Module for Legrand Cable Outlet (with pilot wire functionality)."""


from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    Direction,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legrand import LEGRAND, MANUFACTURER_SPECIFIC_CLUSTER_ID

MANUFACTURER_SPECIFIC_CLUSTER_ID_2 = 0xFC40  # 64576

HEAT_MODE_ATTR = 0x00


class LegrandCluster(CustomCluster):
    """LegrandCluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "LegrandCluster"
    ep_attribute = "legrand_cluster"

    class AttributeDefs(BaseAttributeDefs):
        device_mode = ZCLAttributeDef(
            id=0x0000,
            type=t.data16,
            is_manufacturer_specific=True,
        )
        led_dark = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        led_on = ZCLAttributeDef(
            id=0x0002,
            type=t.Bool,
            is_manufacturer_specific=True,
        )


class HeatMode(t.enum8):
    Comfort = 0x00
    Comfort_minus_1 = 0x01
    Comfort_minus_2 = 0x02
    Eco = 0x03
    Frost_protection = 0x04
    Off = 0x05


class LegrandCableOutletCluster(CustomCluster):
    """Legrand second manufacturer-specific cluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID_2
    name = "CableOutlet"
    ep_attribute = "cable_outlet_cluster"

    class AttributeDefs(BaseAttributeDefs):
        heat_mode = ZCLAttributeDef(
            id=HEAT_MODE_ATTR,
            type=HeatMode,
            is_manufacturer_specific=True,
        )

    class ServerCommandDefs(BaseCommandDefs):
        set_heat_mode = ZCLCommandDef(
            id=HEAT_MODE_ATTR,
            schema={"mode": HeatMode},
            direction=Direction.Client_to_Server,
            is_manufacturer_specific=True,
        )

    async def write_attributes(self, attributes, manufacturer=None) -> list:
        attrs = {}
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if attr_id == HEAT_MODE_ATTR:
                await self.set_heat_mode(value, manufacturer=manufacturer)
            else:
                attrs[attr] = value
        return await super().write_attributes(attrs, manufacturer)


class Legrand064882CableOutlet(CustomDevice):
    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1
        # input_clusters=[0, 3, 4, 6, 5, 64513, 2820, 64576]
        # output_clusters=[6, 0, 64513, 5, 25]>
        MODELS_INFO: [(f" {LEGRAND}", " Cable outlet")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                    ElectricalMeasurement.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_2,
                ],
                OUTPUT_CLUSTERS: [
                    OnOff.cluster_id,
                    Basic.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                ],
            },
            #  <SimpleDescriptor endpoint=242 profile=41440 device_type=102
            # input_clusters=[33]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.COMBO_BASIC,
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    LegrandCluster,
                    ElectricalMeasurement.cluster_id,
                    LegrandCableOutletCluster,
                ],
                OUTPUT_CLUSTERS: [
                    OnOff.cluster_id,
                    Basic.cluster_id,
                    LegrandCluster,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.COMBO_BASIC,
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
