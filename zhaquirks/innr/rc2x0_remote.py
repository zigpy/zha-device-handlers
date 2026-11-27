"""Innr RC 210 and RC 250 remotes, with their Key Event mode.

The remotes have two modes. In Zigbee mode, the default, they touchlink lights and
control them with standard On/Off, Level Control and Color Control commands. In Key
Event mode they stop doing that, and instead report every key event on their private
Device Configuration cluster (0xFD01). Writing a non-zero key report mask switches
the remote to Key Event mode, writing 0x00 switches it back to Zigbee mode. The UI
calls these modes Hub mode and Touchlink mode.

Source: Innr, "Brief Specification of RC 2x0 Functionality", v2.0, 2026-02-25.
"""

from typing import Any, ClassVar, Final

from zigpy.exceptions import DeliveryError
import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.builder import (
    ButtonEvent,
    ButtonEventType,
    QuirkBuilder,
    ReportingConfig,
)
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    DIM_DOWN,
    DIM_UP,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LEFT,
    LONG_PRESS,
    LONG_RELEASE,
    RIGHT,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)
from zhaquirks.innr import INNR

INNR_MANUFACTURER_CODE: Final = 0x1166
CENTER: Final = "center"


class KeyId(t.enum8):
    """Key id of a key event report."""

    none = 0x00
    reset = 0x01
    # BUTTON_OK in the spec: the center key, with the power symbol
    center = 0x02
    up = 0x03
    down = 0x04
    left = 0x05
    right = 0x06


class KeyEvent(t.enum8):
    """Key event of a key event report."""

    press = 0x01
    long_press = 0x02
    double_press = 0x04
    short_release = 0x08
    long_release = 0x10
    release = 0x20


class KeyEventMask(t.bitmap8):
    """Bits of the key report mask: the key events the remote reports.

    The attribute itself is a uint8: the remote refuses a write as a bitmap8.
    """

    Press = 0x01
    Long_press = 0x02
    Double_press = 0x04
    Short_release = 0x08
    Long_release = 0x10
    Release = 0x20


# A short press goes press, short release, release, and a long press goes press, long
# press, long release, release. Key Event mode reports only the events that tell the
# gestures apart, so each gesture fires one event.
KEY_EVENT_MASK_RC250: Final = (
    KeyEventMask.Short_release | KeyEventMask.Long_press | KeyEventMask.Long_release
)
# A double press goes press, double press, release, without a short release
KEY_EVENT_MASK_RC210: Final = KEY_EVENT_MASK_RC250 | KeyEventMask.Double_press
# A mask of 0x00 is Touchlink mode
TOUCHLINK_MODE_MASK: Final = 0x00


class RemoteModeRC250(t.enum8):
    """Mode of the RC 250, by its key report mask.

    Touchlink mode is Zigbee mode in the spec, Hub mode is Key Event mode.
    """

    Touchlink_mode = TOUCHLINK_MODE_MASK
    Hub_mode = int(KEY_EVENT_MASK_RC250)


class RemoteModeRC210(t.enum8):
    """Mode of the RC 210, by its key report mask.

    Touchlink mode is Zigbee mode in the spec, Hub mode is Key Event mode.
    """

    Touchlink_mode = TOUCHLINK_MODE_MASK
    Hub_mode = int(KEY_EVENT_MASK_RC210)


class KeyEventReport(foundation.CommandSchema):
    """Payload of a key event report."""

    group_id: t.uint8_t
    key_id: KeyId
    key_event: KeyEvent
    # Called "expand field" in the spec, and used as a sequence number
    sequence: t.uint8_t


KEY_EVENT_REPORT_ID: Final = 0x12


class InnrDeviceConfigurationCluster(CustomCluster):
    """Innr's private Device Configuration cluster.

    Its attributes and commands carry Innr's manufacturer code. The remote answered
    attribute discovery that way.

    The remote takes a write of its key report mask, but its response does not reliably
    arrive, and it does not report the mask. So the mode is also derived from what the
    remote sends: key events in Hub mode, standard commands in Touchlink mode.
    """

    # The mask written for Hub mode, set per model
    hub_mode_mask: ClassVar[int] = 0
    name: Final = "Innr Device Configuration"
    cluster_id: Final = 0xFD01
    ep_attribute: Final = "innr_device_configuration"

    class AttributeDefs(BaseAttributeDefs):
        """Attributes of the Device Configuration cluster."""

        # Protocol version, number of keys and number of groups, e.g. 0x11050100
        device_information: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint32_t,
            access="r",
            manufacturer_code=INNR_MANUFACTURER_CODE,
        )
        key_report_mask: Final = ZCLAttributeDef(
            id=0x0004,
            # 0x00 for Zigbee mode, else the KeyEventMask bits to report
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=INNR_MANUFACTURER_CODE,
        )

    class ClientCommandDefs(BaseCommandDefs):
        """Commands the remote sends."""

        key_event_report: Final = ZCLCommandDef(
            id=KEY_EVENT_REPORT_ID,
            schema=KeyEventReport,
            manufacturer_code=INNR_MANUFACTURER_CODE,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Commands the remote receives.

        The spec does not say which direction the remote marks its reports with, so
        they are also decoded when it marks them as sent from a client.
        """

        key_event_report: Final = ZCLCommandDef(
            id=KEY_EVENT_REPORT_ID,
            schema=KeyEventReport,
            manufacturer_code=INNR_MANUFACTURER_CODE,
        )

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Any,
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Send key event reports as `<key>_<event>` events, e.g. `center_short_release`."""
        if hdr.command_id == self.ClientCommandDefs.key_event_report.id and isinstance(
            args, KeyEventReport
        ):
            # Only Hub mode sends key events. Keep a mask other than the default.
            if self.get(self.AttributeDefs.key_report_mask.name) == TOUCHLINK_MODE_MASK:
                self.mode_seen(self.hub_mode_mask)

            self.listener_event(
                ZHA_SEND_EVENT, f"{args.key_id.name}_{args.key_event.name}", args
            )

        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

    def mode_seen(self, mask: int) -> None:
        """Update the mask to the mode the remote is seen in, if it changed."""
        attr = self.AttributeDefs.key_report_mask
        if self.get(attr.name) != mask:
            self.debug("Remote is seen with key report mask 0x%02x", mask)
            self._update_attribute(attr.id, t.uint8_t(mask))

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs: Any,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Write attributes, taking a mask write without a response as done.

        The remote switches modes, but its write response often gets lost, also when
        the remote is awake. If the write did not get through, the next key press
        corrects the mode.
        """
        mask_attr = self.AttributeDefs.key_report_mask
        try:
            return await super().write_attributes(
                attributes, manufacturer=manufacturer, **kwargs
            )
        except (TimeoutError, DeliveryError) as exc:
            if len(attributes) != 1:
                raise
            ((attr, value),) = attributes.items()
            if self.find_attribute(attr).id != mask_attr.id:
                raise

            self.debug("No response to writing key report mask %s: %r", value, exc)
            self.mode_seen(int(value))
            return [
                [
                    foundation.WriteAttributesStatusRecord(
                        status=foundation.Status.SUCCESS, attrid=mask_attr.id
                    )
                ]
            ]


class InnrRC250DeviceConfigurationCluster(InnrDeviceConfigurationCluster):
    """Device Configuration cluster of the RC 250."""

    hub_mode_mask: ClassVar[int] = int(KEY_EVENT_MASK_RC250)


class InnrRC210DeviceConfigurationCluster(InnrDeviceConfigurationCluster):
    """Device Configuration cluster of the RC 210."""

    hub_mode_mask: ClassVar[int] = int(KEY_EVENT_MASK_RC210)


class TouchlinkModeCluster(CustomCluster):
    """Client cluster whose commands show that the remote is in Touchlink mode."""

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Any,
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Mark the remote as in Touchlink mode, then handle the command."""
        config = self.endpoint.in_clusters.get(
            InnrDeviceConfigurationCluster.cluster_id
        )
        if isinstance(config, InnrDeviceConfigurationCluster):
            config.mode_seen(TOUCHLINK_MODE_MASK)

        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


class TouchlinkModeOnOff(TouchlinkModeCluster, OnOff):
    """On/Off client cluster of the remote."""


class TouchlinkModeLevelControl(TouchlinkModeCluster, LevelControl):
    """Level Control client cluster of the remote."""


class TouchlinkModeColor(TouchlinkModeCluster, Color):
    """Color Control client cluster of the remote."""


def _triggers(
    subtype: str, key: int, *, double_press: bool = False
) -> dict[tuple[str, str], dict[str, Any]]:
    """Return the device automation triggers of a key."""
    events: dict[str, int] = {
        SHORT_PRESS: KeyEvent.short_release,
        LONG_PRESS: KeyEvent.long_press,
        LONG_RELEASE: KeyEvent.long_release,
    }
    if double_press:
        events[DOUBLE_PRESS] = KeyEvent.double_press

    return {
        (trigger_type, subtype): {
            COMMAND: f"{KeyId(key).name}_{KeyEvent(event).name}",
            CLUSTER_ID: InnrDeviceConfigurationCluster.cluster_id,
            ENDPOINT_ID: 1,
        }
        for trigger_type, event in events.items()
    }


def _button_events(subtype: str, *, double_press: bool = False) -> list[ButtonEvent]:
    """Return the button events of a key, fired by its triggers."""
    events = [
        ButtonEvent(
            event_type=ButtonEventType.SINGLE_PRESS, trigger=(SHORT_PRESS, subtype)
        ),
        ButtonEvent(
            event_type=ButtonEventType.LONG_PRESS_START, trigger=(LONG_PRESS, subtype)
        ),
        ButtonEvent(
            event_type=ButtonEventType.LONG_PRESS_END, trigger=(LONG_RELEASE, subtype)
        ),
    ]
    if double_press:
        events.append(
            ButtonEvent(
                event_type=ButtonEventType.MULTI_PRESS,
                trigger=(DOUBLE_PRESS, subtype),
                press_count=2,
            )
        )
    return events


def _remote(
    model: str,
    config_cluster: type[InnrDeviceConfigurationCluster],
    remote_mode: type[t.enum8],
    keys: list[tuple[str, int, str, str]],
    *,
    double_press: bool,
) -> QuirkBuilder:
    """Return the quirk of a remote with the given keys.

    Each key is a (trigger subtype, key id, translation key, fallback name) tuple.
    """
    triggers: dict[tuple[str, str], dict[str, Any]] = {}
    for subtype, key, _, _ in keys:
        triggers.update(_triggers(subtype, key, double_press=double_press))

    builder = (
        QuirkBuilder(INNR, model)
        .replaces(config_cluster)
        .replace_cluster_occurrences(TouchlinkModeOnOff, replace_server_instances=False)
        .replace_cluster_occurrences(
            TouchlinkModeLevelControl, replace_server_instances=False
        )
        .replace_cluster_occurrences(TouchlinkModeColor, replace_server_instances=False)
        # The reporting config makes ZHA bind the cluster, which the remote needs to
        # send its key events to the coordinator. The RC 250 refuses to report its
        # mask, but the bind goes through.
        .enum(
            attribute_name=InnrDeviceConfigurationCluster.AttributeDefs.key_report_mask.name,
            cluster_id=InnrDeviceConfigurationCluster.cluster_id,
            enum_class=remote_mode,
            reporting_config=ReportingConfig(
                min_interval=0, max_interval=0xFFFE, reportable_change=1
            ),
            translation_key="remote_mode",
            fallback_name="Remote mode",
        )
        .device_automation_triggers(triggers)
    )

    for subtype, _, translation_key, fallback_name in keys:
        builder = builder.button_event(
            events=_button_events(subtype, double_press=double_press),
            cluster_id=InnrDeviceConfigurationCluster.cluster_id,
            cluster_type=ClusterType.Server,
            unique_id_suffix=f"button_{subtype}",
            translation_key=translation_key,
            fallback_name=fallback_name,
        )

    return builder


CENTER_KEY: Final = (CENTER, KeyId.center, "center_button", "Center button")

# The reset key is left out: it is for resetting the remote, not for everyday use. Its
# events still reach the zha_event as `reset_<event>`.
_remote(
    "RC 250",
    InnrRC250DeviceConfigurationCluster,
    RemoteModeRC250,
    [
        CENTER_KEY,
        (DIM_UP, KeyId.up, "dim_up_button", "Dim up button"),
        (DIM_DOWN, KeyId.down, "dim_down_button", "Dim down button"),
        (LEFT, KeyId.left, "left_button", "Left button"),
        (RIGHT, KeyId.right, "right_button", "Right button"),
    ],
    # The RC 250 does not have double press
    double_press=False,
).add_to_registry()

_remote(
    "RC 210",
    InnrRC210DeviceConfigurationCluster,
    RemoteModeRC210,
    [CENTER_KEY],
    double_press=True,
).add_to_registry()
