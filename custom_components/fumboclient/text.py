"""A local-only Minecraft notice, not a server chat or command interface."""
from homeassistant.components.text import TextEntity, TextMode
from .entity import FumboEntity, setup_entities


async def async_setup_entry(hass, entry, async_add_entities):
    setup_entities(entry, async_add_entities, "text", FumboText)


class FumboText(FumboEntity, TextEntity):
    _attr_native_min = 1
    _attr_native_max = 160
    _attr_mode = TextMode.TEXT
    _attr_native_value = ""

    async def async_set_value(self, value):
        await self.coordinator.async_command(self.key, value)
        self._attr_native_value = value
        self.async_write_ha_state()
