"""Deduplicated client events; old events are not replayed on setup/restart."""
from homeassistant.components.event import EventEntity
from homeassistant.core import callback
from .const import EVENT_TYPES
from .entity import FumboEntity, setup_entities


async def async_setup_entry(hass, entry, async_add_entities):
    setup_entities(entry, async_add_entities, "event", FumboEvent)


class FumboEvent(FumboEntity, EventEntity):
    _attr_event_types = EVENT_TYPES

    def __init__(self, coordinator, spec):
        super().__init__(coordinator, spec)
        self._boot = coordinator.data["boot_id"]
        self._cursor = max((e["id"] for e in coordinator.data["events"]), default=0)

    @callback
    def _handle_coordinator_update(self):
        data = self.coordinator.data
        if data["boot_id"] != self._boot:
            self._boot = data["boot_id"]
            self._cursor = max((e["id"] for e in data["events"]), default=0)
        elif self.available:
            for event in data["events"]:
                if event["id"] > self._cursor:
                    self._cursor = event["id"]
                    self._trigger_event(event["event_type"])
                    self.async_write_ha_state()
        super()._handle_coordinator_update()
