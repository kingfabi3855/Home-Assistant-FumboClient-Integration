"""Polling and acknowledged command execution for the embedded client API."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from time import monotonic

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FumboApi, FumboError, InvalidAuth
from .const import DEFAULT_INTERVAL, CONF_INTERVAL, DOMAIN

LOGGER = logging.getLogger(__name__)


class FumboCoordinator(DataUpdateCoordinator):
    """One bounded poll shared by every entity for a client."""

    def __init__(self, hass, entry, api: FumboApi) -> None:
        self.api = api
        self.device_id = entry.unique_id
        super().__init__(hass, LOGGER, name=DOMAIN, config_entry=entry,
                         update_interval=timedelta(seconds=entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)))

    async def _async_update_data(self) -> dict:
        try:
            data = await self.api.status()
            if data["device"]["id"] != self.device_id:
                raise UpdateFailed("Different client at this address; reconfigure the integration")
            return data
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed("Pairing token or client IP permission changed") from err
        except FumboError as err:
            raise UpdateFailed("Local FumboClient unavailable or incompatible") from err

    async def async_command(self, key: str, value: str) -> None:
        """Never retry a POST: a timed-out request may already have executed."""
        if not self.last_update_success or not self.data:
            raise HomeAssistantError("FumboClient is unavailable")
        session = self.data["session"]
        try:
            request_id = await self.api.command(session, key, value)
            deadline = monotonic() + 6
            while monotonic() < deadline:
                await asyncio.sleep(0.25)
                await self.async_refresh()
                if not self.last_update_success:
                    raise HomeAssistantError("Connection lost; command result unknown. Do not repeat blindly.")
                result = next((r for r in self.data["command_results"] if r["request_id"] == request_id), None)
                if result and result["status"] == "executed":
                    return
                if self.data["session"] != session:
                    raise HomeAssistantError("Client session changed; command result must be checked")
                if result and result["status"] in ("rejected", "failed"):
                    raise HomeAssistantError("Client rejected or could not execute the action")
            raise HomeAssistantError("Command result unknown; check Minecraft before repeating")
        except FumboError as err:
            raise HomeAssistantError("Action not confirmed; check client permissions and connection") from err
