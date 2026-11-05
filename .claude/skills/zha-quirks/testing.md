# Tests

Test fixtures are in `tests/conftest.py`:

```python
# For v1 quirks
quirked = zigpy_device_from_quirk(quirk_class)

# For v2 quirks
quirked = zigpy_device_from_v2_quirk(manufacturer, model)
```

Don't add new signature match tests (`assert_signature_matches_quirk`); they only exist for old v1 quirks.

**When tests are NOT needed:** Purely declarative v2 quirks that contain no custom logic do not require test coverage. This includes quirks that only use existing custom clusters (already tested elsewhere), `.device_automation_triggers()`, `.friendly_name()`, `.applies_to()`, `.skip_configuration()`, `_CONSTANT_ATTRIBUTES`, or other pure definitions. Adding `.applies_to()` to an existing quirk doesn't need a test either. Once a device's diagnostics are in ZHA's test data, ZHA's snapshot tests cover the entities its quirk creates, so don't write tests that only assert what the builder produced. Example:

```python
(
    QuirkBuilder("Manufacturer", "Model")
    .friendly_name(model="Wireless Mini Switch", manufacturer="Acme")
    .replaces(ExistingCustomCluster)
    .device_automation_triggers({
        (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_SINGLE},
        (DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_DOUBLE},
    })
    .add_to_registry()
)
```

Tests **are** needed when a quirk introduces custom logic such as custom clusters with overridden methods (e.g., `handle_cluster_request`, `_update_attribute`, `write_attributes`), value parsing or command handling, non-trivial filter functions, or custom entity classes. A one-line `attribute_converter` lambda doesn't need its own test.

**End-to-end tests:** if your quirk is complex, its high-level behavior should be tested. Use `tests/zha_helpers.py` with diagnostics for your device:
```python
async with zha_gateway() as gateway:
    device = await join_device_from_diagnostics(gateway, "your_device.json", DEVICE_REGISTRY)
```

