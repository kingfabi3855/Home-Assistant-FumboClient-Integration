"""UI pairing, reconfiguration and reauthentication."""
from __future__ import annotations

try:
    import probatio as vol
except ImportError:  # HA releases before the schema-library migration
    import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CannotConnect, FumboApi, InvalidAuth, InvalidResponse, validate_host
from .const import CONF_INTERVAL, CONF_TOKEN, DEFAULT_INTERVAL, DEFAULT_PORT, DOMAIN


class FumboConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Pair a specific client installation with a stable device ID."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FumboOptionsFlow()

    async def async_step_user(self, user_input=None):
        return await self._async_pair("user", user_input)

    async def async_step_reconfigure(self, user_input=None):
        return await self._async_pair("reconfigure", user_input, self._get_reconfigure_entry())

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self._async_pair("reauth_confirm", user_input, self._get_reauth_entry())

    async def _async_pair(self, step, user_input, entry=None):
        errors = {}
        defaults = entry.data if entry else {}
        if user_input is not None:
            try:
                host = validate_host(user_input[CONF_HOST].strip())
                port = int(user_input[CONF_PORT])
                token = user_input[CONF_TOKEN].strip()
                data = await FumboApi(async_get_clientsession(self.hass), host, port, token).status()
            except ValueError:
                errors["base"] = "invalid_input"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidResponse:
                errors["base"] = "invalid_response"
            else:
                device_id = data["device"]["id"]
                if entry:
                    if entry.unique_id != device_id:
                        return self.async_abort(reason="wrong_device")
                    return self.async_update_reload_and_abort(entry, data_updates={CONF_HOST: host, CONF_PORT: port, CONF_TOKEN: token})
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data["device"]["name"], data={CONF_HOST: host, CONF_PORT: port, CONF_TOKEN: token})
        schema = vol.Schema({
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)):
                selector.NumberSelector(selector.NumberSelectorConfig(min=1024, max=65535, step=1, mode=selector.NumberSelectorMode.BOX)),
            vol.Required(CONF_TOKEN): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
        })
        return self.async_show_form(step_id=step, data_schema=schema, errors=errors)


class FumboOptionsFlow(config_entries.OptionsFlow):
    """Only polling frequency is changed on the HA side; client permissions stay local."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data={CONF_INTERVAL: int(user_input[CONF_INTERVAL])})
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Required(CONF_INTERVAL, default=self.config_entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)):
                selector.NumberSelector(selector.NumberSelectorConfig(min=2, max=30, step=1, mode=selector.NumberSelectorMode.BOX)),
        }))
