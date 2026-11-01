"""Tests against real Home Assistant, run on Linux/Python 3.14 by CI."""
import copy
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fumboclient.api import CannotConnect, InvalidAuth, InvalidResponse
from custom_components.fumboclient.const import DOMAIN, ENTITY_PLATFORMS

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")
TOKEN = "c"*64
DEVICE_ID = "a"*32
INPUT = {"host": "192.168.1.50", "port": 25809, "token": TOKEN}


@pytest.fixture
def status_data():
    entities = [{"key": key, "platform": platform, "name": key, "icon": "mdi:minecraft", "unit": ""}
                for key, platform in ENTITY_PLATFORMS.items()]
    state = {s["key"]: 20 if s["platform"] == "sensor" else "OFF" for s in entities
             if s["platform"] in ("sensor", "binary_sensor", "switch", "select")}
    state.update(dimension="minecraft:overworld", server="private-server", connected="ON", afk_mode="Auto")
    return {"api_version": 1, "device": {"id": DEVICE_ID, "name": "FumboClient", "client_version": "1.24.0"},
            "boot_id": "11111111-1111-1111-1111-111111111111", "session": "22222222-2222-2222-2222-222222222222",
            "entities": entities, "state": state, "events": [], "command_results": [], "sample_age_seconds": 0}


async def test_user_flow(hass, status_data):
    with patch("custom_components.fumboclient.api.FumboApi.status", return_value=status_data), \
         patch("custom_components.fumboclient.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        assert result["type"] == FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)
        await hass.async_block_till_done()
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == INPUT
        assert result["result"].unique_id == DEVICE_ID


@pytest.mark.parametrize(("error", "expected"), [(CannotConnect(), "cannot_connect"), (InvalidAuth(), "invalid_auth"), (InvalidResponse(), "invalid_response")])
async def test_flow_errors(hass, error, expected):
    with patch("custom_components.fumboclient.api.FumboApi.status", side_effect=error):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": expected}


async def test_public_host_rejected(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT | {"host": "8.8.8.8"})
    assert result["errors"] == {"base": "invalid_input"}


async def test_duplicate(hass, status_data):
    entry = MockConfigEntry(domain=DOMAIN, data=INPUT, unique_id=DEVICE_ID)
    entry.add_to_hass(hass)
    with patch("custom_components.fumboclient.api.FumboApi.status", return_value=status_data):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_reconfigure_wrong_device(hass, status_data):
    entry = MockConfigEntry(domain=DOMAIN, data=INPUT, unique_id="b"*32)
    entry.add_to_hass(hass)
    with patch("custom_components.fumboclient.api.FumboApi.status", return_value=status_data):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "wrong_device"


async def test_all_platforms_permissions_and_events(hass, status_data):
    entry = MockConfigEntry(domain=DOMAIN, data=INPUT, unique_id=DEVICE_ID)
    entry.add_to_hass(hass)
    with patch("custom_components.fumboclient.api.FumboApi.status", return_value=status_data):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        coordinator = entry.runtime_data
        registry = er.async_get(hass)
        entries = [e for e in registry.entities.values() if e.config_entry_id == entry.entry_id]
        assert len(entries) == 39

        def entity(platform, key):
            return registry.async_get_entity_id(platform, DOMAIN, f"{DEVICE_ID}_{key}")

        assert hass.states.get(entity("sensor", "health")).state == "20"
        with patch.object(coordinator, "async_command", new_callable=AsyncMock) as command:
            await hass.services.async_call("switch", "turn_on", {"entity_id": entity("switch", "auto_eat")}, blocking=True)
            command.assert_awaited_with("auto_eat", "ON")
            await hass.services.async_call("button", "press", {"entity_id": entity("button", "stop_helpers")}, blocking=True)
            command.assert_awaited_with("stop_helpers", "PRESS")
            await hass.services.async_call("select", "select_option", {"entity_id": entity("select", "afk_mode"), "option": "AFK"}, blocking=True)
            command.assert_awaited_with("afk_mode", "AFK")

        changed = copy.deepcopy(status_data)
        changed["events"] = [{"id": 1, "event_type": "low_health"}]
        coordinator.async_set_updated_data(changed)
        await hass.async_block_till_done()
        event_state = hass.states.get(entity("event", "events"))
        assert event_state.attributes["event_type"] == "low_health"
        timestamp = event_state.state
        coordinator.async_set_updated_data(copy.deepcopy(changed))
        await hass.async_block_till_done()
        assert hass.states.get(entity("event", "events")).state == timestamp

        revoked = copy.deepcopy(changed)
        revoked["entities"] = [s for s in revoked["entities"] if s["key"] != "auto_eat"]
        coordinator.async_set_updated_data(revoked)
        await hass.async_block_till_done()
        assert hass.states.get(entity("switch", "auto_eat")).state == STATE_UNAVAILABLE

        frozen = copy.deepcopy(changed)
        frozen["sample_age_seconds"] = 30
        coordinator.async_set_updated_data(frozen)
        await hass.async_block_till_done()
        assert hass.states.get(entity("sensor", "health")).state == STATE_UNAVAILABLE
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_diagnostics_are_redacted(hass, status_data):
    from custom_components.fumboclient.diagnostics import async_get_config_entry_diagnostics
    entry = MockConfigEntry(domain=DOMAIN, data=INPUT, unique_id=DEVICE_ID)
    entry.add_to_hass(hass)
    with patch("custom_components.fumboclient.api.FumboApi.status", return_value=status_data):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        diagnostics = await async_get_config_entry_diagnostics(hass, entry)
        assert TOKEN not in str(diagnostics)
        assert INPUT["host"] not in str(diagnostics)
        assert "private-server" not in str(diagnostics)
        assert await hass.config_entries.async_unload(entry.entry_id)
