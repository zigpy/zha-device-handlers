"""Bosch smoke alarm II (BSD-2, RBSH-SD-ZB-EU): sirens, test mode, diagnostics.

Mirrors the Zigbee2MQTT definition (boschSmokeAlarmExtend in
zigbee-herdsman-converters). The device sounds a manual alarm through a Bosch
manufacturer specific command, and reports a few non-standard bits of the IAS Zone
status, so ZHA has nothing for them out of the box.

The device has no IAS WD (warning device) cluster, which ZHA needs for a siren entity.
So the quirk adds a local one on two extra endpoints, one per alarm mode: endpoint 2
sounds the smoke alarm and endpoint 3 the burglar alarm. ZHA turns them into two basic
sirens (turn on with a duration, turn off), like the ones of the frient sensors, and
the local cluster turns ZHA's warning commands into the Bosch alarm command.

Zone status bits (Bosch specific, from the Z2M definition):
- bit 0: smoke detected (handled by ZHA's own smoke sensor, together with bit 1)
- bit 1: smoke alarm sounded manually (alarm_control command, mode smoke)
- bit 3: battery low (not exposed, the battery percentage sensor covers it)
- bit 7: burglar alarm sounded manually (alarm_control command, mode burglar)
- bit 8: the button on the device is held for 3 seconds or more (not exposed)
- bit 10: test mode active
- bit 11: smoke alarm silenced on the device itself for 10 minutes

ZHA's smoke sensor treats bit 1 as a smoke alarm too, so sounding the smoke siren
turns the smoke sensor on. Z2M only looks at bit 0.
"""

import asyncio
from typing import Any, Final

from zha.quirks import SIREN_BASIC
from zigpy import types as t
from zigpy.exceptions import ZigbeeException
from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasWd, IasZone, WarningMode, WarningType
from zigpy.zcl.foundation import ZCLAttributeDef, ZCLCommandDef

from zhaquirks import LocalDataCluster
from zhaquirks.builder import EntityType, QuirkBuilder, UnitOfTime
from zhaquirks.clusters import CustomCluster

MODEL = "RBSH-SD-ZB-EU"
BOSCH_MFG_CODE = 0x1209

# Manufacturer specific command of the IAS Zone cluster that sounds or stops an alarm
CMD_ALARM_CONTROL = 0x80

# Longest alarm in seconds, what Bosch and Z2M use. The device stops it by itself then
MAX_ALARM_TIMEOUT = 240

# Sleepy devices miss broadcasts, so the broadcast is sent twice like Bosch and Z2M do
BROADCAST_REPEAT_DELAY = 4
BROADCAST_SRC_ENDPOINT = 1
BROADCAST_DST_ENDPOINT = 0xFF
BROADCAST_RADIUS = 30

# Sensitivity level sent with the test mode command, 0 is the manufacturer default
TEST_MODE_SENSITIVITY = 0
TEST_MODE_DEFAULT_TIMEOUT = 5

BIT_MANUAL_SMOKE = 1 << 1
BIT_MANUAL_BURGLAR = 1 << 7
BIT_TEST_MODE = 1 << 10
BIT_SMOKE_SILENCED = 1 << 11

# Local attributes, never read from or written to the device. Their state follows the
# zone status bits or is a setting, and writing them sends the matching command. The ids
# 0xF000 and 0xF001 were used by an earlier version, so they stay unused
ATTR_BROADCAST_ALARMS = 0xF002
ATTR_TEST_MODE = 0xF003
ATTR_TEST_MODE_TIMEOUT = 0xF004

# Endpoints that the quirk adds for the sirens
SMOKE_SIREN_ENDPOINT = 2
BURGLAR_SIREN_ENDPOINT = 3


class BoschAlarmMode(t.enum8):
    """Alarm modes of the alarm_control command, each with its own sound."""

    Smoke = 0x00
    Burglar = 0x01


class BoschSmokeAlarmIasZone(CustomCluster, IasZone):
    """IAS Zone cluster of the BSD-2 with local attributes for the settings."""

    class AttributeDefs(IasZone.AttributeDefs):
        """Local attributes added to the IAS Zone attributes."""

        broadcast_alarms: Final = ZCLAttributeDef(
            id=ATTR_BROADCAST_ALARMS, type=t.Bool, access="rw"
        )
        test_mode: Final = ZCLAttributeDef(id=ATTR_TEST_MODE, type=t.Bool, access="rw")
        # Seconds
        test_mode_timeout: Final = ZCLAttributeDef(
            id=ATTR_TEST_MODE_TIMEOUT, type=t.uint8_t, access="rw"
        )

    class ServerCommandDefs(IasZone.ServerCommandDefs):
        """Bosch manufacturer specific command added to the IAS Zone commands."""

        alarm_control: Final = ZCLCommandDef(
            id=CMD_ALARM_CONTROL,
            schema={"alarm_mode": BoschAlarmMode, "alarm_timeout": t.uint8_t},
            is_manufacturer_specific=True,
        )

    # Values of the local attributes until they are set or reported, by attribute id
    _DEFAULT_VALUES: dict[int, Any] = {
        ATTR_BROADCAST_ALARMS: t.Bool(True),
        ATTR_TEST_MODE: t.Bool(False),
        ATTR_TEST_MODE_TIMEOUT: TEST_MODE_DEFAULT_TIMEOUT,
    }

    def get(self, key: int | str, default: Any | None = None) -> Any:
        """Return the cached value, falling back to the default of a local attribute."""
        attr_def = self.find_attribute(key)
        value = super().get(key)
        if value is None:
            return self._DEFAULT_VALUES.get(attr_def.id, default)
        return value

    def _update_attribute(self, attrid: Any, value: Any) -> None:
        """Derive the test mode from the bits of a new zone status."""
        super()._update_attribute(attrid, value)

        if isinstance(attrid, foundation.ZCLAttributeDef):
            attrid = attrid.id
        if attrid != IasZone.AttributeDefs.zone_status.id or value is None:
            return

        self.update_attribute(ATTR_TEST_MODE, t.Bool(bool(int(value) & BIT_TEST_MODE)))

    async def _broadcast_alarm(self, mode: BoschAlarmMode, timeout: int) -> None:
        """Send the alarm_control command as a broadcast to every device."""
        app = self.endpoint.device.application
        tsn = app.get_sequence()
        header = foundation.ZCLHeader(
            frame_control=foundation.FrameControl(
                frame_type=foundation.FrameType.CLUSTER_COMMAND,
                is_manufacturer_specific=True,
                direction=foundation.Direction.Client_to_Server,
                disable_default_response=True,
                reserved=0,
            ),
            manufacturer=BOSCH_MFG_CODE,
            tsn=tsn,
            command_id=CMD_ALARM_CONTROL,
        )
        await app.broadcast(
            profile=zha.PROFILE_ID,
            cluster=self.cluster_id,
            src_ep=BROADCAST_SRC_ENDPOINT,
            dst_ep=BROADCAST_DST_ENDPOINT,
            grpid=0,
            radius=BROADCAST_RADIUS,
            sequence=tsn,
            data=header.serialize() + bytes([mode, timeout]),
            broadcast_address=t.BroadcastAddress.ALL_DEVICES,
        )

    async def _broadcast_again(self, mode: BoschAlarmMode, timeout: int) -> None:
        """Send the broadcast again, for sleepy devices that missed the first one."""
        await asyncio.sleep(BROADCAST_REPEAT_DELAY)
        try:
            await self._broadcast_alarm(mode, timeout)
        except (ZigbeeException, TimeoutError) as err:
            self.warning("Repeating the alarm broadcast failed: %s", err)

    async def set_alarm(self, mode: BoschAlarmMode, timeout: int) -> None:
        """Sound the alarm of a mode for a number of seconds, 0 stops it.

        The command goes to this device, or to every device when broadcasting. Raises
        when it could not be sent, so the siren does not show a sounding alarm.
        """
        if self.get(ATTR_BROADCAST_ALARMS):
            try:
                await self._broadcast_alarm(mode, timeout)
            except (ZigbeeException, TimeoutError) as err:
                raise ZigbeeException(f"Alarm broadcast failed: {err}") from err
            self.create_catching_task(self._broadcast_again(mode, timeout))
            return

        result = await self.alarm_control(
            alarm_mode=mode, alarm_timeout=timeout, manufacturer=BOSCH_MFG_CODE
        )
        status = getattr(result, "status", foundation.Status.SUCCESS)
        if status != foundation.Status.SUCCESS:
            raise ZigbeeException(f"The device refused the alarm command: {status}")

    async def _set_test_mode(self, on: bool) -> foundation.Status:
        """Start the test mode for the set timeout, or end it."""
        if on:
            result = await self.init_test_mode(
                test_mode_duration=self.get(ATTR_TEST_MODE_TIMEOUT),
                current_zone_sensitivity_level=TEST_MODE_SENSITIVITY,
            )
        else:
            result = await self.init_normal_op_mode()
        return getattr(result, "status", foundation.Status.SUCCESS)

    async def _write_local_attribute(
        self, attr_id: int, value: Any
    ) -> foundation.Status:
        """Send the command for a write to a local attribute and update the cache."""
        status = foundation.Status.SUCCESS

        if attr_id == ATTR_TEST_MODE:
            status = await self._set_test_mode(bool(value))

        if status == foundation.Status.SUCCESS:
            self.update_attribute(attr_id, value)
        return status

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        *args,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Turn writes to the local attributes into commands."""
        local: dict[int, Any] = {}
        remote: dict[str | int | foundation.ZCLAttributeDef, Any] = {}
        for attribute, value in attributes.items():
            attr_def = self.find_attribute(attribute)
            if attr_def.id in self._DEFAULT_VALUES:
                local[attr_def.id] = attr_def.type(value)
            else:
                remote[attribute] = value

        if not local:
            return await super().write_attributes(attributes, *args, **kwargs)

        records: list[foundation.WriteAttributesStatusRecord] = []
        if remote:
            result = await super().write_attributes(remote, *args, **kwargs)
            records.extend(result[0])

        for attr_id, value in local.items():
            status = await self._write_local_attribute(attr_id, value)
            records.append(foundation.WriteAttributesStatusRecord(status, attr_id))

        return [records]


class BoschAlarmSiren(LocalDataCluster, IasWd):
    """IAS WD cluster that the device does not have, for the siren of one alarm mode.

    ZHA sends its siren commands to this cluster. They are turned into the alarm command
    of the IAS Zone cluster on endpoint 1 for the alarm mode of this subclass, so the
    tone and level that ZHA sends have no meaning here.
    """

    alarm_mode: BoschAlarmMode

    async def start_warning(
        self, warning: WarningType, warning_duration: int, **kwargs: Any
    ) -> None:
        """Sound the alarm for the duration, or stop it."""
        timeout = 0
        if warning.mode != WarningMode.Stop:
            timeout = min(max(int(warning_duration), 1), MAX_ALARM_TIMEOUT)

        ias_zone = self.endpoint.device.endpoints[1].ias_zone
        await ias_zone.set_alarm(self.alarm_mode, timeout)

    async def squawk(self, *args: Any, **kwargs: Any) -> None:
        """Raise, because the device cannot squawk."""
        raise ZigbeeException("The BSD-2 does not support squawking")


class BoschSmokeSiren(BoschAlarmSiren):
    """Siren that sounds the smoke alarm."""

    alarm_mode = BoschAlarmMode.Smoke


class BoschBurglarSiren(BoschAlarmSiren):
    """Siren that sounds the burglar alarm."""

    alarm_mode = BoschAlarmMode.Burglar


def zone_status_bit(mask: int):
    """Return a converter that reads one bit of the zone status."""

    def convert(value: int) -> bool:
        return bool(int(value) & mask)

    return convert


(
    QuirkBuilder("Bosch", MODEL)
    .applies_to("BOSCH", MODEL)
    # Bosch's product code instead of the Zigbee model string, like Z2M's model id
    .friendly_name(model="BSD-2", manufacturer="Bosch")
    .replaces(BoschSmokeAlarmIasZone)
    .adds_endpoint(SMOKE_SIREN_ENDPOINT, device_type=zha.DeviceType.IAS_WARNING_DEVICE)
    .adds_endpoint(
        BURGLAR_SIREN_ENDPOINT, device_type=zha.DeviceType.IAS_WARNING_DEVICE
    )
    .adds(BoschSmokeSiren, endpoint_id=SMOKE_SIREN_ENDPOINT)
    .adds(BoschBurglarSiren, endpoint_id=BURGLAR_SIREN_ENDPOINT)
    # Basic sirens: turn on with a duration and turn off, no tones or volume
    .exposes_feature(SIREN_BASIC)
    # The smoke sensor stays the primary entity, the sirens are configuration like the
    # ones of the frient sensors
    .change_entity_metadata(
        endpoint_id=SMOKE_SIREN_ENDPOINT,
        cluster_id=IasWd.cluster_id,
        new_primary=False,
        new_entity_category=EntityType.CONFIG,
        new_fallback_name="Smoke siren",
    )
    .change_entity_metadata(
        endpoint_id=BURGLAR_SIREN_ENDPOINT,
        cluster_id=IasWd.cluster_id,
        new_primary=False,
        new_entity_category=EntityType.CONFIG,
        new_fallback_name="Burglar siren",
    )
    .switch(
        BoschSmokeAlarmIasZone.AttributeDefs.broadcast_alarms.name,
        BoschSmokeAlarmIasZone.cluster_id,
        entity_type=EntityType.CONFIG,
        # Core's key for interlinked alarms, which brings its name and shield icon
        translation_key="linkage_alarm",
        fallback_name="Linkage alarm",
    )
    .switch(
        BoschSmokeAlarmIasZone.AttributeDefs.test_mode.name,
        BoschSmokeAlarmIasZone.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="test_mode",
        fallback_name="Test mode",
    )
    .number(
        BoschSmokeAlarmIasZone.AttributeDefs.test_mode_timeout.name,
        BoschSmokeAlarmIasZone.cluster_id,
        min_value=1,
        max_value=255,
        step=1,
        unit=UnitOfTime.SECONDS,
        entity_type=EntityType.CONFIG,
        translation_key="test_mode_timeout",
        fallback_name="Test mode timeout",
    )
    .binary_sensor(
        IasZone.AttributeDefs.zone_status.name,
        BoschSmokeAlarmIasZone.cluster_id,
        attribute_converter=zone_status_bit(BIT_MANUAL_SMOKE),
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix="manual_smoke_alarm",
        translation_key="manual_smoke_alarm",
        fallback_name="Manual smoke alarm",
    )
    .binary_sensor(
        IasZone.AttributeDefs.zone_status.name,
        BoschSmokeAlarmIasZone.cluster_id,
        attribute_converter=zone_status_bit(BIT_MANUAL_BURGLAR),
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix="manual_burglar_alarm",
        translation_key="manual_burglar_alarm",
        fallback_name="Manual burglar alarm",
    )
    .binary_sensor(
        IasZone.AttributeDefs.zone_status.name,
        BoschSmokeAlarmIasZone.cluster_id,
        attribute_converter=zone_status_bit(BIT_SMOKE_SILENCED),
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix="smoke_alarm_silenced",
        translation_key="smoke_alarm_silenced",
        fallback_name="Smoke alarm silenced",
    )
    .add_to_registry()
)
