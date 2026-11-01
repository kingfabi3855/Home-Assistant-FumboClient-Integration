"""Bounded, authenticated LAN API. No HA runtime imports or extra dependencies."""
from __future__ import annotations

import asyncio
import ipaddress
import json
import math
import re
from typing import Any
from uuid import uuid4

import aiohttp

from .const import ENTITY_PLATFORMS, EVENT_TYPES


class FumboError(Exception):
    """Safe public error without URLs, tokens or remote response bodies."""


class CannotConnect(FumboError):
    """The local client is offline or unreachable."""


class InvalidAuth(FumboError):
    """Pairing token or peer permission is invalid."""


class InvalidResponse(FumboError):
    """Not a compatible FumboClient API."""


class CommandRejected(FumboError):
    """The client refused the requested action."""


def validate_host(value: str) -> str:
    """Accept explicit RFC1918/ULA/loopback addresses, never arbitrary URLs/DNS."""
    if value == "localhost":
        return "127.0.0.1"
    try:
        address = ipaddress.ip_address(value)
    except ValueError as err:
        raise ValueError("Use a literal LAN IP address") from err
    allowed = address.is_loopback or any(
        address in ipaddress.ip_network(network)
        for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7")
    )
    if not allowed or address.is_unspecified or address.is_multicast:
        raise ValueError("Use a private LAN address")
    return str(address)


def validate_status(data: Any) -> dict[str, Any]:
    """Constrain the remote schema before entities consume it."""
    try:
        if not isinstance(data, dict) or type(data.get("api_version")) is not int or data["api_version"] != 1:
            raise ValueError
        device = data["device"]
        if not isinstance(device, dict) or not re.fullmatch(r"[a-f0-9]{32}", device["id"]):
            raise ValueError
        for key, maximum in (("name", 48), ("client_version", 64)):
            if not isinstance(device[key], str) or not 1 <= len(device[key]) <= maximum:
                raise ValueError
        for key in ("boot_id", "session"):
            if not isinstance(data[key], str) or not re.fullmatch(r"[a-f0-9-]{36}", data[key]):
                raise ValueError
        entities = data["entities"]
        if not isinstance(entities, list) or len(entities) > 64:
            raise ValueError
        seen = set()
        for item in entities:
            key = item["key"]
            if key in seen or ENTITY_PLATFORMS.get(key) != item["platform"]:
                raise ValueError
            seen.add(key)
            for field in ("name", "icon", "unit"):
                if not isinstance(item[field], str) or len(item[field]) > 80:
                    raise ValueError
        state = data["state"]
        if not isinstance(state, dict) or len(state) > 64:
            raise ValueError
        for key, value in state.items():
            if key not in seen or type(value) not in (str, int, float):
                raise ValueError
            if isinstance(value, str) and len(value) > 256:
                raise ValueError
            if isinstance(value, (int, float)) and not math.isfinite(value):
                raise ValueError
        events = data["events"]
        if not isinstance(events, list) or len(events) > 64:
            raise ValueError
        previous_id = 0
        for event in events:
            if type(event["id"]) is not int or event["id"] <= previous_id or event["event_type"] not in EVENT_TYPES:
                raise ValueError
            previous_id = event["id"]
        results = data["command_results"]
        if not isinstance(results, list) or len(results) > 128:
            raise ValueError
        for result in results:
            if not isinstance(result, dict) or result.get("status") not in ("queued", "executed", "rejected", "failed"):
                raise ValueError
            if not isinstance(result.get("request_id"), str) or len(result["request_id"]) != 36:
                raise ValueError
        age = data.get("sample_age_seconds", 0)
        if type(age) not in (int, float) or not math.isfinite(age) or age < 0:
            raise ValueError
    except (ValueError, TypeError, KeyError, OverflowError) as err:
        raise InvalidResponse("Invalid FumboClient status") from err
    return data


class FumboApi:
    """Use Home Assistant's shared aiohttp session; never follow redirects."""

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int, token: str) -> None:
        host = validate_host(host)
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("Invalid local port")
        if not isinstance(token, str) or not re.fullmatch(r"[a-f0-9]{64}", token):
            raise ValueError("Invalid pairing token")
        self._session = session
        self._base = f"http://{'['+host+']' if ':' in host else host}:{port}/api/v1"
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        try:
            async with self._session.request(
                method, self._base + path, headers=self._headers, json=payload,
                allow_redirects=False, timeout=aiohttp.ClientTimeout(total=6),
            ) as response:
                if response.status == 401 or response.status == 403 and method == "GET":
                    raise InvalidAuth("Pairing token or allowed HA IP must be checked")
                if response.status in (400, 403, 409, 429) and method == "POST":
                    raise CommandRejected("Action not permitted, session changed or queue full")
                if response.status not in (200, 202):
                    raise CannotConnect("Client returned an unexpected HTTP status")
                raw = bytearray()
                async for chunk in response.content.iter_chunked(8192):
                    raw.extend(chunk)
                    if len(raw) > 131072:
                        raise InvalidResponse("Client response too large")
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise InvalidResponse("Client response is not an object")
                return data
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise CannotConnect("Local FumboClient unavailable") from err
        except (ValueError, UnicodeError) as err:
            raise InvalidResponse("Invalid JSON from client") from err

    async def status(self) -> dict:
        return validate_status(await self._request("GET", "/status"))

    async def command(self, session: str, command: str, value: str) -> str:
        request_id = str(uuid4())
        reply = await self._request("POST", "/command", {
            "session": session, "request_id": request_id, "command": command, "value": value,
        })
        if reply.get("request_id") != request_id or reply.get("status") not in ("queued", "executed"):
            raise InvalidResponse("Client did not acknowledge the action")
        return request_id
