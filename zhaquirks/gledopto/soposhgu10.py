"""GLEDOPTO Soposh Dual White and color 5W GU10 300lm device."""

from zigpy.quirks.v2 import QuirkBuilder

# Note: This quirk is incomplete and non-functional
# It has no MODELS_INFO so it won't match any devices
# The only operation it performed was removing endpoint 13 from the signature
# In v2, not mentioning an endpoint effectively removes it from configuration
# However, without manufacturer/model info, this quirk cannot be properly migrated
# TODO: Add proper MODELS_INFO when device details are known

# Placeholder - will not match any devices
(
    QuirkBuilder("UNKNOWN_MANUFACTURER", "UNKNOWN_MODEL")
    .skip_configuration()
    .add_to_registry()
)
