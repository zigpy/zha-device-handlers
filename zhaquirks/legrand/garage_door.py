"""Quirk for the Legrand/Netatmo NLJ garage-door module.

Exposes the proprietary ``movingState`` attribute as a diagnostic enum sensor.
The native ZHA cover is left unchanged; users can combine both entities with
a Home Assistant template cover to expose transient ``opening`` and ``closing``
states.
"""

from zha.application import EntityPlatform, EntityType
import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.legrand import LEGRAND


class MovingState(t.enum8):
    """Legrand manufacturer-specific Window Covering moving state."""

    stopped = 0
    closing = 1
    opening = 2


class LegrandNLJWindowCoveringCluster(CustomCluster, WindowCovering):
    """Window Covering cluster with Legrand's moving-state attribute."""

    class AttributeDefs(WindowCovering.AttributeDefs):
        """Cluster attributes."""

        moving_state = ZCLAttributeDef(
            id=0xF007,
            type=MovingState,
            access="rp",
            is_manufacturer_specific=True,
        )

    @classmethod
    def find_attribute(
        cls,
        name_or_id,
        *,
        manufacturer_code: int | UndefinedType | None = UNDEFINED,
    ):
        """Accept the NLJ's non-compliant global reports for moving state only."""
        if (
            manufacturer_code is None
            and name_or_id == cls.AttributeDefs.moving_state.id
        ):
            return cls.AttributeDefs.moving_state
        return super().find_attribute(name_or_id, manufacturer_code=manufacturer_code)


(
    QuirkBuilder(f" {LEGRAND}", " NLJ - Garage door")
    .replaces(LegrandNLJWindowCoveringCluster, endpoint_id=1)
    .enum(
        attribute_name=LegrandNLJWindowCoveringCluster.AttributeDefs.moving_state.name,
        enum_class=MovingState,
        cluster_id=WindowCovering.cluster_id,
        endpoint_id=1,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        translation_key="garage_door_moving_state",
        fallback_name="Garage door moving state",
    )
    .add_to_registry()
)
