"""Tuya Pool sensor."""

from typing import Any, Dict

import zigpy.types as t
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time
from zigpy.zcl.clusters.measurement import (
    PH,
    SodiumConcentration,
    ElectricalConductivity,
    ChlorineConcentration,
    TemperatureMeasurement,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TuyaLocalCluster, TuyaEnchantableCluster
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster, EnchantedDevice, TuyaPowerConfigurationCluster

# Make the TuyaPowerConfigurationCluster ENchantable, with a specific spell.
class MyTuyaPowerConfigurationCluster(TuyaPowerConfigurationCluster, TuyaEnchantableCluster):

    async def spell(self):
        """Cast spell, so the Tuya device works correctly."""
        # normal spell (also needed):
        self.debug("Executing spell on Tuya device %s", self.endpoint.device.ieee)
        attr_to_read = [4, 0, 1, 5, 7, 0xFFFE]
        basic_cluster = self.endpoint.device.endpoints[1].in_clusters[0]
        await basic_cluster.read_attributes(attr_to_read)
        self.debug("Executed spell on Tuya device %s", self.endpoint.device.ieee)

        # new part for sending command with id 3 on `0xEF00` cluster
        self.debug("Executing data query spell on Tuya device %s", self.endpoint.device.ieee)
        tuya_manuf_cluster = self.endpoint.device.endpoints[1].in_clusters[TuyaMCUCluster.cluster_id]
        await tuya_manuf_cluster.command(0x03)
        self.debug("Executed data query spell on Tuya device %s", self.endpoint.device.ieee)

class TuyaTemperatureMeasurement(TemperatureMeasurement, TuyaLocalCluster):
    """Tuya local TemperatureMeasurement cluster."""

class TuyaPH(PH, TuyaLocalCluster):
    """Tuya local pH cluster."""

class TuyaORP(TuyaLocalCluster):
    """Tuya local Oxido-Reduction Potential cluster."""
    cluster_id = 0x042F
    name = "ORP Level"
    ep_attribute = "redox_potential"

    attributes = {
        0x0000: ("measured_value", t.Single),  # fraction of 1 (one)
        0x0001: ("min_measured_value", t.Single),
        0x0002: ("max_measured_value", t.Single),
    }

    server_commands = {}
    client_commands = {}


class TuyaTDS(TuyaLocalCluster):
    """Tuya local Total Dissolved Solids cluster."""
    cluster_id = 0x0430
    name = "TDS Level"
    ep_attribute = "total_dissolved_solids"

    attributes = {
        0x0000: ("measured_value", t.Single),  # fraction of 1 (one)
        0x0001: ("min_measured_value", t.Single),
        0x0002: ("max_measured_value", t.Single),
    }

    server_commands = {}
    client_commands = {}


class TuyaSodiumConcentration(SodiumConcentration, TuyaLocalCluster):
    """Tuya local NaCl cluster."""

class TuyaElectricalConductivity(ElectricalConductivity, TuyaLocalCluster):
    """Tuya local Electrical Conductivity cluster."""

class TuyaChlorineConcentration(ChlorineConcentration, TuyaLocalCluster):
    """Tuya local Chlorine Concentration cluster with a device RH_MULTIPLIER factor."""

class PoolManufCluster(TuyaMCUCluster):
    """Tuya Manufacturer Cluster with Pool data points."""

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            # ramdom attribute IDs
            0xEF01: ("dp_106", t.uint32_t, True),
            0xEF02: ("dp_107", t.uint32_t, True),
            0xEF03: ("dp_108", t.uint32_t, True),
            0xEF04: ("dp_109", t.uint32_t, True),
            0xEF05: ("dp_110", t.uint32_t, True),
            0xEF06: ("dp_111", t.uint32_t, True),
            0xEF07: ("dp_112", t.uint32_t, True),
            0xEF08: ("dp_113", t.uint32_t, True),
        }
    )

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaTDS.ep_attribute,
            "measured_value",
        ),
        2: DPToAttributeMapping(
            TuyaTemperatureMeasurement.ep_attribute,
            "measured_value",
            converter=lambda x: x * 10,
        ),
        101: DPToAttributeMapping(
            TuyaORP.ep_attribute,
            "measured_value",
        ),
        102: DPToAttributeMapping(
            TuyaChlorineConcentration.ep_attribute,
            "measured_value",
        ),
        7: DPToAttributeMapping(
            MyTuyaPowerConfigurationCluster.ep_attribute,
            "battery_percentage_remaining",
        ),
        # TODO 103 pH Calibration
        # TODO 104 Backlight
        # TODO 105 Backlight Value
        #
        10: DPToAttributeMapping(
            TuyaPH.ep_attribute,
            "measured_value",
        ),
        11: DPToAttributeMapping(
            TuyaElectricalConductivity.ep_attribute,
            "measured_value",
        ),
        106: DPToAttributeMapping(
             TuyaMCUCluster.ep_attribute,
             "dp_106",
        ),
        107: DPToAttributeMapping(
             TuyaMCUCluster.ep_attribute,
             "dp_107",
        ),
        108: DPToAttributeMapping(
             TuyaMCUCluster.ep_attribute,
             "dp_108",
        ),
        109: DPToAttributeMapping(
             TuyaMCUCluster.ep_attribute,
             "dp_109",
        ),
        110: DPToAttributeMapping(
             TuyaMCUCluster.ep_attribute,
             "dp_110",
        ),
        111: DPToAttributeMapping(
             TuyaMCUCluster.ep_attribute,
             "dp_111",
        ),
        112: DPToAttributeMapping(
             TuyaMCUCluster.ep_attribute,
             "dp_112",
        ),
        113: DPToAttributeMapping(
             TuyaMCUCluster.ep_attribute,
             "dp-113",
        ),
        # TODO 114: PH Calibration
        # TODO 115: EC Calibration
        # TODO 116: ORP Calibration
        117: DPToAttributeMapping(
            TuyaSodiumConcentration.ep_attribute,
            "measured_value",
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        101: "_dp_2_attr_update",
        102: "_dp_2_attr_update",
        7: "_dp_2_attr_update",
        10: "_dp_2_attr_update",
        11: "_dp_2_attr_update",
        106: "_dp_2_attr_update",
        107: "_dp_2_attr_update",
        108: "_dp_2_attr_update",
        109: "_dp_2_attr_update",
        110: "_dp_2_attr_update",
        111: "_dp_2_attr_update",
        112: "_dp_2_attr_update",
        113: "_dp_2_attr_update",
        117: "_dp_2_attr_update",
    }


class TuyaPoolSensor(EnchantedDevice):
    """Tuya Pool sensor."""

    signature = {
        # "profile_id": 260,
        # "device_type": "0x0051",
        # "in_clusters": ["0x0000","0x0004","0x0005","0xef00"],
        # "out_clusters": ["0x000a","0x0019"]
        MODELS_INFO: [
            ("_TZE200_v1jqz5cy", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    PoolManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    PoolManufCluster,
                    TuyaTemperatureMeasurement,
                    TuyaPH,
                    TuyaORP,
                    TuyaChlorineConcentration,
                    TuyaTDS,
                    TuyaElectricalConductivity,
                    TuyaSodiumConcentration,
                    MyTuyaPowerConfigurationCluster
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            }
        },
    }
