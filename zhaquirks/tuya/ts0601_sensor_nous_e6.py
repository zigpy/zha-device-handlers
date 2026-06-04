"""Nous E6 Temperature and Humidity sensor (_TZE284_wtikaxzs)."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zhaquirks import CustomCluster, CustomDevice
import zhaquirks.const as data_const
from zhaquirks.tuya.mcu import TuyaMCUCluster


class TuyaManufacturerSpecificCluster(CustomCluster):
    """Tuya manufacturer specific cluster (0xED00)."""

    cluster_id = 0xED00


class NousE6ManufCluster(TuyaMCUCluster):
    """Tuya MCU cluster for Temperature and Humidity data point mapping."""

    cluster_id = 0xEF00

    # Bypassing automatic mapping to ensure compatibility with Python 3.14/HA 2026.6
    # and to handle the specific TuyaData object structure.
    dp_to_attribute = {}
    data_point_handlers = {
        1: "handle_temp",
        2: "handle_hum",
        4: "handle_batt",
    }

    def _extract_value(self, datum):
        """Safely extract integer value from TuyaData objects."""
        try:
            d = datum.data
            for attr in ("payload", "value"):
                if hasattr(d, attr):
                    return int(getattr(d, attr))
            return int(d)
        except (TypeError, ValueError, AttributeError):
            return None

    def handle_temp(self, datum):
        """Handle temperature data points (DP 1)."""
        val = self._extract_value(datum)
        if val is not None:
            # Tuya sends 243 for 24.3°C -> ZCL expects 2430 (0.01°C units)
            self.endpoint.temperature.update_attribute(0x0000, val * 10)

    def handle_hum(self, datum):
        """Handle humidity data points (DP 2)."""
        val = self._extract_value(datum)
        if val is not None:
            # Tuya sends 49 for 49% -> ZCL expects 4900 (0.01% units)
            self.endpoint.humidity.update_attribute(0x0000, val * 100)

    def handle_batt(self, datum):
        """Handle battery data points (DP 4)."""
        val = self._extract_value(datum)
        if val is not None:
            # Tuya sends 100 for 100% -> ZCL expects 200 (0.5% units)
            self.endpoint.device_power.update_attribute(0x0021, val * 2)


class NousE6_TZE284_wtikaxzs(CustomDevice):
    """Nous E6 variant (_TZE284_wtikaxzs) custom quirk."""

    signature = {
        data_const.MODELS_INFO: [("_TZE284_wtikaxzs", "TS0601")],
        data_const.ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=81
            # device_version=1
            # input_clusters=[0, 4, 5, 60672, 61184]
            # output_clusters=[10, 25]>
            1: {
                data_const.PROFILE_ID: zha.PROFILE_ID,
                data_const.DEVICE_TYPE: 81,
                data_const.INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufacturerSpecificCluster.cluster_id,
                    TuyaMCUCluster.cluster_id,
                ],
                data_const.OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        data_const.ENDPOINTS: {
            1: {
                data_const.DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                data_const.INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufacturerSpecificCluster,
                    NousE6ManufCluster,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    PowerConfiguration.cluster_id,
                ],
                data_const.OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }
