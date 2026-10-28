"""Quirk for LUMI lumi.sensor_smoke.acn03 smoke sensor."""

from typing import Any

from zigpy import types
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.security import IasZone
from zigpy.zdo.types import NodeDescriptor

from zhaquirks import PowerConfigurationCluster
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZONE_STATUS,
    BatterySize,
)
from zhaquirks.legacy import CustomDevice
from zhaquirks.xiaomi import (
    BATTERY_QUANTITY_ATTR,
    BATTERY_SIZE_ATTR,
    LUMI,
    XiaomiAqaraE1Cluster,
)

MODE = 0x0009
BUZZER_MANUAL_MUTE = 0x0126
SELF_TEST = 0x0127
SMOKE = 0x013A
SMOKE_DENSITY = 0x013B
HEARTBEAT_INDICATOR = 0x013C
BUZZER_MANUAL_ALARM = 0x013D
BUZZER = 0x013E
LINKAGE_ALARM = 0x014B
LINKAGE_ALARM_STATE = 0x014C
SMOKE_DENSITY_DBM = 0x1403  # fake attribute for smoke density in dB/m

SMOKE_DENSITY_DBM_MAP = {
    0: 0,
    1: 0.085,
    2: 0.088,
    3: 0.093,
    4: 0.095,
    5: 0.100,
    6: 0.105,
    7: 0.110,
    8: 0.115,
    9: 0.120,
    10: 0.125,
}


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    attributes = {
        MODE: ("mode", types.uint8_t, True),
        BUZZER_MANUAL_MUTE: ("buzzer_manual_mute", types.uint8_t, True),
        SELF_TEST: ("self_test", types.Bool, True),
        SMOKE: ("smoke", types.uint8_t, True),
        SMOKE_DENSITY: ("smoke_density", types.uint8_t, True),
        HEARTBEAT_INDICATOR: ("heartbeat_indicator", types.uint8_t, True),
        BUZZER_MANUAL_ALARM: ("buzzer_manual_alarm", types.uint8_t, True),
        BUZZER: ("buzzer", types.uint32_t, True),
        LINKAGE_ALARM: ("linkage_alarm", types.uint8_t, True),
        LINKAGE_ALARM_STATE: ("linkage_alarm_state", types.uint8_t, True),
        SMOKE_DENSITY_DBM: ("smoke_density_dbm", types.Single, True),
    }

    # Until this is written, firmware 0x13 sends no manufacturer-specific reports at
    # all, including the smoke attribute, and never sends an IAS zone status change
    # for smoke. Reporting can't be configured for the smoke attribute
    # (UNREPORTABLE_ATTRIBUTE), the device pushes it on its own once this is set.
    attr_config = {MODE: 0x01}

    async def bind(self):
        """Bind cluster and enable manufacturer-specific reporting."""
        result = await super().bind()
        # This is a sleepy device, so the write frequently times out even when the
        # device applies it. Best effort only: a failure must not break binding,
        # enrollment or the battery path.
        self.create_catching_task(self.write_attributes(self.attr_config))
        return result

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Pass attribute update to another cluster if necessary."""
        super()._update_attribute(attrid, value)
        if attrid == SMOKE:
            self.endpoint.ias_zone.update_attribute(ZONE_STATUS, value)
        elif attrid == SMOKE_DENSITY:
            self.update_attribute(SMOKE_DENSITY_DBM, SMOKE_DENSITY_DBM_MAP[value])


class SmokeIasZone(CustomCluster, IasZone):
    """IAS Zone cluster of the smoke detector.

    This is a real (remote) cluster, so ZHA writes the CIE address, binds the
    cluster and enrolls the device, which never happened while this was a
    `LocalDataCluster` (both the CIE address write and the bind were local no-ops
    there). The smoke state itself does not arrive as an IAS zone status change,
    it is forwarded here from the Opple cluster's smoke attribute. `zone_type` is
    still served from the quirk, as the binary sensor's device class must not
    depend on a sleepy device answering a read.
    """

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Fire_Sensor
    }

    async def read_attributes(self, attributes, *args, **kwargs):
        """Read attributes, serving `zone_status` from the cache.

        The device answers `zone_status` reads without the alarm bit even during
        an alarm, as it only reports smoke through the Opple cluster. A read from
        the device (e.g. when ZHA re-initializes a device that became available
        again) would clear an active alarm, so `zone_status` is never read from
        the device, as was the case while this was a `LocalDataCluster`.
        """
        zone_status = [attr for attr in attributes if self._is_zone_status(attr)]
        others = [attr for attr in attributes if attr not in zone_status]

        success, failure = {}, {}
        if others:
            success, failure = await super().read_attributes(others, *args, **kwargs)
        if zone_status:
            cached_success, cached_failure = await super().read_attributes(
                zone_status, only_cache=True
            )
            success.update(cached_success)
            failure.update(cached_failure)
        return success, failure

    def _is_zone_status(self, attr) -> bool:
        """Return whether an attribute ID, name or definition is `zone_status`."""
        try:
            return self.find_attribute(attr).id == ZONE_STATUS
        except KeyError:
            return False


class XiaomiSmokePowerConfiguration(PowerConfigurationCluster):
    """Power configuration cluster of the smoke detector.

    This is a real (remote) cluster, so ZHA binds it and configures reporting.
    Firmware 0x13 accepts reporting on `battery_voltage` and then reports it.
    `battery_percentage_remaining` is derived from the voltage, as the device
    rejects reporting configuration for it and answers reads of it with
    `UNSUPPORTED_ATTRIBUTE` (which `PowerConfigurationCluster` keeps from
    clearing the derived value).

    The Xiaomi attribute report blob (firmware 0x11, and 0x13 once the Opple
    cluster's mode is set) still lands here through `battery_reported()` /
    `battery_percent_reported()`.
    """

    MIN_VOLTS = 2.475
    MAX_VOLTS = 3.0

    _CONSTANT_ATTRIBUTES = {
        BATTERY_QUANTITY_ATTR: 1,
        BATTERY_SIZE_ATTR: BatterySize.Unknown,
    }

    def battery_reported(self, voltage_mv: int) -> None:
        """Handle a battery voltage from a Xiaomi attribute report."""
        # The base class would derive the percentage from the rounded voltage, so
        # derive it from the exact millivolts instead, as before.
        base = super(PowerConfigurationCluster, self)
        base._update_attribute(self.BATTERY_VOLTAGE_ATTR, round(voltage_mv / 100, 1))
        base._update_attribute(
            self.BATTERY_PERCENTAGE_REMAINING,
            self._calculate_battery_percentage(voltage_mv / 100),
        )

    def battery_percent_reported(self, battery_percent: int) -> None:
        """Handle a battery percentage from a Xiaomi attribute report."""
        self._update_attribute(self.BATTERY_PERCENTAGE_REMAINING, battery_percent * 2)


class LumiSensorSmokeAcn03(CustomDevice):
    """lumi.sensor_smoke.acn03 smoke sensor."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.sensor_smoke.acn03")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        NODE_DESCRIPTOR: NodeDescriptor(
            0x02, 0x40, 0x80, 0x115F, 0x7F, 0x0064, 0x2C00, 0x0064, 0x00
        ),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    XiaomiSmokePowerConfiguration,
                    Identify.cluster_id,
                    SmokeIasZone,
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }
