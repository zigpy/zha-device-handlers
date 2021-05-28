"""Tuya based smart air box (temperature, relative humidity, VOC, CO2, formaldehyde."""
from zigpy import types
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time
from zigpy.zcl.clusters.measurement import CarbonDioxideConcentration, FormaldehydeConcentration, EthyleneConcentration

from zhaquirks import LocalDataCluster, Bus
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TuyaManufClusterAttributes,
)
from zhaquirks.tuya.siren import TuyaTemperatureMeasurement, TuyaRelativeHumidity

#Commandid are two bytes, e.g. 0x0202. starting at 0x0200 == 0
# example log line:
# [zhaquirks.tuya] [0x719b:1:0xef00] Received value [0, 0, 1, 116] for attribute 0x0202 (command 0x0001)
TUYA_SMART_AIR_TEMPERATURE_ATTR = 0x0212  # temperature in decidegree (°C = value / 10)
TUYA_SMART_AIR_HUMIDITY_ATTR    = 0x0213  # [ humidity (%rh = value /10)
TUYA_SMART_AIR_CO2_ATTR         = 0x0202  # formaldehyde ()
TUYA_SMART_AIR_HCHO_ATTR        = 0x0215  # formaldehyde ()
TUYA_SMART_AIR_VOC_ATTR         = 0x0216  # Volatile organic compounds ()


class TuyaCO2Concentration(LocalDataCluster, CarbonDioxideConcentration):
    """Humidity cluster acting from events from humidity bus."""

    cluster_id = CarbonDioxideConcentration.cluster_id
    ATTR_ID = 0

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.co2_bus.add_listener(self)

    def co2_reported(self, value):
        """CO2 reported."""
        self._update_attribute(self.ATTR_ID, value)

# XXX: EthyleneConcentration is the wrong type, but there is currently no type specified for VOC,
# unsure how to handle this, possibly expose as analogvalue cluster?
class TuyaVOCConcentration(LocalDataCluster, EthyleneConcentration):
    """Humidity cluster acting from events from humidity bus."""

    cluster_id = EthyleneConcentration.cluster_id
    ATTR_ID = 0

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.voc_bus.add_listener(self)

    def voc_reported(self, value):
        """VOC reported."""
        self._update_attribute(self.ATTR_ID, value)


class TuyaFormaldehydeConcentration(LocalDataCluster, FormaldehydeConcentration):
    """Humidity cluster acting from events from humidity bus."""

    cluster_id = FormaldehydeConcentration.cluster_id
    ATTR_ID = 0

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.hcho_bus.add_listener(self)

    def hcho_reported(self, value):
        """Formaldehyde reported."""
        self._update_attribute(self.ATTR_ID, value)


class TuyaManufClusterSmartAirBox(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the tuya smart air box device."""

    manufacturer_attributes = {
        TUYA_SMART_AIR_TEMPERATURE_ATTR: ("temperature", types.uint32_t),
        TUYA_SMART_AIR_HUMIDITY_ATTR: ("humidity", types.uint32_t),
        TUYA_SMART_AIR_CO2_ATTR: ("CO2", types.uint32_t),
        TUYA_SMART_AIR_HCHO_ATTR: ("Formaldehyde", types.uint32_t),
        TUYA_SMART_AIR_VOC_ATTR: ("VOC", types.uint32_t),
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == TUYA_SMART_AIR_TEMPERATURE_ATTR:
            self.endpoint.device.temperature_bus.listener_event(
                "temperature_reported", value * 10  # decidegree to centidegree
            )
        elif attrid == TUYA_SMART_AIR_HUMIDITY_ATTR:
            self.endpoint.device.humidity_bus.listener_event(
                "humidity_reported", value * 10  # whole percentage to 1/100th
            )
        elif attrid == TUYA_SMART_AIR_CO2_ATTR:
            self.endpoint.device.co2_bus.listener_event(
                "co2_reported", value  # unit still unknown, supposedly 0-1000 ppm according to product sheet
            )
        elif attrid == TUYA_SMART_AIR_HCHO_ATTR:
            self.endpoint.device.hcho_bus.listener_event(
                "hcho_reported", value  # unit still unknown, supposedly 0-10 mg/m3 according to product sheet
            )
        elif attrid == TUYA_SMART_AIR_VOC_ATTR:
            self.endpoint.device.voc_bus.listener_event(
                "voc_reported", value  # unit still unknown, supposedly 0-99.9 ppm according to product sheet
            )


class TuyaSmartAirBox(CustomDevice):
    """Tuya Smart Air Box device."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.temperature_bus = Bus()
        self.humidity_bus = Bus()
        self.voc_bus = Bus()
        self.hcho_bus = Bus()
        self.co2_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=1, byte2=64, mac_capability_flags=142, manufacturer_code=4098,
        #                       maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        #                       maximum_outgoing_transfer_size=82, descriptor_capability_field=0)",
        # device_version=1
        # input_clusters=[0x0000, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x000a, 0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=81 device_version=1 input_clusters=[0, 4, 5, 61184] output_clusters=[25, 10]>
        MODELS_INFO: [("_TZE200_8ygsuhe1", "TS0601")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufClusterSmartAirBox.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaTemperatureMeasurement,
                    TuyaRelativeHumidity,
                    TuyaCO2Concentration,
                    TuyaVOCConcentration,
                    TuyaFormaldehydeConcentration,
                    TuyaManufClusterSmartAirBox
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
