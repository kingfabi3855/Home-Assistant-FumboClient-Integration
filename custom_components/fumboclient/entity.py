"""Shared entities and capability discovery after local permission changes."""
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class FumboEntity(CoordinatorEntity):
    """Every platform shares one coordinator and one device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, spec):
        super().__init__(coordinator)
        self.key = spec["key"]
        self._attr_unique_id = f"{coordinator.device_id}_{self.key}"
        self._attr_name = spec["name"]
        self._attr_icon = spec["icon"]
        device = coordinator.data["device"]
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, coordinator.device_id)}, name=device["name"], manufacturer="Fumbo", model="Minecraft Client", sw_version=device["client_version"])

    @property
    def available(self):
        return (super().available and self.coordinator.data.get("sample_age_seconds", 0) <= 15
                and any(s["key"] == self.key for s in self.coordinator.data["entities"]))


def setup_entities(entry, async_add_entities, platform, factory):
    """Discover newly permitted entities without restarting HA; revoke availability immediately."""
    coordinator = entry.runtime_data
    known = set()

    @callback
    def discover():
        entities = []
        for spec in coordinator.data["entities"]:
            if spec["platform"] == platform and spec["key"] not in known:
                known.add(spec["key"])
                entities.append(factory(coordinator, spec))
        if entities:
            async_add_entities(entities)

    discover()
    entry.async_on_unload(coordinator.async_add_listener(discover))
