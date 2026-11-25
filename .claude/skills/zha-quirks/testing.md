# Tests

Test fixtures are in `tests/conftest.py`:

```python
# For v1 quirks
quirked = zigpy_device_from_quirk(quirk_class)

# For v2 quirks
quirked = zigpy_device_from_v2_quirk(manufacturer, model)
```

**Test code, not definitions.** Only write tests for the custom code listed below. If a quirk has none, do not write a test for it. Do not write tests for entity creation, quirk matching, signatures, or other definitions. These tests are long and fragile, and we do not accept them. ZHA already covers definitions with snapshot tests of the device diagnostics JSON. Example of a quirk that must not have a test:

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

Tests **are** needed for custom cluster methods (e.g., `handle_cluster_request`, `_update_attribute`, `write_attributes`), custom filter functions, and custom entity classes. Test what that code does, not that the entities exist.

**End-to-end tests:** if your quirk is complex, its high-level behavior should be tested. Use `tests/zha_helpers.py` with diagnostics for your device:
```python
async with zha_gateway() as gateway:
    device = await join_device_from_diagnostics(gateway, "your_device.json", DEVICE_REGISTRY)
```
