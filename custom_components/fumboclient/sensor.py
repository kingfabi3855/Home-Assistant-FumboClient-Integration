"""Native sensors."""
from homeassistant.components.sensor import SensorEntity
from .entity import FumboEntity, setup_entities


async def async_setup_entry(hass, entry, async_add_entities):
    setup_entities(entry, async_add_entities, "sensor", FumboSensor)


class FumboSensor(FumboEntity, SensorEntity):
    def __init__(self, coordinator, spec):
        super().__init__(coordinator, spec)
        self._attr_native_unit_of_measurement = spec["unit"] or None

    @property
    def native_value(self):
        return self.coordinator.data["state"].get(self.key)
