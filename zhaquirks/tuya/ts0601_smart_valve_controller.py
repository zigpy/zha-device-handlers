from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE284_zm8zpwas", "TS0601")
    .tuya_onoff(dp_id=1, inverted=True)  # נסה עם inverted
    .skip_configuration()
    .add_to_registry()
)
