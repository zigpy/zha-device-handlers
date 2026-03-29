"""Tests for Tuya TS0601 keypad quirk."""

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasAce, IasZone

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya.ts0601_keypad import (
    TuyaAlarmControlPanelCluster,
    TuyaIasZoneTamper,
    TuyaKeypadManufCluster,
    TuyaPowerConfigurationCluster3AAA,
    TuyaWirelessZigbeeKeypad,
)

zhaquirks.setup()

# ZCL frames: frame_control(0x09) + TSN + cmd(0x01=get_data) + status + mcu_tsn + DP data
# Enum DP format: dp_id + type(0x04=enum) + len(0x00 0x01) + value(0x00)
# Integer DP format: dp_id + type(0x02=value) + len(0x00 0x04) + value(4 bytes BE)

# DP 27 (armed away) - enum 0
ZCL_TUYA_ARM_AWAY = b"\x09\x01\x01\x00\x01\x1b\x04\x00\x01\x00"
# DP 26 (disarmed) - enum 0
ZCL_TUYA_DISARM = b"\x09\x02\x01\x00\x02\x1a\x04\x00\x01\x00"
# DP 28 (armed home) - enum 0
ZCL_TUYA_ARM_HOME = b"\x09\x03\x01\x00\x03\x1c\x04\x00\x01\x00"
# DP 29 (SOS/panic) - enum 0
ZCL_TUYA_PANIC = b"\x09\x04\x01\x00\x04\x1d\x04\x00\x01\x00"
# DP 24 (anti-remove/tamper triggered) - bool true
ZCL_TUYA_EMERGENCY = b"\x09\x05\x01\x00\x05\x18\x01\x00\x01\x01"
# DP 24 (anti-remove/tamper cleared) - bool false
ZCL_TUYA_TAMPER_CLEAR = b"\x09\x08\x01\x00\x08\x18\x01\x00\x01\x00"
# DP 3 (battery percentage = 100) - integer
ZCL_TUYA_BATTERY_100 = b"\x09\x06\x01\x00\x06\x03\x02\x00\x04\x00\x00\x00\x64"
# DP 3 (battery percentage = 50) - integer
ZCL_TUYA_BATTERY_50 = b"\x09\x07\x01\x00\x07\x03\x02\x00\x04\x00\x00\x00\x32"


@pytest.fixture
def keypad_device(zigpy_device_from_quirk):
    """Create a keypad device from the quirk."""
    return zigpy_device_from_quirk(TuyaWirelessZigbeeKeypad)


def _send_tuya_command(ep, frame):
    """Deserialize and dispatch a Tuya ZCL frame to the MCU cluster."""
    hdr, data = ep.tuya_manufacturer.deserialize(frame)
    return ep.tuya_manufacturer.handle_get_data(data.data)


class TestTuyaKeypadQuirk:
    """Test the Tuya keypad quirk applies correctly."""

    def test_quirk_signature(self, keypad_device):
        """Test that the quirk applies and creates the expected clusters."""
        ep = keypad_device.endpoints[1]

        assert isinstance(ep.tuya_manufacturer, TuyaKeypadManufCluster)
        assert isinstance(ep.ias_ace, TuyaAlarmControlPanelCluster)
        assert isinstance(ep.power, TuyaPowerConfigurationCluster3AAA)
        assert isinstance(ep.ias_zone, TuyaIasZoneTamper)
        assert hasattr(keypad_device, "ias_bus")

    def test_device_automation_triggers(self, keypad_device):
        """Test that device automation triggers are defined."""
        triggers = keypad_device.device_automation_triggers
        assert ("disarm", "disarm") in triggers
        assert ("arm_away", "arm_away") in triggers
        assert ("arm_home", "arm_home") in triggers
        assert ("panic", "panic") in triggers
        assert ("emergency", "emergency") in triggers

    def test_battery_constant_attributes(self, keypad_device):
        """Test that battery constant attributes are set correctly."""
        power_cluster = keypad_device.endpoints[1].power
        battery_size_id = PowerConfiguration.attributes_by_name["battery_size"].id
        battery_qty_id = PowerConfiguration.attributes_by_name["battery_quantity"].id
        battery_voltage_id = PowerConfiguration.attributes_by_name[
            "battery_rated_voltage"
        ].id

        assert power_cluster._CONSTANT_ATTRIBUTES[battery_size_id] == (
            PowerConfiguration.BatterySize.AAA
        )
        assert power_cluster._CONSTANT_ATTRIBUTES[battery_qty_id] == 3
        assert power_cluster._CONSTANT_ATTRIBUTES[battery_voltage_id] == 15


class TestTuyaKeypadBattery:
    """Test battery DP handling."""

    def test_battery_100_percent(self, keypad_device):
        """Test battery percentage reporting at 100%."""
        ep = keypad_device.endpoints[1]
        power_listener = ClusterListener(ep.power)

        status = _send_tuya_command(ep, ZCL_TUYA_BATTERY_100)
        assert status == foundation.Status.SUCCESS

        # Battery 100 → battery_percentage_remaining = 200 (ZCL uses 0-200 range)
        assert len(power_listener.attribute_updates) == 1
        assert power_listener.attribute_updates[0][0] == (
            PowerConfiguration.attributes_by_name["battery_percentage_remaining"].id
        )
        assert power_listener.attribute_updates[0][1] == 200

    def test_battery_50_percent(self, keypad_device):
        """Test battery percentage reporting at 50%."""
        ep = keypad_device.endpoints[1]
        power_listener = ClusterListener(ep.power)

        status = _send_tuya_command(ep, ZCL_TUYA_BATTERY_50)
        assert status == foundation.Status.SUCCESS

        assert len(power_listener.attribute_updates) == 1
        assert power_listener.attribute_updates[0][1] == 100  # 50 * 2 = 100


class TestTuyaKeypadAlarmEvents:
    """Test arm/disarm/panic event generation."""

    def test_arm_away(self, keypad_device):
        """Test arm away generates IAS ACE event and zha_event."""
        ep = keypad_device.endpoints[1]
        ace_listener = ClusterListener(ep.ias_ace)

        status = _send_tuya_command(ep, ZCL_TUYA_ARM_AWAY)
        assert status == foundation.Status.SUCCESS

        # IAS ACE arm command should be fired
        assert len(ace_listener.cluster_commands) == 1
        assert ace_listener.cluster_commands[0][2] == [
            IasAce.ArmMode.Arm_All_Zones,
            "1234",
            0,
        ]

    def test_disarm(self, keypad_device):
        """Test disarm generates IAS ACE event."""
        ep = keypad_device.endpoints[1]
        ace_listener = ClusterListener(ep.ias_ace)

        status = _send_tuya_command(ep, ZCL_TUYA_DISARM)
        assert status == foundation.Status.SUCCESS

        assert len(ace_listener.cluster_commands) == 1
        assert ace_listener.cluster_commands[0][2] == [
            IasAce.ArmMode.Disarm,
            "1234",
            0,
        ]

    def test_arm_home(self, keypad_device):
        """Test arm home generates IAS ACE event."""
        ep = keypad_device.endpoints[1]
        ace_listener = ClusterListener(ep.ias_ace)

        status = _send_tuya_command(ep, ZCL_TUYA_ARM_HOME)
        assert status == foundation.Status.SUCCESS

        assert len(ace_listener.cluster_commands) == 1
        assert ace_listener.cluster_commands[0][2] == [
            IasAce.ArmMode.Arm_Day_Home_Only,
            "1234",
            0,
        ]

    def test_panic(self, keypad_device):
        """Test SOS/panic generates IAS ACE panic event."""
        ep = keypad_device.endpoints[1]
        ace_listener = ClusterListener(ep.ias_ace)

        status = _send_tuya_command(ep, ZCL_TUYA_PANIC)
        assert status == foundation.Status.SUCCESS

        assert len(ace_listener.cluster_commands) == 1
        # Panic command ID
        assert ace_listener.cluster_commands[0][1] == (
            IasAce.commands_by_name["panic"].id
        )

    def test_emergency(self, keypad_device):
        """Test tamper/anti-remove generates IAS ACE emergency event."""
        ep = keypad_device.endpoints[1]
        ace_listener = ClusterListener(ep.ias_ace)

        status = _send_tuya_command(ep, ZCL_TUYA_EMERGENCY)
        assert status == foundation.Status.SUCCESS

        assert len(ace_listener.cluster_commands) == 1
        assert ace_listener.cluster_commands[0][1] == (
            IasAce.commands_by_name["emergency"].id
        )

    def test_tamper_sets_zone_status(self, keypad_device):
        """Test that tamper/anti-remove sets and clears IAS Zone zone_status."""
        ep = keypad_device.endpoints[1]
        zone_listener = ClusterListener(ep.ias_zone)
        zone_status_id = IasZone.AttributeDefs.zone_status.id

        # Tamper triggered
        status = _send_tuya_command(ep, ZCL_TUYA_EMERGENCY)
        assert status == foundation.Status.SUCCESS

        tamper_updates = [
            u for u in zone_listener.attribute_updates if u[0] == zone_status_id
        ]
        assert len(tamper_updates) == 1
        assert tamper_updates[0][1] == (
            IasZone.ZoneStatus.Alarm_1 | IasZone.ZoneStatus.Tamper
        )

        # Tamper cleared
        status = _send_tuya_command(ep, ZCL_TUYA_TAMPER_CLEAR)
        assert status == foundation.Status.SUCCESS

        tamper_updates = [
            u for u in zone_listener.attribute_updates if u[0] == zone_status_id
        ]
        assert len(tamper_updates) == 2
        assert tamper_updates[1][1] == 0

    def test_arm_uses_cached_user_code(self, keypad_device):
        """Test that arm events use the cached user code from DP 109."""
        ep = keypad_device.endpoints[1]
        mcu_cluster = ep.tuya_manufacturer

        # Set a custom user code in the attribute cache
        user_code_attr_id = mcu_cluster.attributes_by_name["user_code"].id
        mcu_cluster._attr_cache[user_code_attr_id] = "5678"

        ace_listener = ClusterListener(ep.ias_ace)
        _send_tuya_command(ep, ZCL_TUYA_ARM_AWAY)

        assert ace_listener.cluster_commands[0][2] == [
            IasAce.ArmMode.Arm_All_Zones,
            "5678",
            0,
        ]


class TestTuyaKeypadModelsInfo:
    """Test that all supported models are listed."""

    def test_models_info(self):
        """Test that both known manufacturer IDs are supported."""
        models = TuyaWirelessZigbeeKeypad.signature["models_info"]
        manufacturers = [m[0] for m in models]
        assert "_TZE200_n9clpsht" in manufacturers
        assert "_TZE200_nyvavzbj" in manufacturers
