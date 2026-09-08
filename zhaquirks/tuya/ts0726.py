"""Tuya TS0726 1/2/3-gang switch (Beseed/Moes).

Fixes the issue where toggling one gang activates all gangs by:
1. Replacing OnOff with a custom cluster that includes Tuya attribute 0x5000
2. Writing 0x5000=0 (command mode) on initialization to enable per-gang control

The TS0726 ships with attribute 0x5000 (operation_mode) set to 1 (event/scene mode),
which causes all relays to toggle together on any On/Off command. Setting it to 0
switches to command mode, enabling individual per-gang relay control.

Based on the ts001x.py quirk pattern from zha-device-handlers.
"""

from typing import Final

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes, Time
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    EnchantedDevice,
    TuyaSwitch,
    TuyaZBE000Cluster,
    TuyaZBExternalSwitchTypeCluster,
    TuyaZBOnOffAttributeCluster,
)

# Green Power endpoint constants
GP_PROFILE_ID = 0xA1E0
GP_DEVICE_TYPE = 0x0061
GP_CLUSTER_ID = 0x0021


class TuyaTS0726OnOffCluster(TuyaZBOnOffAttributeCluster):
    """OnOff cluster for TS0726 with operation_mode attribute (0x5000).

    Attribute 0x5000 controls the switch operation mode:
      0 = command mode (individual relay control)
      1 = event/scene mode (all relays toggle together)

    The attribute uses enum8 type on endpoint 1 only.
    """

    class AttributeDefs(TuyaZBOnOffAttributeCluster.AttributeDefs):
        """Attribute definitions."""

        operation_mode: Final = ZCLAttributeDef(id=0x5000, type=t.enum8)

    async def apply_custom_configuration(self, *args, **kwargs):
        """Set operation_mode to 0 (command mode) for individual gang control."""
        self.debug(
            "Writing operation_mode=0 (command mode) on EP %s",
            self.endpoint.endpoint_id,
        )
        try:
            await self.write_attributes({"operation_mode": 0})
        except Exception as e:  # noqa: BLE001
            self.warning("Failed to write operation_mode: %s", e)
        await super().apply_custom_configuration(*args, **kwargs)


class TuyaTS0726_1Gang(EnchantedDevice, TuyaSwitch):
    """Tuya TS0726 1-gang switch (Beseed/Moes) with 0xE000/0xE001 clusters."""

    signature = {
        MODELS_INFO: [("_TZ3002_jn2x20tg", "TS0726")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SCENE_SELECTOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBE000Cluster.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: GP_PROFILE_ID,
                DEVICE_TYPE: GP_DEVICE_TYPE,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GP_CLUSTER_ID],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaTS0726OnOffCluster,
                    TuyaZBE000Cluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                PROFILE_ID: GP_PROFILE_ID,
                DEVICE_TYPE: GP_DEVICE_TYPE,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GP_CLUSTER_ID],
            },
        },
    }


class TuyaTS0726_2Gang(EnchantedDevice, TuyaSwitch):
    """Tuya TS0726 2-gang switch (Beseed/Moes) with 0xE000/0xE001 clusters."""

    signature = {
        MODELS_INFO: [("_TZ3002_zjuvw9zf", "TS0726")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SCENE_SELECTOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBE000Cluster.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SCENE_SELECTOR,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: GP_PROFILE_ID,
                DEVICE_TYPE: GP_DEVICE_TYPE,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GP_CLUSTER_ID],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaTS0726OnOffCluster,
                    TuyaZBE000Cluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaTS0726OnOffCluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: GP_PROFILE_ID,
                DEVICE_TYPE: GP_DEVICE_TYPE,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GP_CLUSTER_ID],
            },
        },
    }
