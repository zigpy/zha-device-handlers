"""Tuya fingerbot."""

import asyncio

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff

from zhaquirks.builder import PERCENTAGE, UnitOfTime
from zhaquirks.const import BatterySize
from zhaquirks.tuya import TUYA_CLUSTER_ID, TUYA_SEND_DATA
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster, TuyaOnOffNM


class FingerBotMode(t.enum8):
    """FingerBot mode."""

    CLICK = 0x00
    SWITCH = 0x01
    PROGRAM = 0x02


class FingerBotReverse(t.enum8):
    """FingerBot reverse."""

    UP_ON = 0x00
    UP_OFF = 0x01


(
    TuyaQuirkBuilder("_TZ3210_dse8ogfy", "TS0001")
    .applies_to("_TZ3210_j4pdtz9v", "TS0001")
    .applies_to("_TZ3210_7vgttna6", "TS0001")
    .applies_to("_TZ3210_a04acm9s", "TS0001")
    .tuya_enum(
        dp_id=101,
        attribute_name="mode",
        enum_class=FingerBotMode,
        translation_key="mode",
        fallback_name="Mode",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="down_movement",
        min_value=50,
        type=t.uint16_t,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        translation_key="down_movement",
        fallback_name="Down movement",
    )
    .tuya_number(
        dp_id=103,
        attribute_name="sustain_time",
        min_value=0,
        type=t.uint16_t,
        max_value=10,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="sustain_time",
        fallback_name="Sustain time",
    )
    .tuya_enum(
        dp_id=104,
        attribute_name="reverse",
        enum_class=FingerBotReverse,
        translation_key="reverse",
        fallback_name="Reverse",
    )
    .tuya_battery(dp_id=105, battery_type=BatterySize.CR2, battery_qty=1)
    .tuya_number(
        dp_id=106,
        attribute_name="up_movement",
        min_value=0,
        type=t.uint16_t,
        max_value=50,
        step=1,
        unit=PERCENTAGE,
        translation_key="up_movement",
        fallback_name="Up movement",
    )
    .tuya_switch(
        dp_id=107,
        attribute_name="touch_control",
        translation_key="touch_control",
        fallback_name="Touch control",
    )
    .tuya_enchantment()
    .add_to_registry(mcu_write_command=TUYA_SEND_DATA)
)


class FingerBotModeCZF02(t.enum8):
    """Lincukoo CZF02 fingerbot mode."""

    BUTTON = 0x00
    SWITCH = 0x01


class FingerBotCZF02OnOff(TuyaOnOffNM):
    """OnOff cluster for the Lincukoo CZF02 that also handles button mode.

    In button mode the arm presses and releases on every change of DP 1, and the
    device keeps the new value. Each command therefore sends the opposite of the
    device state, and the switch turns off again once the arm is released.
    """

    reset_margin_s: float = 1.0

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._timer_handle: asyncio.TimerHandle | None = None

    def _is_button_mode(self) -> bool:
        tuya_cluster = self.endpoint.in_clusters.get(TUYA_CLUSTER_ID)
        return (
            tuya_cluster is not None
            and tuya_cluster.get("mode") == FingerBotModeCZF02.BUTTON
        )

    async def command(self, command_id, *args, **kwargs):
        """Press the arm on every on, off or toggle command in button mode."""
        if (
            command_id
            not in (
                OnOff.ServerCommandDefs.off.id,
                OnOff.ServerCommandDefs.on.id,
                OnOff.ServerCommandDefs.toggle.id,
            )
            or not self._is_button_mode()
        ):
            return await super().command(command_id, *args, **kwargs)

        tuya_cluster = self.endpoint.in_clusters[TUYA_CLUSTER_ID]
        device_state = bool(tuya_cluster.get("device_state"))
        result = await super().command(
            OnOff.ServerCommandDefs.off.id
            if device_state
            else OnOff.ServerCommandDefs.on.id,
            *args,
            **kwargs,
        )
        tuya_cluster.update_attribute("device_state", not device_state)
        self._update_attribute(OnOff.AttributeDefs.on_off.name, True)
        return result

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)

        try:
            attr_def = self.find_attribute(attrid)
        except KeyError:
            return
        if attr_def.name != OnOff.AttributeDefs.on_off.name:
            return

        if self._timer_handle:
            self._timer_handle.cancel()
            self._timer_handle = None

        if value and self._is_button_mode():
            tuya_cluster = self.endpoint.in_clusters[TUYA_CLUSTER_ID]
            sustain_time_ms = tuya_cluster.get("sustain_time") or 0
            self._timer_handle = asyncio.get_running_loop().call_later(
                sustain_time_ms / 1000 + self.reset_margin_s, self._turn_off
            )

    def _turn_off(self):
        self._timer_handle = None
        self._update_attribute(OnOff.AttributeDefs.on_off.name, False)


(
    TuyaQuirkBuilder("_TZE284_chcnj5st", "TS0601")
    .applies_to("_TZE2841000000_chcnj5st", "TS0601")
    .applies_to("_TZE284_gw05grph", "TS0601")
    .applies_to("_TZE2841000000_gw05grph", "TS0601")
    .applies_to("_TZE284_pislt0wa", "TS0601")
    .applies_to("_TZE2841000000_pislt0wa", "TS0601")
    # DP 1 is also kept on the Tuya cluster, as the switch state is reset in
    # button mode
    .tuya_dp_multi(
        dp_id=1,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=FingerBotCZF02OnOff.ep_attribute,
                attribute_name=OnOff.AttributeDefs.on_off.name,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaMCUCluster.ep_attribute,
                attribute_name="device_state",
            ),
        ],
    )
    .tuya_attribute(dp_id=1, attribute_name="device_state", type=t.Bool)
    .adds(FingerBotCZF02OnOff)
    .tuya_enum(
        dp_id=2,
        attribute_name="mode",
        enum_class=FingerBotModeCZF02,
        translation_key="mode",
        fallback_name="Mode",
    )
    # The device uses 0.1 s steps, exposed in ms so the value written is exact
    .tuya_dp_attribute(
        dp_id=3,
        attribute_name="sustain_time",
        type=t.uint16_t,
        access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write,
        converter=lambda x: x * 100,
        dp_converter=lambda x: round(x / 100),
    )
    .number(
        attribute_name="sustain_time",
        cluster_id=TUYA_CLUSTER_ID,
        min_value=300,
        max_value=10000,
        step=100,
        unit=UnitOfTime.MILLISECONDS,
        translation_key="sustain_time",
        fallback_name="Sustain time",
    )
    .tuya_number(
        dp_id=5,
        attribute_name="down_movement",
        type=t.uint16_t,
        min_value=0,
        max_value=30,
        step=1,
        translation_key="down_movement",
        fallback_name="Down movement",
    )
    .tuya_number(
        dp_id=6,
        attribute_name="up_movement",
        type=t.uint16_t,
        min_value=0,
        max_value=30,
        step=1,
        translation_key="up_movement",
        fallback_name="Up movement",
    )
    .tuya_battery(dp_id=8, battery_type=BatterySize.CR2, battery_qty=1)
    .tuya_dp_attribute(
        dp_id=101,
        attribute_name="auto_calibration",
        type=t.Bool,
        access=foundation.ZCLAttributeAccess.Write,
    )
    .write_attr_button(
        attribute_name="auto_calibration",
        attribute_value=True,
        cluster_id=TUYA_CLUSTER_ID,
        translation_key="run_auto_calibration",
        fallback_name="Run auto-calibration",
    )
    .tuya_enchantment(data_query_spell=True)
    .add_to_registry()
)
