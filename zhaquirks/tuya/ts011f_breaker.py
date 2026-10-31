"""TS011F smart circuit breaker for ZHA.

This DIN-rail format contactor/switch is sold as a white-label product under various
brand names (Tongou, EARU, TOMZN, UNSH, Chayo). It is a contactor rated at up to 63A,
and while it offers software protection settings, suitable for secondary protection.

Matches the following DIN rail smart circuit breakers:
- _TZ3000_cayepv1a TS011F (Tongou TO-Q-SY2-163JZT / TO-Q-SY1-JZT)
- _TZ3000_lepzuhto TS011F (EARU EAKCB-T-M-Z 1P 63A)
- _TZ3000_zrm3oxsh TS011F (EARU EAYCBM 2P)
- _TZ3000_303avxxt TS011F (TOMZN TOB9Z-VAP)
- _TZ3000_ibefeicf TS011F (TOMZN TOB9Z-VAP)
- _TZ3000_qystbcjg TS011F (UNSH SMKG-1KNL-EU-Z)
- _TZ3000_zjchz7pd TS011F (Immax NEO 07573L)
- _TZ3000_zv6x8bt2 TS011F (Tuya DIN rail smart circuit breaker)

See also: https://github.com/Koenkk/zigbee-herdsman-converters/issues/10204


This ZHA quirk exposes the breaker's protection settings:
a threshold and an on/off "breaker" flag each for over-current, over-voltage,
under-voltage, temperature, and power.
The TOMZN TOB9Z-VAP breaker does not support temperature sensing.

Protocol details:
The protocol runs on cluster 0xE001 of endpoint 1 (verified on hardware):
- Settings are grouped under two command IDs:
  0xE7 = over-current, over-voltage, under-voltage
  0xE6 = temperature, power
- Each setting is a 4-byte record:
  [setting id, enabled, threshold high byte, threshold low byte]
- Writing a setting sends its group's command ID with a 4-byte record. The enabled
  flag and threshold always travel together.
- Querying a group sends its command ID with an empty payload.
- In both cases, the breaker responds with a report using the same command ID
  carrying all records in that group. Settings are not exposed as standard ZCL
  attributes, so these reports are the only source of truth.
- Entities are backed by a local cluster (0xFC70) holding the last reported state.
"""

import asyncio
from collections.abc import Iterator
from dataclasses import dataclass
import logging
import time
from typing import Any, Final

from zha.application.platforms.number.device_class import NumberDeviceClass
from zha.quirks import TUYA_PLUG_ONOFF
from zha.units import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
)
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks import LocalDataCluster
from zhaquirks.tuya import (
    TuyaZBE000Cluster,
    TuyaZBElectricalMeasurement,
    TuyaZBExternalSwitchTypeCluster,
    TuyaZBMeteringCluster,
    TuyaZBOnOffAttributeCluster,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder

_LOGGER = logging.getLogger(__name__)

CMD_OPTIONS_2: Final = 0xE6  # temperature, power
CMD_OPTIONS_3: Final = 0xE7  # over-current, over-voltage, under-voltage
PROTECTION_CLUSTER_ID: Final = 0xFC70  # local cluster, never sent on the wire
REFRESH_COOLDOWN: Final = 30.0  # seconds a successful refresh stays fresh
REPORT_TIMEOUT: Final = 5.0  # seconds to wait for the breaker's report
RAW_PAYLOAD: Final = {"data": t.Bytes}


@dataclass(frozen=True)
class Setting:
    """One protection setting: a threshold and the flag that arms it."""

    sid: int
    command_id: int
    name: str
    min_value: int
    max_value: int
    unit: str
    device_class: NumberDeviceClass

    @property
    def label(self) -> str:
        """Return the sentence-case name for entity labels."""
        return self.name.replace("_", "-").capitalize()


# Ranges match Zigbee2MQTT's TS011F_with_threshold converter, except the
# under-voltage maximum: the firmware rejects thresholds above 220 V.
SETTINGS: Final = (
    Setting(
        1,
        CMD_OPTIONS_3,
        "over_current",
        1,
        65,
        UnitOfElectricCurrent.AMPERE,
        NumberDeviceClass.CURRENT,
    ),
    Setting(
        3,
        CMD_OPTIONS_3,
        "over_voltage",
        90,
        265,
        UnitOfElectricPotential.VOLT,
        NumberDeviceClass.VOLTAGE,
    ),
    Setting(
        4,
        CMD_OPTIONS_3,
        "under_voltage",
        75,
        220,
        UnitOfElectricPotential.VOLT,
        NumberDeviceClass.VOLTAGE,
    ),
    Setting(
        5,
        CMD_OPTIONS_2,
        "temperature",
        40,
        100,
        UnitOfTemperature.CELSIUS,
        NumberDeviceClass.TEMPERATURE,
    ),
    Setting(
        7,
        CMD_OPTIONS_2,
        "power",
        1,
        26,
        UnitOfPower.KILO_WATT,
        NumberDeviceClass.POWER,
    ),
)
SETTINGS_BY_ID: Final = {setting.sid: setting for setting in SETTINGS}
SETTINGS_BY_NAME: Final = {setting.name: setting for setting in SETTINGS}


def encode_record(setting: Setting, enabled: bool, threshold: int) -> bytes:
    """Build the 4-byte record that writes one setting."""
    return bytes([setting.sid, enabled]) + threshold.to_bytes(2, "big")


def decode_records(data: bytes) -> Iterator[tuple[int, bool, int]]:
    """Yield (setting id, enabled, threshold) for each 4-byte record in a report."""
    for offset in range(0, len(data) - 3, 4):
        sid, enabled = data[offset], data[offset + 1]
        yield sid, bool(enabled), int.from_bytes(data[offset + 2 : offset + 4], "big")


class TongouThresholdCluster(TuyaZBExternalSwitchTypeCluster):
    """Cluster 0xE001: stock external switch type attribute plus protection commands."""

    class ServerCommandDefs(BaseCommandDefs):
        """Commands to the breaker: one record to write, empty payload to query."""

        set_options_2: Final = ZCLCommandDef(id=CMD_OPTIONS_2, schema=RAW_PAYLOAD)
        set_options_3: Final = ZCLCommandDef(id=CMD_OPTIONS_3, schema=RAW_PAYLOAD)

    class ClientCommandDefs(BaseCommandDefs):
        """Reports from the breaker: every record of the group."""

        options_2_report: Final = ZCLCommandDef(id=CMD_OPTIONS_2, schema=RAW_PAYLOAD)
        options_3_report: Final = ZCLCommandDef(id=CMD_OPTIONS_3, schema=RAW_PAYLOAD)

    async def send_options(self, command_id: int, payload: bytes = b"") -> None:
        """Send a write (one record) or a query (no payload) to the breaker."""
        reply = await self.command(command_id, payload)
        client_cmds = TongouThresholdCluster.ClientCommandDefs
        expected_schema = (
            client_cmds.options_2_report.schema
            if command_id == CMD_OPTIONS_2
            else client_cmds.options_3_report.schema
        )
        if isinstance(reply, expected_schema):
            self._deliver_report(command_id, reply.data)

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Any,
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Forward settings reports to the protection cluster."""
        if hdr.command_id in (CMD_OPTIONS_2, CMD_OPTIONS_3):
            self._deliver_report(hdr.command_id, args.data)
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

    def _deliver_report(self, command_id: int, data: bytes) -> None:
        """Hand a report's payload to the protection cluster."""
        protection = self.endpoint.in_clusters[PROTECTION_CLUSTER_ID]
        protection.report_received(command_id, bytes(data))


class TongouProtectionCluster(LocalDataCluster):
    """Local cluster 0xFC70: protection settings exposed as standard ZCL attributes.

    Attribute values are populated strictly from the breaker's own reports, never
    optimistically from writes, so entities reflect confirmed hardware state.
    """

    cluster_id = PROTECTION_CLUSTER_ID
    name = "TongouProtection"
    ep_attribute = "tongou_protection"

    class AttributeDefs(BaseAttributeDefs):
        """One threshold and one enabled flag per setting."""

        over_current_threshold: Final = ZCLAttributeDef(id=0x0001, type=t.uint16_t)
        over_current_enabled: Final = ZCLAttributeDef(id=0x0002, type=t.Bool)
        over_voltage_threshold: Final = ZCLAttributeDef(id=0x0003, type=t.uint16_t)
        over_voltage_enabled: Final = ZCLAttributeDef(id=0x0004, type=t.Bool)
        under_voltage_threshold: Final = ZCLAttributeDef(id=0x0005, type=t.uint16_t)
        under_voltage_enabled: Final = ZCLAttributeDef(id=0x0006, type=t.Bool)
        temperature_threshold: Final = ZCLAttributeDef(id=0x0007, type=t.uint16_t)
        temperature_enabled: Final = ZCLAttributeDef(id=0x0008, type=t.Bool)
        power_threshold: Final = ZCLAttributeDef(id=0x0009, type=t.uint16_t)
        power_enabled: Final = ZCLAttributeDef(id=0x000A, type=t.Bool)

    # Unreported attributes are unknown (None), not unsupported.
    _VALID_ATTRIBUTES = {attribute.id for attribute in AttributeDefs}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize synchronization primitives for serializing breaker access."""
        super().__init__(*args, **kwargs)
        self._lock = asyncio.Lock()
        self._report_arrived = {
            CMD_OPTIONS_2: asyncio.Event(),
            CMD_OPTIONS_3: asyncio.Event(),
        }
        self._refresh_task: asyncio.Task[None] | None = None
        self._last_refresh = float("-inf")

    def report_received(self, command_id: int, data: bytes) -> None:
        """Store every setting decoded from a breaker report."""
        for sid, enabled, threshold in decode_records(data):
            setting = SETTINGS_BY_ID.get(sid)
            _LOGGER.debug(
                "Tongou breaker report: setting=%s (%s) enabled=%s threshold=%s",
                sid,
                setting.name if setting else "unknown",
                enabled,
                threshold,
            )
            if setting is None:
                continue
            self._update_attribute(
                self.find_attribute(f"{setting.name}_enabled").id, enabled
            )
            self._update_attribute(
                self.find_attribute(f"{setting.name}_threshold").id, threshold
            )
        if command_id in self._report_arrived:
            self._report_arrived[command_id].set()

    def _last_reported(self, setting: Setting) -> tuple[bool, int] | None:
        """Return (enabled, threshold) as last reported, or None if unknown."""
        enabled = self.get(f"{setting.name}_enabled")
        threshold = self.get(f"{setting.name}_threshold")
        if enabled is None or threshold is None:
            return None
        return bool(enabled), int(threshold)

    async def _exchange(self, command_id: int, payload: bytes = b"") -> None:
        """Send a write or query and wait for the corresponding report.

        The caller must hold self._lock.
        """
        arrived = self._report_arrived[command_id]
        arrived.clear()
        thresholds = self.endpoint.in_clusters[TongouThresholdCluster.cluster_id]
        await thresholds.send_options(command_id, payload)
        try:
            await asyncio.wait_for(arrived.wait(), REPORT_TIMEOUT)
        except TimeoutError:
            raise TimeoutError(
                f"no report from the breaker after command 0x{command_id:02X}"
            ) from None

    async def _refresh(self) -> None:
        """Query both option groups so cached attributes match the breaker."""
        async with self._lock:
            try:
                for command_id in (CMD_OPTIONS_3, CMD_OPTIONS_2):
                    await self._exchange(command_id)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Tongou breaker: reading settings failed: %r", exc)
            else:
                self._last_refresh = time.monotonic()

    async def read_attributes(
        self, attributes: list[int | str], *args: Any, **kwargs: Any
    ) -> Any:
        """Return cached attributes and trigger a background refresh if stale."""
        refreshing = self._refresh_task is not None and not self._refresh_task.done()
        if not refreshing and time.monotonic() - self._last_refresh >= REFRESH_COOLDOWN:
            self._refresh_task = asyncio.create_task(self._refresh())
        return await super().read_attributes(attributes, *args, **kwargs)

    async def _write(self, attribute_name: str, new_value: Any) -> None:
        """Modify one component of a setting and wait for hardware confirmation."""
        name, _, field = attribute_name.rpartition("_")
        setting = SETTINGS_BY_NAME[name]
        if field == "threshold":
            new_value = int(new_value)
            if not setting.min_value <= new_value <= setting.max_value:
                raise ValueError(
                    f"{new_value} is outside {setting.min_value} to "
                    f"{setting.max_value} {setting.unit}"
                )

        async with self._lock:
            if self._last_reported(setting) is None:
                await self._exchange(setting.command_id)
            current = self._last_reported(setting)
            if current is None:
                raise ValueError("the breaker does not report this setting")

            enabled, threshold = current
            if field == "threshold":
                threshold = new_value
            else:
                enabled = bool(new_value)
            wanted = (enabled, threshold)

            await self._exchange(setting.command_id, encode_record(setting, *wanted))
            current = self._last_reported(setting)
            if current != wanted:
                raise ValueError(
                    f"the breaker reports (enabled, threshold) = {current}, "
                    f"not {wanted}"
                )

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer: int | t.uint16_t | None = None,
        **kwargs: Any,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Write attributes to the breaker as 0xE6/0xE7 commands."""
        records = []
        for attribute, value in attributes.items():
            attr_def = self.find_attribute(attribute)
            status = foundation.Status.SUCCESS
            try:
                await self._write(attr_def.name, value)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning(
                    "Tongou breaker: writing %s=%r failed: %r",
                    attr_def.name,
                    value,
                    exc,
                )
                status = foundation.Status.FAILURE
            records.append(foundation.WriteAttributesStatusRecord(status, attr_def.id))
        return [records]


builder = (
    TuyaQuirkBuilder("_TZ3000_cayepv1a", "TS011F")
    .applies_to("_TZ3000_lepzuhto", "TS011F")
    .applies_to("_TZ3000_zrm3oxsh", "TS011F")
    .applies_to("_TZ3000_303avxxt", "TS011F")
    .applies_to("_TZ3000_ibefeicf", "TS011F")
    .applies_to("_TZ3000_qystbcjg", "TS011F")
    .applies_to("_TZ3000_zjchz7pd", "TS011F")
    .applies_to("_TZ3000_zv6x8bt2", "TS011F")
    .tuya_enchantment()
    .replaces(TuyaZBOnOffAttributeCluster)
    .replaces(TuyaZBMeteringCluster)
    .replaces(TuyaZBElectricalMeasurement)
    .replaces(TuyaZBE000Cluster)
    .replaces(TongouThresholdCluster)
    .adds(TongouProtectionCluster)
    .exposes_feature(TUYA_PLUG_ONOFF)
)

for _setting in SETTINGS:
    builder = builder.number(
        f"{_setting.name}_threshold",
        TongouProtectionCluster.cluster_id,
        min_value=_setting.min_value,
        max_value=_setting.max_value,
        step=1,
        unit=_setting.unit,
        device_class=_setting.device_class,
        translation_key=f"{_setting.name}_threshold",
        fallback_name=f"{_setting.label} threshold",
    ).switch(
        f"{_setting.name}_enabled",
        TongouProtectionCluster.cluster_id,
        translation_key=f"{_setting.name}_breaker",
        fallback_name=f"{_setting.label} breaker",
    )

builder.add_to_registry()
