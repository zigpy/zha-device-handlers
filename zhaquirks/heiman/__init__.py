"""Quirks for Heiman devices."""
HEIMAN = "Heiman"

# """Minimal Heiman smoke detector quirk"""
# import logging
# from zigpy.quirks import CustomCluster
# from zigpy.zcl.clusters.security import IasZone

# _LOGGER = logging.getLogger(__name__)


# class HeimanSmokeDebug(CustomCluster, IasZone):
#     """Debug cluster for Heiman smoke"""
    
#     cluster_id = IasZone.cluster_id
    
#     def _update_attribute(self, attrid, value):
#         """Log all attribute updates"""
#         _LOGGER.debug("HEIMAN DEBUG - Cluster: 0x%04X, Attr: 0x%04X, Value: %s", 
#                      self.cluster_id, attrid, value)
        
#         if isinstance(value, bytes):
#             _LOGGER.debug("HEIMAN DEBUG - Bytes hex: %s", value.hex())
        
#         return super()._update_attribute(attrid, value)