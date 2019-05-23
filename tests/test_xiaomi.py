"""Tests for xiaomi."""
from unittest import mock

from zhaquirks.xiaomi import BasicCluster


def test_basic_cluster_deserialize_wrong_len():
    """Test attr report with model and xiaomi attr."""
    cluster = BasicCluster(mock.MagicMock())

    tsn, frame_type, is_reply, command_id = 0xee, 0x00, True, 0x0a
    data = b'\x05\x00B\x15lumi.sensor_wleak.aq1\x01\xffB"\x01!\xb3\x0b\x03('
    data += b'\x17\x04!\xa8C\x05!\xa7\x00\x06$\x00\x00\x00\x00\x00\x08!\x04'
    data += b'\x02\n!\x00\x00d\x10\x01'

    d = cluster.deserialize(tsn, frame_type, is_reply, command_id, data)
    assert d[3]


def test_basic_cluster_deserialize_wrong_len_2():
    """Test attr report with xiaomi attr."""
    cluster = BasicCluster(mock.MagicMock())

    tsn, frame_type, is_reply, command_id = 0xee, 0x00, True, 0x0a
    data = b'\x01\xffB"\x01!\xb3\x0b\x03(\x17\x04!\xa8C\x05!\xa7\x00\x06$\x15'
    data += b'\x00\x14\x00\x00\x08!\x04\x02\n!\x00\x00d\x10\x01'

    d = cluster.deserialize(tsn, frame_type, is_reply, command_id, data)
    assert d[3]
