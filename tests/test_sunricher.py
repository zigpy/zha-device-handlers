"""Tests for the ROBB/Sunricher floor thermostat quirk."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import Cluster, ClusterType
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

import zhaquirks
from zhaquirks.sunricher import robb_200_040_0_fw_1033 as sunricher_quirk
from zhaquirks.sunricher.robb_200_040_0_fw_1033 import (
    ATTR_CONTROL_SEQUENCE,
    ATTR_CONTROL_TYPE,
    ATTR_DISPLAY_AUTO_OFF,
    ATTR_FLOOR_SENSOR_CALIBRATION,
    ATTR_FLOOR_SENSOR_TYPE,
    ATTR_HYSTERESIS,
    ATTR_LCD_DISPLAY_SOURCE,
    ATTR_LOCAL_TEMP,
    ATTR_LOCAL_TEMP_CALIBRATION,
    ATTR_MODE_AFTER_DRY,
    ATTR_OUTDOOR_TEMP,
    ATTR_SYSTEM_MODE,
    ChildLockEnum,
    ControlTypeEnum,
    FloorSensorTypeEnum,
    SunricherFloorProbeCluster,
    SunricherThermostatCluster,
    SunricherUserInterfaceCluster,
    TempUnitEnum,
)

zhaquirks.setup()

MANUFACTURER = "ROBB smarrt"
MODEL = "ROB_200-040-0"


@pytest.fixture
def thermostat(zigpy_device_from_v2_quirk):
    """Return a quirked ROBB floor thermostat."""
    return zigpy_device_from_v2_quirk(
        MANUFACTURER,
        MODEL,
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                UserInterface.cluster_id: ClusterType.Server,
                TemperatureMeasurement.cluster_id: ClusterType.Server,
            },
        },
    )


def test_user_interface_attributes_are_normalized(thermostat):
    """Temperature scale is typed and every nonzero lock value means locked."""
    cluster = thermostat.endpoints[1].in_clusters[UserInterface.cluster_id]
    assert isinstance(cluster, SunricherUserInterfaceCluster)

    cluster._update_attribute(0x0000, 0)
    assert cluster.get("temperature_unit_scale") is TempUnitEnum.Celsius
    cluster._update_attribute(0x0000, 1)
    assert cluster.get("temperature_unit_scale") is TempUnitEnum.Fahrenheit

    cluster._update_attribute(0x0001, 0)
    assert cluster.get("keypad_lock_active") is ChildLockEnum.No
    cluster._update_attribute(0x0001, 7)
    assert cluster.get("keypad_lock_active") is ChildLockEnum.Yes

    cluster._update_attribute(0xFFFF, "unmapped")
    assert cluster._attr_cache[0xFFFF] == "unmapped"


@pytest.mark.asyncio
async def test_user_interface_writes_are_normalized(thermostat):
    """The UI cluster writes standard attribute IDs and binary lock values."""
    cluster = thermostat.endpoints[1].in_clusters[UserInterface.cluster_id]

    with mock.patch.object(
        Cluster, "write_attributes", new_callable=mock.AsyncMock
    ) as write_attributes:
        await cluster.write_attributes(
            {"temperature_unit_scale": 1, "keypad_lock_active": 7}
        )
        write_attributes.assert_awaited_once_with(
            {0x0000: TempUnitEnum.Fahrenheit, 0x0001: 1}, manufacturer=None
        )

        write_attributes.reset_mock()
        await cluster.write_attributes({"keypad_lockout": 0})
        write_attributes.assert_awaited_once_with({0x0001: 0}, manufacturer=None)

        write_attributes.reset_mock()
        assert cluster.write_attributes({}) == []
        write_attributes.assert_not_awaited()

        await cluster.write_attributes({"unmapped_attribute": 3})
        write_attributes.assert_awaited_once_with(
            {"unmapped_attribute": 3}, manufacturer=None
        )


def test_floor_probe_updates_thermostat_floor_temperature(thermostat):
    """The measured floor temperature is routed to thermostat outdoor/local temp."""
    endpoint = thermostat.endpoints[1]
    thermostat_cluster = endpoint.in_clusters[Thermostat.cluster_id]
    probe_cluster = endpoint.in_clusters[TemperatureMeasurement.cluster_id]

    assert isinstance(thermostat_cluster, SunricherThermostatCluster)
    assert isinstance(probe_cluster, SunricherFloorProbeCluster)

    probe_cluster._update_attribute(
        TemperatureMeasurement.AttributeDefs.measured_value.id, 2150
    )

    assert thermostat_cluster.get(ATTR_OUTDOOR_TEMP) == 2150
    assert thermostat_cluster.get(ATTR_LOCAL_TEMP) == 2150

    thermostat_cluster._update_attribute(ATTR_LOCAL_TEMP_CALIBRATION, 50)
    thermostat_cluster._update_attribute(ATTR_FLOOR_SENSOR_CALIBRATION, -50)
    assert thermostat_cluster.get(ATTR_LOCAL_TEMP_CALIBRATION) == 30
    assert thermostat_cluster.get(ATTR_FLOOR_SENSOR_CALIBRATION) == -30


def test_current_floor_temperature_falls_back_to_probe_cache(thermostat):
    """Use the measurement-cluster cache when thermostat outdoor temp is absent."""
    endpoint = thermostat.endpoints[1]
    thermostat_cluster = endpoint.in_clusters[Thermostat.cluster_id]
    probe_cluster = endpoint.in_clusters[TemperatureMeasurement.cluster_id]
    measured_value_id = TemperatureMeasurement.AttributeDefs.measured_value.id

    thermostat_cluster._update_attribute(ATTR_OUTDOOR_TEMP, 1800)
    assert thermostat_cluster._get_current_floor_temp() == 1800
    thermostat_cluster._attr_cache.clear()

    assert thermostat_cluster.get(ATTR_OUTDOOR_TEMP) is None
    probe_cluster._attr_cache[measured_value_id] = 2150
    assert thermostat_cluster._get_current_floor_temp() == 2150

    probe_cluster._attr_cache.clear()
    assert thermostat_cluster._get_current_floor_temp() is None


def test_quirk_entities_and_default_entity_filter(thermostat):
    """The app version and config controls target the expected ZCL attributes."""
    entry = DEVICE_REGISTRY.match_entry(thermostat)
    assert entry is not None
    definition = entry.zha_device_factory.quirk_definition
    entities = {
        metadata.resolved_unique_id_suffix: metadata
        for metadata in definition.entity_metadata
    }

    app_version = entities["app_version"]
    assert app_version.cluster_id == Basic.cluster_id
    assert app_version.attribute_name == Basic.AttributeDefs.app_version.name
    assert app_version.attribute_initialized_from_cache is False

    assert entities["temperature_unit_scale"].entity_type.name == "CONFIG"
    assert entities["keypad_lock_active"].entity_type.name == "CONFIG"

    (default_filter,) = definition.disabled_default_entities
    assert default_filter.endpoint_id == 1
    assert default_filter.unique_id_suffix == "keypad_lockout"
    assert default_filter.cluster_id == UserInterface.cluster_id


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, None), (0, "Off"), (1, "Low"), (255, "Off")],
)
def test_vibration_sensor_converter(thermostat, value, expected):
    """The vibration sensor translates known values and uses its configured fallback."""
    entry = DEVICE_REGISTRY.match_entry(thermostat)
    assert entry is not None
    entities = {
        metadata.resolved_unique_id_suffix: metadata
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    }

    assert entities["vibration_level_text"].attribute_converter(value) == expected


def test_floor_sensor_control_type_keeps_room_temperature(thermostat):
    """Room-sensor mode does not replace local temperature with floor readings."""
    endpoint = thermostat.endpoints[1]
    thermostat_cluster = endpoint.in_clusters[Thermostat.cluster_id]
    probe_cluster = endpoint.in_clusters[TemperatureMeasurement.cluster_id]

    thermostat_cluster._update_attribute(ATTR_CONTROL_TYPE, ControlTypeEnum.Room_Sensor)
    thermostat_cluster._update_attribute(ATTR_LOCAL_TEMP, 2200)
    probe_cluster._update_attribute(
        TemperatureMeasurement.AttributeDefs.measured_value.id, 1800
    )

    assert thermostat_cluster.get(ATTR_OUTDOOR_TEMP) == 1800
    assert thermostat_cluster.get(ATTR_LOCAL_TEMP) == 2200


def test_local_temperature_is_deferred_until_sensor_mode_is_known(thermostat):
    """Cache room temperature while floor mode is active, then restore it on switch."""
    endpoint = thermostat.endpoints[1]
    cluster = endpoint.in_clusters[Thermostat.cluster_id]

    cluster._update_attribute(ATTR_LOCAL_TEMP, 2200)
    assert cluster._air_temp == 2200
    assert cluster.get(ATTR_LOCAL_TEMP) is None

    cluster._update_attribute(ATTR_CONTROL_TYPE, ControlTypeEnum.Room_Sensor)
    assert cluster.get(ATTR_LOCAL_TEMP) == 2200

    probe_cluster = endpoint.in_clusters[TemperatureMeasurement.cluster_id]
    probe_cluster._update_attribute(
        TemperatureMeasurement.AttributeDefs.measured_value.id, 1800
    )
    cluster._update_attribute(ATTR_CONTROL_TYPE, ControlTypeEnum.Floor_Sensor)
    assert cluster.get(ATTR_LOCAL_TEMP) == 1800

    cluster._update_attribute(ATTR_LOCAL_TEMP, 2200)
    assert cluster._air_temp == 2200
    assert cluster.get(ATTR_LOCAL_TEMP) == 1800

    cluster._update_attribute(ATTR_CONTROL_TYPE, ControlTypeEnum.Room_Sensor)
    assert cluster.get(ATTR_LOCAL_TEMP) == 2200

    cluster._update_attribute(ATTR_CONTROL_TYPE, ControlTypeEnum.Floor_Sensor)
    assert cluster.get(ATTR_LOCAL_TEMP) == 1800


def test_thermostat_attribute_normalization(thermostat):
    """Ignore unsafe values and normalize thermostat mode and sensor settings."""
    cluster = thermostat.endpoints[1].in_clusters[Thermostat.cluster_id]

    cluster._update_attribute(ATTR_DISPLAY_AUTO_OFF, 1)
    assert ATTR_DISPLAY_AUTO_OFF not in cluster._attr_cache

    cluster._update_attribute(ATTR_CONTROL_SEQUENCE, 0)
    assert (
        cluster.get(ATTR_CONTROL_SEQUENCE)
        is Thermostat.ControlSequenceOfOperation.Heating_Only
    )

    cluster._update_attribute(ATTR_FLOOR_SENSOR_TYPE, 256)
    assert cluster.get(ATTR_FLOOR_SENSOR_TYPE) is FloorSensorTypeEnum.NTC_12k_Ohm
    cluster._update_attribute(ATTR_FLOOR_SENSOR_TYPE, 1)
    assert cluster.get(ATTR_FLOOR_SENSOR_TYPE) is FloorSensorTypeEnum.NTC_10k_Ohm

    cluster._update_attribute(ATTR_SYSTEM_MODE, 1)
    assert cluster.get(ATTR_SYSTEM_MODE) is Thermostat.SystemMode.Heat
    cluster._update_attribute(ATTR_SYSTEM_MODE, 0)
    assert cluster.get(ATTR_SYSTEM_MODE) is Thermostat.SystemMode.Off


@pytest.mark.asyncio
async def test_thermostat_writes_filter_and_route_attributes(thermostat):
    """Writes are filtered, normalized, and sent with the correct manufacturer."""
    cluster = thermostat.endpoints[1].in_clusters[Thermostat.cluster_id]

    with mock.patch.object(
        Cluster, "write_attributes", new_callable=mock.AsyncMock
    ) as write_attributes:
        assert (
            cluster.write_attributes(
                {ATTR_DISPLAY_AUTO_OFF: 1, sunricher_quirk.ATTR_OPERATE_BRIGHTNESS: 2}
            )
            == []
        )
        write_attributes.assert_not_awaited()

        await cluster.write_attributes({"system_mode": 1})
        write_attributes.assert_awaited_once_with(
            {ATTR_SYSTEM_MODE: Thermostat.SystemMode.Heat}, manufacturer=None
        )
        assert cluster.get(ATTR_SYSTEM_MODE) is Thermostat.SystemMode.Heat

        write_attributes.reset_mock()
        await cluster.write_attributes(
            {
                ATTR_FLOOR_SENSOR_TYPE: 255,
                ATTR_CONTROL_TYPE: 255,
                ATTR_LCD_DISPLAY_SOURCE: 255,
                ATTR_FLOOR_SENSOR_CALIBRATION: 99,
            }
        )
        write_attributes.assert_awaited_once_with(
            {
                ATTR_FLOOR_SENSOR_TYPE: 5,
                ATTR_CONTROL_TYPE: 1,
                ATTR_LCD_DISPLAY_SOURCE: 1,
                ATTR_FLOOR_SENSOR_CALIBRATION: 30,
            },
            manufacturer=sunricher_quirk.SUNRICHER_MANUFACTURER_CODE,
        )

        write_attributes.reset_mock()
        await cluster.write_attributes({ATTR_MODE_AFTER_DRY: 2})
        write_attributes.assert_awaited_once_with(
            {ATTR_MODE_AFTER_DRY: 2},
            manufacturer=sunricher_quirk.SUNRICHER_MANUFACTURER_CODE,
        )

        write_attributes.reset_mock()
        await cluster.write_attributes({0xFFFF: 3})
        write_attributes.assert_awaited_once_with({0xFFFF: 3}, manufacturer=None)

        write_attributes.reset_mock()
        await cluster.write_attributes({ATTR_HYSTERESIS: 10, "system_mode": 0})
        write_attributes.assert_awaited_once_with(
            {ATTR_SYSTEM_MODE: Thermostat.SystemMode.Off}, manufacturer=None
        )
        await cluster._bg_task
        assert write_attributes.await_count == 2
        assert write_attributes.await_args_list[1] == mock.call(
            {ATTR_HYSTERESIS: 10},
            manufacturer=sunricher_quirk.SUNRICHER_MANUFACTURER_CODE,
        )


@pytest.mark.asyncio
async def test_thermostat_write_routes_mixed_manufacturer_attributes(thermostat):
    """Mixed writes send proprietary and standard attributes separately."""
    cluster = thermostat.endpoints[1].in_clusters[Thermostat.cluster_id]

    with mock.patch.object(
        Cluster, "write_attributes", new_callable=mock.AsyncMock
    ) as write_attributes:
        await cluster.write_attributes({ATTR_HYSTERESIS: 10, ATTR_SYSTEM_MODE: 1})
        write_attributes.assert_awaited_once_with(
            {ATTR_SYSTEM_MODE: Thermostat.SystemMode.Heat}, manufacturer=None
        )
        await cluster._bg_task

    assert write_attributes.await_args_list == [
        mock.call({ATTR_SYSTEM_MODE: Thermostat.SystemMode.Heat}, manufacturer=None),
        mock.call(
            {ATTR_HYSTERESIS: 10},
            manufacturer=sunricher_quirk.SUNRICHER_MANUFACTURER_CODE,
        ),
    ]


@pytest.mark.asyncio
async def test_thermostat_reads_filter_and_route_attributes(thermostat):
    """Reads skip the unsafe register and route manufacturer attributes separately."""
    cluster = thermostat.endpoints[1].in_clusters[Thermostat.cluster_id]

    with mock.patch.object(
        Cluster, "read_attributes_raw", new_callable=mock.AsyncMock
    ) as read_attributes_raw:
        read_attributes_raw.side_effect = [["manufacturer"], ["standard"]]
        result = await cluster.read_attributes_raw(
            [
                ATTR_DISPLAY_AUTO_OFF,
                ATTR_HYSTERESIS,
                ATTR_SYSTEM_MODE,
                "display_auto_off",
            ]
        )

    assert result == ["standard"]
    assert read_attributes_raw.await_args_list == [
        mock.call(
            [ATTR_HYSTERESIS],
            manufacturer=sunricher_quirk.SUNRICHER_MANUFACTURER_CODE,
        ),
        mock.call([ATTR_SYSTEM_MODE], manufacturer=None),
    ]

    with mock.patch.object(
        Cluster, "read_attributes_raw", new_callable=mock.AsyncMock
    ) as read_attributes_raw:
        assert await cluster.read_attributes_raw([ATTR_DISPLAY_AUTO_OFF]) == [{}]
        read_attributes_raw.assert_not_awaited()

    cluster._update_attribute(ATTR_CONTROL_TYPE, ControlTypeEnum.Room_Sensor)
    cluster._update_attribute(ATTR_LOCAL_TEMP, 2200)
    cluster._update_attribute(ATTR_CONTROL_TYPE, ControlTypeEnum.Floor_Sensor)
    cluster._update_attribute(ATTR_OUTDOOR_TEMP, 1800)
    cluster._attr_cache[ATTR_LOCAL_TEMP] = 2200

    with mock.patch.object(
        Cluster, "read_attributes_raw", new_callable=mock.AsyncMock
    ) as read_attributes_raw:
        await cluster.read_attributes_raw([ATTR_SYSTEM_MODE])

    assert cluster.get(ATTR_LOCAL_TEMP) == 1800


@pytest.mark.asyncio
async def test_thermostat_bind_sets_control_sequence_and_starts_configuration(
    thermostat,
):
    """Binding establishes the heating sequence and launches initialization."""
    cluster = thermostat.endpoints[1].in_clusters[Thermostat.cluster_id]

    with (
        mock.patch.object(
            Cluster, "bind", new_callable=mock.AsyncMock, return_value="bound"
        ) as bind,
        mock.patch.object(
            cluster, "write_config_registers", new_callable=mock.AsyncMock
        ) as configure,
    ):
        assert await cluster.bind() == "bound"
        await cluster._bg_task

    bind.assert_awaited_once()
    configure.assert_awaited_once()
    assert (
        cluster.get(ATTR_CONTROL_SEQUENCE)
        is Thermostat.ControlSequenceOfOperation.Heating_Only
    )


@pytest.mark.asyncio
async def test_write_config_registers_initializes_device(thermostat):
    """Configuration writes defaults and reads thermostat and UI state."""
    endpoint = thermostat.endpoints[1]
    cluster = endpoint.in_clusters[Thermostat.cluster_id]
    ui_cluster = endpoint.in_clusters[UserInterface.cluster_id]

    with (
        mock.patch.object(
            sunricher_quirk.asyncio, "sleep", new_callable=mock.AsyncMock
        ),
        mock.patch.object(
            cluster, "write_attributes", new_callable=mock.AsyncMock
        ) as write,
        mock.patch.object(
            cluster, "read_attributes", new_callable=mock.AsyncMock
        ) as read,
        mock.patch.object(
            ui_cluster, "read_attributes", new_callable=mock.AsyncMock
        ) as ui_read,
    ):
        await cluster.write_config_registers()

    assert write.await_args_list == [
        mock.call({ATTR_FLOOR_SENSOR_TYPE: 5}, manufacturer=0x1224),
        mock.call({ATTR_CONTROL_TYPE: 1}, manufacturer=0x1224),
        mock.call({ATTR_HYSTERESIS: 10}, manufacturer=0x1224),
        mock.call({ATTR_LCD_DISPLAY_SOURCE: 1}, manufacturer=0x1224),
    ]
    assert read.await_args_list == [
        mock.call([ATTR_SYSTEM_MODE], manufacturer=None),
        mock.call(
            [
                sunricher_quirk.ATTR_OPERATE_BRIGHTNESS,
                sunricher_quirk.ATTR_BUTTON_VIBRATION,
                sunricher_quirk.ATTR_MODE_AFTER_DRY,
                ATTR_FLOOR_SENSOR_CALIBRATION,
            ],
            manufacturer=0x1224,
        ),
    ]
    ui_read.assert_awaited_once_with([0x0000, 0x0001], manufacturer=None)


@pytest.mark.asyncio
async def test_write_config_registers_without_ui_cluster(zigpy_device_from_v2_quirk):
    """Configuration also completes when the device has no UI cluster."""
    thermostat = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    cluster = thermostat.endpoints[1].in_clusters[Thermostat.cluster_id]

    with (
        mock.patch.object(
            sunricher_quirk.asyncio, "sleep", new_callable=mock.AsyncMock
        ),
        mock.patch.object(cluster, "write_attributes", new_callable=mock.AsyncMock),
        mock.patch.object(cluster, "read_attributes", new_callable=mock.AsyncMock),
    ):
        await cluster.write_config_registers()


@pytest.mark.asyncio
async def test_write_config_registers_logs_failures(thermostat, caplog):
    """A failed initialization is logged and deferred rather than propagated."""
    cluster = thermostat.endpoints[1].in_clusters[Thermostat.cluster_id]

    with (
        mock.patch.object(
            sunricher_quirk.asyncio, "sleep", new_callable=mock.AsyncMock
        ),
        mock.patch.object(
            cluster,
            "write_attributes",
            new_callable=mock.AsyncMock,
            side_effect=RuntimeError("write failed"),
        ),
    ):
        await cluster.write_config_registers()

    assert "Register initialization deferred: write failed" in caplog.text
