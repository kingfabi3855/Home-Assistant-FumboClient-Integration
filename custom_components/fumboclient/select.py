"""Explicit AFK state, without any anti-AFK movement."""
from homeassistant.components.select import SelectEntity
from .entity import FumboEntity, setup_entities


async def async_setup_entry(hass, entry, async_add_entities):
    setup_entities(entry, async_add_entities, "select", FumboSelect)


class FumboSelect(FumboEntity, SelectEntity):
    _attr_options = ["Auto", "AFK", "Aktiv"]

    @property
    def current_option(self):
        return self.coordinator.data["state"].get(self.key)

    async def async_select_option(self, option):
        await self.coordinator.async_command(self.key, option)
