"""HOBEIAN ZG-305Z dual USB switch."""

from zigpy.profiles import zha

from zhaquirks.builder import QuirkBuilder

(
    QuirkBuilder("HOBEIAN", "ZG-305Z")
    .replaces_endpoint(1, device_type=zha.DeviceType.ON_OFF_OUTPUT)
    .replaces_endpoint(2, device_type=zha.DeviceType.ON_OFF_OUTPUT)
    .add_to_registry()
)
