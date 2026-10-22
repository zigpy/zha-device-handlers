"""Candeo smart switched fused spur."""

from typing import Final

import zigpy.types as t
from zigpy.zcl import AttributeReportedEvent
from zigpy.zcl.clusters.general import OnOff, OnOffControl
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import BaseAttributeDefs, Status, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.builder import QuirkBuilder
from zhaquirks.candeo import CANDEO
from zhaquirks.clusters import CustomCluster


class CandeoSwitchedFusedSpurElectricalMeasurement(
    CustomCluster, ElectricalMeasurement
):
    """Set divisor and multiplier attributes missing on the device."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
    }


class CandeoSwitchedFusedSpurMeteringCluster(CustomCluster, Metering):
    """Set divisor and multiplier attributes missing on the device."""

    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.multiplier.id: 1,
        Metering.AttributeDefs.divisor.id: 100,
    }


class CandeoPowerOnBehaviour(t.enum8):
    """Candeo power-on behaviour."""

    Off = 0
    On = 1
    Previous = 2


class CandeoSwitchedFusedSpurPreferencesCluster(LocalDataCluster):
    """Local ZHA preferences for the Candeo switched fused spur."""

    # Virtual local cluster. This does not represent a physical device cluster.
    cluster_id = 0xFBFE
    ep_attribute = "candeo_preferences"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        enforce_child_lock: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.Bool,
            access="rw",
        )

    _DEFAULT_VALUES = {
        AttributeDefs.enforce_child_lock.id: t.Bool.false,
    }


class CandeoSwitchedFusedSpurOnOffCluster(CustomCluster, OnOff):
    """Candeo OnOff cluster."""

    class AttributeDefs(OnOff.AttributeDefs):
        """Attribute definitions."""

        child_lock: Final = ZCLAttributeDef(
            id=0x8000,
            type=t.Bool,
            access="rw",
            manufacturer_code=0x1141,
        )

        power_on_behaviour: Final = ZCLAttributeDef(
            id=0x8002,
            type=CandeoPowerOnBehaviour,
            access="rw",
            manufacturer_code=0x1141,
        )

    def __init__(self, *args, **kwargs):
        """Initialize."""
        super().__init__(*args, **kwargs)
        self.on_event(
            AttributeReportedEvent.event_type,
            self._handle_attribute_report,
        )

    def _handle_attribute_report(self, event: AttributeReportedEvent) -> None:
        """Handle attribute reports from the device."""
        if event.attribute_id == OnOff.AttributeDefs.on_off.id:
            self.create_catching_task(self._handle_output_state_update())

    async def command(
        self,
        command_id,
        *args,
        manufacturer=None,
        expect_reply=True,
        tsn=None,
        **kwargs,
    ):
        """Override On With Timed Off for the device's non-standard behaviour."""
        if command_id != OnOff.ServerCommandDefs.on_with_timed_off.id:
            return await super().command(
                command_id,
                *args,
                manufacturer=manufacturer,
                expect_reply=expect_reply,
                tsn=tsn,
                **kwargs,
            )

        # Honour the standard Accept Only When On control bit. The workaround
        # below sends On before On With Timed Off, so an Accept Only When On
        # request must be discarded here if the device is currently off.
        on_off_control = args[0] if args else kwargs.get("on_off_control", 0)

        if OnOffControl(on_off_control) & OnOffControl.Accept_Only_When_On:
            on_off = self.get(OnOff.AttributeDefs.on_off.id)

            # If the current output state is not cached, read it from the
            # device before deciding whether to discard the command.
            if on_off is None:
                success, _ = await self.read_attributes(
                    [OnOff.AttributeDefs.on_off.id]
                )
                on_off = success.get(OnOff.AttributeDefs.on_off.id)

            if not on_off:
                return None

        # on_time may be supplied positionally or by keyword.
        if len(args) >= 2:
            on_time = args[1]
        else:
            on_time = kwargs["on_time"]

        # Remove command parameters because the translated command below supplies
        # its own values. Preserve any request-level keyword arguments.
        request_kwargs = kwargs.copy()
        request_kwargs.pop("on_off_control", None)
        request_kwargs.pop("on_time", None)
        request_kwargs.pop("off_wait_time", None)

        # This device does not implement On With Timed Off according to the ZCL
        # specification. Instead, it toggles the output after the requested
        # delay and interprets the raw on_time value as seconds rather than
        # tenths of a second.
        #
        # Send On first so the output is in a known ON state. The delayed
        # toggle will then always result in the output switching OFF.
        on_result = await super().command(
            OnOff.ServerCommandDefs.on.id,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            **request_kwargs,
        )

        # Do not send the timed command if the prerequisite On command failed.
        if getattr(on_result, "status", Status.SUCCESS) != Status.SUCCESS:
            return on_result

        # This workaround implements the automatic-off behaviour exposed by
        # the product. Force on_off_control and off_wait_time to zero and
        # translate on_time for this device's firmware.
        #
        # Standard ZCL on_time is expressed in tenths of a second. This device
        # incorrectly interprets the raw value as whole seconds. Preserve zero
        # and round positive durations up to the nearest whole second.
        device_on_time = 0 if int(on_time) == 0 else (int(on_time) + 9) // 10

        return await super().command(
            OnOff.ServerCommandDefs.on_with_timed_off.id,
            0x00,
            device_on_time,
            0x00,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **request_kwargs,
        )

    def _enforce_child_lock_enabled(self) -> bool:
        """Return whether persistent child-lock enforcement is enabled."""
        preferences = self.endpoint.in_clusters.get(
            CandeoSwitchedFusedSpurPreferencesCluster.cluster_id
        )

        if preferences is None:
            return False

        return bool(
            preferences.get(
                CandeoSwitchedFusedSpurPreferencesCluster.AttributeDefs.enforce_child_lock.id,
                False,
            )
        )

    async def _handle_output_state_update(self):
        """Refresh or restore child lock after an output state update."""
        # child_lock does not support attribute reporting. Explicitly refresh
        # it after output updates so the ZHA entity reflects the real state.
        try:
            success, _ = await self.read_attributes([self.AttributeDefs.child_lock.id])
        except Exception as exc:
            self.warning("Failed to refresh child lock state: %s", exc)
            return

        child_lock = success.get(self.AttributeDefs.child_lock.id)

        # The device can clear child_lock when its output is operated. Restore
        # it only when enforcement is enabled and it actually reads back off.
        if self._enforce_child_lock_enabled() and child_lock == t.Bool.false:
            try:
                await self.write_attributes(
                    {self.AttributeDefs.child_lock.id: True}
                )
            except Exception as exc:
                self.warning("Failed to restore child lock: %s", exc)


(
    QuirkBuilder(CANDEO, "C-ZB-SSFS")
    .adds(CandeoSwitchedFusedSpurPreferencesCluster)
    .replace_cluster_occurrences(CandeoSwitchedFusedSpurOnOffCluster)
    .replace_cluster_occurrences(CandeoSwitchedFusedSpurElectricalMeasurement)
    .replace_cluster_occurrences(CandeoSwitchedFusedSpurMeteringCluster)
    .switch(
        attribute_name=(
            CandeoSwitchedFusedSpurOnOffCluster.AttributeDefs.child_lock.name
        ),
        cluster_id=CandeoSwitchedFusedSpurOnOffCluster.cluster_id,
        endpoint_id=1,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .enum(
        attribute_name=(
            CandeoSwitchedFusedSpurOnOffCluster.AttributeDefs.power_on_behaviour.name
        ),
        cluster_id=CandeoSwitchedFusedSpurOnOffCluster.cluster_id,
        endpoint_id=1,
        enum_class=CandeoPowerOnBehaviour,
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .switch(
        attribute_name=(
            CandeoSwitchedFusedSpurPreferencesCluster.AttributeDefs.enforce_child_lock.name
        ),
        cluster_id=CandeoSwitchedFusedSpurPreferencesCluster.cluster_id,
        endpoint_id=1,
        translation_key="enforce_child_lock",
        fallback_name="Enforce child lock",
    )
    .add_to_registry()
)
