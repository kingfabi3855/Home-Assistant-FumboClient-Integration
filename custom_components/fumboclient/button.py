"""Stop/disconnect buttons; permissions are checked in Minecraft."""
from homeassistant.components.button import ButtonEntity
from .entity import FumboEntity, setup_entities


async def async_setup_entry(hass, entry, async_add_entities):
    setup_entities(entry, async_add_entities, "button", FumboButton)


class FumboButton(FumboEntity, ButtonEntity):
    async def async_press(self):
        await self.coordinator.async_command(self.key, "PRESS")
