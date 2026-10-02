"""Tuya based cover and blinds."""

from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE600_ogyg1y6b", "TS0105")
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2)
    .add_to_registry()
)
