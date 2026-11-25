"""Smoke Sensor."""

import asyncio

import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff, Time
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.builder import BinarySensorDeviceClass, EntityType, QuirkBuilder
from zhaquirks.tuya import (
    BatterySize,
    TuyaDatapointData,
    TuyaManufClusterAttributes,
    TuyaPowerConfigurationCluster2AAA,
)
from zhaquirks.tuya.builder import TuyaIasFire, TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster


class TuyaSensitivityMode(t.enum8):
    """Tuya sensitivity mode enum."""

    Low = 0x00
    Medium = 0x01
    High = 0x02


class TuyaSmokeState(t.enum8):
    """Tuya smoke state enum."""

    Alarm = 0x00
    Normal = 0x01
    Detecting = 0x02
    Unknown = 0x03


class TuyaIasZone(LocalDataCluster, IasZone):
    """IAS Zone."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Fire_Sensor
    }


class TuyaSmokeDetectorCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the TS0205 smoke detector."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        smoke_detected = ZCLAttributeDef(
            id=0x0401,  # [0]/[1] [Detected]/[Clear]
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.smoke_detected.id:
            self.endpoint.ias_zone.update_attribute(
                IasZone.AttributeDefs.zone_status.id,
                IasZone.ZoneStatus.Alarm_1 if value == 0 else 0,
            )


(
    QuirkBuilder("_TZ3210_up3pngle", "TS0205")
    .removes(LightLink.cluster_id)
    .removes(OnOff.cluster_id)
    .removes(Time.cluster_id)
    .replaces(TuyaIasZone)
    .replaces(TuyaSmokeDetectorCluster)
    .add_to_registry()
)

(
    TuyaQuirkBuilder("_TZE200_aycxwiau", "TS0601")
    .applies_to("_TZE200_dq1mfjug", "TS0601")
    .applies_to("_TZE200_vzekyi4c", "TS0601")
    .applies_to("_TZE204_vawy74yh", "TS0601")
    .tuya_smoke(dp_id=1)
    .skip_configuration()
    .add_to_registry()
)

# --- PA-44Z (_TZE284_rccxox8p) fixed parameters, derived from device logs ---
# The device reports the start of an alarm (DP 1) but never its end. While the
# alarm sounds it streams DP 101 = false reports, at most about 20 s apart.
ALARM_CLEAR_S = 60  # no DP 101 = false report for this long: alarm over

DP_SMOKE = 1
DP_SELF_TEST = 101
# Local only, never sent by the device: gives the saved timer flag an ID.
DP_LOCAL_TIMER_FLAG = 0xFE

ATTR_ZONE_STATUS = IasZone.AttributeDefs.zone_status.name
# Saved across restarts: a heartbeat was seen in the current alarm, so the
# clear timer applies to it.
ATTR_TIMER_RUNNING = "alarm_timer_running"


class PA44ZTuyaCluster(TuyaMCUCluster):
    """Tuya cluster that clears the latching smoke alarm."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._loop = asyncio.get_running_loop()
        self._alarm_handle = None
        # A smoke alarm restored from the database after a restart is not seen
        # by the datapoint handlers. Check it once the saved values are
        # restored: it is cleared only if its clear timer was running.
        # DP 101 = false reports from a real ongoing alarm replace this check.
        self._alarm_handle = self._loop.call_later(
            ALARM_CLEAR_S, self._check_restored_alarm
        )

    # --- smoke alarm ---

    def _ias(self) -> IasZone | None:
        return getattr(self.endpoint, IasZone.ep_attribute, None)

    def _alarm_active(self) -> bool:
        ias = self._ias()
        if ias is None:
            return False
        status = ias.get(ATTR_ZONE_STATUS)
        return bool(status) and bool(int(status) & IasZone.ZoneStatus.Alarm_1)

    def _cancel_alarm_timer(self) -> None:
        if self._alarm_handle:
            self._alarm_handle.cancel()
            self._alarm_handle = None

    def _set_timer_running(self, running: bool) -> None:
        if bool(self.get(ATTR_TIMER_RUNNING)) != running:
            self.update_attribute(ATTR_TIMER_RUNNING, running)

    def _arm_alarm_timer(self, delay: float) -> None:
        self._cancel_alarm_timer()
        self._alarm_handle = self._loop.call_later(delay, self._clear_alarm)
        self._set_timer_running(True)

    def _check_restored_alarm(self) -> None:
        self._alarm_handle = None
        if self.get(ATTR_TIMER_RUNNING):
            self._clear_alarm()

    def _clear_alarm(self) -> None:
        self._cancel_alarm_timer()
        self._set_timer_running(False)
        ias = self._ias()
        if ias is not None and self._alarm_active():
            self.debug("%s - Clearing smoke alarm", self.endpoint.device.ieee)
            ias.update_attribute(ATTR_ZONE_STATUS, 0)

    # --- datapoint handling ---

    def _dp_2_attr_update(self, datapoint: TuyaDatapointData) -> None:
        """Map the datapoint as usual, then apply the latching workarounds."""
        super()._dp_2_attr_update(datapoint)
        value = datapoint.data.payload

        if datapoint.dp == DP_SMOKE:
            # Start (0) or end of an alarm: no clear timer until this alarm's
            # first heartbeat. Units that report the end clear normally.
            self._cancel_alarm_timer()
            self._set_timer_running(False)

        elif datapoint.dp == DP_SELF_TEST:
            if value:
                # Self test done, only possible when not alarming: clear now.
                self._clear_alarm()
            elif self._alarm_active():
                # Alarm heartbeat: keep the alarm on.
                self._arm_alarm_timer(ALARM_CLEAR_S)


(
    TuyaQuirkBuilder("_TZE284_rccxox8p", "TS0601")
    .applies_to("_TZE200_m9skfctm", "TS0601")
    .applies_to("_TZE200_rccxox8p", "TS0601")
    .applies_to("_TZE2841000000_rccxox8p", "TS0601")
    .tuya_smoke(dp_id=DP_SMOKE)
    .tuya_binary_sensor(
        dp_id=11,
        attribute_name="fault_alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="fault_alarm",
        fallback_name="Fault alarm",
    )
    .tuya_battery(
        dp_id=15,
        battery_type=BatterySize.AA,
        battery_qty=2,
    )
    # DP 16 mute state is two-way, but delivery is best-effort: during an alarm
    # the device sends reports every 0.1-0.2 s and may miss or delay one-off
    # writes and reports.
    .tuya_switch(
        dp_id=16,
        attribute_name="silence_alarm",
        entity_type=EntityType.STANDARD,
        translation_key="silence_alarm",
        fallback_name="Silence alarm",
    )
    .tuya_binary_sensor(
        dp_id=DP_SELF_TEST,
        attribute_name="self_test_done",
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="self_test_done",
        fallback_name="Self-test done",
    )
    .tuya_attribute(
        dp_id=DP_LOCAL_TIMER_FLAG,
        attribute_name=ATTR_TIMER_RUNNING,
        type=t.Bool,
    )
    .skip_configuration()
    .add_to_registry(replacement_cluster=PA44ZTuyaCluster)
)

(
    TuyaQuirkBuilder("TZE200_0zaf1cr8", "TS0601")
    .applies_to("_TZE284_0zaf1cr8", "TS0601")
    .tuya_smoke(dp_id=1)
    .tuya_binary_sensor(
        dp_id=14,
        attribute_name="battery_low",
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Battery low",
    )
    .tuya_battery(dp_id=15, battery_type=BatterySize.CR123A, battery_qty=1)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE284_n4ttsck2", "TS0601")
    .tuya_smoke(dp_id=1)
    .tuya_battery(dp_id=15, battery_type=BatterySize.CR123A, battery_qty=1)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE204_ntcy3xu1", "TS0601")
    .applies_to("_TZE200_ntcy3xu1", "TS0601")
    .tuya_smoke(dp_id=1)
    .tuya_binary_sensor(
        dp_id=4,
        attribute_name="tamper",
        device_class=BinarySensorDeviceClass.TAMPER,
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Tamper",
    )
    .tuya_dp(
        dp_id=14,
        ep_attribute=TuyaPowerConfigurationCluster2AAA.ep_attribute,
        attribute_name="battery_percentage_remaining",
        converter=lambda x: {0: 10, 1: 80, 2: 200}[x],
    )
    .adds(TuyaPowerConfigurationCluster2AAA)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE204_kgaxpvxr", "TS0601")
    .tuya_ias(
        dp_id=1,
        ias_cfg=TuyaIasFire,
        converter=lambda x: (
            IasZone.ZoneStatus.Alarm_1 if x == TuyaSmokeState.Alarm else 0
        ),
    )
    .tuya_battery(dp_id=15, battery_type=BatterySize.CR123A, battery_qty=1)
    .tuya_switch(
        dp_id=16,
        attribute_name="silence_alarm",
        translation_key="silence_alarm",
        fallback_name="Silence alarm",
    )
    .tuya_binary_sensor(
        dp_id=101,
        attribute_name="self_test_result",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Self test result",
    )
    .tuya_enum(
        dp_id=102,
        attribute_name="motion_sensitivity",
        enum_class=TuyaSensitivityMode,
        translation_key="motion_sensitivity",
        fallback_name="Motion sensitivity",
    )
    .skip_configuration()
    .add_to_registry()
)
