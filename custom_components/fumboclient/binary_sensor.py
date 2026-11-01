"""Native binary sensors."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from .entity import FumboEntity, setup_entities


async def async_setup_entry(hass, entry, async_add_entities):
    setup_entities(entry, async_add_entities, "binary_sensor", FumboBinarySensor)


class FumboBinarySensor(FumboEntity, BinarySensorEntity):
    @property
    def is_on(self):
        value = self.coordinator.data["state"].get(self.key)
        return None if value is None else value == "ON"
