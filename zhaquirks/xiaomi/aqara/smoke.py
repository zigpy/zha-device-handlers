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

    # Until this is written the device sends no manufacturer-specific reports at
    # all, so the smoke attribute never arrives. Other Aqara quirks (plug_eu,
    # opple_remote) write the same attribute for the same reason.
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
    cluster and enrolls the device. Firmware 0x13 only sends zone status
    notifications once it is actually enrolled, which never happened while this
    was a `LocalDataCluster` (both the CIE address write and the bind were
    local no-ops there). `zone_type` is still served from the quirk, as the
    binary sensor's device class must not depend on a sleepy device answering a
    read.
    """

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Fire_Sensor
    }


class XiaomiSmokePowerConfiguration(PowerConfigurationCluster):
    """Power configuration cluster of the smoke detector.

    This is a real (remote) cluster, so ZHA binds it and configures reporting.
    Firmware 0x13 accepts reporting on `battery_voltage` and then reports it,
    while it never sends the Xiaomi attribute report blob older firmware uses.
    `battery_percentage_remaining` is derived from the voltage, as the device
    rejects reporting configuration for it.

    Firmware 0x11 sends the Xiaomi blob instead, which still lands here through
    `battery_reported()` / `battery_percent_reported()`, so it keeps working
    even if the device answers standard reads with `UNSUPPORTED_ATTRIBUTE`.
    """

    MIN_VOLTS = 2.475
    MAX_VOLTS = 3.0

    _CONSTANT_ATTRIBUTES = {
        BATTERY_QUANTITY_ATTR: 1,
        BATTERY_SIZE_ATTR: BatterySize.Unknown,
    }

    def battery_reported(self, voltage_mv: int) -> None:
        """Handle a battery voltage from a Xiaomi attribute report."""
        # updating the voltage also updates the derived percentage
        self._update_attribute(self.BATTERY_VOLTAGE_ATTR, round(voltage_mv / 100, 1))

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
