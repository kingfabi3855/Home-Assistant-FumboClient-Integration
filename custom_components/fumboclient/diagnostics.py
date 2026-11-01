"""Diagnostics contain neither token, IP, player location, server nor notice text."""


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    return {
        "integration_version": "0.1.0",
        "api_version": data.get("api_version"),
        "last_update_success": coordinator.last_update_success,
        "client_version": data.get("device", {}).get("client_version"),
        "entity_keys": [spec["key"] for spec in data.get("entities", [])],
    }
