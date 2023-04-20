"""CTM Lyng mKomfy Stove Guard"""
import zigpy.profiles.zha as zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    BinaryInput,
    Identify,
    Ota,
    PowerConfiguration,
)
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from zhaquirks.ctm import CTM, CTM_MFCODE, CtmDiagnosticsCluster, CtmStoveGuardCluster


class CtmMKomfyCluster(CtmStoveGuardCluster):
    """CTM Lyng custom mKomfy cluster."""

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        await self.configure_reporting_multiple(
            {
                "alarm_status": (1, 43200, 0),
                "active": (1, 43200, 0),
            },
            manufacturer=CTM_MFCODE,
        )
        await self.read_attributes(
            [
                "alarm_status",
                "active",
            ],
            manufacturer=CTM_MFCODE,
        )
        return result

    def _update_attribute(self, attrid, value):
        if attrid == self.attributes_by_name["alarm_status"].id:
            status = 0x0000  # OK
            if value == self.AlarmStatus.Tamper:
                status = IasZone.ZoneStatus.Tamper

            elif value == self.AlarmStatus.High_Temperature:
                status = IasZone.ZoneStatus.Alarm_1

            elif value == self.AlarmStatus.Timer:
                status = IasZone.ZoneStatus.Alarm_2

            elif value == self.AlarmStatus.Battery_Alarm:
                status = IasZone.ZoneStatus.Battery

            elif value == self.AlarmStatus.Error:
                status = IasZone.ZoneStatus.Trouble

            self.endpoint.device.alarm_status_bus.listener_event(
                "alarm_status_change", status
            )

        elif attrid == self.attributes_by_name["active"].id:
            status = True if value == self.ActiveStatus.Active else False
            self.endpoint.device.active_status_bus.listener_event(
                "active_status_change", status
            )

        super()._update_attribute(attrid, value)


class CtmAlarmCluster(LocalDataCluster, IasZone):
    """CTM Lyng custom stove guard alarm cluster."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.alarm_status_bus.add_listener(self)
        self._update_attribute(
            self.attributes_by_name["zone_type"].id,
            self.ZoneType.Standard_Warning_Device,
        )

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        await self.endpoint.ctm_stove_guard.bind()
        return result

    def alarm_status_change(self, status):
        self._update_attribute(self.attributes_by_name["zone_status"].id, status)


class CtmActiveStatusCluster(LocalDataCluster, BinaryInput):
    """CTM Lyng custom stove guard active status cluster."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.active_status_bus.add_listener(self)
        self._update_attribute(self.attributes_by_name["active_text"].id, "Active")
        self._update_attribute(self.attributes_by_name["description"].id, "Cooking")
        self._update_attribute(self.attributes_by_name["inactive_text"].id, "Inactive")
        self._update_attribute(
            self.attributes_by_name["application_type"].id, 0x03010008
        )

    def active_status_change(self, status):
        self._update_attribute(self.attributes_by_name["present_value"].id, status)


class CtmLyngMKomfy(CustomDevice):
    """CTM Lyng custom device mKomfy Stove Guard."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.alarm_status_bus = Bus()
        self.active_status_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [
            (CTM, "mKomfy"),
            (CTM, "mKomfy Tak"),
            (CTM, "mKomfy Infinity"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=770
            # device_version=1
            # input_clusters=[0, 1, 3, 1026, 65261, 65481]
            # output_clusters=[3, 25, 4096]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    CtmDiagnosticsCluster.cluster_id,
                    CtmStoveGuardCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    CtmDiagnosticsCluster,
                    CtmMKomfyCluster,
                    CtmAlarmCluster,
                    CtmActiveStatusCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }
