"""ZHA quirk for the Rti-Tek TRV601Z valve."""

import asyncio
import datetime as dt
import enum

import attrs
from zha.application import EntityPlatform, EntityType
from zha.application.helpers import write_attributes_safe
from zha.application.platforms import (
    ClusterMatch,
    PlatformFeatureGroup,
    register_entity,
)
from zha.application.platforms.select import ZCLEnumSelectEntity
from zha.application.platforms.update import FirmwareUpdateEntity
from zha.exceptions import ZHAException
import zigpy.types as t
from zigpy.zcl import (
    AttributeReadEvent,
    AttributeReportedEvent,
    AttributeUpdatedEvent,
    AttributeWrittenEvent,
)
from zigpy.zcl.clusters.general import Ota, PowerConfiguration
from zigpy.zcl.clusters.hvac import SeqDayOfWeek, SeqMode, Thermostat
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, Status, ZCLAttributeDef

from zhaquirks.builder import (
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.builder.device import QuirkV2Device
from zhaquirks.builder.discovery import QUIRKS_ENTITY_META_TO_ENTITY_CLASS
from zhaquirks.builder.metadata import ZCLEnumMetadata
from zhaquirks.clusters import CustomCluster


# The current device firmware reports the Zigbee model string "eTRV-ZB01".
def _is_heat_setpoint_limit_entity(entity):
    """Match ZHA's default editable heat-limit entities."""

    attribute_names = ("min_heat_setpoint_limit", "max_heat_setpoint_limit")
    for field in (
        "unique_id",
        "unique_id_suffix",
        "translation_key",
        "fallback_name",
        "attribute_name",
        "name",
    ):
        value = getattr(entity, field, None)
        if value is not None and any(name in str(value) for name in attribute_names):
            return True
    return False


def _round_valve_switching_difference_raw_value(value):
    """Keep raw writes aligned with the 0.1 C UI step."""

    return round(value / 10) * 10


TRVZB_FAULT_CODE_TEXT = {
    0: "Internal sensor fault",
    1: "Motor operation fault",
    2: "Critical battery level",
    3: "Low battery blocks firmware upgrade",
}
TRVZB_KNOWN_FAULT_CODE_MASK = sum(1 << bit for bit in TRVZB_FAULT_CODE_TEXT)
TRVZB_OTA_MINIMUM_BATTERY_PERCENT = 50
TRVZB_OTA_MINIMUM_BATTERY_RAW = TRVZB_OTA_MINIMUM_BATTERY_PERCENT * 2


def _fault_code_status(value):
    """Convert the documented TRVZB fault bitmap to diagnostic text."""

    try:
        raw_value = int(value)
    except (TypeError, ValueError):
        return "Unknown error"

    if raw_value < 0 or raw_value > 0xFFFFFFFF:
        return "Unknown error"
    if raw_value == 0:
        return "No error"

    errors = [
        description
        for bit, description in TRVZB_FAULT_CODE_TEXT.items()
        if raw_value & (1 << bit)
    ]
    unknown_bits = raw_value & ~TRVZB_KNOWN_FAULT_CODE_MASK
    if unknown_bits:
        errors.append(f"Unknown error (0x{unknown_bits:08X})")
    return ", ".join(errors)


def _motor_travel_calibration_status(value):
    """Convert the documented calibration result to status text."""

    try:
        return "Success" if int(value) == 0 else "Failed"
    except (TypeError, ValueError):
        return "Failed"


@register_entity(Ota.cluster_id)
class RtiTekTrvzbFirmwareUpdateEntity(FirmwareUpdateEntity):
    """Block OTA installation when the valve battery is too low."""

    _cluster_match = ClusterMatch(
        client_clusters=frozenset({Ota.cluster_id}),
        manufacturers=frozenset({"Rti-Tek"}),
        models=frozenset({"eTRV-ZB01"}),
        feature_priority=(PlatformFeatureGroup.OTA_UPDATE, 2),
    )

    async def async_install(self, version):
        """Read battery level before starting a firmware update."""

        endpoint = self.device.device.endpoints.get(self.endpoint.id)
        if endpoint is None:
            raise ZHAException("Firmware update blocked: endpoint is unavailable")
        power_cluster = endpoint.in_clusters.get(PowerConfiguration.cluster_id)
        if power_cluster is None:
            raise ZHAException("Firmware update blocked: battery level is unavailable")

        battery_attribute = (
            PowerConfiguration.AttributeDefs.battery_percentage_remaining
        )
        try:
            values, _ = await power_cluster.read_attributes(
                [battery_attribute.name], allow_cache=False
            )
            battery_raw = values.get(
                battery_attribute.name, values.get(battery_attribute.id)
            )
            battery_raw = int(battery_raw)
        except (TypeError, ValueError, KeyError) as exc:
            raise ZHAException(
                "Firmware update blocked: battery level is unavailable"
            ) from exc
        except Exception as exc:
            raise ZHAException(
                "Firmware update blocked: battery level could not be read"
            ) from exc

        if not 0 <= battery_raw <= 200:
            raise ZHAException("Firmware update blocked: battery level is invalid")
        if battery_raw <= TRVZB_OTA_MINIMUM_BATTERY_RAW:
            raise ZHAException("Firmware update requires battery level above 50%")

        await super().async_install(version)


class RtiTekTrvzbTemperatureControlMode(t.enum8):
    """TRVZB temperature-control modes defined by FD22/0x1004."""

    PID = 0x00
    ON_OFF = 0x01


@attrs.define(frozen=True, kw_only=True, repr=True)
class RtiTekTrvzbTemperatureControlModeMetadata(ZCLEnumMetadata):
    """Metadata for the temperature control mode select."""


class RtiTekTrvzbTemperatureControlModeSelectEntity(ZCLEnumSelectEntity):
    """Expose protocol enum8 values with the documented ON-OFF label."""

    _option_values = {
        "PID": RtiTekTrvzbTemperatureControlMode.PID,
        "ON-OFF": RtiTekTrvzbTemperatureControlMode.ON_OFF,
    }

    def __init__(self, *args, **kwargs):
        """Initialize the select with its protocol-defined option labels."""

        super().__init__(*args, **kwargs)
        self._attr_options = list(self._option_values)

    @property
    def current_option(self):
        """Return the label matching the cached enum8 value."""

        value = self._cluster.get(self._attribute_name)
        if value is None:
            return None
        for option, enum_value in self._option_values.items():
            if int(value) == int(enum_value):
                return option
        return None

    async def async_select_option(self, option):
        """Write the selected PID or ON-OFF mode as Zigbee enum8."""

        if option not in self._option_values:
            raise ValueError("Temperature control mode is not supported")

        await write_attributes_safe(
            self._cluster,
            {self._attribute_name: self._option_values[option]},
        )
        self.maybe_emit_state_changed_event()


QUIRKS_ENTITY_META_TO_ENTITY_CLASS[
    (EntityPlatform.SELECT, RtiTekTrvzbTemperatureControlModeMetadata)
] = RtiTekTrvzbTemperatureControlModeSelectEntity


class RtiTekTrvzbSystemMode(t.enum8):
    """TRVZB system modes supported by the Thermostat cluster."""

    Off = 0x00
    Auto = 0x01
    Manual = 0x04


class RtiTekTrvzbScreenBrightness(t.enum8):
    """TRVZB screen brightness levels defined by the FD22 protocol."""

    High = 0x00
    Medium = 0x01
    Low = 0x02


RtiTekTrvzbScreenDirection = enum.Enum(
    "RtiTekTrvzbScreenDirection",
    {"0°": 0x00, "90°": 0x03, "180°": 0x01, "270°": 0x02},
    type=t.uint8_t,
)


@attrs.define(frozen=True, kw_only=True, repr=True)
class RtiTekTrvzbScreenDirectionMetadata(ZCLEnumMetadata):
    """Metadata for the product-dependent screen direction select."""


class RtiTekTrvzbScreenDirectionSelectEntity(ZCLEnumSelectEntity):
    """Limit screen orientation options to the capabilities of the display."""

    _four_direction_product_names = frozenset({"eTRV-602"})
    _two_direction_options = ["0°", "180°"]

    @property
    def options(self):
        """Return directions supported by the reported display type."""

        product_name = self._cluster.get(
            RtiTekTrvzbPrivateCluster.AttributeDefs.product_name.name
        )
        if str(product_name) in self._four_direction_product_names:
            return self._attr_options
        return self._two_direction_options

    def on_add(self):
        """Refresh options when the device reports its product name."""

        super().on_add()
        for event_type in (
            AttributeReadEvent,
            AttributeReportedEvent,
            AttributeUpdatedEvent,
            AttributeWrittenEvent,
        ):
            self._on_remove_callbacks.append(
                self._cluster.on_event(
                    event_type.event_type, self.handle_product_attribute_updated
                )
            )

    async def async_select_option(self, option):
        """Write the documented uint8 screen-direction value."""

        if option not in self.options:
            raise ValueError("Screen direction is not supported by this product")
        await write_attributes_safe(
            self._cluster,
            {self._attribute_name: t.uint8_t(self._enum[option].value)},
        )
        self.maybe_emit_state_changed_event()

    def handle_product_attribute_updated(self, event):
        """Update the available directions after the product name is known."""

        if event.attribute_name == (
            RtiTekTrvzbPrivateCluster.AttributeDefs.product_name.name
        ):
            self.maybe_emit_state_changed_event()


QUIRKS_ENTITY_META_TO_ENTITY_CLASS[
    (EntityPlatform.SELECT, RtiTekTrvzbScreenDirectionMetadata)
] = RtiTekTrvzbScreenDirectionSelectEntity


RtiTekTrvzbScreenDisplayDuration = enum.Enum(
    "RtiTekTrvzbScreenDisplayDuration",
    {"Seconds_5": 5, "Seconds_10": 10, "Seconds_15": 15},
    type=t.uint16_t,
)


RtiTekTrvzbBoostDuration = enum.Enum(
    "RtiTekTrvzbBoostDuration",
    {
        "0_min": 0,
        "30_min": 1800,
        "60_min": 3600,
        "90_min": 5400,
        "120_min": 7200,
    },
    type=t.uint32_t,
)


RtiTekTrvzbLowBatteryValveState = enum.Enum(
    "RtiTekTrvzbLowBatteryValveState",
    {"0%": 0, "30%": 30},
    type=t.uint8_t,
)


RtiTekTrvzbScheduleDay = enum.Enum(
    "RtiTekTrvzbScheduleDay",
    {
        "Sunday": int(SeqDayOfWeek.Sunday),
        "Monday": int(SeqDayOfWeek.Monday),
        "Tuesday": int(SeqDayOfWeek.Tuesday),
        "Wednesday": int(SeqDayOfWeek.Wednesday),
        "Thursday": int(SeqDayOfWeek.Thursday),
        "Friday": int(SeqDayOfWeek.Friday),
        "Saturday": int(SeqDayOfWeek.Saturday),
    },
    type=t.uint8_t,
)


RtiTekTrvzbScheduleHour = enum.Enum(
    "RtiTekTrvzbScheduleHour",
    {"Disabled": 0xFF, **{f"{hour:02d}": hour for hour in range(24)}},
    type=t.uint8_t,
)


RtiTekTrvzbScheduleMinute = enum.Enum(
    "RtiTekTrvzbScheduleMinute",
    {f"{minute:02d}": minute for minute in range(60)},
    type=t.uint8_t,
)


class RtiTekTrvzbTemporaryManualState(t.enum8):
    """Locally derived state of a TRVZB temporary manual setpoint."""

    Inactive = 0x00
    Active = 0x01
    Unknown = 0x02


TRVZB_WEEKLY_SCHEDULE_MAX_PERIODS = 6
TRVZB_WEEKLY_SCHEDULE_NULL_TIME = 0xFFFF
TRVZB_WEEKLY_SCHEDULE_DISABLED_HOUR = int(RtiTekTrvzbScheduleHour.Disabled)
TRVZB_WEEKLY_SCHEDULE_DEFAULT_TEMPERATURE = 2000
TRVZB_WEEKLY_SCHEDULE_APPLY_SETTLE_SECONDS = 2
TRVZB_WEEKLY_SCHEDULE_DAY_ATTR = 0xF100
TRVZB_WEEKLY_SCHEDULE_TIME_ATTRS = {
    index: 0xF101 + index - 1
    for index in range(1, TRVZB_WEEKLY_SCHEDULE_MAX_PERIODS + 1)
}
TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS = {
    index: 0xF107 + index - 1
    for index in range(1, TRVZB_WEEKLY_SCHEDULE_MAX_PERIODS + 1)
}
TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS = {
    index: 0xF10D + index - 1
    for index in range(1, TRVZB_WEEKLY_SCHEDULE_MAX_PERIODS + 1)
}
TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS = {
    index: 0xF113 + index - 1
    for index in range(1, TRVZB_WEEKLY_SCHEDULE_MAX_PERIODS + 1)
}
TRVZB_TEMPORARY_MANUAL_TEMPERATURE_ATTR = 0xF119
TRVZB_TEMPORARY_MANUAL_STATE_ATTR = 0xF11A


def _trvzb_schedule_editor_defaults():
    """Return the safe local values used before a schedule is fetched."""

    defaults = {
        TRVZB_WEEKLY_SCHEDULE_DAY_ATTR: int(RtiTekTrvzbScheduleDay.Monday.value),
    }
    for index in range(1, TRVZB_WEEKLY_SCHEDULE_MAX_PERIODS + 1):
        defaults[TRVZB_WEEKLY_SCHEDULE_TIME_ATTRS[index]] = (
            TRVZB_WEEKLY_SCHEDULE_NULL_TIME
        )
        defaults[TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[index]] = (
            TRVZB_WEEKLY_SCHEDULE_DISABLED_HOUR
        )
        defaults[TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS[index]] = 0
        defaults[TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[index]] = 0
    return defaults


def _trvzb_today_schedule_day(timezone):
    """Return today's standard Thermostat weekday in the ZHA local timezone."""

    days = (
        RtiTekTrvzbScheduleDay.Monday,
        RtiTekTrvzbScheduleDay.Tuesday,
        RtiTekTrvzbScheduleDay.Wednesday,
        RtiTekTrvzbScheduleDay.Thursday,
        RtiTekTrvzbScheduleDay.Friday,
        RtiTekTrvzbScheduleDay.Saturday,
        RtiTekTrvzbScheduleDay.Sunday,
    )
    return int(days[dt.datetime.now(timezone).weekday()].value)


def _trvzb_next_schedule_day(day):
    """Return the next standard Thermostat weekday."""

    days = tuple(RtiTekTrvzbScheduleDay)
    return int(days[(days.index(RtiTekTrvzbScheduleDay(day)) + 1) % len(days)].value)


def _trvzb_previous_schedule_day(day):
    """Return the previous standard Thermostat weekday."""

    days = tuple(RtiTekTrvzbScheduleDay)
    return int(days[(days.index(RtiTekTrvzbScheduleDay(day)) - 1) % len(days)].value)


def _temporary_manual_status(value):
    """Expose local inference without claiming a device-reported state."""

    try:
        return RtiTekTrvzbTemporaryManualState(value).name
    except (KeyError, TypeError, ValueError):
        return RtiTekTrvzbTemporaryManualState.Unknown.name


class RtiTekTrvzbWindowState(t.enum8):
    """TRVZB window states defined by the FD22 protocol."""

    Closed = 0x00
    Open = 0x01


def _window_detection_status(value):
    """Map the verified window states to the Sonoff-style status text."""

    try:
        value = int(value)
    except (TypeError, ValueError):
        return "Unknown"
    if value == RtiTekTrvzbWindowState.Open:
        return "Detected"
    if value == RtiTekTrvzbWindowState.Closed:
        return "Not detected"
    return "Unknown"


class RtiTekTrvzbThermostat(CustomCluster, Thermostat):
    """Keep device heat limits available to climate but not user-editable."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """TRVZB Thermostat extensions and local schedule editor attributes."""

        system_mode = ZCLAttributeDef(
            id=Thermostat.AttributeDefs.system_mode.id,
            type=RtiTekTrvzbSystemMode,
            zcl_type=DataTypeId.enum8,
            access=Thermostat.AttributeDefs.system_mode.access,
            mandatory=Thermostat.AttributeDefs.system_mode.mandatory,
            manufacturer_code=Thermostat.AttributeDefs.system_mode.manufacturer_code,
        )
        min_heat_setpoint_limit = ZCLAttributeDef(
            id=Thermostat.AttributeDefs.min_heat_setpoint_limit.id,
            type=t.int16s,
            access="r",
            mandatory=Thermostat.AttributeDefs.min_heat_setpoint_limit.mandatory,
            manufacturer_code=(
                Thermostat.AttributeDefs.min_heat_setpoint_limit.manufacturer_code
            ),
        )
        max_heat_setpoint_limit = ZCLAttributeDef(
            id=Thermostat.AttributeDefs.max_heat_setpoint_limit.id,
            type=t.int16s,
            access="r",
            mandatory=Thermostat.AttributeDefs.max_heat_setpoint_limit.mandatory,
            manufacturer_code=(
                Thermostat.AttributeDefs.max_heat_setpoint_limit.manufacturer_code
            ),
        )
        # 0xF100-0xF10C only keep the editor state in ZHA. They are not
        # device attributes and are sent as one standard Thermostat command.
        weekly_schedule_day = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_DAY_ATTR,
            type=RtiTekTrvzbScheduleDay,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_1_time = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_TIME_ATTRS[1],
            type=t.uint16_t,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_2_time = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_TIME_ATTRS[2],
            type=t.uint16_t,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_3_time = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_TIME_ATTRS[3],
            type=t.uint16_t,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_4_time = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_TIME_ATTRS[4],
            type=t.uint16_t,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_5_time = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_TIME_ATTRS[5],
            type=t.uint16_t,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_6_time = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_TIME_ATTRS[6],
            type=t.uint16_t,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_1_hour = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[1],
            type=RtiTekTrvzbScheduleHour,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_2_hour = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[2],
            type=RtiTekTrvzbScheduleHour,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_3_hour = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[3],
            type=RtiTekTrvzbScheduleHour,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_4_hour = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[4],
            type=RtiTekTrvzbScheduleHour,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_5_hour = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[5],
            type=RtiTekTrvzbScheduleHour,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_6_hour = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[6],
            type=RtiTekTrvzbScheduleHour,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_1_minute = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS[1],
            type=RtiTekTrvzbScheduleMinute,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_2_minute = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS[2],
            type=RtiTekTrvzbScheduleMinute,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_3_minute = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS[3],
            type=RtiTekTrvzbScheduleMinute,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_4_minute = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS[4],
            type=RtiTekTrvzbScheduleMinute,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_5_minute = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS[5],
            type=RtiTekTrvzbScheduleMinute,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_6_minute = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS[6],
            type=RtiTekTrvzbScheduleMinute,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_1_temperature = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[1],
            type=t.int16s,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_2_temperature = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[2],
            type=t.int16s,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_3_temperature = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[3],
            type=t.int16s,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_4_temperature = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[4],
            type=t.int16s,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_5_temperature = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[5],
            type=t.int16s,
            access="rw",
            manufacturer_code=None,
        )
        weekly_schedule_period_6_temperature = ZCLAttributeDef(
            id=TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[6],
            type=t.int16s,
            access="rw",
            manufacturer_code=None,
        )
        temporary_manual_temperature = ZCLAttributeDef(
            id=TRVZB_TEMPORARY_MANUAL_TEMPERATURE_ATTR,
            type=t.int16s,
            access="rw",
            manufacturer_code=None,
        )
        temporary_manual_state = ZCLAttributeDef(
            id=TRVZB_TEMPORARY_MANUAL_STATE_ATTR,
            type=RtiTekTrvzbTemporaryManualState,
            access="r",
            manufacturer_code=None,
        )

    def __init__(self, *args, **kwargs):
        """Initialize local schedule and temporary-manual state."""

        super().__init__(*args, **kwargs)
        self._weekly_schedule_cache = {}
        self._weekly_schedule_device_cache = {}
        self._temporary_manual_expiry_task = None
        self._temporary_manual_detection_task = None
        self._temporary_manual_inference_active = False
        self._trvzb_timezone = None
        for attrid, value in _trvzb_schedule_editor_defaults().items():
            self._update_attribute(attrid, value)
        self._update_attribute(
            TRVZB_TEMPORARY_MANUAL_STATE_ATTR,
            RtiTekTrvzbTemporaryManualState.Unknown,
        )

    def set_local_timezone(self, timezone):
        """Use ZHA's configured timezone for weekly-schedule transitions."""

        self._trvzb_timezone = timezone

    def _temporary_manual_now(self):
        """Return the local time used by the weekly Thermostat schedule."""

        timezone = self._trvzb_timezone or dt.datetime.now().astimezone().tzinfo
        return dt.datetime.now(timezone)

    def _set_temporary_manual_state(self, state):
        """Publish the explicitly local temporary-manual state."""

        super()._update_attribute(TRVZB_TEMPORARY_MANUAL_STATE_ATTR, state)

    def _cancel_temporary_manual_expiry(self):
        """Cancel the currently inferred schedule-transition deadline."""

        if self._temporary_manual_expiry_task is not None:
            self._temporary_manual_expiry_task.cancel()
            self._temporary_manual_expiry_task = None

    def _clear_temporary_manual_mode(self):
        """End the local temporary-manual inference."""

        self._cancel_temporary_manual_expiry()
        self._temporary_manual_inference_active = False
        self._set_temporary_manual_state(RtiTekTrvzbTemporaryManualState.Inactive)

    def _next_temporary_manual_transition(self):
        """Return the next device-reported weekly transition, if known."""

        now = self._temporary_manual_now()
        today = _trvzb_today_schedule_day(now.tzinfo)
        today_transitions = self._weekly_schedule_device_cache.get(today)
        if today_transitions is None:
            return None

        minutes = now.hour * 60 + now.minute
        for transition_minutes, _temperature in today_transitions:
            if transition_minutes > minutes:
                return now.replace(
                    hour=transition_minutes // 60,
                    minute=transition_minutes % 60,
                    second=0,
                    microsecond=0,
                )

        tomorrow = _trvzb_next_schedule_day(today)
        tomorrow_transitions = self._weekly_schedule_device_cache.get(tomorrow)
        if not tomorrow_transitions:
            return None

        transition_minutes = tomorrow_transitions[0][0]
        return (now + dt.timedelta(days=1)).replace(
            hour=transition_minutes // 60,
            minute=transition_minutes % 60,
            second=0,
            microsecond=0,
        )

    def _refresh_temporary_manual_expiry(self):
        """Derive temporary-manual expiry only from device-reported schedules."""

        if not self._temporary_manual_inference_active:
            return

        transition = self._next_temporary_manual_transition()
        self._cancel_temporary_manual_expiry()
        if transition is None:
            self._set_temporary_manual_state(RtiTekTrvzbTemporaryManualState.Unknown)
            return

        self._set_temporary_manual_state(RtiTekTrvzbTemporaryManualState.Active)
        delay = max(0, (transition - self._temporary_manual_now()).total_seconds())
        loop = asyncio.get_running_loop()
        self._temporary_manual_expiry_task = loop.call_later(
            delay, self._clear_temporary_manual_mode
        )

    async def _request_temporary_manual_schedules(self):
        """Fetch adjacent weekdays for temporary-manual inference."""

        now = self._temporary_manual_now()
        today = _trvzb_today_schedule_day(now.tzinfo)
        for day in (
            _trvzb_previous_schedule_day(today),
            today,
            _trvzb_next_schedule_day(today),
        ):
            try:
                response = await self.get_weekly_schedule(
                    days_to_return=SeqDayOfWeek(day),
                    mode_to_return=SeqMode.Heat,
                )
                self._store_weekly_schedule_response(response)
            except Exception as exc:
                self.debug("TRVZB temporary manual schedule fetch failed: %s", exc)

    async def _temporary_manual_is_supported_in_auto(self):
        """Return whether the device currently supports Auto temporary manual."""

        private_cluster = self.endpoint.in_clusters.get(
            RtiTekTrvzbPrivateCluster.cluster_id
        )
        if private_cluster is None:
            return None

        capability_name = RtiTekTrvzbPrivateCluster.AttributeDefs.manual_temperature_in_auto_supported.name
        system_mode_name = self.AttributeDefs.system_mode.name
        try:
            capability_values, _ = await private_cluster.read_attributes(
                [capability_name], only_cache=True
            )
            system_mode_values, _ = await self.read_attributes(
                [system_mode_name], allow_cache=False
            )
        except Exception as exc:
            self.debug("TRVZB temporary manual state read failed: %s", exc)
            return None

        capability = capability_values.get(
            capability_name,
            capability_values.get(
                RtiTekTrvzbPrivateCluster.AttributeDefs.manual_temperature_in_auto_supported.id
            ),
        )
        system_mode = system_mode_values.get(
            system_mode_name,
            system_mode_values.get(self.AttributeDefs.system_mode.id),
        )
        return (
            bool(capability)
            and system_mode is not None
            and int(system_mode) == int(RtiTekTrvzbSystemMode.Auto)
        )

    async def _start_temporary_manual_inference(self):
        """Infer temporary manual state after an acknowledged setpoint write."""

        supported = await self._temporary_manual_is_supported_in_auto()
        if supported is None:
            self._temporary_manual_inference_active = False
            self._set_temporary_manual_state(RtiTekTrvzbTemporaryManualState.Unknown)
            return
        if supported:
            self._temporary_manual_inference_active = True
            self._set_temporary_manual_state(RtiTekTrvzbTemporaryManualState.Active)
            self._refresh_temporary_manual_expiry()
            await self._request_temporary_manual_schedules()
            return

        self._clear_temporary_manual_mode()

    def _current_weekly_schedule_temperature(self):
        """Return the scheduled setpoint effective at the current local time."""

        now = self._temporary_manual_now()
        today = _trvzb_today_schedule_day(now.tzinfo)
        transitions = self._weekly_schedule_device_cache.get(today)
        if transitions is None:
            return None

        minute_of_day = now.hour * 60 + now.minute
        active_temperature = None
        for transition_time, temperature in transitions:
            if transition_time > minute_of_day:
                break
            active_temperature = temperature
        if active_temperature is not None:
            return active_temperature

        previous_transitions = self._weekly_schedule_device_cache.get(
            _trvzb_previous_schedule_day(today)
        )
        if previous_transitions:
            return previous_transitions[-1][1]
        return None

    async def _detect_device_temporary_manual_mode(self, reported_temperature):
        """Infer a device-side temporary override from one setpoint report."""

        expected_temperature = self._current_weekly_schedule_temperature()
        if expected_temperature is None:
            self._temporary_manual_inference_active = False
            self._set_temporary_manual_state(RtiTekTrvzbTemporaryManualState.Unknown)
            return

        supported = await self._temporary_manual_is_supported_in_auto()
        if supported is None:
            self._temporary_manual_inference_active = False
            self._set_temporary_manual_state(RtiTekTrvzbTemporaryManualState.Unknown)
            return
        if not supported or int(reported_temperature) == int(expected_temperature):
            self._clear_temporary_manual_mode()
            return

        self._temporary_manual_inference_active = True
        self._set_temporary_manual_state(RtiTekTrvzbTemporaryManualState.Active)
        self._refresh_temporary_manual_expiry()
        await self._request_temporary_manual_schedules()

    def _schedule_device_temporary_manual_detection(self, reported_temperature):
        """Schedule one non-blocking inference for a setpoint report."""

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        if self._temporary_manual_detection_task is not None:
            self._temporary_manual_detection_task.cancel()
        self._temporary_manual_detection_task = loop.create_task(
            self._detect_device_temporary_manual_mode(reported_temperature)
        )

    @staticmethod
    def _write_succeeded(result, attrid):
        """Return whether a normal Write Attributes response accepted attrid."""

        for records in result:
            for record in records:
                if record.attrid == attrid:
                    return record.status == Status.SUCCESS
        return False

    async def _read_private_mode_attributes(self, *attr_defs):
        """Read the requested mode attributes from the final private cluster."""

        private_cluster = self.endpoint.in_clusters.get(
            RtiTekTrvzbPrivateCluster.cluster_id
        )
        if private_cluster is None:
            raise ValueError("Unable to access TRVZB mode configuration")
        values, _ = await private_cluster.read_attributes(
            [attr_def.name for attr_def in attr_defs], allow_cache=False
        )
        mode_values = {}
        for attr_def in attr_defs:
            value = values.get(attr_def.name, values.get(attr_def.id))
            if value is None:
                raise ValueError(f"Unable to read {attr_def.name} before mode change")
            mode_values[attr_def.id] = int(value)
        return private_cluster, mode_values

    async def _write_private_mode_attribute(self, cluster, attr_def, value):
        """Write and confirm one private mode attribute."""

        result = await cluster.write_attributes({attr_def.name: value})
        if not self._write_succeeded(result, attr_def.id):
            raise ValueError(f"Unable to write {attr_def.name} during mode change")

    async def _prepare_system_mode_change(self):
        """Leave Boost before a system-mode change and retain Holiday state."""

        holiday_attr = RtiTekTrvzbPrivateCluster.AttributeDefs.holiday_duration
        boost_attr = RtiTekTrvzbPrivateCluster.AttributeDefs.boost_duration
        private_cluster, mode_values = await self._read_private_mode_attributes(
            holiday_attr, boost_attr
        )
        holiday_duration = mode_values[holiday_attr.id]
        boost_duration = mode_values[boost_attr.id]
        if boost_duration > 0:
            await self._write_private_mode_attribute(private_cluster, boost_attr, 0)
        return private_cluster, bool(holiday_duration > 0)

    async def _finish_system_mode_change(self, private_cluster, holiday_was_active):
        """Clear Holiday only after a non-Boost mode change has succeeded."""

        if not holiday_was_active:
            return
        holiday_attr = RtiTekTrvzbPrivateCluster.AttributeDefs.holiday_duration
        await self._write_private_mode_attribute(private_cluster, holiday_attr, 0)

    def _update_attribute(self, attrid, value):
        """Keep local temporary-manual values aligned with device reports."""

        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.occupied_heating_setpoint.id:
            super()._update_attribute(TRVZB_TEMPORARY_MANUAL_TEMPERATURE_ATTR, value)
            self._schedule_device_temporary_manual_detection(value)
        elif attrid == self.AttributeDefs.system_mode.id:
            try:
                is_auto = int(value) == int(RtiTekTrvzbSystemMode.Auto)
            except (TypeError, ValueError):
                is_auto = False
            if not is_auto:
                self._clear_temporary_manual_mode()

    async def read_attributes(self, attributes, *args, **kwargs):
        """Mirror standard setpoint and mode reads into local derived state."""

        success, failure = await super().read_attributes(attributes, *args, **kwargs)
        for attr_def in (
            self.AttributeDefs.occupied_heating_setpoint,
            self.AttributeDefs.system_mode,
        ):
            value = success.get(attr_def.name, success.get(attr_def.id))
            if value is not None:
                self._update_attribute(attr_def.id, value)
        return success, failure

    @staticmethod
    def _weekly_schedule_editor_attribute_ids():
        return {
            TRVZB_WEEKLY_SCHEDULE_DAY_ATTR,
            *TRVZB_WEEKLY_SCHEDULE_TIME_ATTRS.values(),
            *TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS.values(),
            *TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS.values(),
            *TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS.values(),
        }

    def _weekly_schedule_editor_value(self, attrid):
        return self._attr_cache.get(attrid, _trvzb_schedule_editor_defaults()[attrid])

    @staticmethod
    def _weekly_schedule_period_index(attrid):
        """Return the editor period owning one local time attribute."""

        for attributes in (
            TRVZB_WEEKLY_SCHEDULE_TIME_ATTRS,
            TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS,
            TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS,
            TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS,
        ):
            for index, candidate_attrid in attributes.items():
                if attrid == candidate_attrid:
                    return index
        return None

    def _update_weekly_schedule_period_time(self, index, time):
        """Keep raw minute storage and the hour/minute editor fields aligned."""

        time = int(time)
        raw_attrid = TRVZB_WEEKLY_SCHEDULE_TIME_ATTRS[index]
        hour_attrid = TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[index]
        minute_attrid = TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS[index]
        if time == TRVZB_WEEKLY_SCHEDULE_NULL_TIME:
            self._update_attribute(raw_attrid, time)
            self._update_attribute(hour_attrid, TRVZB_WEEKLY_SCHEDULE_DISABLED_HOUR)
            self._update_attribute(minute_attrid, 0)
            return
        if time < 0 or time >= 24 * 60:
            raise ValueError("weekly schedule times must be within one day")
        self._update_attribute(raw_attrid, time)
        self._update_attribute(hour_attrid, time // 60)
        self._update_attribute(minute_attrid, time % 60)

    def _disable_weekly_schedule_period(self, index):
        """Clear local editor values for one disabled schedule period."""

        self._update_weekly_schedule_period_time(index, TRVZB_WEEKLY_SCHEDULE_NULL_TIME)
        self._update_attribute(TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[index], 0)

    def _load_weekly_schedule_editor(self, transitions):
        """Populate the editor with one cached or device-reported weekday."""

        for index, (time, temperature) in enumerate(transitions, start=1):
            self._update_weekly_schedule_period_time(index, time)
            self._update_attribute(
                TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[index], temperature
            )
        for index in range(len(transitions) + 1, TRVZB_WEEKLY_SCHEDULE_MAX_PERIODS + 1):
            self._disable_weekly_schedule_period(index)

    def _weekly_schedule_editor_periods(self):
        """Return the selected editor day's raw periods."""

        return [
            (
                int(
                    self._weekly_schedule_editor_value(
                        TRVZB_WEEKLY_SCHEDULE_TIME_ATTRS[index]
                    )
                ),
                int(
                    self._weekly_schedule_editor_value(
                        TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[index]
                    )
                ),
            )
            for index in range(1, TRVZB_WEEKLY_SCHEDULE_MAX_PERIODS + 1)
        ]

    @staticmethod
    def _validate_weekly_schedule_periods(periods):
        """Validate and return enabled periods from one editor day."""

        transitions = []
        previous_time = -1
        for time, temperature in periods:
            if time == TRVZB_WEEKLY_SCHEDULE_NULL_TIME:
                continue
            if not 0 <= time < 24 * 60:
                raise ValueError("Weekly schedule time must be between 00:00 and 23:59")
            if time <= previous_time:
                raise ValueError("Weekly schedule periods must be strictly increasing")
            if not 500 <= temperature <= 3000:
                raise ValueError(
                    "Weekly schedule temperature must be between 5 and 30 C"
                )
            transitions.append((time, temperature))
            previous_time = time
        return transitions

    def _cache_weekly_schedule_editor(self, day):
        """Save the six local editor fields for one weekday."""

        self._weekly_schedule_cache[day] = [
            (
                int(
                    self._weekly_schedule_editor_value(
                        TRVZB_WEEKLY_SCHEDULE_TIME_ATTRS[index]
                    )
                ),
                int(
                    self._weekly_schedule_editor_value(
                        TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[index]
                    )
                ),
            )
            for index in range(1, TRVZB_WEEKLY_SCHEDULE_MAX_PERIODS + 1)
        ]

    def _build_weekly_schedule(self):
        """Build a six-period heating-only Thermostat schedule request."""

        day = int(self._weekly_schedule_editor_value(TRVZB_WEEKLY_SCHEDULE_DAY_ATTR))
        if day not in {int(member.value) for member in RtiTekTrvzbScheduleDay}:
            raise ValueError("weekly schedule day must contain one weekday")

        transitions = self._validate_weekly_schedule_periods(
            self._weekly_schedule_editor_periods()
        )

        if not transitions:
            raise ValueError("weekly schedule needs at least one period")

        # The current firmware expects all six standard schedule slots. Keep
        # disabled editor rows local and repeat the final real transition only
        # in the device command, matching the Sonoff editor's padding model.
        device_transitions = transitions + [transitions[-1]] * (
            TRVZB_WEEKLY_SCHEDULE_MAX_PERIODS - len(transitions)
        )
        values = [value for transition in device_transitions for value in transition]
        return SeqDayOfWeek(day), device_transitions, values

    async def schedule_apply(self, expect_reply=False):
        """Apply one day, then read it back after the device settles."""

        day, transitions, values = self._build_weekly_schedule()
        result = await self.set_weekly_schedule(
            num_transitions_for_sequence=TRVZB_WEEKLY_SCHEDULE_MAX_PERIODS,
            day_of_week_for_sequence=day,
            mode_for_sequence=SeqMode.Heat,
            values=values,
            expect_reply=True,
        )
        if (
            getattr(result, "status", None) != Status.SUCCESS
            or getattr(result, "command_id", None) != 0x01
        ):
            status = getattr(result, "status", "unknown response")
            raise ValueError(f"Weekly schedule apply failed: {status}")
        await asyncio.sleep(TRVZB_WEEKLY_SCHEDULE_APPLY_SETTLE_SECONDS)
        await self.schedule_fetch(expect_reply=True, days_to_return=day)
        return result

    async def schedule_fetch(self, expect_reply=False, days_to_return=None):
        """Request one day or fetch the full week one day at a time."""

        if days_to_return is not None:
            response = await self.get_weekly_schedule(
                days_to_return=SeqDayOfWeek(days_to_return),
                mode_to_return=SeqMode.Heat,
                expect_reply=expect_reply,
            )
            self._store_weekly_schedule_response(response)
            return response

        selected_day = SeqDayOfWeek(
            self._weekly_schedule_editor_value(TRVZB_WEEKLY_SCHEDULE_DAY_ATTR)
        )
        days = (selected_day,) + tuple(
            SeqDayOfWeek(day)
            for day in RtiTekTrvzbScheduleDay
            if int(day.value) != int(selected_day)
        )
        responses = []
        for day in days:
            response = await self.get_weekly_schedule(
                days_to_return=day,
                mode_to_return=SeqMode.Heat,
                expect_reply=True,
            )
            self._store_weekly_schedule_response(response)
            responses.append(response)
        return responses

    def _weekly_schedule_response(self, args):
        """Validate a standard schedule response before updating local state."""

        response = args
        if isinstance(args, (list, tuple)):
            if len(args) == 1:
                response = args[0]
            elif len(args) == 4:
                response = None
                transition_count, day, mode, values = args
            else:
                return None

        if response is not None:
            try:
                transition_count = response.num_transitions_for_sequence
                day = response.day_of_week_for_sequence
                mode = response.mode_for_sequence
                values = response.values
            except AttributeError:
                return None

        try:
            transition_count = int(transition_count)
            day = int(day)
            mode = int(mode)
            values = [int(value) for value in values]
        except (TypeError, ValueError):
            return None

        if not 1 <= transition_count <= TRVZB_WEEKLY_SCHEDULE_MAX_PERIODS:
            return None
        if not day or not mode & int(SeqMode.Heat):
            return None
        if len(values) != transition_count * 2:
            return None

        device_transitions = list(zip(values[::2], values[1::2], strict=True))
        transitions = []
        padding_started = False
        previous_time = -1
        for time, temperature in device_transitions:
            if time < 0 or time >= 24 * 60:
                return None
            if not 500 <= temperature <= 3000:
                return None
            if transitions and (time, temperature) == transitions[-1]:
                padding_started = True
                continue
            if padding_started or time <= previous_time:
                return None
            transitions.append((time, temperature))
            previous_time = time

        return day, transitions

    def _store_weekly_schedule_response(self, args):
        """Cache one valid response and refresh the selected editor day."""

        schedule = self._weekly_schedule_response(args)
        if schedule is None:
            return False

        response_day, transitions = schedule
        for day in RtiTekTrvzbScheduleDay:
            if response_day & int(day.value):
                self._weekly_schedule_cache[int(day.value)] = transitions
                self._weekly_schedule_device_cache[int(day.value)] = transitions

        selected_day = int(
            self._weekly_schedule_editor_value(TRVZB_WEEKLY_SCHEDULE_DAY_ATTR)
        )
        if response_day & selected_day:
            self._load_weekly_schedule_editor(transitions)
        self._refresh_temporary_manual_expiry()
        return True

    def handle_cluster_request(self, hdr, args, *super_args, **kwargs):
        """Update the selected editor only from a valid schedule response."""

        if hdr.command_id == 0x00 and self._store_weekly_schedule_response(args):
            return None

        return super().handle_cluster_request(hdr, args, *super_args, **kwargs)

    async def write_attributes(self, attributes, *args, **kwargs):  # noqa: C901
        """Handle local schedule and temporary-manual editor attributes."""

        remaining_attributes = dict(attributes)
        temporary_manual_temperature = None
        written_system_mode = None
        private_mode_cluster = None
        holiday_was_active = False
        for key in list(remaining_attributes):
            try:
                attr = self.find_attribute(key)
            except KeyError:
                continue
            if attr.id == TRVZB_TEMPORARY_MANUAL_TEMPERATURE_ATTR:
                if temporary_manual_temperature is not None:
                    raise ValueError("Temporary manual temperature was provided twice")
                temporary_manual_temperature = remaining_attributes.pop(key)
            elif attr.id == self.AttributeDefs.system_mode.id:
                written_system_mode = remaining_attributes[key]

        if temporary_manual_temperature is not None:
            temporary_manual_temperature = int(temporary_manual_temperature)
            if not 500 <= temporary_manual_temperature <= 3000:
                raise ValueError("Temporary manual temperature must be 5-30 C")
            if temporary_manual_temperature % 50:
                raise ValueError("Temporary manual temperature must use 0.5 C steps")
            if written_system_mode is not None:
                raise ValueError(
                    "Temporary manual temperature cannot be changed with system mode"
                )
            remaining_attributes[self.AttributeDefs.occupied_heating_setpoint.name] = (
                temporary_manual_temperature
            )

        editor_attr_ids = self._weekly_schedule_editor_attribute_ids()
        for key in list(remaining_attributes):
            try:
                attr = self.find_attribute(key)
            except KeyError:
                continue
            if attr.id not in editor_attr_ids:
                continue
            value = remaining_attributes.pop(key)
            if attr.id == TRVZB_WEEKLY_SCHEDULE_DAY_ATTR:
                value = int(value)
                if value not in {
                    int(member.value) for member in RtiTekTrvzbScheduleDay
                }:
                    raise ValueError("weekly schedule day must contain one weekday")
                previous_day = int(self._weekly_schedule_editor_value(attr.id))
                self._cache_weekly_schedule_editor(previous_day)
                self._update_attribute(attr.id, value)
                if value != previous_day:
                    self._load_weekly_schedule_editor(
                        self._weekly_schedule_cache.get(value, [])
                    )
                continue

            period_index = self._weekly_schedule_period_index(attr.id)
            if period_index is not None:
                value = int(value)
                raw_attrid = TRVZB_WEEKLY_SCHEDULE_TIME_ATTRS[period_index]
                hour_attrid = TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[period_index]
                minute_attrid = TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS[period_index]
                temperature_attrid = TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[
                    period_index
                ]
                periods = self._weekly_schedule_editor_periods()

                if attr.id == raw_attrid:
                    if value == TRVZB_WEEKLY_SCHEDULE_NULL_TIME:
                        self._disable_weekly_schedule_period(period_index)
                    else:
                        temperature = periods[period_index - 1][1]
                        if temperature == 0:
                            temperature = TRVZB_WEEKLY_SCHEDULE_DEFAULT_TEMPERATURE
                        periods[period_index - 1] = (value, temperature)
                        self._validate_weekly_schedule_periods(periods)
                        self._update_weekly_schedule_period_time(period_index, value)
                        self._update_attribute(temperature_attrid, temperature)
                elif attr.id == hour_attrid:
                    if (
                        value != TRVZB_WEEKLY_SCHEDULE_DISABLED_HOUR
                        and not 0 <= value < 24
                    ):
                        raise ValueError("weekly schedule hour must be 0-23")
                    if value == TRVZB_WEEKLY_SCHEDULE_DISABLED_HOUR:
                        self._disable_weekly_schedule_period(period_index)
                    else:
                        minute = int(self._weekly_schedule_editor_value(minute_attrid))
                        temperature = periods[period_index - 1][1]
                        if temperature == 0:
                            temperature = TRVZB_WEEKLY_SCHEDULE_DEFAULT_TEMPERATURE
                        periods[period_index - 1] = (value * 60 + minute, temperature)
                        self._validate_weekly_schedule_periods(periods)
                        self._update_attribute(hour_attrid, value)
                        self._update_attribute(raw_attrid, value * 60 + minute)
                        self._update_attribute(temperature_attrid, temperature)
                elif attr.id == minute_attrid:
                    if not 0 <= value < 60:
                        raise ValueError("weekly schedule minute must be 0-59")
                    hour = int(self._weekly_schedule_editor_value(hour_attrid))
                    if hour == TRVZB_WEEKLY_SCHEDULE_DISABLED_HOUR:
                        raise ValueError("This weekly schedule period is disabled")
                    periods[period_index - 1] = (
                        hour * 60 + value,
                        periods[period_index - 1][1],
                    )
                    self._validate_weekly_schedule_periods(periods)
                    self._update_attribute(minute_attrid, value)
                    self._update_attribute(raw_attrid, hour * 60 + value)
                else:
                    hour = int(self._weekly_schedule_editor_value(hour_attrid))
                    if hour == TRVZB_WEEKLY_SCHEDULE_DISABLED_HOUR:
                        raise ValueError("This weekly schedule period is disabled")
                    periods[period_index - 1] = (
                        periods[period_index - 1][0],
                        value,
                    )
                    self._validate_weekly_schedule_periods(periods)
                    self._update_attribute(attr.id, value)

                self._cache_weekly_schedule_editor(
                    int(
                        self._weekly_schedule_editor_value(
                            TRVZB_WEEKLY_SCHEDULE_DAY_ATTR
                        )
                    )
                )
                continue

        if written_system_mode is not None:
            (
                private_mode_cluster,
                holiday_was_active,
            ) = await self._prepare_system_mode_change()

        if remaining_attributes:
            result = await super().write_attributes(
                remaining_attributes, *args, **kwargs
            )
            if temporary_manual_temperature is not None and self._write_succeeded(
                result, self.AttributeDefs.occupied_heating_setpoint.id
            ):
                super()._update_attribute(
                    TRVZB_TEMPORARY_MANUAL_TEMPERATURE_ATTR,
                    temporary_manual_temperature,
                )
                await self._start_temporary_manual_inference()
            if written_system_mode is not None and self._write_succeeded(
                result, self.AttributeDefs.system_mode.id
            ):
                self._clear_temporary_manual_mode()
                self._update_attribute(
                    self.AttributeDefs.system_mode.id, written_system_mode
                )
                await self._finish_system_mode_change(
                    private_mode_cluster, holiday_was_active
                )
            return result
        return {}, {}


class RtiTekTrvzbPrivateCluster(CustomCluster):
    """Rti-Tek TRVZB private configuration cluster."""

    cluster_id = 0xFD22
    ep_attribute = "rti_tek_trvzb_private"

    class AttributeDefs(BaseAttributeDefs):
        """TRVZB attributes defined by the Rti-Tek FD22 protocol."""

        temperature_unit = ZCLAttributeDef(
            id=0x0000, type=t.enum8, access="rwp", manufacturer_code=None
        )
        child_lock = ZCLAttributeDef(
            id=0x0001, type=t.Bool, access="rwp", manufacturer_code=None
        )
        fault_code = ZCLAttributeDef(
            id=0x0002, type=t.bitmap32, access="rp", manufacturer_code=None
        )
        product_name = ZCLAttributeDef(
            id=0x0003,
            type=t.CharacterString,
            access="r",
            manufacturer_code=None,
        )
        model_string = ZCLAttributeDef(
            id=0x0004,
            type=t.CharacterString,
            access="r",
            manufacturer_code=None,
        )
        device_switch = ZCLAttributeDef(
            id=0x0005, type=t.Bool, access="rwp", manufacturer_code=None
        )
        supported_features = ZCLAttributeDef(
            id=0x0006, type=t.bitmap32, access="r", manufacturer_code=None
        )
        screen_brightness = ZCLAttributeDef(
            id=0x000A,
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=None,
        )
        screen_direction = ZCLAttributeDef(
            id=0x0008,
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=None,
        )
        screen_display_duration = ZCLAttributeDef(
            id=0x0009, type=t.uint16_t, access="rwp", manufacturer_code=None
        )

        open_window_detection = ZCLAttributeDef(
            id=0x1000, type=t.Bool, access="rwp", manufacturer_code=None
        )
        window_state = ZCLAttributeDef(
            id=0x1001,
            type=RtiTekTrvzbWindowState,
            access="rp",
            manufacturer_code=None,
        )
        valve_opening = ZCLAttributeDef(
            id=0x1002, type=t.uint16_t, access="rp", manufacturer_code=None
        )
        motor_force = ZCLAttributeDef(
            id=0x1003, type=t.enum8, access="rwp", manufacturer_code=None
        )
        temperature_control_mode = ZCLAttributeDef(
            id=0x1004,
            type=RtiTekTrvzbTemperatureControlMode,
            access="rwp",
            manufacturer_code=None,
        )
        valve_switching_difference = ZCLAttributeDef(
            id=0x1005, type=t.int16s, access="rwp", manufacturer_code=None
        )
        valve_opening_difference = ZCLAttributeDef(
            id=0x1006, type=t.int16s, access="rwp", manufacturer_code=None
        )
        frost_protection_enabled = ZCLAttributeDef(
            id=0x1007, type=t.Bool, access="rwp", manufacturer_code=None
        )
        comfort_temperature = ZCLAttributeDef(
            id=0x1008, type=t.int16s, access="rwp", manufacturer_code=None
        )
        eco_temperature = ZCLAttributeDef(
            id=0x1009, type=t.int16s, access="rwp", manufacturer_code=None
        )
        frost_temperature = ZCLAttributeDef(
            id=0x100A, type=t.int16s, access="rwp", manufacturer_code=None
        )
        temperature_source = ZCLAttributeDef(
            id=0x100B, type=t.enum8, access="rwp", manufacturer_code=None
        )
        external_temperature = ZCLAttributeDef(
            id=0x100C, type=t.int16s, access="rp", manufacturer_code=None
        )
        external_humidity = ZCLAttributeDef(
            id=0x100D, type=t.int16s, access="rp", manufacturer_code=None
        )
        internal_humidity = ZCLAttributeDef(
            id=0x100E, type=t.int16s, access="rp", manufacturer_code=None
        )
        heating_valve_opening = ZCLAttributeDef(
            id=0x100F, type=t.uint8_t, access="rwp", manufacturer_code=None
        )
        idle_valve_opening = ZCLAttributeDef(
            id=0x1010, type=t.uint8_t, access="rwp", manufacturer_code=None
        )
        remote_temperature = ZCLAttributeDef(
            id=0x1011, type=t.int16s, access="rwp", manufacturer_code=None
        )
        temperature_source_status = ZCLAttributeDef(
            id=0x1012, type=t.uint8_t, access="rwp", manufacturer_code=None
        )
        low_battery_valve_state = ZCLAttributeDef(
            id=0x1013, type=t.uint8_t, access="rwp", manufacturer_code=None
        )
        manual_temperature_in_auto_supported = ZCLAttributeDef(
            id=0x1014, type=t.Bool, access="rwp", manufacturer_code=None
        )
        enhanced_child_lock_supported = ZCLAttributeDef(
            id=0x1015, type=t.Bool, access="rwp", manufacturer_code=None
        )
        motor_travel_calibration = ZCLAttributeDef(
            id=0x1016, type=t.Bool, access="w", manufacturer_code=None
        )
        motor_travel_calibration_status = ZCLAttributeDef(
            id=0x1017, type=t.uint8_t, access="rp", manufacturer_code=None
        )
        holiday_duration = ZCLAttributeDef(
            id=0x1018, type=t.uint32_t, access="rwp", manufacturer_code=None
        )
        boost_duration = ZCLAttributeDef(
            id=0x1019, type=t.uint32_t, access="rwp", manufacturer_code=None
        )
        motor_forward_turns = ZCLAttributeDef(
            id=0x101A, type=t.uint16_t, access="r", manufacturer_code=None
        )
        motor_reverse_turns = ZCLAttributeDef(
            id=0x101B, type=t.uint16_t, access="r", manufacturer_code=None
        )
        motor_loaded_turns = ZCLAttributeDef(
            id=0x101C, type=t.uint16_t, access="r", manufacturer_code=None
        )
        motor_type = ZCLAttributeDef(
            id=0x101D, type=t.uint8_t, access="r", manufacturer_code=None
        )
        motor_adaptive_force_percentage = ZCLAttributeDef(
            id=0x101F, type=t.uint8_t, access="r", manufacturer_code=None
        )

    async def _validate_boost_duration_write(self, attributes):
        """Allow Boost only while Auto or Holiday mode is active."""

        thermostat = self.endpoint.in_clusters.get(Thermostat.cluster_id)
        if thermostat is None:
            raise ValueError(
                "Unable to verify system mode before writing Boost duration"
            )

        holiday_name = self.AttributeDefs.holiday_duration.name
        holiday_id = self.AttributeDefs.holiday_duration.id
        try:
            system_values, _ = await thermostat.read_attributes(
                [Thermostat.AttributeDefs.system_mode.name], allow_cache=False
            )
            system_mode = system_values.get(Thermostat.AttributeDefs.system_mode.name)
        except Exception as exc:
            raise ValueError("Unable to verify Boost duration prerequisites") from exc

        if system_mode is None:
            raise ValueError("Unable to verify Boost duration prerequisites")
        if int(system_mode) == int(RtiTekTrvzbSystemMode.Auto):
            return

        try:
            holiday_values, _ = await self.read_attributes(
                [holiday_name], allow_cache=False
            )
            holiday_duration = holiday_values.get(holiday_name)
        except Exception as exc:
            raise ValueError("Unable to verify Boost duration prerequisites") from exc

        for attribute in (holiday_name, holiday_id):
            if attribute in attributes:
                holiday_duration = attributes[attribute]
                break

        if holiday_duration is None:
            raise ValueError("Unable to verify Boost duration prerequisites")
        if int(holiday_duration) <= 0:
            raise ValueError(
                "Boost duration can only be changed in Auto or Holiday mode"
            )

    @staticmethod
    def _attribute_input_value(attributes, attr_def):
        """Return a named or numeric write value for one attribute."""

        for attribute in (attr_def.name, attr_def.id):
            if attribute in attributes:
                return attributes[attribute]
        return None

    @staticmethod
    def _write_succeeded(result, attrid):
        """Return whether a normal Write Attributes response accepted attrid."""

        for records in result:
            for record in records:
                if record.attrid == attrid:
                    return record.status == Status.SUCCESS
        return False

    async def _clear_active_boost_before_holiday_write(self):
        """End Boost and require acknowledgement before changing Holiday."""

        boost_attr = self.AttributeDefs.boost_duration
        values, _ = await self.read_attributes([boost_attr.name], allow_cache=False)
        boost_duration = values.get(boost_attr.name, values.get(boost_attr.id))
        if boost_duration is None:
            raise ValueError("Unable to read Boost duration before Holiday change")
        if int(boost_duration) <= 0:
            return

        result = await super().write_attributes({boost_attr.name: 0})
        if not self._write_succeeded(result, boost_attr.id):
            raise ValueError("Unable to exit Boost before Holiday change")

    async def write_attributes(self, attributes, *args, **kwargs):
        """Apply TRVZB mode-specific configuration write restrictions."""

        attributes = dict(attributes)
        boost_value = self._attribute_input_value(
            attributes, self.AttributeDefs.boost_duration
        )
        if boost_value is not None and int(boost_value) > 0:
            await self._validate_boost_duration_write(attributes)

        holiday_value = self._attribute_input_value(
            attributes, self.AttributeDefs.holiday_duration
        )
        if holiday_value is not None:
            await self._clear_active_boost_before_holiday_write()

        attribute_name = self.AttributeDefs.valve_switching_difference.name
        attribute_id = self.AttributeDefs.valve_switching_difference.id
        has_valve_difference = any(
            attribute in attributes for attribute in (attribute_name, attribute_id)
        )
        if not has_valve_difference:
            return await super().write_attributes(attributes, *args, **kwargs)

        mode_name = self.AttributeDefs.temperature_control_mode.name
        try:
            values, _ = await self.read_attributes([mode_name], allow_cache=False)
            mode = values.get(mode_name)
        except Exception as exc:
            raise ValueError(
                "Unable to verify temperature control mode before writing "
                "valve switching difference"
            ) from exc

        if mode is None or int(mode) != int(RtiTekTrvzbTemperatureControlMode.ON_OFF):
            raise ValueError(
                "Valve switching difference can only be changed in ON-OFF mode"
            )

        for attribute in (attribute_name, attribute_id):
            if attribute in attributes:
                attributes[attribute] = _round_valve_switching_difference_raw_value(
                    attributes[attribute]
                )
        return await super().write_attributes(attributes, *args, **kwargs)


class RtiTekTrvzbDevice(QuirkV2Device):
    """Synchronize the weekly editor after initialization."""

    async def async_initialize(self, from_cache=False):
        """Select today and fetch the complete schedule after initialization."""

        await super().async_initialize(from_cache)
        endpoint = self.device.endpoints.get(1)
        if endpoint is None:
            return
        thermostat = endpoint.in_clusters.get(RtiTekTrvzbThermostat.cluster_id)
        if thermostat is None:
            return
        private_cluster = endpoint.in_clusters.get(RtiTekTrvzbPrivateCluster.cluster_id)
        thermostat.set_local_timezone(self.gateway.config.local_timezone)
        if from_cache or not self.available:
            return
        if private_cluster is not None:
            capability_attr = RtiTekTrvzbPrivateCluster.AttributeDefs.manual_temperature_in_auto_supported
            try:
                await private_cluster.read_attributes(
                    [capability_attr.name], allow_cache=True
                )
            except Exception as exc:
                self.debug("TRVZB temporary-manual capability read failed: %s", exc)

        today = _trvzb_today_schedule_day(self.gateway.config.local_timezone)
        thermostat._update_attribute(TRVZB_WEEKLY_SCHEDULE_DAY_ATTR, today)
        try:
            await thermostat.schedule_fetch()
        except Exception as exc:
            self.debug("TRVZB automatic weekly schedule fetch failed: %s", exc)


TRVZB_QUIRK_BUILDER = (
    QuirkBuilder("Rti-Tek", "eTRV-ZB01")
    .zha_device_class(RtiTekTrvzbDevice)
    .replaces(RtiTekTrvzbThermostat)
    .replaces(RtiTekTrvzbPrivateCluster)
    .prevent_default_entity_creation(function=_is_heat_setpoint_limit_entity)
    .prevent_default_entity_creation(
        cluster_id=Thermostat.cluster_id,
        unique_id_suffix="local_temperature_calibration",
    )
    .number(
        Thermostat.AttributeDefs.local_temperature_calibration.name,
        Thermostat.cluster_id,
        min_value=-10.0,
        max_value=10.0,
        step=0.1,
        unit=UnitOfTemperature.CELSIUS,
        mode="slider",
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        unique_id_suffix="temperature_offset",
        translation_key="temperature_offset",
        fallback_name="Temperature offset",
    )
    .switch(
        RtiTekTrvzbPrivateCluster.AttributeDefs.child_lock.name,
        RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .switch(
        RtiTekTrvzbPrivateCluster.AttributeDefs.open_window_detection.name,
        RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="open_window_detection",
        fallback_name="Open window detection",
    )
    .switch(
        RtiTekTrvzbPrivateCluster.AttributeDefs.frost_protection_enabled.name,
        RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="frost_protection_enabled",
        fallback_name="Frost protection",
    )
    .enum(
        RtiTekTrvzbPrivateCluster.AttributeDefs.screen_brightness.name,
        RtiTekTrvzbScreenBrightness,
        RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="screen_brightness",
        fallback_name="Screen brightness",
    )
    .enum(
        RtiTekTrvzbPrivateCluster.AttributeDefs.screen_display_duration.name,
        RtiTekTrvzbScreenDisplayDuration,
        RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="screen_display_duration",
        fallback_name="Screen display duration",
    )
    .enum(
        RtiTekTrvzbPrivateCluster.AttributeDefs.boost_duration.name,
        RtiTekTrvzbBoostDuration,
        RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="boost_duration",
        fallback_name="Boost duration",
    )
    .enum(
        RtiTekTrvzbPrivateCluster.AttributeDefs.low_battery_valve_state.name,
        RtiTekTrvzbLowBatteryValveState,
        RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="low_battery_valve_state",
        fallback_name="Low battery valve state",
    )
    .sensor(
        RtiTekTrvzbPrivateCluster.AttributeDefs.window_state.name,
        RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        entity_type=EntityType.STANDARD,
        attribute_converter=_window_detection_status,
        translation_key="open_window_detected",
        fallback_name="Open window detected",
    )
    .sensor(
        RtiTekTrvzbPrivateCluster.AttributeDefs.valve_opening.name,
        RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        divisor=10,
        unit="%",
        translation_key="valve_opening",
        fallback_name="Valve opening",
    )
    .sensor(
        RtiTekTrvzbPrivateCluster.AttributeDefs.fault_code.name,
        RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        entity_type=EntityType.STANDARD,
        attribute_converter=_fault_code_status,
        translation_key="fault_code",
        fallback_name="Fault code",
    )
    .sensor(
        RtiTekTrvzbPrivateCluster.AttributeDefs.motor_travel_calibration_status.name,
        RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        entity_type=EntityType.STANDARD,
        attribute_converter=_motor_travel_calibration_status,
        translation_key="motor_travel_calibration_status",
        fallback_name="Valve calibration status",
    )
    .sensor(
        RtiTekTrvzbPrivateCluster.AttributeDefs.product_name.name,
        RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        entity_type=EntityType.STANDARD,
        translation_key="product_name",
        fallback_name="Product name",
    )
    .number(
        RtiTekTrvzbPrivateCluster.AttributeDefs.valve_switching_difference.name,
        RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        min_value=0.5,
        max_value=5.0,
        step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE_DELTA,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="valve_switching_difference",
        fallback_name="Valve switching difference",
    )
    .number(
        RtiTekTrvzbPrivateCluster.AttributeDefs.holiday_duration.name,
        RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_initialized_from_cache=False,
        min_value=0,
        max_value=60,
        step=1,
        unit=UnitOfTime.DAYS,
        multiplier=1 / 24,
        mode="slider",
        entity_type=EntityType.CONFIG,
        translation_key="holiday_duration",
        fallback_name="Holiday duration",
    )
    .enum(
        RtiTekTrvzbThermostat.AttributeDefs.system_mode.name,
        RtiTekTrvzbSystemMode,
        RtiTekTrvzbThermostat.cluster_id,
        translation_key="system_mode",
        fallback_name="System mode",
    )
    .number(
        RtiTekTrvzbThermostat.AttributeDefs.temporary_manual_temperature.name,
        RtiTekTrvzbThermostat.cluster_id,
        attribute_initialized_from_cache=True,
        min_value=5.0,
        max_value=30.0,
        step=0.5,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        mode="slider",
        entity_type=EntityType.CONFIG,
        translation_key="temporary_manual_temperature",
        fallback_name="Temporary manual temperature",
    )
    .sensor(
        RtiTekTrvzbThermostat.AttributeDefs.temporary_manual_state.name,
        RtiTekTrvzbThermostat.cluster_id,
        attribute_initialized_from_cache=True,
        entity_type=EntityType.STANDARD,
        attribute_converter=_temporary_manual_status,
        translation_key="temporary_manual_mode",
        fallback_name="Temporary manual mode",
    )
    .command_button(
        "schedule_apply",
        RtiTekTrvzbThermostat.cluster_id,
        unique_id_suffix="weekly_schedule_apply",
        translation_key="weekly_schedule_apply",
        fallback_name="Weekly schedule apply",
    )
    .command_button(
        "schedule_fetch",
        RtiTekTrvzbThermostat.cluster_id,
        unique_id_suffix="weekly_schedule_fetch",
        translation_key="weekly_schedule_fetch",
        fallback_name="Weekly schedule fetch",
    )
    .enum(
        RtiTekTrvzbThermostat.AttributeDefs.weekly_schedule_day.name,
        RtiTekTrvzbScheduleDay,
        RtiTekTrvzbThermostat.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="weekly_schedule_day",
        fallback_name="Weekly schedule day",
    )
    .write_attr_button(
        attribute_name=(
            RtiTekTrvzbPrivateCluster.AttributeDefs.motor_travel_calibration.name
        ),
        cluster_id=RtiTekTrvzbPrivateCluster.cluster_id,
        attribute_value=0x01,
        unique_id_suffix="start_motor_travel_calibration",
        translation_key="calibrate_valve",
        fallback_name="Calibrate valve",
    )
)

for _index in range(1, TRVZB_WEEKLY_SCHEDULE_MAX_PERIODS + 1):
    TRVZB_QUIRK_BUILDER = (
        TRVZB_QUIRK_BUILDER.enum(
            getattr(
                RtiTekTrvzbThermostat.AttributeDefs,
                f"weekly_schedule_period_{_index}_hour",
            ).name,
            RtiTekTrvzbScheduleHour,
            RtiTekTrvzbThermostat.cluster_id,
            attribute_initialized_from_cache=True,
            translation_key=f"weekly_schedule_period_{_index}_hour",
            fallback_name=f"Weekly schedule period {_index} hour",
        )
        .enum(
            getattr(
                RtiTekTrvzbThermostat.AttributeDefs,
                f"weekly_schedule_period_{_index}_minute",
            ).name,
            RtiTekTrvzbScheduleMinute,
            RtiTekTrvzbThermostat.cluster_id,
            attribute_initialized_from_cache=True,
            translation_key=f"weekly_schedule_period_{_index}_minute",
            fallback_name=f"Weekly schedule period {_index} minute",
        )
        .number(
            getattr(
                RtiTekTrvzbThermostat.AttributeDefs,
                f"weekly_schedule_period_{_index}_temperature",
            ).name,
            RtiTekTrvzbThermostat.cluster_id,
            attribute_initialized_from_cache=True,
            min_value=5.0,
            max_value=30.0,
            step=0.5,
            device_class=NumberDeviceClass.TEMPERATURE,
            unit=UnitOfTemperature.CELSIUS,
            multiplier=0.01,
            entity_type=EntityType.CONFIG,
            translation_key=f"weekly_schedule_period_{_index}_temperature",
            fallback_name=f"Weekly schedule period {_index} temperature",
        )
    )

TRVZB_QUIRK_BUILDER._add_entity_metadata(
    RtiTekTrvzbTemperatureControlModeMetadata(
        endpoint_id=1,
        cluster_id=RtiTekTrvzbPrivateCluster.cluster_id,
        entity_platform=EntityPlatform.SELECT,
        entity_type=EntityType.CONFIG,
        attribute_initialized_from_cache=False,
        translation_key="temperature_control_mode",
        translation_placeholders={},
        fallback_name="Temperature control mode",
        enum=RtiTekTrvzbTemperatureControlMode,
        attribute_name=(
            RtiTekTrvzbPrivateCluster.AttributeDefs.temperature_control_mode.name
        ),
    )
)

TRVZB_QUIRK_BUILDER._add_entity_metadata(
    RtiTekTrvzbScreenDirectionMetadata(
        endpoint_id=1,
        cluster_id=RtiTekTrvzbPrivateCluster.cluster_id,
        entity_platform=EntityPlatform.SELECT,
        entity_type=EntityType.CONFIG,
        attribute_initialized_from_cache=False,
        translation_key="screen_direction",
        translation_placeholders={},
        fallback_name="Screen direction",
        enum=RtiTekTrvzbScreenDirection,
        attribute_name=RtiTekTrvzbPrivateCluster.AttributeDefs.screen_direction.name,
    )
)

TRVZB_QUIRK_BUILDER.add_to_registry()
