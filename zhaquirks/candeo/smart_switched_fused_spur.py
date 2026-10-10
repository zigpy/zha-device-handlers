"""Candeo smart switched fused spur."""

from typing import Final

import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.builder import NumberDeviceClass, QuirkBuilder, UnitOfTime
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

    off = 0
    on = 1
    previous = 2


class CandeoSwitchedFusedSpurPreferencesCluster(LocalDataCluster):
    """Local ZHA preferences for the Candeo switched fused spur."""

    # Virtual local cluster. This does not represent a physical device cluster.
    cluster_id = 0xFBFE
    ep_attribute = "candeo_preferences"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        automatic_off_delay: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint16_t,
            access="rw",
        )

        enforce_child_lock: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
            access="rw",
        )

    _DEFAULT_VALUES = {
        AttributeDefs.automatic_off_delay.id: 0,
        AttributeDefs.enforce_child_lock.id: t.Bool.false,
    }


class CandeoSwitchedFusedSpurTimedOnOffCluster(CustomCluster, OnOff):
    """Candeo timed OnOff cluster."""

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
        self._automatic_off_delay = 0
        self._enforce_child_lock = False
        super().__init__(*args, **kwargs)

    async def apply_custom_configuration(self, *args, **kwargs):
        """Read custom attributes during pairing to populate their entities."""
        # These manufacturer-specific attributes are not part of the standard
        # OnOff cluster initialization reads, so explicitly read them during
        # configuration to populate their ZHA entities.
        await self.read_attributes(
            [
                self.AttributeDefs.child_lock.id,
                self.AttributeDefs.power_on_behaviour.id,
            ]
        )

    def _update_preferences(self):
        """Update preferences from the local ZHA preferences cluster."""
        cluster = self.endpoint.in_clusters.get(
            CandeoSwitchedFusedSpurPreferencesCluster.cluster_id
        )

        if cluster is None:
            self._automatic_off_delay = 0
            self._enforce_child_lock = False
            return

        self._automatic_off_delay = cluster.get(
            CandeoSwitchedFusedSpurPreferencesCluster.AttributeDefs.automatic_off_delay.id,
            0,
        )
        self._enforce_child_lock = cluster.get(
            CandeoSwitchedFusedSpurPreferencesCluster.AttributeDefs.enforce_child_lock.id,
            False,
        )

    async def on(self):
        """Turn the output on and apply automatic-off and lock preferences."""
        self._update_preferences()

        result = await self.command(self.commands_by_name["on"].id)

        if self._automatic_off_delay:
            # This device does not implement On With Timed Off according to
            # the ZCL specification. Instead, it toggles the output after the
            # requested delay and interprets the delay value as seconds.
            #
            # Send On first so the output is in a known ON state. The delayed
            # toggle will then always result in the output switching OFF.
            await self.command(
                self.commands_by_name["on_with_timed_off"].id,
                0x00,
                self._automatic_off_delay,
                0x00,
            )

        if self._enforce_child_lock:
            # The device clears child_lock after an On command. Restore it
            # when the ZHA-side enforce-child-lock preference is enabled.
            await self.write_attributes({self.AttributeDefs.child_lock.id: True})

        # child_lock does not support attribute reporting. Explicitly refresh
        # it after commands so the ZHA entity reflects the device's real state.
        await self.read_attributes([self.AttributeDefs.child_lock.id])

        # Follow-up operations are supplementary; return the primary command result.
        return result

    async def off(self):
        """Turn the output off and apply the child-lock preference."""
        self._update_preferences()

        result = await self.command(self.commands_by_name["off"].id)

        if self._enforce_child_lock:
            await self.write_attributes({self.AttributeDefs.child_lock.id: True})

        # child_lock does not support attribute reporting. Explicitly refresh
        # it after commands so the ZHA entity reflects the device's real state.
        await self.read_attributes([self.AttributeDefs.child_lock.id])

        return result


(
    QuirkBuilder(CANDEO, "C-ZB-SSFS")
    .adds(CandeoSwitchedFusedSpurPreferencesCluster)
    .replace_cluster_occurrences(CandeoSwitchedFusedSpurTimedOnOffCluster)
    .replace_cluster_occurrences(CandeoSwitchedFusedSpurElectricalMeasurement)
    .replace_cluster_occurrences(CandeoSwitchedFusedSpurMeteringCluster)
    .number(
        attribute_name=(
            CandeoSwitchedFusedSpurPreferencesCluster.AttributeDefs.automatic_off_delay.name
        ),
        cluster_id=CandeoSwitchedFusedSpurPreferencesCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=43200,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="automatic_off_delay",
        fallback_name="Automatic off delay",
    )
    .switch(
        attribute_name=(
            CandeoSwitchedFusedSpurTimedOnOffCluster.AttributeDefs.child_lock.name
        ),
        cluster_id=CandeoSwitchedFusedSpurTimedOnOffCluster.cluster_id,
        endpoint_id=1,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .enum(
        attribute_name=(
            CandeoSwitchedFusedSpurTimedOnOffCluster.AttributeDefs.power_on_behaviour.name
        ),
        cluster_id=CandeoSwitchedFusedSpurTimedOnOffCluster.cluster_id,
        endpoint_id=1,
        enum_class=CandeoPowerOnBehaviour,
        translation_key="power_on_behaviour",
        fallback_name="Power on behaviour",
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
