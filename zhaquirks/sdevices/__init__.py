"""SDevices shared clusters, enums and constants.

These handlers cover the native SDevices Zigbee devices, ported from the
``zigbee-herdsman-converters`` reference implementation. Device families live in
their own modules:

* ``switch.py`` - wall switches (SBDV-00196 / 00197 / 00199 / 00200)
* ``cover.py``  - window covering mode of the two-button switches (00199 / 00200)
* ``socket.py`` - wall socket (SBDV-00202)

The manufacturer-specific cluster 0xFCCF (``manuSpecificSDevices``) and the
manufacturer attributes added to the standard ``OnOff`` (0x0006),
``WindowCovering`` (0x0102) and ``Diagnostic`` (0x0B05) clusters all use
manufacturer code 0x152F (5423).

The 0xFCCF cluster declares the attributes used by the switch and socket
families. The RTC attributes (used only by the thermostat model, not ported
yet) are omitted.
"""

from __future__ import annotations

from typing import Any, Final

import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import ReportingConfig
from zigpy.zcl.clusters.closures import WindowCovering, WindowCoveringMode
from zigpy.zcl.clusters.general import DeviceTemperature, MultistateInput, OnOff
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.foundation import BaseAttributeDefs, Status, ZCLAttributeDef

from zhaquirks.clusters import CustomCluster
from zhaquirks.const import ZHA_SEND_EVENT

SDEVICES = "SDevices"
SDEVICES_MFR_CODE = 0x152F  # 5423 (see node descriptor)


class _SDevicesFirmwareReportingMixin:
    """Keep the reporting configuration owned by the device firmware.

    ZHA platform entities bind standard clusters and normally follow that with
    ``Configure Reporting`` using ZHA's own intervals. SDevices firmware ships
    the reporting table, so acknowledge those configuration attempts locally
    while leaving the table on the device unchanged.
    """

    async def configure_reporting_multiple(
        self, config: dict[ZCLAttributeDef, ReportingConfig]
    ) -> dict[ZCLAttributeDef, Status]:
        """Do not replace the firmware reporting configuration."""
        return dict.fromkeys(config, Status.SUCCESS)


class _SDevicesBindOnlyMixin(_SDevicesFirmwareReportingMixin):
    """Bind a report source without sending ``Configure Reporting``."""

    async def apply_custom_configuration(self, *args, **kwargs) -> None:
        """Bind reports to the coordinator and retain firmware defaults."""
        await self.bind()


class ButtonEventMode(t.enum8):
    """Kind of events emitted on a button press (``event_mode``)."""

    No_event = 0x00
    Multistate_input = 0x01


class RelayMode(t.enum8):
    """Relay/button coupling mode (``relay_mode``)."""

    Control_relay = 0x00
    Decoupled = 0x01


class ButtonsMode(t.enum8):
    """Cover button mode (``buttons_mode``, EP3)."""

    Normal = 0x00
    Inverted = 0x01


class PowerProfile(t.enum8):
    """Power profile used when no neutral wire is connected (``power_profile``).

    ``Quick`` is the most responsive; ``Anti_flicker_*`` values trade responsiveness
    for a longer polling period (milliseconds) to avoid flicker; the fallback value
    is the safest mode the device falls back to on instability.
    """

    Quick = 0x00
    Anti_flicker_250 = 0x01
    Anti_flicker_500 = 0x02
    Anti_flicker_750 = 0x03
    Anti_flicker_1000 = 0x04
    Anti_flicker_1250 = 0x05
    Anti_flicker_1750 = 0x06
    Anti_flicker_2000 = 0x07
    Anti_flicker_fallback = 0xFE


class LedIndicationType(t.enum8):
    """LED indication style (``led_indication_type``)."""

    Continuous = 0x00
    Flashes = 0x01


class NeutralPresence(t.enum8):
    """Read-only indicator of neutral wire presence (``neutral_presence``)."""

    No = 0x00
    Yes = 0x01


class EmergencyRecovery(t.enum8):
    """Auto-recovery condition after an emergency shutoff (``emergency_shutoff_recovery``).

    The attribute stays BITMAP16 on the wire; this enum8 only drives the select
    entity, like ``RelayMode`` over the Bool ``sdevices_relay_decouple`` attribute.
    """

    Disabled = 0x00
    Voltage_is_good = 0x01


class SDevicesCluster(_SDevicesFirmwareReportingMixin, CustomCluster):
    """Manufacturer-specific cluster 0xFCCF (``manuSpecificSDevices``).

    Declares the attributes used by the switch and socket families; the
    thermostat-only RTC attributes are omitted.
    """

    cluster_id: Final = 0xFCCF
    ep_attribute: Final = "sdevices_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # button
        button_event_mode: Final = ZCLAttributeDef(
            id=0x1001,
            type=ButtonEventMode,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        button_enable_multi_click: Final = ZCLAttributeDef(
            id=0x1002,
            type=t.Bool,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        child_lock: Final = ZCLAttributeDef(
            id=0x1003,
            type=t.Bool,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        # LED indication in the ON state
        led_indicator_on_enable: Final = ZCLAttributeDef(
            id=0x2001,
            type=t.Bool,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        led_indicator_on_h: Final = ZCLAttributeDef(
            id=0x2002,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        led_indicator_on_s: Final = ZCLAttributeDef(
            id=0x2003,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        led_indicator_on_b: Final = ZCLAttributeDef(
            id=0x2004,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        # LED indication in the OFF state
        led_indicator_off_enable: Final = ZCLAttributeDef(
            id=0x2005,
            type=t.Bool,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        led_indicator_off_h: Final = ZCLAttributeDef(
            id=0x2006,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        led_indicator_off_s: Final = ZCLAttributeDef(
            id=0x2007,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        led_indicator_off_b: Final = ZCLAttributeDef(
            id=0x2008,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        led_indication_type: Final = ZCLAttributeDef(
            id=0x2009,
            type=LedIndicationType,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        # emergency shutoff and protection thresholds (socket 00202)
        emergency_shutoff_state: Final = ZCLAttributeDef(
            id=0x3001,
            type=t.bitmap16,
            access="rp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        # Per-flag views of emergency_shutoff_state (0x3001). These are synthetic,
        # local-only attributes - never read or written over the air. They are
        # populated by SDevicesCluster._update_attribute splitting the bitmap, so
        # each flag becomes its own binary sensor that updates correctly on a live
        # attribute report (the generic binary sensor ignores attribute_converter on
        # updates and would otherwise flip every flag together).
        emergency_overvoltage: Final = ZCLAttributeDef(
            id=0x3101, type=t.Bool, access="r"
        )
        emergency_undervoltage: Final = ZCLAttributeDef(
            id=0x3102, type=t.Bool, access="r"
        )
        emergency_overcurrent: Final = ZCLAttributeDef(
            id=0x3103, type=t.Bool, access="r"
        )
        emergency_overheat: Final = ZCLAttributeDef(id=0x3104, type=t.Bool, access="r")
        emergency_shutoff_recovery: Final = ZCLAttributeDef(
            id=0x3002,
            type=t.bitmap16,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        upper_voltage_threshold: Final = ZCLAttributeDef(
            id=0x3011,
            type=t.uint32_t,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        lower_voltage_threshold: Final = ZCLAttributeDef(
            id=0x3012,
            type=t.uint32_t,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        upper_current_threshold: Final = ZCLAttributeDef(
            id=0x3013,
            type=t.uint32_t,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        upper_temp_threshold: Final = ZCLAttributeDef(
            id=0x3014,
            type=t.int16s,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        # energy metering (socket 00202)
        rms_voltage_mv: Final = ZCLAttributeDef(
            id=0x4001,
            type=t.uint32_t,
            access="rp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        rms_current_ma: Final = ZCLAttributeDef(
            id=0x4002,
            type=t.uint32_t,
            access="rp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        active_power_mw: Final = ZCLAttributeDef(
            id=0x4003,
            type=t.int32s,
            access="rp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        # power without neutral (optional-neutral models 00197 / 00200)
        power_profile: Final = ZCLAttributeDef(
            id=0x4100,
            type=PowerProfile,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        neutral_presence: Final = ZCLAttributeDef(
            id=0x4101,
            type=NeutralPresence,
            access="rp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )

    # Bits of emergency_shutoff_state (0x3001) -> synthetic per-flag attribute.
    _EMERGENCY_BITS: Final = {
        0x3101: 0x01,  # overvoltage
        0x3102: 0x02,  # undervoltage
        0x3103: 0x04,  # overcurrent
        0x3104: 0x08,  # overheat
    }

    def _update_attribute(self, attrid, value):
        """Split the emergency bitmap into per-flag attributes on update."""
        super()._update_attribute(attrid, value)
        if (
            attrid == self.AttributeDefs.emergency_shutoff_state.id
            and value is not None
        ):
            for flag_id, bit in self._EMERGENCY_BITS.items():
                super()._update_attribute(flag_id, bool(value & bit))


class SDevicesReportingCluster(_SDevicesBindOnlyMixin, SDevicesCluster):
    """Manufacturer cluster instances that produce attribute reports."""

    async def apply_custom_configuration(self, *args, **kwargs) -> None:
        """Bind only the report-source endpoints used by current devices."""
        if self.endpoint.endpoint_id in (1, 3):
            await super().apply_custom_configuration(*args, **kwargs)


class SDevicesOnOffCluster(_SDevicesFirmwareReportingMixin, CustomCluster, OnOff):
    """``OnOff`` (0x0006) with the SDevices relay-decouple attribute."""

    class AttributeDefs(OnOff.AttributeDefs):
        """Attribute definitions."""

        sdevices_relay_decouple: Final = ZCLAttributeDef(
            id=0x10DC,
            type=t.Bool,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )


class SDevicesWindowCoveringCluster(
    _SDevicesFirmwareReportingMixin, CustomCluster, WindowCovering
):
    """``WindowCovering`` (0x0102) with SDevices manufacturer attributes (EP3).

    The attribute IDs 0x1001-0x1003 here do not clash with the same IDs on the
    0xFCCF cluster - attribute IDs are scoped per cluster.
    """

    class AttributeDefs(WindowCovering.AttributeDefs):
        """Attribute definitions."""

        sdevices_calibration_time: Final = ZCLAttributeDef(
            id=0x1001,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        sdevices_buttons_mode: Final = ZCLAttributeDef(
            id=0x1002,
            type=ButtonsMode,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        sdevices_motor_timeout: Final = ZCLAttributeDef(
            id=0x1003,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        cover_calibration_mode: Final = ZCLAttributeDef(
            id=0xF001, type=t.Bool, access="rw"
        )
        cover_maintenance_mode: Final = ZCLAttributeDef(
            id=0xF002, type=t.Bool, access="rw"
        )
        cover_led_feedback: Final = ZCLAttributeDef(id=0xF003, type=t.Bool, access="rw")

    _MODE_BITS: Final = {
        AttributeDefs.cover_calibration_mode.id: WindowCoveringMode.Run_in_calibration_mode,
        AttributeDefs.cover_maintenance_mode.id: WindowCoveringMode.Motor_in_maintenance_mode,
        AttributeDefs.cover_led_feedback.id: WindowCoveringMode.LEDs_display_feedback,
    }

    def _update_attribute(self, attrid, value):
        """Split the standard Mode bitmap into local per-bit attributes."""
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.window_covering_mode.id and value is not None:
            mode = WindowCoveringMode(value)
            for flag_id, bit in self._MODE_BITS.items():
                super()._update_attribute(flag_id, bit in mode)

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> list:
        """Translate local per-bit writes into one Mode bitmap write."""
        mode_updates: list[tuple[WindowCoveringMode, bool]] = []
        translated: dict[str | int | ZCLAttributeDef, Any] = {}

        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr, manufacturer_code=manufacturer)
            if (bit := self._MODE_BITS.get(attr_def.id)) is None:
                translated[attr] = value
            else:
                mode_updates.append((bit, bool(value)))

        mode_attr = self.AttributeDefs.window_covering_mode
        if mode_updates:
            current_mode = self.get(mode_attr.id)
            if current_mode is None:
                success, _ = await self.read_attributes(
                    [mode_attr], manufacturer=manufacturer
                )
                current_mode = success.get(mode_attr.name)
            if current_mode is None:
                raise ValueError(
                    "Unable to read WindowCovering.Mode before updating it"
                )

            mode = WindowCoveringMode(current_mode)
            for bit, enabled in mode_updates:
                if enabled:
                    mode |= bit
                else:
                    mode &= ~bit
            translated[mode_attr] = mode

        result = await super().write_attributes(
            translated, manufacturer=manufacturer, **kwargs
        )
        if mode_updates and all(
            record.status is Status.SUCCESS for records in result for record in records
        ):
            self.update_attribute(mode_attr.id, translated[mode_attr])
        return result


class SDevicesDiagnosticCluster(_SDevicesBindOnlyMixin, CustomCluster, Diagnostic):
    """``Diagnostic`` (0x0B05) with SDevices telemetry (uptime / clicks / switches)."""

    class AttributeDefs(Diagnostic.AttributeDefs):
        """Attribute definitions."""

        sdevices_uptime_s: Final = ZCLAttributeDef(
            id=0x1001,
            type=t.uint32_t,
            access="rp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        sdevices_button1_clicks: Final = ZCLAttributeDef(
            id=0x1002,
            type=t.uint32_t,
            access="rp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        sdevices_button2_clicks: Final = ZCLAttributeDef(
            id=0x1003,
            type=t.uint32_t,
            access="rp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        sdevices_button3_clicks: Final = ZCLAttributeDef(
            id=0x1004,
            type=t.uint32_t,
            access="rp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        sdevices_relay1_switches: Final = ZCLAttributeDef(
            id=0x1005,
            type=t.uint32_t,
            access="rp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )
        sdevices_relay2_switches: Final = ZCLAttributeDef(
            id=0x1006,
            type=t.uint32_t,
            access="rp",
            manufacturer_code=SDEVICES_MFR_CODE,
        )


class _SDevicesBaseButtonCluster(
    _SDevicesBindOnlyMixin, CustomCluster, MultistateInput
):
    """MultistateInput base that binds physical button reports to the coordinator."""


class SDevicesButtonCluster(_SDevicesBaseButtonCluster):
    """Single-button ``MultistateInput`` (0x0012): present_value -> button events.

    The device reports button presses via the ``present_value`` attribute
    (0 = hold, 1 = single, 2 = double). Each value is turned into a
    ``zha_send_event`` matching the device automation triggers.
    """

    _ACTIONS: dict[int, str] = {
        0: "button_hold",
        1: "button_single",
        2: "button_double",
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == MultistateInput.AttributeDefs.present_value.id:
            action = self._ACTIONS.get(value)
            if action is not None:
                self.listener_event(ZHA_SEND_EVENT, action, {})


class SDevicesTwoButtonCluster(_SDevicesBaseButtonCluster):
    """Two-gang ``MultistateInput`` (0x0012): present_value -> per-endpoint events.

    Emits ``{single,double,hold}_switch_{endpoint_id}`` so the two gangs (EP1/EP2)
    produce distinct actions, matching ``postfixWithEndpointName`` in the reference.
    """

    _ACTIONS: dict[int, str] = {0: "hold", 1: "single", 2: "double"}

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == MultistateInput.AttributeDefs.present_value.id:
            raw = self._ACTIONS.get(value)
            if raw is not None:
                action = f"{raw}_switch_{self.endpoint.endpoint_id}"
                self.listener_event(ZHA_SEND_EVENT, action, {})


class SDevicesDeviceTemperatureCluster(
    _SDevicesBindOnlyMixin, CustomCluster, DeviceTemperature
):
    """Device temperature using the reporting table shipped by the firmware."""
