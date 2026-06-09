"""HZC Test Cases."""

import unittest

from zhaquirks.hzc.dimmerswitch060 import ModeType


class TestModeType(unittest.TestCase):
    """TestModeType."""

    def test_get_arr(self):
        """Test get_arr."""
        mode_type = ModeType()
        mode_type.extend("1 17 0 10 18 0")
        arr = mode_type.get_arr()
        assert len(arr) == 6

    def test_serialize(self):
        """Test serialize."""
        mode_type = ModeType()
        mode_type.extend("1 17 0 10 18 0")
        serialized = mode_type.serialize()
        assert serialized == b"\x01\x11\x00\n\x12\x00"
        try:
            mode_type = ModeType()
            mode_type.extend("1 17 0 10 18")
            mode_type.serialize()
            return None
        except ValueError as Argument:
            return Argument
