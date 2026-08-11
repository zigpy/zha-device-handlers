"""Tests for SDevices quirks."""

from unittest import mock

import pytest
from zigpy.profiles import zha
from zigpy.zcl import ClusterType, ReportingConfig, foundation
from zigpy.zcl.clusters.closures import WindowCovering, WindowCoveringMode
from zigpy.zcl.clusters.general import DeviceTemperature, MultistateInput, OnOff
from zigpy.zcl.clusters.homeautomation import Diagnostic

import zhaquirks
from zhaquirks.builder.metadata import NumberMetadata, SwitchMetadata, ZCLEnumMetadata
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    COMMAND,
    DOUBLE_PRESS,
    LONG_PRESS,
    SHORT_PRESS,
)
from zhaquirks.sdevices import (
    SDevicesButtonCluster,
    SDevicesCluster,
    SDevicesDeviceTemperatureCluster,
    SDevicesOnOffCluster,
    SDevicesTwoButtonCluster,
    SDevicesWindowCoveringCluster,
)
from zhaquirks.sdevices.socket import _socket
from zhaquirks.sdevices.switch import _single_button_switch, _two_button_switch

zhaquirks.setup()

PRESENT_VALUE = MultistateInput.AttributeDefs.present_value.id


@pytest.mark.parametrize("model", ("SBDV-00196", "SBDV-00197"))
def test_single_button_actions(zigpy_device_from_v2_quirk, model):
    """A single-button switch emits button_single/double/hold events."""
    device = zigpy_device_from_v2_quirk("SDevices", model)

    cluster = device.endpoints[1].multistate_input
    assert isinstance(cluster, SDevicesButtonCluster)

    listener = mock.MagicMock()
    cluster.add_listener(listener)

    # unknown present_value -> no event
    cluster.update_attribute(PRESENT_VALUE, 5)
    assert listener.zha_send_event.call_count == 0

    for value, action in (
        (1, "button_single"),
        (2, "button_double"),
        (0, "button_hold"),
    ):
        cluster.update_attribute(PRESENT_VALUE, value)
        listener.zha_send_event.assert_called_with(action, {})


@pytest.mark.parametrize("model", ("SBDV-00199", "SBDV-00200"))
@pytest.mark.parametrize("endpoint", (1, 2))
def test_two_button_actions(zigpy_device_from_v2_quirk, model, endpoint):
    """A two-button switch emits per-endpoint {single,double,hold}_switch_N events."""
    device = zigpy_device_from_v2_quirk(
        "SDevices",
        model,
        cluster_ids={
            1: {
                OnOff.cluster_id: ClusterType.Server,
                MultistateInput.cluster_id: ClusterType.Server,
            },
            2: {
                OnOff.cluster_id: ClusterType.Server,
                MultistateInput.cluster_id: ClusterType.Server,
            },
        },
    )

    cluster = device.endpoints[endpoint].multistate_input
    assert isinstance(cluster, SDevicesTwoButtonCluster)

    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.update_attribute(PRESENT_VALUE, 5)
    assert listener.zha_send_event.call_count == 0

    for value, raw in ((1, "single"), (2, "double"), (0, "hold")):
        cluster.update_attribute(PRESENT_VALUE, value)
        listener.zha_send_event.assert_called_with(f"{raw}_switch_{endpoint}", {})


@pytest.mark.parametrize("model", ("SBDV-00199", "SBDV-00200"))
def test_two_button_relays_are_switches(zigpy_device_from_v2_quirk, model):
    """Switch-mode relays get the ON_OFF_OUTPUT device type (switch platform)."""
    device = zigpy_device_from_v2_quirk(
        "SDevices",
        model,
        cluster_ids={
            1: {OnOff.cluster_id: ClusterType.Server},
            2: {OnOff.cluster_id: ClusterType.Server},
        },
    )
    for endpoint in (1, 2):
        assert device.endpoints[endpoint].device_type == zha.DeviceType.ON_OFF_OUTPUT


def test_socket_relay_is_switch(zigpy_device_from_v2_quirk):
    """The socket is a Mains Power Outlet (0x0009) - a switch, not a light."""
    device = zigpy_device_from_v2_quirk("SDevices", "SBDV-00202")
    assert device.endpoints[1].device_type == zha.DeviceType.MAIN_POWER_OUTLET


def test_socket_emergency_flags_split_from_bitmap(zigpy_device_from_v2_quirk):
    """The emergency bitmap is split into per-flag attributes on attribute update."""
    device = zigpy_device_from_v2_quirk("SDevices", "SBDV-00202")
    cluster = device.endpoints[1].sdevices_cluster

    # one flag at a time -> only that flag's synthetic attribute flips
    for attr_name, bitmap in (
        ("emergency_overvoltage", 0x01),
        ("emergency_undervoltage", 0x02),
        ("emergency_overcurrent", 0x04),
        ("emergency_overheat", 0x08),
    ):
        cluster.update_attribute(0x3001, bitmap)
        assert cluster.get(attr_name) is True
        others = {
            "emergency_overvoltage",
            "emergency_undervoltage",
            "emergency_overcurrent",
            "emergency_overheat",
        } - {attr_name}
        assert all(cluster.get(other) is False for other in others)

    # all flags at once -> all set
    cluster.update_attribute(0x3001, 0x0F)
    assert all(
        cluster.get(n) is True
        for n in (
            "emergency_overvoltage",
            "emergency_undervoltage",
            "emergency_overcurrent",
            "emergency_overheat",
        )
    )

    # each flag is its own binary sensor on its synthetic attribute, not the bitmap
    binary_attrs = {
        entity.attribute_name
        for entity in _socket("SDevices", "SBDV-00202").entity_metadata
        if type(entity).__name__ == "BinarySensorMetadata"
    }
    assert binary_attrs == {
        "emergency_overvoltage",
        "emergency_undervoltage",
        "emergency_overcurrent",
        "emergency_overheat",
    }


@pytest.mark.parametrize("model", ("SBDV-00199", "SBDV-00200"))
def test_cover_mode(zigpy_device_from_v2_quirk, model):
    """Covering-mode instance (EP3 WindowCovering) matches the cover quirk."""
    device = zigpy_device_from_v2_quirk(
        "SDevices",
        model,
        endpoint_ids=[3],
        cluster_ids={
            3: {
                WindowCovering.cluster_id: ClusterType.Server,
                Diagnostic.cluster_id: ClusterType.Server,
                SDevicesCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    cluster = device.endpoints[3].window_covering
    assert isinstance(cluster, SDevicesWindowCoveringCluster)
    # manufacturer attribute is available on the replaced cluster
    assert cluster.AttributeDefs.sdevices_calibration_time.id == 0x1001
    # switch-mode gangs must not exist on a covering-mode device
    assert 1 not in device.endpoints
    assert 2 not in device.endpoints


@pytest.mark.asyncio
async def test_button_clusters_bind(zigpy_device_from_v2_quirk):
    """Report sources bind without changing firmware reporting defaults."""
    single = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00196",
        cluster_ids={
            1: {
                MultistateInput.cluster_id: ClusterType.Server,
                Diagnostic.cluster_id: ClusterType.Server,
            }
        },
    )
    single_cluster = single.endpoints[1].multistate_input
    single_cluster.bind = mock.AsyncMock()
    await single_cluster.apply_custom_configuration()
    single_cluster.bind.assert_awaited_once()

    diagnostic_cluster = single.endpoints[1].diagnostic
    diagnostic_cluster.bind = mock.AsyncMock()
    await diagnostic_cluster.apply_custom_configuration()
    diagnostic_cluster.bind.assert_awaited_once()

    socket = zigpy_device_from_v2_quirk("SDevices", "SBDV-00202")
    socket_reporting_cluster = socket.endpoints[1].sdevices_cluster
    socket_reporting_cluster.bind = mock.AsyncMock()
    await socket_reporting_cluster.apply_custom_configuration()
    socket_reporting_cluster.bind.assert_awaited_once()

    device_temperature_cluster = socket.endpoints[1].device_temperature
    device_temperature_cluster.bind = mock.AsyncMock()
    await device_temperature_cluster.apply_custom_configuration()
    device_temperature_cluster.bind.assert_not_awaited()

    dual = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00199",
        cluster_ids={
            1: {MultistateInput.cluster_id: ClusterType.Server},
            2: {MultistateInput.cluster_id: ClusterType.Server},
        },
    )
    for endpoint_id in (1, 2):
        dual_cluster = dual.endpoints[endpoint_id].multistate_input
        dual_cluster.bind = mock.AsyncMock()
        await dual_cluster.apply_custom_configuration()
        dual_cluster.bind.assert_awaited_once()


@pytest.mark.asyncio
async def test_manufacturer_cluster_binding_matches_report_sources(
    zigpy_device_from_v2_quirk,
):
    """Bind 0xFCCF only where the reference device emits attribute reports."""
    no_neutral = zigpy_device_from_v2_quirk("SDevices", "SBDV-00196")
    no_neutral_cluster = no_neutral.endpoints[1].sdevices_cluster
    no_neutral_cluster.bind = mock.AsyncMock()
    await no_neutral_cluster.apply_custom_configuration()
    no_neutral_cluster.bind.assert_not_awaited()

    optional_neutral = zigpy_device_from_v2_quirk("SDevices", "SBDV-00197")
    optional_neutral_cluster = optional_neutral.endpoints[1].sdevices_cluster
    optional_neutral_cluster.bind = mock.AsyncMock()
    await optional_neutral_cluster.apply_custom_configuration()
    optional_neutral_cluster.bind.assert_awaited_once()

    dual = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00199",
        cluster_ids={
            1: {SDevicesCluster.cluster_id: ClusterType.Server},
            2: {SDevicesCluster.cluster_id: ClusterType.Server},
        },
    )
    for endpoint_id, should_bind in ((1, True), (2, False)):
        cluster = dual.endpoints[endpoint_id].sdevices_cluster
        cluster.bind = mock.AsyncMock()
        await cluster.apply_custom_configuration()
        if should_bind:
            cluster.bind.assert_awaited_once()
        else:
            cluster.bind.assert_not_awaited()

    cover = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00199",
        endpoint_ids=[3],
        cluster_ids={3: {SDevicesCluster.cluster_id: ClusterType.Server}},
    )
    cover_cluster = cover.endpoints[3].sdevices_cluster
    cover_cluster.bind = mock.AsyncMock()
    await cover_cluster.apply_custom_configuration()
    cover_cluster.bind.assert_awaited_once()


@pytest.mark.asyncio
async def test_clusters_retain_firmware_reporting_configuration(
    zigpy_device_from_v2_quirk,
):
    """SDevices clusters acknowledge reporting setup without sending a command."""
    socket = zigpy_device_from_v2_quirk("SDevices", "SBDV-00202")
    clusters_and_attributes = (
        (
            socket.endpoints[1].on_off,
            OnOff.AttributeDefs.on_off,
            SDevicesOnOffCluster,
        ),
        (
            socket.endpoints[1].device_temperature,
            DeviceTemperature.AttributeDefs.current_temperature,
            SDevicesDeviceTemperatureCluster,
        ),
        (
            socket.endpoints[1].sdevices_cluster,
            SDevicesCluster.AttributeDefs.rms_voltage_mv,
            SDevicesCluster,
        ),
    )

    for cluster, attribute, cluster_class in clusters_and_attributes:
        assert isinstance(cluster, cluster_class)
        cluster._configure_reporting = mock.AsyncMock()
        result = await cluster.configure_reporting_multiple(
            {
                attribute: ReportingConfig(
                    min_interval=1,
                    max_interval=2,
                    reportable_change=1,
                )
            }
        )
        assert result == {attribute: foundation.Status.SUCCESS}
        cluster._configure_reporting.assert_not_awaited()

    cover = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00199",
        endpoint_ids=[3],
        cluster_ids={
            3: {WindowCovering.cluster_id: ClusterType.Server},
        },
    )
    cover_cluster = cover.endpoints[3].window_covering
    cover_cluster._configure_reporting = mock.AsyncMock()
    attribute = WindowCovering.AttributeDefs.current_position_lift_percentage
    result = await cover_cluster.configure_reporting_multiple(
        {
            attribute: ReportingConfig(
                min_interval=1,
                max_interval=2,
                reportable_change=1,
            )
        }
    )
    assert result == {attribute: foundation.Status.SUCCESS}
    cover_cluster._configure_reporting.assert_not_awaited()


def test_device_automation_triggers_use_standard_types():
    """SDevices actions use Home Assistant's localized trigger types/subtypes."""
    single = _single_button_switch("SDevices", "SBDV-00196")
    assert single.device_automation_triggers_metadata == {
        (SHORT_PRESS, BUTTON_1): {COMMAND: "button_single"},
        (DOUBLE_PRESS, BUTTON_1): {COMMAND: "button_double"},
        (LONG_PRESS, BUTTON_1): {COMMAND: "button_hold"},
    }

    dual = _two_button_switch("SDevices", "SBDV-00199")
    assert dual.device_automation_triggers_metadata == {
        (SHORT_PRESS, BUTTON_1): {COMMAND: "single_switch_1"},
        (DOUBLE_PRESS, BUTTON_1): {COMMAND: "double_switch_1"},
        (LONG_PRESS, BUTTON_1): {COMMAND: "hold_switch_1"},
        (SHORT_PRESS, BUTTON_2): {COMMAND: "single_switch_2"},
        (DOUBLE_PRESS, BUTTON_2): {COMMAND: "double_switch_2"},
        (LONG_PRESS, BUTTON_2): {COMMAND: "hold_switch_2"},
    }


@pytest.mark.asyncio
async def test_cover_mode_bit_write_preserves_other_bits(
    zigpy_device_from_v2_quirk,
):
    """Writing one synthetic cover-mode switch preserves every unrelated bit."""
    device = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00199",
        endpoint_ids=[3],
        cluster_ids={3: {WindowCovering.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[3].window_covering
    mode_attr = WindowCovering.AttributeDefs.window_covering_mode
    initial_mode = (
        WindowCoveringMode.Motor_direction_reversed
        | WindowCoveringMode.LEDs_display_feedback
    )
    cluster.update_attribute(mode_attr.id, initial_mode)

    cluster.write_attributes_raw = mock.AsyncMock(
        return_value=(
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],
        )
    )
    await cluster.write_attributes({"cover_calibration_mode": True})

    ((written,),), _ = cluster.write_attributes_raw.call_args
    assert written.attrid == mode_attr.id
    assert written.value.value == (
        initial_mode | WindowCoveringMode.Run_in_calibration_mode
    )
    assert cluster.get("cover_calibration_mode") is True
    assert cluster.get("cover_led_feedback") is True


@pytest.mark.asyncio
async def test_cover_mode_bit_write_reads_uncached_mode(
    zigpy_device_from_v2_quirk,
):
    """An uncached Mode is read before clearing a bit and other writes pass through."""
    device = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00199",
        endpoint_ids=[3],
        cluster_ids={3: {WindowCovering.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[3].window_covering
    mode_attr = WindowCovering.AttributeDefs.window_covering_mode
    initial_mode = (
        WindowCoveringMode.Run_in_calibration_mode
        | WindowCoveringMode.LEDs_display_feedback
    )
    cluster.read_attributes = mock.AsyncMock(
        return_value=({mode_attr.name: initial_mode}, {})
    )
    cluster.write_attributes_raw = mock.AsyncMock(
        return_value=(
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],
        )
    )

    await cluster.write_attributes(
        {"cover_calibration_mode": False, "velocity_lift": 25}
    )

    cluster.read_attributes.assert_awaited_once()
    ((written),), _ = cluster.write_attributes_raw.call_args
    written_values = {record.attrid: record.value.value for record in written}
    assert written_values == {
        WindowCovering.AttributeDefs.velocity_lift.id: 25,
        mode_attr.id: WindowCoveringMode.LEDs_display_feedback,
    }
    assert cluster.get("cover_calibration_mode") is False
    assert cluster.get("cover_led_feedback") is True


@pytest.mark.asyncio
async def test_cover_mode_bit_write_fails_without_current_mode(
    zigpy_device_from_v2_quirk,
):
    """A synthetic bit cannot be safely written if Mode cannot be read."""
    device = zigpy_device_from_v2_quirk(
        "SDevices",
        "SBDV-00199",
        endpoint_ids=[3],
        cluster_ids={3: {WindowCovering.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[3].window_covering
    cluster.read_attributes = mock.AsyncMock(return_value=({}, {}))
    cluster.write_attributes_raw = mock.AsyncMock()

    with pytest.raises(
        ValueError, match="Unable to read WindowCovering.Mode before updating it"
    ):
        await cluster.write_attributes({"cover_calibration_mode": True})

    cluster.write_attributes_raw.assert_not_awaited()


def test_config_entities_request_initial_values():
    """Writable config entities are read before ZHA checks their support."""
    builders = (
        _single_button_switch("SDevices", "SBDV-00197", optional_neutral=True),
        _two_button_switch("SDevices", "SBDV-00200", optional_neutral=True),
        _socket("SDevices", "SBDV-00202"),
    )
    local_cover_mode_attributes = {
        "cover_calibration_mode",
        "cover_maintenance_mode",
        "cover_led_feedback",
    }

    missing_startup_reads = []
    for builder in builders:
        for metadata in builder.entity_metadata:
            if not isinstance(
                metadata, (NumberMetadata, SwitchMetadata, ZCLEnumMetadata)
            ):
                continue
            if metadata.attribute_name in local_cover_mode_attributes:
                continue
            if (
                metadata.reporting_config is None
                and metadata.attribute_initialized_from_cache
            ):
                missing_startup_reads.append(
                    (metadata.endpoint_id, metadata.attribute_name)
                )

    assert missing_startup_reads == []


def test_optional_neutral_cover_entities_are_declared():
    """SBDV-00200 exposes its optional-neutral attributes on cover endpoint 3."""
    metadata = _two_button_switch(
        "SDevices", "SBDV-00200", optional_neutral=True
    ).entity_metadata
    assert {
        (entity.endpoint_id, entity.attribute_name)
        for entity in metadata
        if entity.attribute_name
        in {"power_profile", "led_indication_type", "neutral_presence"}
    } == {
        (1, "power_profile"),
        (1, "led_indication_type"),
        (1, "neutral_presence"),
        (3, "power_profile"),
        (3, "led_indication_type"),
        (3, "neutral_presence"),
    }
    neutral_entities = [
        entity for entity in metadata if entity.attribute_name == "neutral_presence"
    ]
    assert all(
        entity.attribute_initialized_from_cache is False
        and entity.reporting_config is None
        for entity in neutral_entities
    )


def test_switch_diagnostic_counter_mapping():
    """Diagnostics distinguish pairing and physical wall buttons."""
    single = _single_button_switch("SDevices", "SBDV-00196")
    single_diagnostics = {
        entity.attribute_name
        for entity in single.entity_metadata
        if entity.cluster_id == Diagnostic.cluster_id
    }
    assert {
        "number_of_resets",
        "sdevices_button1_clicks",
        "sdevices_button2_clicks",
        "sdevices_relay1_switches",
    } <= single_diagnostics
    assert "persistent_memory_writes" not in single_diagnostics

    dual = _two_button_switch("SDevices", "SBDV-00199")
    dual_diagnostics = {
        (entity.endpoint_id, entity.attribute_name)
        for entity in dual.entity_metadata
        if entity.cluster_id == Diagnostic.cluster_id
    }
    for endpoint_id in (1, 3):
        assert {
            (endpoint_id, "sdevices_button1_clicks"),
            (endpoint_id, "sdevices_button2_clicks"),
            (endpoint_id, "sdevices_button3_clicks"),
            (endpoint_id, "sdevices_relay1_switches"),
            (endpoint_id, "sdevices_relay2_switches"),
        } <= dual_diagnostics
    assert not any(
        attribute_name == "persistent_memory_writes"
        for _, attribute_name in dual_diagnostics
    )


def test_unsupported_flash_writes_entity_is_not_declared_for_socket():
    """The firmware does not support Diagnostic persistent memory writes."""
    assert not any(
        entity.attribute_name == "persistent_memory_writes"
        for entity in _socket("SDevices", "SBDV-00202").entity_metadata
    )


def test_socket_device_temperature_unique_id_is_preserved():
    """The replacement matches ZHA's native `{ieee}-1-2` unique ID."""
    (metadata,) = (
        entity
        for entity in _socket("SDevices", "SBDV-00202").entity_metadata
        if entity.cluster_id == DeviceTemperature.cluster_id
        and entity.attribute_name == "current_temperature"
    )
    assert metadata.unique_id_suffix == str(DeviceTemperature.cluster_id)


def test_socket_scaling_and_reporting_metadata():
    """Socket declarations leave reporting intervals to the firmware."""
    metadata = _socket("SDevices", "SBDV-00202").entity_metadata
    numbers = {
        entity.attribute_name: entity
        for entity in metadata
        if isinstance(entity, NumberMetadata)
    }
    assert (
        numbers["upper_voltage_threshold"].min,
        numbers["upper_voltage_threshold"].max,
    ) == (230, 260)
    assert numbers["upper_voltage_threshold"].multiplier == 0.001
    assert (
        numbers["lower_voltage_threshold"].min,
        numbers["lower_voltage_threshold"].max,
    ) == (100, 230)
    assert numbers["lower_voltage_threshold"].multiplier == 0.001
    assert (
        numbers["upper_current_threshold"].min,
        numbers["upper_current_threshold"].max,
    ) == (0.1, 16)
    assert numbers["upper_current_threshold"].multiplier == 0.001
    assert (
        numbers["upper_temp_threshold"].min,
        numbers["upper_temp_threshold"].max,
    ) == (10, 100)

    sensors = {
        entity.attribute_name: entity
        for entity in metadata
        if type(entity).__name__ == "ZCLSensorMetadata"
    }
    for attr_name in ("rms_voltage_mv", "rms_current_ma", "active_power_mw"):
        sensor = sensors[attr_name]
        assert sensor.divisor == 1000
        assert sensor.reporting_config is None
        assert sensor.attribute_initialized_from_cache is False

    emergency = sensors["emergency_shutoff_state"]
    assert emergency.initially_disabled is True
    assert emergency.reporting_config is None
    assert emergency.attribute_initialized_from_cache is False
