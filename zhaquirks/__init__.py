import importlib
import pkgutil
from zigpy.quirks import CustomCluster
from zigpy.util import ListenableMixin

UNKNOWN = 'Unknown'


class Bus(ListenableMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._listeners = {}


class LocalDataCluster(CustomCluster):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def read_attributes_raw(self, attributes, manufacturer=None):
        attributes = [types.uint16_t(a) for a in attributes]
        v = [self._attr_cache.get(attr) for attr in attributes]
        return v

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)


class EventableCluster(CustomCluster):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle_cluster_request(self, tsn, command_id, args):
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

name = __name__
path = __path__
for importer, modname, ispkg in pkgutil.walk_packages(
        path=path,
        prefix=name +'.'
        ):
    importlib.import_module(modname)
