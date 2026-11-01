"""Capability-gated switches for existing client features."""
from homeassistant.components.switch import SwitchEntity
from .entity import FumboEntity, setup_entities


async def async_setup_entry(hass, entry, async_add_entities):
    setup_entities(entry, async_add_entities, "switch", FumboSwitch)


class FumboSwitch(FumboEntity, SwitchEntity):
    @property
    def is_on(self):
        return self.coordinator.data["state"].get(self.key) == "ON"

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_command(self.key, "ON")

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_command(self.key, "OFF")
