# Local API v1

Made by Fumbo. Intended for trusted LANs only; HTTP is not encrypted.

The client hosts the server itself. Default port: `25809`. No MQTT required.
All endpoints require `Authorization: Bearer <64-character pairing token>`.
Token values never belong in URLs. Browser `Origin` requests are rejected and
there is no CORS allowlist. Only private/loopback peer addresses are accepted;
the client may further restrict access to a configured HA IP.

## GET /api/v1/status

Response fields:

- `api_version`: integer `1`
- `device`: stable `id` (32 lowercase hex), `name`, `client_version`
- `boot_id`: UUID identifying this Minecraft process
- `session`: UUID invalidated on client configuration or world changes
- `sample_age_seconds`: age of the last client-thread sample, or 999 before a sample
- `entities`: enabled descriptors with `key`, `platform`, `name`, `icon`, `unit`
- `state`: flat map of only the enabled state keys, strings/numbers
- `events`: up to 64 ordered `{id, event_type}` events for this process
- `command_results`: up to 128 recent `{request_id, command, value, status}` records

States use `ON`/`OFF` for binary values. Entity keys and types are listed in
`custom_components/fumboclient/const.py`. Disabled privacy/permission categories
are omitted; an HA entity that previously existed becomes unavailable.

State collection occurs on the Minecraft client thread once per second. The
integration defaults to polling every 5 seconds (configurable 2–30). Data older
than 15 seconds is marked unavailable by the integration. Event IDs are monotonic
within a `boot_id`. Establish a baseline on setup/new boot to avoid historical replay.

## POST /api/v1/command

Content type: `application/json`; maximum body size: 2048 bytes. Exactly four
string fields are accepted:

```json
{
  "session": "UUID_FROM_STATUS",
  "request_id": "NEW_CANONICAL_UUID",
  "command": "auto_eat",
  "value": "ON"
}
```

Only allowlisted actions with the matching local master/category permission are
accepted. `ON`/`OFF` for switches, `PRESS` for buttons, `Auto`/`AFK`/`Aktiv` for
`afk_mode`, and 1–160 non-control/non-formatting characters for `notify`.

`202` means queued, **not executed**. Reusing a recent request ID with the same
command/value returns its existing result instead of executing it again; reuse
with different parameters is rejected. Never retry blindly after network failure.
Poll status for `executed`, `rejected` or `failed`. Client-thread queue capacity is
16, with a five-second expiry. Old-session or permission-revoked commands cannot
execute. Switching worlds may cancel a pending request; check its result/session.

Common errors: `400` malformed, `401` token, `403` permission/peer/origin,
`404` path, `405` method, `409` stale session/request ID, `413` size,
`415` content type, `429` queue full, `503` reconfiguring. Error bodies are generic;
do not log pairing headers or full sensitive state/command responses.
