"""SDevices smart wall switches.

Covers the native SDevices wall switches:

* SBDV-00196  Smart Wall Switch (with neutral, single button)
* SBDV-00197  Smart Wall Switch (with optional neutral, single button)
* SBDV-00199  Smart Wall Switch (with neutral, two buttons)
* SBDV-00200  Smart Wall Switch (with optional neutral, two buttons)

The "optional neutral" models (00197 / 00200) additionally expose
``power_profile`` / ``led_indication_type`` / ``neutral_presence``.

The two-button models (00199 / 00200) are dual-mode: they announce either as a
two-gang switch (relays on EP1/EP2) or as a window covering (EP3). Both signatures
share one quirk registration per model; covering-mode entity metadata lives in
``cover.py``.

The relays are exposed as ``switch`` entities: the endpoint device type is set
to ``ON_OFF_OUTPUT`` so ZHA maps the ``OnOff`` cluster to the switch platform,
matching the reference ``zigbee-herdsman-converters`` implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import zigpy.device
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff

from zhaquirks.builder import EntityType, QuirkBuilder, UnitOfTime
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    COMMAND,
    DOUBLE_PRESS,
    LONG_PRESS,
    SHORT_PRESS,
)
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.sdevices import (
    SDEVICES,
    ButtonEventMode,
    LedIndicationType,
    PowerProfile,
    RelayMode,
    SDevicesButtonCluster,
    SDevicesCluster,
    SDevicesDiagnosticCluster,
    SDevicesOnOffCluster,
    SDevicesReportingCluster,
    SDevicesTwoButtonCluster,
    SDevicesWindowCoveringCluster,
)
from zhaquirks.sdevices.cover import _add_cover_entities

if TYPE_CHECKING:
    from zigpy.application import ControllerApplication

_READ_ON_STARTUP = {"attribute_initialized_from_cache": False}


class SDevicesSwitchCoverDevice(CustomZigpyDevice):
    """Clone dual-mode switches and expose every present OnOff endpoint as switch."""

    def __init__(
        self,
        application: ControllerApplication,
        ieee: t.EUI64,
        nwk: t.NWK,
        replaces: zigpy.device.Device,
    ) -> None:
        """Preserve the interviewed signature while correcting relay device types."""
        super().__init__(application, ieee, nwk, replaces)
        for endpoint in self.non_zdo_endpoints:
            if OnOff.cluster_id in endpoint.in_clusters:
                endpoint.device_type = zha.DeviceType.ON_OFF_OUTPUT


def _add_optional_neutral(qb: QuirkBuilder, *, endpoint_id: int = 1) -> QuirkBuilder:
    """Add the extra entities of the "optional neutral" models (00197 / 00200)."""
    return (
        qb.enum(
            "power_profile",
            PowerProfile,
            SDevicesCluster.cluster_id,
            endpoint_id=endpoint_id,
            entity_type=EntityType.CONFIG,
            translation_key="power_profile",
            fallback_name="Power profile",
            **_READ_ON_STARTUP,
        )
        .enum(
            "led_indication_type",
            LedIndicationType,
            SDevicesCluster.cluster_id,
            endpoint_id=endpoint_id,
            entity_type=EntityType.CONFIG,
            translation_key="led_indication_type",
            fallback_name="LED indication type",
            **_READ_ON_STARTUP,
        )
        .binary_sensor(
            "neutral_presence",
            SDevicesCluster.cluster_id,
            endpoint_id=endpoint_id,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="neutral_presence",
            fallback_name="Neutral presence",
            **_READ_ON_STARTUP,
        )
    )


def _add_led_entities(
    qb: QuirkBuilder, *, endpoint_id: int, include_on: bool, numbered: bool = False
) -> QuirkBuilder:
    """Add the LED indicator entities for one endpoint.

    ``include_on`` adds the ON-state LED set; the OFF-state set is always added.
    """
    suffix = f" {endpoint_id}" if numbered else ""
    key_suffix = "_id" if numbered else ""
    placeholders = {"id": str(endpoint_id)} if numbered else None
    if include_on:
        qb = (
            qb.switch(
                "led_indicator_on_enable",
                SDevicesCluster.cluster_id,
                endpoint_id=endpoint_id,
                entity_type=EntityType.CONFIG,
                translation_key=f"led_indicator_on_enable{key_suffix}",
                fallback_name=f"LED indicator (on){suffix}",
                translation_placeholders=placeholders,
                **_READ_ON_STARTUP,
            )
            .number(
                "led_indicator_on_h",
                SDevicesCluster.cluster_id,
                endpoint_id=endpoint_id,
                min_value=0,
                max_value=359,
                step=1,
                unit="°",
                entity_type=EntityType.CONFIG,
                translation_key=f"led_indicator_on_h{key_suffix}",
                fallback_name=f"LED hue (on){suffix}",
                translation_placeholders=placeholders,
                **_READ_ON_STARTUP,
            )
            .number(
                "led_indicator_on_s",
                SDevicesCluster.cluster_id,
                endpoint_id=endpoint_id,
                min_value=0,
                max_value=254,
                step=1,
                entity_type=EntityType.CONFIG,
                translation_key=f"led_indicator_on_s{key_suffix}",
                fallback_name=f"LED saturation (on){suffix}",
                translation_placeholders=placeholders,
                **_READ_ON_STARTUP,
            )
            .number(
                "led_indicator_on_b",
                SDevicesCluster.cluster_id,
                endpoint_id=endpoint_id,
                min_value=1,
                max_value=254,
                step=1,
                entity_type=EntityType.CONFIG,
                translation_key=f"led_indicator_on_b{key_suffix}",
                fallback_name=f"LED brightness (on){suffix}",
                translation_placeholders=placeholders,
                **_READ_ON_STARTUP,
            )
        )
    return (
        qb.switch(
            "led_indicator_off_enable",
            SDevicesCluster.cluster_id,
            endpoint_id=endpoint_id,
            entity_type=EntityType.CONFIG,
            translation_key=f"led_indicator_off_enable{key_suffix}",
            fallback_name=f"LED indicator (off){suffix}",
            translation_placeholders=placeholders,
            **_READ_ON_STARTUP,
        )
        .number(
            "led_indicator_off_h",
            SDevicesCluster.cluster_id,
            endpoint_id=endpoint_id,
            min_value=0,
            max_value=359,
            step=1,
            unit="°",
            entity_type=EntityType.CONFIG,
            translation_key=f"led_indicator_off_h{key_suffix}",
            fallback_name=f"LED hue (off){suffix}",
            translation_placeholders=placeholders,
            **_READ_ON_STARTUP,
        )
        .number(
            "led_indicator_off_s",
            SDevicesCluster.cluster_id,
            endpoint_id=endpoint_id,
            min_value=0,
            max_value=254,
            step=1,
            entity_type=EntityType.CONFIG,
            translation_key=f"led_indicator_off_s{key_suffix}",
            fallback_name=f"LED saturation (off){suffix}",
            translation_placeholders=placeholders,
            **_READ_ON_STARTUP,
        )
        .number(
            "led_indicator_off_b",
            SDevicesCluster.cluster_id,
            endpoint_id=endpoint_id,
            min_value=1,
            max_value=254,
            step=1,
            entity_type=EntityType.CONFIG,
            translation_key=f"led_indicator_off_b{key_suffix}",
            fallback_name=f"LED brightness (off){suffix}",
            translation_placeholders=placeholders,
            **_READ_ON_STARTUP,
        )
    )


def _add_gang(qb: QuirkBuilder, endpoint_id: int) -> QuirkBuilder:
    """Add the per-gang config entities of a two-button switch (00199 / 00200)."""
    suffix = f" {endpoint_id}"
    qb = qb.enum(
        "sdevices_relay_decouple",
        RelayMode,
        OnOff.cluster_id,
        endpoint_id=endpoint_id,
        entity_type=EntityType.CONFIG,
        translation_key="relay_mode_id",
        fallback_name=f"Relay mode{suffix}",
        translation_placeholders={"id": str(endpoint_id)},
        **_READ_ON_STARTUP,
    )
    qb = qb.enum(
        "button_event_mode",
        ButtonEventMode,
        SDevicesCluster.cluster_id,
        endpoint_id=endpoint_id,
        entity_type=EntityType.CONFIG,
        translation_key="event_mode_id",
        fallback_name=f"Event mode{suffix}",
        translation_placeholders={"id": str(endpoint_id)},
        **_READ_ON_STARTUP,
    )
    qb = qb.switch(
        "button_enable_multi_click",
        SDevicesCluster.cluster_id,
        endpoint_id=endpoint_id,
        entity_type=EntityType.CONFIG,
        translation_key="allow_double_click_id",
        fallback_name=f"Allow double click{suffix}",
        translation_placeholders={"id": str(endpoint_id)},
        **_READ_ON_STARTUP,
    )
    return _add_led_entities(
        qb, endpoint_id=endpoint_id, include_on=True, numbered=True
    )


def _single_button_switch(
    manufacturer: str, model: str, *, optional_neutral: bool = False
) -> QuirkBuilder:
    """Build a single-button SDevices wall switch (00196 / 00197)."""
    qb = (
        # Relay EP1 -> switch platform (device type ON_OFF_OUTPUT).
        QuirkBuilder(manufacturer, model)
        .replaces_endpoint(1, device_type=zha.DeviceType.ON_OFF_OUTPUT)
        .replaces(SDevicesOnOffCluster)
        .replaces(SDevicesButtonCluster)
        .replaces(SDevicesDiagnosticCluster)
        .replaces(SDevicesReportingCluster if optional_neutral else SDevicesCluster)
        .enum(
            "sdevices_relay_decouple",
            RelayMode,
            OnOff.cluster_id,
            entity_type=EntityType.CONFIG,
            translation_key="relay_mode",
            fallback_name="Relay mode",
            **_READ_ON_STARTUP,
        )
        .enum(
            "button_event_mode",
            ButtonEventMode,
            SDevicesCluster.cluster_id,
            entity_type=EntityType.CONFIG,
            translation_key="event_mode",
            fallback_name="Event mode",
            **_READ_ON_STARTUP,
        )
        .switch(
            "button_enable_multi_click",
            SDevicesCluster.cluster_id,
            entity_type=EntityType.CONFIG,
            translation_key="allow_double_click",
            fallback_name="Allow double click",
            **_READ_ON_STARTUP,
        )
        .switch(
            "child_lock",
            SDevicesCluster.cluster_id,
            entity_type=EntityType.CONFIG,
            translation_key="child_lock",
            fallback_name="Child lock",
            **_READ_ON_STARTUP,
        )
    )
    qb = _add_led_entities(qb, endpoint_id=1, include_on=True)
    qb = (
        qb.sensor(
            "sdevices_uptime_s",
            SDevicesDiagnosticCluster.cluster_id,
            unit=UnitOfTime.SECONDS,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="uptime",
            fallback_name="Uptime",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "number_of_resets",
            SDevicesDiagnosticCluster.cluster_id,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="resets_count",
            fallback_name="Resets count",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_button1_clicks",
            SDevicesDiagnosticCluster.cluster_id,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="pairing_button_clicks",
            fallback_name="Pairing button clicks",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_button2_clicks",
            SDevicesDiagnosticCluster.cluster_id,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="wall_button_clicks",
            fallback_name="Wall button clicks",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_relay1_switches",
            SDevicesDiagnosticCluster.cluster_id,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="relay_switches_1",
            fallback_name="Relay 1 switches",
            **_READ_ON_STARTUP,
        )
        .device_automation_triggers(
            {
                (SHORT_PRESS, BUTTON_1): {COMMAND: "button_single"},
                (DOUBLE_PRESS, BUTTON_1): {COMMAND: "button_double"},
                (LONG_PRESS, BUTTON_1): {COMMAND: "button_hold"},
            }
        )
    )
    if optional_neutral:
        qb = _add_optional_neutral(qb, endpoint_id=1)
    return qb


def _two_button_switch(
    manufacturer: str, model: str, *, optional_neutral: bool = False
) -> QuirkBuilder:
    """Build both signatures of a two-button SDevices switch (00199 / 00200)."""
    qb = (
        QuirkBuilder(manufacturer, model)
        .zigpy_device_class(SDevicesSwitchCoverDevice)
        .replace_cluster_occurrences(
            SDevicesOnOffCluster, replace_client_instances=False
        )
        .replace_cluster_occurrences(
            SDevicesTwoButtonCluster, replace_client_instances=False
        )
        .replace_cluster_occurrences(
            SDevicesWindowCoveringCluster, replace_client_instances=False
        )
        .replace_cluster_occurrences(
            SDevicesDiagnosticCluster, replace_client_instances=False
        )
        .replace_cluster_occurrences(
            SDevicesReportingCluster, replace_client_instances=False
        )
    )
    # Two relays -> distinct "Switch 1" / "Switch 2" (Z2M switch_1 / switch_2
    # parity). A custom translation_key + fallback_name is needed so the two
    # names differ; the built-in "switch" key would render both identically.
    # Only the display name changes - unique_id / entity_id / history are untouched.
    for endpoint_id in (1, 2):
        qb = qb.change_entity_metadata(
            endpoint_id=endpoint_id,
            cluster_id=OnOff.cluster_id,
            new_translation_key="relay_id",
            new_translation_placeholders={"id": str(endpoint_id)},
            new_fallback_name=f"Switch {endpoint_id}",
        )
    for endpoint_id in (1, 2):
        qb = _add_gang(qb, endpoint_id)
    qb = qb.switch(
        "child_lock",
        SDevicesCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="child_lock",
        fallback_name="Child lock",
        **_READ_ON_STARTUP,
    )
    qb = (
        qb.sensor(
            "sdevices_uptime_s",
            SDevicesDiagnosticCluster.cluster_id,
            endpoint_id=1,
            unit=UnitOfTime.SECONDS,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="uptime",
            fallback_name="Uptime",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "number_of_resets",
            SDevicesDiagnosticCluster.cluster_id,
            endpoint_id=1,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="resets_count",
            fallback_name="Resets count",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_button1_clicks",
            SDevicesDiagnosticCluster.cluster_id,
            endpoint_id=1,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="pairing_button_clicks",
            fallback_name="Pairing button clicks",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_button2_clicks",
            SDevicesDiagnosticCluster.cluster_id,
            endpoint_id=1,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="left_button_clicks",
            fallback_name="Left button clicks",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_button3_clicks",
            SDevicesDiagnosticCluster.cluster_id,
            endpoint_id=1,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="right_button_clicks",
            fallback_name="Right button clicks",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_relay1_switches",
            SDevicesDiagnosticCluster.cluster_id,
            endpoint_id=1,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="relay_switches_1",
            fallback_name="Relay 1 switches",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_relay2_switches",
            SDevicesDiagnosticCluster.cluster_id,
            endpoint_id=1,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="relay_switches_2",
            fallback_name="Relay 2 switches",
            **_READ_ON_STARTUP,
        )
        .device_automation_triggers(
            {
                (SHORT_PRESS, BUTTON_1): {COMMAND: "single_switch_1"},
                (DOUBLE_PRESS, BUTTON_1): {COMMAND: "double_switch_1"},
                (LONG_PRESS, BUTTON_1): {COMMAND: "hold_switch_1"},
                (SHORT_PRESS, BUTTON_2): {COMMAND: "single_switch_2"},
                (DOUBLE_PRESS, BUTTON_2): {COMMAND: "double_switch_2"},
                (LONG_PRESS, BUTTON_2): {COMMAND: "hold_switch_2"},
            }
        )
    )
    qb = _add_cover_entities(qb)
    if optional_neutral:
        qb = _add_optional_neutral(qb, endpoint_id=1)
        qb = _add_optional_neutral(qb, endpoint_id=3)
    return qb


_single_button_switch(SDEVICES, "SBDV-00196").add_to_registry()
_single_button_switch(SDEVICES, "SBDV-00197", optional_neutral=True).add_to_registry()
_two_button_switch(SDEVICES, "SBDV-00199").add_to_registry()
_two_button_switch(SDEVICES, "SBDV-00200", optional_neutral=True).add_to_registry()
