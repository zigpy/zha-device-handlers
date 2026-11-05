"""SDevices two-button switches in window-covering mode.

SBDV-00199 / 00200 are dual-mode devices. In covering mode they announce a
single endpoint (EP3, device type ``WINDOW_COVERING``) carrying the
``WindowCovering`` cluster instead of the two ``OnOff`` gangs of the switch
mode. The switch and cover signatures share one quirk registry entry per model.
This module only adds the cover-mode entity metadata; ``switch.py`` owns the
registrations.

The cover entity (position / open / close / stop) is created by ZHA from the
``WindowCovering`` cluster on the covering endpoint. The cluster is replaced by
``SDevicesWindowCoveringCluster`` to expose the manufacturer attributes
(calibration time, buttons mode, motor timeout).
"""

from __future__ import annotations

from zigpy.zcl.clusters.closures import WindowCovering

from zhaquirks.builder import EntityType, QuirkBuilder, UnitOfTime
from zhaquirks.sdevices import ButtonsMode, SDevicesCluster, SDevicesDiagnosticCluster

_COVER_ENDPOINT = 3
_READ_ON_STARTUP = {"attribute_initialized_from_cache": False}


def _add_cover_entities(qb: QuirkBuilder) -> QuirkBuilder:
    """Add covering-mode entities for SBDV-00199 / SBDV-00200 on EP3."""
    ep = _COVER_ENDPOINT
    return (
        qb
        # The raw Mode bitmap is kept disabled but forces one startup read. The
        # custom cluster splits it into the three local per-bit attributes below;
        # ZHA's native WindowCovering inversion switch handles the direction bit.
        .sensor(
            WindowCovering.AttributeDefs.window_covering_mode.name,
            WindowCovering.cluster_id,
            endpoint_id=ep,
            entity_type=EntityType.DIAGNOSTIC,
            initially_disabled=True,
            attribute_initialized_from_cache=False,
            translation_key="cover_mode",
            fallback_name="Cover mode",
        )
        .switch(
            "cover_calibration_mode",
            WindowCovering.cluster_id,
            endpoint_id=ep,
            entity_type=EntityType.CONFIG,
            translation_key="cover_calibration_mode",
            fallback_name="Cover calibration mode",
        )
        .switch(
            "cover_maintenance_mode",
            WindowCovering.cluster_id,
            endpoint_id=ep,
            entity_type=EntityType.CONFIG,
            translation_key="cover_maintenance_mode",
            fallback_name="Cover maintenance mode",
        )
        .switch(
            "cover_led_feedback",
            WindowCovering.cluster_id,
            endpoint_id=ep,
            entity_type=EntityType.CONFIG,
            translation_key="cover_led_feedback",
            fallback_name="Cover LED feedback",
        )
        # motion parameters (standard WindowCovering attributes)
        .number(
            "velocity_lift",
            WindowCovering.cluster_id,
            endpoint_id=ep,
            min_value=0,
            max_value=1000,
            step=1,
            unit="cm/s",
            entity_type=EntityType.CONFIG,
            translation_key="velocity",
            fallback_name="Velocity",
            **_READ_ON_STARTUP,
        )
        .number(
            "acceleration_time_lift",
            WindowCovering.cluster_id,
            endpoint_id=ep,
            min_value=0,
            max_value=60,
            step=0.1,
            multiplier=0.1,
            unit=UnitOfTime.SECONDS,
            entity_type=EntityType.CONFIG,
            translation_key="acceleration_time",
            fallback_name="Acceleration time",
            **_READ_ON_STARTUP,
        )
        .number(
            "deceleration_time_lift",
            WindowCovering.cluster_id,
            endpoint_id=ep,
            min_value=0,
            max_value=60,
            step=0.1,
            multiplier=0.1,
            unit=UnitOfTime.SECONDS,
            entity_type=EntityType.CONFIG,
            translation_key="deceleration_time",
            fallback_name="Deceleration time",
            **_READ_ON_STARTUP,
        )
        # manufacturer attributes on the covering cluster
        .number(
            "sdevices_calibration_time",
            WindowCovering.cluster_id,
            endpoint_id=ep,
            min_value=0,
            max_value=3600,
            step=0.1,
            multiplier=0.1,
            unit=UnitOfTime.SECONDS,
            entity_type=EntityType.CONFIG,
            translation_key="calibration_time",
            fallback_name="Calibration time",
            **_READ_ON_STARTUP,
        )
        .number(
            "sdevices_motor_timeout",
            WindowCovering.cluster_id,
            endpoint_id=ep,
            min_value=0,
            max_value=3600,
            step=1,
            unit=UnitOfTime.SECONDS,
            entity_type=EntityType.CONFIG,
            translation_key="motor_timeout",
            fallback_name="Motor timeout",
            **_READ_ON_STARTUP,
        )
        .enum(
            "sdevices_buttons_mode",
            ButtonsMode,
            WindowCovering.cluster_id,
            endpoint_id=ep,
            entity_type=EntityType.CONFIG,
            translation_key="buttons_mode",
            fallback_name="Buttons mode",
            **_READ_ON_STARTUP,
        )
        # LED indication (covering mode only exposes the OFF set)
        .switch(
            "led_indicator_off_enable",
            SDevicesCluster.cluster_id,
            endpoint_id=ep,
            entity_type=EntityType.CONFIG,
            translation_key="led_indicator_off_enable",
            fallback_name="LED indicator (off)",
            **_READ_ON_STARTUP,
        )
        .number(
            "led_indicator_off_h",
            SDevicesCluster.cluster_id,
            endpoint_id=ep,
            min_value=0,
            max_value=359,
            step=1,
            unit="°",
            entity_type=EntityType.CONFIG,
            translation_key="led_indicator_off_h",
            fallback_name="LED hue (off)",
            **_READ_ON_STARTUP,
        )
        .number(
            "led_indicator_off_s",
            SDevicesCluster.cluster_id,
            endpoint_id=ep,
            min_value=0,
            max_value=254,
            step=1,
            entity_type=EntityType.CONFIG,
            translation_key="led_indicator_off_s",
            fallback_name="LED saturation (off)",
            **_READ_ON_STARTUP,
        )
        .number(
            "led_indicator_off_b",
            SDevicesCluster.cluster_id,
            endpoint_id=ep,
            min_value=1,
            max_value=254,
            step=1,
            entity_type=EntityType.CONFIG,
            translation_key="led_indicator_off_b",
            fallback_name="LED brightness (off)",
            **_READ_ON_STARTUP,
        )
        .switch(
            "child_lock",
            SDevicesCluster.cluster_id,
            endpoint_id=ep,
            entity_type=EntityType.CONFIG,
            translation_key="child_lock",
            fallback_name="Child lock",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_uptime_s",
            SDevicesDiagnosticCluster.cluster_id,
            endpoint_id=ep,
            unit=UnitOfTime.SECONDS,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="uptime",
            fallback_name="Uptime",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "number_of_resets",
            SDevicesDiagnosticCluster.cluster_id,
            endpoint_id=ep,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="resets_count",
            fallback_name="Resets count",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_button1_clicks",
            SDevicesDiagnosticCluster.cluster_id,
            endpoint_id=ep,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="pairing_button_clicks",
            fallback_name="Pairing button clicks",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_button2_clicks",
            SDevicesDiagnosticCluster.cluster_id,
            endpoint_id=ep,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="left_button_clicks",
            fallback_name="Left button clicks",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_button3_clicks",
            SDevicesDiagnosticCluster.cluster_id,
            endpoint_id=ep,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="right_button_clicks",
            fallback_name="Right button clicks",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_relay1_switches",
            SDevicesDiagnosticCluster.cluster_id,
            endpoint_id=ep,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="relay_switches_1",
            fallback_name="Relay 1 switches",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_relay2_switches",
            SDevicesDiagnosticCluster.cluster_id,
            endpoint_id=ep,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="relay_switches_2",
            fallback_name="Relay 2 switches",
            **_READ_ON_STARTUP,
        )
    )
