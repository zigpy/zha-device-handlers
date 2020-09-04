"""Quirks common helpers."""


ZCL_IAS_MOTION_COMMAND = b"\t!\x00\x01\x00\x00\x00\x00\x00"
ZCL_OCC_ATTR_RPT_OCC = b"\x18d\n\x00\x00\x18\x01"


class ClusterListener:
    """Generic cluster listener."""

    def __init__(self, cluster):
        """Init instance."""
        self.cluster_commands = []
        self.attribute_updates = []
        cluster.add_listener(self)

    def attribute_updated(self, attr_id, value):
        """Attribute updated listener."""
        self.attribute_updates.append((attr_id, value))

    def cluster_command(self, tsn, commdand_id, args):
        """Command received listener."""
        self.cluster_commands.append((tsn, commdand_id, args))
