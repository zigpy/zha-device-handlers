"""Quirk for the Aqara Climate Sensor W100 (lumi.sensor_ht.agl001).

Exposes the three buttons (plus/center/minus = endpoints 1/2/3) as zha_event and
device-automation triggers via the shared Aqara ``MultistateInputCluster``, and battery
from the 0xFCC0 heartbeat struct. The W100 reports battery percent only in heartbeat
tag 102 — there is no tag-1 voltage, and the standard PowerConfiguration attribute
always reports 0 — so ``XiaomiCluster._parse_aqara_attributes`` maps tag 102 for this
model (matching zigbee2mqtt's TH-S04D converter,
https://github.com/Koenkk/zigbee-herdsman-converters/pull/10787).
"""

from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import MultistateInput

from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.const import COMMAND, DOUBLE_PRESS, LONG_PRESS, LONG_RELEASE, SHORT_PRESS
from zhaquirks.xiaomi import (
    AQARA,
    RelativeHumidityCluster,
    TemperatureMeasurementCluster,
    XiaomiAqaraE1Cluster,
    XiaomiPowerConfiguration,
)
from zhaquirks.xiaomi.aqara.opple_remote import (
    COMMAND_1_DOUBLE,
    COMMAND_1_HOLD,
    COMMAND_1_RELEASE,
    COMMAND_1_SINGLE,
    COMMAND_2_DOUBLE,
    COMMAND_2_HOLD,
    COMMAND_2_RELEASE,
    COMMAND_2_SINGLE,
    COMMAND_3_DOUBLE,
    COMMAND_3_HOLD,
    COMMAND_3_RELEASE,
    COMMAND_3_SINGLE,
    MultistateInputCluster,
)

PLUS_BUTTON = "plus"
CENTER_BUTTON = "center"
MINUS_BUTTON = "minus"


class W100PowerConfiguration(XiaomiPowerConfiguration):
    """PowerConfiguration that drops the device's own ZCL battery reports.

    The W100's battery_percentage_remaining attribute always reports 0, and a
    reporting config from a pre-quirk join persists in the device — a 0 every
    max-interval that overwrites the heartbeat-derived value. Battery comes solely
    from the 0xFCC0 heartbeat via ``battery_percent_reported``.
    """

    def handle_cluster_general_request(self, hdr, args, *, dst_addressing=None):
        """Drop attribute reports; pass everything else through."""
        if hdr.command_id == foundation.GeneralCommand.Report_Attributes:
            return
        super().handle_cluster_general_request(hdr, args, dst_addressing=dst_addressing)


(
    QuirkBuilder(AQARA, "lumi.sensor_ht.agl001")
    .friendly_name(manufacturer="Aqara", model="Climate Sensor W100")
    .replaces(TemperatureMeasurementCluster)
    .replaces(RelativeHumidityCluster)
    .replaces(W100PowerConfiguration)
    .replaces(XiaomiAqaraE1Cluster)
    .replaces(MultistateInputCluster)
    .replaces(MultistateInputCluster, endpoint_id=2)
    .replaces(MultistateInputCluster, endpoint_id=3)
    .device_automation_triggers(
        {
            (SHORT_PRESS, PLUS_BUTTON): {COMMAND: COMMAND_1_SINGLE},
            (DOUBLE_PRESS, PLUS_BUTTON): {COMMAND: COMMAND_1_DOUBLE},
            (LONG_PRESS, PLUS_BUTTON): {COMMAND: COMMAND_1_HOLD},
            (LONG_RELEASE, PLUS_BUTTON): {COMMAND: COMMAND_1_RELEASE},
            (SHORT_PRESS, CENTER_BUTTON): {COMMAND: COMMAND_2_SINGLE},
            (DOUBLE_PRESS, CENTER_BUTTON): {COMMAND: COMMAND_2_DOUBLE},
            (LONG_PRESS, CENTER_BUTTON): {COMMAND: COMMAND_2_HOLD},
            (LONG_RELEASE, CENTER_BUTTON): {COMMAND: COMMAND_2_RELEASE},
            (SHORT_PRESS, MINUS_BUTTON): {COMMAND: COMMAND_3_SINGLE},
            (DOUBLE_PRESS, MINUS_BUTTON): {COMMAND: COMMAND_3_DOUBLE},
            (LONG_PRESS, MINUS_BUTTON): {COMMAND: COMMAND_3_HOLD},
            (LONG_RELEASE, MINUS_BUTTON): {COMMAND: COMMAND_3_RELEASE},
        }
    )
    # Each button reports on its own endpoint. It counts its presses itself, reports a
    # hold at the hold threshold and the release after it (Zigbee2MQTT TH-S04D: hold 0,
    # single 1, double 2, release 255). Whether the hold is repeated while the button
    # stays down is not confirmed, so repeats are allowed, and the release only ends a
    # hold seen, in case it also follows other presses. Nothing is sent while the
    # device is in thermostat mode.
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS,
                trigger=(SHORT_PRESS, PLUS_BUTTON),
            ),
            ButtonEvent(
                event_type=ButtonEventType.MULTI_PRESS,
                trigger=(DOUBLE_PRESS, PLUS_BUTTON),
                press_count=2,
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, PLUS_BUTTON),
                repeats=True,
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, PLUS_BUTTON),
                while_held=True,
            ),
        ],
        cluster_id=MultistateInput.cluster_id,
        cluster_type=ClusterType.Server,
        endpoint_id=1,
        unique_id_suffix="button_plus",
        translation_key="plus_button",
        fallback_name="Plus button",
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS,
                trigger=(SHORT_PRESS, CENTER_BUTTON),
            ),
            ButtonEvent(
                event_type=ButtonEventType.MULTI_PRESS,
                trigger=(DOUBLE_PRESS, CENTER_BUTTON),
                press_count=2,
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, CENTER_BUTTON),
                repeats=True,
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, CENTER_BUTTON),
                while_held=True,
            ),
        ],
        cluster_id=MultistateInput.cluster_id,
        cluster_type=ClusterType.Server,
        endpoint_id=2,
        unique_id_suffix="button_center",
        translation_key="center_button",
        fallback_name="Center button",
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS,
                trigger=(SHORT_PRESS, MINUS_BUTTON),
            ),
            ButtonEvent(
                event_type=ButtonEventType.MULTI_PRESS,
                trigger=(DOUBLE_PRESS, MINUS_BUTTON),
                press_count=2,
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, MINUS_BUTTON),
                repeats=True,
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, MINUS_BUTTON),
                while_held=True,
            ),
        ],
        cluster_id=MultistateInput.cluster_id,
        cluster_type=ClusterType.Server,
        endpoint_id=3,
        unique_id_suffix="button_minus",
        translation_key="minus_button",
        fallback_name="Minus button",
    )
    .add_to_registry()
)
