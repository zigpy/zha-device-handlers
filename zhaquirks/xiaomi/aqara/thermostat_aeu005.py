"""Aqara W600 TRV (lumi.airrtc.aeu005 / WT-A03E) ZHA quirk.

The mode path follows the supplied Zigbee2MQTT createW600Thermostat()
reference.  W600 mode is a composite state in Aqara cluster 0xFCC0 and must
not be written to standard Thermostat.system_mode (0x0201/0x001C).  The
setpoint path follows the Z2M reference order: wake an explicitly off
device into heat via ``0xFCC0/0x0271=1`` first, then write the standard
``0x0201/0x0012`` occupied heating setpoint, then arm the manual override
when the schedule is on.
"""

# Upstream preparation revision: tested W600 mode/setpoint/extras path.
# Device-validation evidence is kept in the accompanying upstream notes.

from __future__ import annotations

from collections.abc import Iterable
import logging
from typing import Any, Final

import zigpy.exceptions
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.helpers import ReportingConfig as ZigpyReportingConfig

from zhaquirks import CustomCluster
from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
)
from zhaquirks.device import CustomZigpyDevice

_LOGGER = logging.getLogger(__name__)

# Device match and vendor code from the W600/WT-A03E ZHA diagnostic snapshot.
AQARA: Final = "Aqara"
MODEL: Final = "lumi.airrtc.aeu005"
AQARA_MANUFACTURER_CODE: Final = 4447  # 0x115F, ZHA/Zigbee2MQTT mapping

# Standard Thermostat cluster (0x0201), ZCL-defined attributes.
ATTR_OCCUPIED_HEATING_SETPOINT: Final = 0x0012
ATTR_CTRL_SEQUENCE_OF_OPER: Final = 0x001B
ATTR_SYSTEM_MODE: Final = 0x001C
ATTR_TEMP_SETPOINT_HOLD: Final = 0x0023
ATTR_RUNNING_STATE: Final = 0x0029

# Standard ZCL enum/map values.  0x02 means Heating Only and is the
# capability value that removes cooling modes from the ZHA climate entity.
SYS_OFF: Final = 0x00
SYS_AUTO: Final = 0x01
SYS_HEAT: Final = 0x04
CTRL_SEQ_HEATING_ONLY: Final = 0x02
RUNSTATE_HEAT_ON: Final = 0x0001
RUNSTATE_IDLE: Final = 0x0000

# WT-A03E Zigbee2MQTT mapping:
# https://www.zigbee2mqtt.io/devices/WT-A03E.html
# Device-support context:
# https://github.com/zigpy/zha-device-handlers/issues/4518
# Attribute IDs/types are also present in the anonymized W600 ZHA diagnostic
# snapshot shipped with the upstream preparation notes.
# The mode attributes 0x0271/0x027D and valve 0x0360 were also exercised on
# a real W600; their raw valve scale remains explicitly unconfirmed below.
ATTR_THERMOSTAT_ENABLED: Final = 0x0271
ATTR_CALIBRATE: Final = 0x0270
ATTR_WINDOW_DETECTION: Final = 0x0273
# Known mapping retained for future wire-level work; intentionally not exposed
# or read/reported by this patch after device testing showed no useful HA state.
ATTR_TEMPERATURE_CONTROL_ABNORMAL_NOTIFICATION: Final = 0x0274
ATTR_CHILD_LOCK: Final = 0x0277
ATTR_ANTI_FREEZE_TEMPERATURE: Final = 0x0279
ATTR_CALIBRATED: Final = 0x027B
ATTR_SCHEDULE_ENABLED: Final = 0x027D
ATTR_DEVICE_STATE_AUX: Final = 0x0310
ATTR_DEVICE_STATE: Final = 0x0311
ATTR_DISPLAY_FLIP: Final = 0x0330
ATTR_VALVE_POSITION_RAW: Final = 0x0360

# Confirmed mode matrix from the WT-A03E converter and real-device tests.
# The standard 0x0201/0x001C attribute is deliberately never sent.
W600_MODE_WRITES: Final = {
    SYS_OFF: {
        ATTR_THERMOSTAT_ENABLED: 0,
        ATTR_SCHEDULE_ENABLED: 0,
    },
    SYS_HEAT: {
        ATTR_THERMOSTAT_ENABLED: 1,
        ATTR_SCHEDULE_ENABLED: 0,
    },
    SYS_AUTO: {
        ATTR_THERMOSTAT_ENABLED: 1,
        ATTR_SCHEDULE_ENABLED: 1,
    },
}

# The raw value is exposed only as a diagnostic sensor.  The mapping used for
# hvac_action is intentionally conservative until more device traces confirm
# whether the firmware reports percent or tenths of a percent:
#   raw == 0 -> idle; raw > 0 -> heating when thermostat_enabled is true.


def _iter_status_records(records: Any) -> Iterable[Any]:
    """Yield write-status records from Zigpy's nested response shape.

    Current Zigpy returns ``list[list[WriteAttributesStatusRecord]]`` because
    one call may be split into multiple wire requests.  Older releases and
    some test doubles return a flat list, so both shapes are accepted.
    """
    if isinstance(records, (list, tuple)):
        for item in records:
            yield from _iter_status_records(item)
    elif records is not None:
        yield records


def _all_success(records: Any) -> bool:
    """Return true only when every Zigpy write-status record is successful."""
    flattened = list(_iter_status_records(records))
    return bool(flattened) and all(
        getattr(record, "status", None) == foundation.Status.SUCCESS
        for record in flattened
    )


def _calibration_status_name(value: Any) -> str:
    """Return a stable human-readable name for the confirmed 0x027B enum."""
    return {
        0: "not_ready",
        1: "ready",
        2: "error",
        3: "in_progress",
    }.get(int(value), f"unknown_{value}")


def _key_matches_attrid(key: Any, attrid: int, name: str) -> bool:
    """Match a ``write_attributes`` dict key in every form Zigpy accepts.

    Zigpy's public ``write_attributes`` takes attribute names (str),
    numeric attribute ids (int) and ``ZCLAttributeDef`` objects as dict
    keys.  The quirk must recognise sensitive keys -- above all the
    standard ``system_mode``, which must never leak to the device -- in
    all accepted forms.
    """
    if isinstance(key, foundation.ZCLAttributeDef):
        return key.id == attrid or key.name == name
    if isinstance(key, str):
        return key == name
    try:
        return int(key) == attrid
    except (TypeError, ValueError):
        return False


class AqaraW600Thermostat(CustomCluster, Thermostat):
    """Thermostat cluster with W600's composite off/heat/auto mode path."""

    _CONSTANT_ATTRIBUTES = {
        ATTR_CTRL_SEQUENCE_OF_OPER: CTRL_SEQ_HEATING_ONLY,
    }

    def _fcc0(self):
        return getattr(self.endpoint, "aqara_w600_fcc0", None)

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Keep ZHA's stock Thermostat entity in a heating-only shape.

        ZHA 2.3 maps standard ZCL ``SystemMode.Auto`` to Home Assistant's
        ``heat_cool`` UI, which expects cooling setpoints the W600 does not
        implement and consequently leaves ``target_temperature`` empty.  The
        W600 schedule state remains cached in 0xFCC0/0x027D and is still used
        for writes; the generic ZHA entity is presented as heating-only until
        a dedicated entity implementation can expose a true ``auto`` mode.
        """
        if attrid == ATTR_CTRL_SEQUENCE_OF_OPER:
            value = CTRL_SEQ_HEATING_ONLY
        elif attrid == ATTR_SYSTEM_MODE and value == SYS_AUTO:
            value = SYS_HEAT
        super()._update_attribute(attrid, value)

    async def _write_fcc0(self, attributes: dict[int, int]):
        """Write confirmed W600 attributes with Aqara manufacturer code.

        ``update_cache=False`` keeps Zigpy from locally caching the
        attributes of a write before it is validated: the quirk updates
        the FCC0 cache itself only after the complete write set
        succeeded, so one partially failed write changes nothing
        locally (rule: no local state change presented as success).
        """
        fcc0 = self._fcc0()
        if fcc0 is None:
            raise RuntimeError("W600 Aqara cluster 0xFCC0 is unavailable")
        return await fcc0.write_attributes(
            attributes,
            manufacturer=AQARA_MANUFACTURER_CODE,
            update_cache=False,
        )

    def _sync_system_mode_from_w600(self) -> None:
        """Publish the persistent mode from enable and schedule telemetry."""
        fcc0 = self._fcc0()
        if fcc0 is None:
            return

        enabled = fcc0._attr_cache.get(ATTR_THERMOSTAT_ENABLED)
        schedule = fcc0._attr_cache.get(ATTR_SCHEDULE_ENABLED)
        if enabled is None:
            return

        if int(enabled) == 0:
            mode = SYS_OFF
        elif int(schedule or 0) != 0:
            mode = SYS_AUTO
        else:
            mode = SYS_HEAT
        self._update_attribute(ATTR_SYSTEM_MODE, mode)

    def _sync_running_state_from_valve(self, valve_position: Any) -> None:
        """Map valve telemetry to action only; never to persistent HVAC mode.

        The W600 reports valve position via ``0xFCC0/0x0360``.  The exact
        scale (raw units vs. percent vs. tenths of a percent) is still
        UNCONFIRMED; see the module-level note next to
        ``ATTR_VALVE_POSITION_RAW``.  Until Phase 3 device-side logging
        clarifies the range, the mapping stays intentionally conservative:

        * ``enabled == 0``  -> idle, regardless of the reported valve value.
        * ``enabled != 0``  -> idle when ``valve_position == 0``,
                              heating when ``valve_position > 0``.

        A higher deadband (e.g. treat ``raw < 50`` as idle when the device
        reports tenths of a percent) will only be introduced after the
        real-device traces confirm whether such flutter exists.  Until
        then this function only touches ``ATTR_RUNNING_STATE``; it never
        touches ``ATTR_SYSTEM_MODE``.
        """
        fcc0 = self._fcc0()
        enabled = (
            fcc0._attr_cache.get(ATTR_THERMOSTAT_ENABLED) if fcc0 is not None else None
        )
        if enabled is None or int(enabled) == 0:
            state = RUNSTATE_IDLE
        else:
            state = RUNSTATE_HEAT_ON if int(valve_position) > 0 else RUNSTATE_IDLE
        self._update_attribute(ATTR_RUNNING_STATE, state)

    async def _set_w600_mode(self, requested_mode: int) -> bool:
        """Apply the Z2M mode matrix without a standard system_mode write."""
        if requested_mode not in W600_MODE_WRITES:
            return False

        status = await self._write_fcc0(W600_MODE_WRITES[requested_mode])
        if not _all_success(status):
            return False

        # Z2M clears manual override for all explicit mode changes.
        hold_status = await super().write_attributes({ATTR_TEMP_SETPOINT_HOLD: 0})
        if not _all_success(hold_status):
            return False

        # Change the cache only after all device writes have succeeded.
        fcc0 = self._fcc0()
        for attrid, value in W600_MODE_WRITES[requested_mode].items():
            fcc0._update_attribute(attrid, value)
        self._update_attribute(ATTR_TEMP_SETPOINT_HOLD, 0)
        self._sync_system_mode_from_w600()
        if requested_mode == SYS_OFF:
            self._update_attribute(ATTR_RUNNING_STATE, RUNSTATE_IDLE)
        return True

    async def _prepare_setpoint_write(self) -> bool:
        """Wake an explicitly off thermostat into heat before the setpoint.

        Follows the Zigbee2MQTT reference order: ``0xFCC0/0x0271=1`` is sent
        before the standard ``0x0201/0x0012`` setpoint so the device is
        already in heat when the new target temperature arrives.

        The wake is attempted **only** when the FCC0 cache explicitly carries
        ``ATTR_THERMOSTAT_ENABLED == 0``.  An unknown cache (sleeping device,
        before the first attribute read) is treated as "do not wake" — the
        setpoint write must never be blocked on extra 0xFCC0 traffic, that
        was the regression that broke ``target_temperature`` in the climate
        card.  Returns ``True`` when a wake write was sent and succeeded,
        ``False`` otherwise; the caller must always proceed with the setpoint
        regardless of this return value.
        """
        fcc0 = self._fcc0()
        if fcc0 is None:
            return False

        # ``_attr_cache.get(...) is None`` distinguishes "unknown" from
        # an explicit zero.  Only an explicit zero triggers the wake.
        enabled_raw = fcc0._attr_cache.get(ATTR_THERMOSTAT_ENABLED)
        if enabled_raw is None or int(enabled_raw) != 0:
            return False

        try:
            status = await self._write_fcc0({ATTR_THERMOSTAT_ENABLED: 1})
        except (TimeoutError, zigpy.exceptions.DeliveryError) as exc:
            _LOGGER.warning(
                "W600 wake write (0xFCC0/0x0271=1) before setpoint failed: %s",
                exc,
            )
            return False

        if not _all_success(status):
            _LOGGER.warning(
                "W600 wake write (0xFCC0/0x0271=1) before setpoint returned a"
                " non-success status record; setpoint will be sent anyway"
            )
            return False

        fcc0._update_attribute(ATTR_THERMOSTAT_ENABLED, 1)
        self._sync_system_mode_from_w600()
        return True

    async def write_attributes(
        self, attributes: dict[str, Any], *args: Any, **kwargs: Any
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Route system_mode to 0xFCC0 and retain standard setpoint handling.

        Order for the setpoint path follows the Zigbee2MQTT reference:
        wake the device into heat first (when the cache explicitly says it
        is off), then write the standard setpoint, then arm the manual
        override when the schedule is on.
        """
        outgoing = dict(attributes)
        # Pop every accepted key form for system_mode; the last one wins
        # when a caller passes several.  This keeps the standard
        # 0x001C write strictly off the wire no matter how the caller
        # spells the key.
        requested_mode = None
        for key in list(outgoing):
            if _key_matches_attrid(key, ATTR_SYSTEM_MODE, "system_mode"):
                requested_mode = outgoing.pop(key)
        has_setpoint = any(
            _key_matches_attrid(
                key, ATTR_OCCUPIED_HEATING_SETPOINT, "occupied_heating_setpoint"
            )
            for key in outgoing
        )
        # Keep a flat internal list; Zigpy's public return shape is rebuilt
        # as one outer list at the end.  This matters on current Zigpy, where
        # ``Cluster.write_attributes`` returns list[list[StatusRecord]].
        result = []

        if requested_mode is not None:
            try:
                requested_mode = int(requested_mode)
            except (TypeError, ValueError):
                requested_mode = -1
            if requested_mode not in (SYS_OFF, SYS_HEAT, SYS_AUTO):
                result.append(
                    foundation.WriteAttributesStatusRecord(
                        status=foundation.Status.UNSUPPORTED_ATTRIBUTE,
                        attrid=ATTR_SYSTEM_MODE,
                    )
                )
            elif not await self._set_w600_mode(requested_mode):
                result.append(
                    foundation.WriteAttributesStatusRecord(
                        status=foundation.Status.FAILURE,
                        attrid=ATTR_SYSTEM_MODE,
                    )
                )
            else:
                result.append(
                    foundation.WriteAttributesStatusRecord(
                        status=foundation.Status.SUCCESS,
                        attrid=ATTR_SYSTEM_MODE,
                    )
                )

        # Per the Z2M reference, wake a sleeping/off device into heat before
        # the setpoint.  This is best-effort: a wake failure only logs and
        # never blocks the standard 0x0201/0x0012 write that follows.
        if has_setpoint:
            await self._prepare_setpoint_write()

        # The temperature write is the primary operation.  Do not gate it on
        # extra 0xFCC0 traffic: an unknown enabled-cache must not block the
        # write, and a sleeping battery device may defer the response.
        if outgoing:
            result.extend(
                _iter_status_records(
                    await super().write_attributes(outgoing, *args, **kwargs)
                )
            )

        if has_setpoint and outgoing:
            fcc0 = self._fcc0()
            if (
                fcc0 is not None
                and int(fcc0._attr_cache.get(ATTR_SCHEDULE_ENABLED) or 0) != 0
            ):
                hold_status = await super().write_attributes(
                    {ATTR_TEMP_SETPOINT_HOLD: 1}
                )
                if _all_success(hold_status):
                    self._update_attribute(ATTR_TEMP_SETPOINT_HOLD, 1)
                else:
                    _LOGGER.warning(
                        "W600 setpoint was written but manual override was not enabled"
                    )

        # Current Zigpy expects list[list[WriteAttributesStatusRecord]].
        # Returning the same shape also keeps ZHA's write helper compatible
        # when a mode and a setpoint are written in one service call.
        return [result]

    async def refresh_w600_mode_state(self) -> None:
        """Read the Z2M startup state needed to reconstruct the climate mode."""
        fcc0 = self._fcc0()
        if fcc0 is None:
            return
        await fcc0.read_attributes(
            [ATTR_THERMOSTAT_ENABLED, ATTR_SCHEDULE_ENABLED, ATTR_DEVICE_STATE],
            manufacturer=AQARA_MANUFACTURER_CODE,
        )
        await super().read_attributes([ATTR_TEMP_SETPOINT_HOLD])
        self._sync_system_mode_from_w600()


class AqaraW600FCC0(CustomCluster):
    """Confirmed Aqara W600 attributes on manufacturer cluster 0xFCC0."""

    cluster_id = 0xFCC0
    name = "AqaraW600FCC0"
    ep_attribute = "aqara_w600_fcc0"

    class AttributeDefs(BaseAttributeDefs):
        """W600 attributes with their exact Aqara manufacturer code."""

        calibrate: Final = ZCLAttributeDef(
            id=ATTR_CALIBRATE, type=t.uint8_t, manufacturer_code=AQARA_MANUFACTURER_CODE
        )
        thermostat_enabled: Final = ZCLAttributeDef(
            id=ATTR_THERMOSTAT_ENABLED,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        window_detection: Final = ZCLAttributeDef(
            id=ATTR_WINDOW_DETECTION,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        temperature_control_abnormal_notification: Final = ZCLAttributeDef(
            id=ATTR_TEMPERATURE_CONTROL_ABNORMAL_NOTIFICATION,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        child_lock: Final = ZCLAttributeDef(
            id=ATTR_CHILD_LOCK,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        anti_freeze_temperature: Final = ZCLAttributeDef(
            id=ATTR_ANTI_FREEZE_TEMPERATURE,
            type=t.uint32_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        calibrated: Final = ZCLAttributeDef(
            id=ATTR_CALIBRATED,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        schedule_enabled: Final = ZCLAttributeDef(
            id=ATTR_SCHEDULE_ENABLED,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        device_state_aux: Final = ZCLAttributeDef(
            id=ATTR_DEVICE_STATE_AUX,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        device_state: Final = ZCLAttributeDef(
            id=ATTR_DEVICE_STATE,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        display_flip: Final = ZCLAttributeDef(
            id=ATTR_DISPLAY_FLIP,
            type=t.uint8_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )
        valve_position_raw: Final = ZCLAttributeDef(
            id=ATTR_VALVE_POSITION_RAW,
            type=t.uint16_t,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)
        thermostat = getattr(self.endpoint, "thermostat", None)
        if not isinstance(thermostat, AqaraW600Thermostat):
            return
        if attrid in (ATTR_THERMOSTAT_ENABLED, ATTR_SCHEDULE_ENABLED):
            thermostat._sync_system_mode_from_w600()
        elif attrid == ATTR_VALVE_POSITION_RAW:
            thermostat._sync_running_state_from_valve(value)

    async def configure_reporting(self) -> None:
        """Refresh W600 state and request reports after a device wake-up."""
        await super().configure_reporting()
        try:
            await self.configure_reporting_multiple(
                {
                    self.find_attribute(
                        ATTR_THERMOSTAT_ENABLED,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_SCHEDULE_ENABLED,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_DEVICE_STATE,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_VALVE_POSITION_RAW,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_WINDOW_DETECTION,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_CHILD_LOCK,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_ANTI_FREEZE_TEMPERATURE,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_CALIBRATED,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                    self.find_attribute(
                        ATTR_DISPLAY_FLIP,
                        manufacturer_code=AQARA_MANUFACTURER_CODE,
                    ): ZigpyReportingConfig(5, 900, 1),
                }
            )
        except (TimeoutError, zigpy.exceptions.DeliveryError) as exc:
            _LOGGER.warning("W600 FCC0 reporting configuration deferred: %s", exc)

        try:
            await self.read_attributes(
                [
                    ATTR_THERMOSTAT_ENABLED,
                    ATTR_SCHEDULE_ENABLED,
                    ATTR_DEVICE_STATE_AUX,
                    ATTR_DEVICE_STATE,
                    ATTR_VALVE_POSITION_RAW,
                    ATTR_WINDOW_DETECTION,
                    ATTR_CHILD_LOCK,
                    ATTR_ANTI_FREEZE_TEMPERATURE,
                    ATTR_CALIBRATED,
                    ATTR_DISPLAY_FLIP,
                ],
                manufacturer=AQARA_MANUFACTURER_CODE,
            )
        except (TimeoutError, zigpy.exceptions.DeliveryError) as exc:
            _LOGGER.warning("W600 FCC0 state read deferred: %s", exc)


# Single Quirk V2 registration.  The two replacement clusters retain the
# W600 transport and mode behavior while the same registration exposes the
# confirmed
# Aqara attributes as native Home Assistant entities.  All of these entities
# use the replacement Aqara cluster and therefore retain manufacturer code
# 4447 for reads/writes.

_REPORTING = ReportingConfig(min_interval=5, max_interval=900, reportable_change=1)

(
    QuirkBuilder(AQARA, MODEL)
    .zigpy_device_class(CustomZigpyDevice)
    .replaces(AqaraW600Thermostat, endpoint_id=1)
    .replaces(AqaraW600FCC0, endpoint_id=1)
    .prevent_default_entity_creation(
        endpoint_id=2,
        cluster_id=Thermostat.cluster_id,
    )
    .switch(
        attribute_name=AqaraW600FCC0.AttributeDefs.child_lock.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        reporting_config=_REPORTING,
        translation_key="child_lock",
        fallback_name="Child lock",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-child_lock",
    )
    .switch(
        attribute_name=AqaraW600FCC0.AttributeDefs.display_flip.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        reporting_config=_REPORTING,
        translation_key="display_flip",
        fallback_name="Display flip",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-display_flip",
    )
    .switch(
        attribute_name=AqaraW600FCC0.AttributeDefs.window_detection.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        reporting_config=_REPORTING,
        translation_key="window_detection",
        fallback_name="Open window detection",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-window_detection",
    )
    .number(
        attribute_name=AqaraW600FCC0.AttributeDefs.anti_freeze_temperature.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        min_value=5,
        max_value=15,
        step=0.5,
        unit="°C",
        mode="box",
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        reporting_config=_REPORTING,
        translation_key="anti_freeze_temperature",
        fallback_name="Anti-freeze temperature",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-anti_freeze_temperature",
    )
    .write_attr_button(
        attribute_name=AqaraW600FCC0.AttributeDefs.calibrate.name,
        attribute_value=1,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="calibrate",
        fallback_name="Start calibration",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-calibrate",
    )
    .sensor(
        attribute_name=AqaraW600FCC0.AttributeDefs.calibrated.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        attribute_converter=_calibration_status_name,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=_REPORTING,
        translation_key="calibration_status",
        fallback_name="Calibration status",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-calibration_status",
    )
    .binary_sensor(
        attribute_name=Thermostat.AttributeDefs.temp_setpoint_hold.name,
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=_REPORTING,
        translation_key="override_active",
        fallback_name="Override active",
        unique_id_suffix=f"{Thermostat.cluster_id}-override_active",
    )
    .sensor(
        attribute_name="local_temperature",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=2,
        divisor=100,
        suggested_display_precision=1,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit="°C",
        initially_disabled=True,
        translation_key="local_temperature_internal",
        fallback_name="Internal temperature (endpoint 2)",
        unique_id_suffix=f"{Thermostat.cluster_id}-ep2-local_temperature_internal",
    )
    .sensor(
        attribute_name=AqaraW600FCC0.AttributeDefs.valve_position_raw.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        suggested_display_precision=0,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=_REPORTING,
        translation_key="valve_position_raw",
        fallback_name="Valve position (raw)",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-valve_position_raw",
    )
    .sensor(
        attribute_name=AqaraW600FCC0.AttributeDefs.device_state_aux.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        suggested_display_precision=0,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=_REPORTING,
        translation_key="device_state_aux",
        fallback_name="Device state auxiliary (raw)",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-device_state_aux",
    )
    .sensor(
        attribute_name=AqaraW600FCC0.AttributeDefs.device_state.name,
        cluster_id=AqaraW600FCC0.cluster_id,
        endpoint_id=1,
        suggested_display_precision=0,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=_REPORTING,
        translation_key="device_state",
        fallback_name="Device state (raw)",
        unique_id_suffix=f"{AqaraW600FCC0.cluster_id}-device_state",
    )
    .add_to_registry()
)

# Endpoint 2 is intentionally reduced to an optional, disabled temperature
# sensor.  The device currently reports 0 °C there; it must not create a
# second climate or HVAC-action entity, and the sensor can be enabled later
# if the firmware starts reporting a meaningful value.
