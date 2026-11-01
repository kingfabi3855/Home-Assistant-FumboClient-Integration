"""Standalone protocol/security tests; no installed HA instance is needed."""
import asyncio
import copy
import importlib
import json
from pathlib import Path
import sys
import types
import unittest

import aiohttp
from aiohttp import web

# Import the dependency-free API module without executing HA's integration setup.
PACKAGE = "fumbo_protocol_test"
module = types.ModuleType(PACKAGE)
module.__path__ = [str(Path(__file__).resolve().parents[1]/"custom_components"/"fumboclient")]
sys.modules[PACKAGE] = module
api = importlib.import_module(PACKAGE+".api")


def sample():
    return {"api_version": 1, "device": {"id": "a"*32, "name": "FumboClient", "client_version": "1.24.0"},
            "boot_id": "a"*8+"-"+"a"*4+"-"+"a"*4+"-"+"a"*4+"-"+"a"*12,
            "session": "b"*8+"-"+"b"*4+"-"+"b"*4+"-"+"b"*4+"-"+"b"*12,
            "entities": [{"platform": "sensor", "key": "health", "name": "Leben", "icon": "mdi:heart", "unit": ""}],
            "state": {"health": 20}, "events": [], "command_results": [], "sample_age_seconds": 0}


class SchemaTests(unittest.TestCase):
    def test_local_hosts(self):
        for host in ("localhost", "127.0.0.1", "192.168.1.5", "10.0.0.5", "172.16.0.5", "::1", "fd00::5"):
            self.assertTrue(api.validate_host(host))
        for host in ("8.8.8.8", "0.0.0.0", "172.15.0.1", "example.org", "http://127.0.0.1", "169.254.1.1", "224.0.0.1", "::"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                api.validate_host(host)

    def test_status_validation(self):
        self.assertEqual(api.validate_status(sample())["state"]["health"], 20)
        patches = [{"api_version": 2}, {"entities": [{}]}, {"state": {"token": "private"}},
                   {"state": {"health": float("nan")}}, {"state": {"health": True}},
                   {"events": [{"id": 1, "event_type": "shell"}]}, {"events": "bad"},
                   {"sample_age_seconds": -1}, {"command_results": [{}]}]
        for patch in patches:
            with self.subTest(patch=patch), self.assertRaises(api.InvalidResponse):
                api.validate_status(sample() | patch)
        duplicate = sample()
        duplicate["entities"] *= 2
        with self.assertRaises(api.InvalidResponse):
            api.validate_status(duplicate)


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.data = sample()
        self.requests = []
        self.mode = "normal"

        async def handler(request):
            self.requests.append((request.path, request.headers.get("Authorization")))
            if self.mode == "auth":
                return web.Response(status=401, text="must not expose remote text")
            if self.mode == "redirect":
                raise web.HTTPFound("http://8.8.8.8/")
            if self.mode == "large":
                return web.Response(text="x"*131073)
            if self.mode == "invalid":
                return web.Response(text="not json")
            if request.method == "POST":
                if self.mode == "denied":
                    return web.json_response({"error": "not_permitted"}, status=403)
                data = await request.json()
                return web.json_response({"request_id": data["request_id"], "status": "queued"}, status=202)
            return web.json_response(self.data)

        app = web.Application()
        app.router.add_route("*", "/api/v1/{tail:.*}", handler)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        self.session = aiohttp.ClientSession()
        self.api = api.FumboApi(self.session, "127.0.0.1", port, "c"*64)

    async def asyncTearDown(self):
        await self.session.close()
        await self.runner.cleanup()

    async def test_status_and_command(self):
        self.assertEqual((await self.api.status())["device"]["id"], "a"*32)
        self.assertEqual(len(await self.api.command(self.data["session"], "auto_eat", "ON")), 36)
        self.assertTrue(all(auth == "Bearer "+"c"*64 for _,auth in self.requests))

    async def test_auth_is_safe(self):
        self.mode = "auth"
        with self.assertRaises(api.InvalidAuth) as caught:
            await self.api.status()
        self.assertNotIn("must not expose", str(caught.exception))

    async def test_no_redirect(self):
        self.mode = "redirect"
        with self.assertRaises(api.CannotConnect):
            await self.api.status()
        self.assertEqual(len(self.requests), 1)

    async def test_bounded_response(self):
        self.mode = "large"
        with self.assertRaises(api.InvalidResponse):
            await self.api.status()

    async def test_bad_json(self):
        self.mode = "invalid"
        with self.assertRaises(api.InvalidResponse):
            await self.api.status()

    async def test_denied_is_not_retried(self):
        self.mode = "denied"
        with self.assertRaises(api.CommandRejected):
            await self.api.command(self.data["session"], "auto_eat", "ON")
        self.assertEqual(len(self.requests), 1)


if __name__ == "__main__":
    unittest.main()
