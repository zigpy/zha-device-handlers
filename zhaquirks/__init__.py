"""Quirks implementations for the ZHA component of Homeassistant."""
import importlib
import pkgutil

from zigpy.quirks import CustomCluster
import zigpy.types as types
from zigpy.util import ListenableMixin

UNKNOWN = 'Unknown'


class Bus(ListenableMixin):
    """Event bus implementation."""

    def __init__(self, *args, **kwargs):
        """Init event bus."""
        super().__init__(*args, **kwargs)
        self._listeners = {}


class LocalDataCluster(CustomCluster):
    """Cluster meant to prevent remote calls."""

    async def read_attributes_raw(self, attributes, manufacturer=None):
        """Prevent remote reads."""
        attributes = [types.uint16_t(a) for a in attributes]
        values = [self._attr_cache.get(attr) for attr in attributes]
        return values


class EventableCluster(CustomCluster):
    """Cluster that generates events."""

    def handle_cluster_request(self, tsn, command_id, args):
        """Send cluster requests as events."""
        super().handle_cluster_request(tsn, command_id, args)
        if self.server_commands is not None and\
                self.server_commands.get(command_id) is not None:
            self.listener_event(
                'zha_send_event',
                self,
                self.server_commands.get(command_id)[0],
                args
            )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        self.listener_event(
            'zha_send_event',
            self,
            'attribute_updated',
            {
                'attribute_id': attrid,
                'attribute_name': self.attributes.get(attrid, [UNKNOWN])[0],
                'value': value
            }
        )


NAME = __name__
PATH = __path__
for importer, modname, ispkg in pkgutil.walk_packages(
        path=PATH,
        prefix=NAME + '.'
        ):
    importlib.import_module(modname)
