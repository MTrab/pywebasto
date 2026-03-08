# Webasto Connect Protocol Notes (Reverse Engineered)

This document describes protocol behavior inferred from the current `pywebasto` codebase.
It is not official Webasto documentation.

## Evidence and Confidence

- Source of truth for this document:
  - `pywebasto/consts.py`
  - `pywebasto/enums.py`
  - `pywebasto/__init__.py`
  - `pywebasto/device.py`
- Confidence:
  - High: endpoint paths, command strings, high-level call flow
  - Medium: payload shape for settings updates
  - Medium/Low: full response schema (only fields parsed in code are documented here)

For protocol changes, always validate with sanitized network captures from `my.webastoconnect.com`.

## Base URL and Transport

- Base URL: `https://my.webastoconnect.com/webapi`
- HTTP method used by client: `POST` for all endpoints
- Timeout: `60` seconds (`aiohttp.ClientTimeout(total=60)`)

## Headers and Session Cookies

Client sends:

- `User-Agent`: browser-like static value
- Optional `Cookie` header:
  - `hssess=<value>;` or
  - `hssess-webclient=<value>;`

Cookie behavior in client:

1. First successful response may set `hssess` and/or `hssess-webclient`.
2. Client stores cookie values.
3. Subsequent requests include one cookie:
   - prefers `hssess-webclient` when available
   - otherwise uses `hssess`

## Endpoint Map

All paths are relative to `/webapi`.

| Enum | Path | Purpose |
|---|---|---|
| `LOGIN` | `/login` | Authenticate with username/password |
| `COMMAND` | `/command` | Send output ON/OFF command |
| `GET_DATA` | `/get_service_data?poll=true` | Fetch service data with poll |
| `GET_DATA_NOPOLL` | `/get_service_data?poll=false` | Fetch service data without poll |
| `POST_SETTING` | `/post_settings` | Update settings |
| `GET_SETTINGS` | `/get_settings` | Read settings |
| `CHANGE_DEVICE` | `/change_device` | Switch active device context |

## Request Payloads

## Login

- Endpoint: `/login`
- Payload type in client: form-like key/value
- Fields:
  - `username`
  - `password`

## Change Active Device

- Endpoint: `/change_device`
- Payload:
  - `device`: device ID string

## Command Endpoint

- Endpoint: `/command`
- Payload type in client: plain string command
- Known command values:
  - `OUT H ON`
  - `OUT H OFF`
  - `OUT V ON`
  - `OUT V OFF`
  - `OUT 1 ON`
  - `OUT 1 OFF`
  - `OUT 2 ON`
  - `OUT 2 OFF`

## Settings Update (`/post_settings`)

Client sends a JSON string (not dict object) as request body.

Common top-level structure:

```json
{
  "device_settings": {},
  "service_settings": {},
  "location_events": null,
  "air_heater": {}
}
```

Observed variants:

1. Ventilation mode / main timeout update:
   - `device_settings`: `OUTV_timeout_*`, `OUTH_timeout_*`, `webasto_emul_mode`
   - `service_settings`: `OUTH_on`, `OUTV_on`, `heater_mode`, names/icons
2. AUX timeout update:
   - `device_settings`: `<OUT1|OUT2>_function`, `<OUT1|OUT2>_timeout_*`
   - `service_settings`: `<OUT1|OUT2>_on`, `<OUT1|OUT2>_name`, `<OUT1|OUT2>_icon`
3. Low-voltage cutoff:
   - `device_settings.low_voltage_cutoff`
4. Temperature compensation:
   - `device_settings.ext_temp_comp`

## Response Handling in Client

- Client expects JSON only for endpoints where enum name contains `GET`:
  - `/get_service_data?...`
  - `/get_settings`
- Other endpoints are treated as success/failure by HTTP status only.

Status handling:

- `200`: marks client as authorized
- `401`: raises `UnauthorizedException`
- `403`: schedules async retry after 30s (current implementation retries in background)
- Other non-200: raises `InvalidRequestException` with response text

## Device Discovery and Data Extraction

`update()` flow in client:

1. Call `GET_DATA_NOPOLL`.
2. Read `account_info.devices`.
3. For each device:
   - `CHANGE_DEVICE`
   - `GET_SETTINGS`
   - `GET_DATA` (poll=true)
   - `GET_DATA_NOPOLL` (poll=false)

Device list structure expected by code:

- `account_info.devices` is an array of arrays:
  - index `0`: device ID
  - index `1`: device name

## Parsed Fields from `GET_DATA`

Fields consumed by `WebastoDevice.last_data`:

- `temperature` (string ending in `C` or `F`, parsed to int value + unit)
- `voltage` (string, trailing unit removed, parsed to float)
- `location` (dict with at least `state`; if `state != "ON"` location is treated as disabled)
- `connection_lost` (bool; observed `false` online, `true` when device is offline from cloud)
- `outputs` (array)
  - `line` values used: `OUTH`, `OUTV`, `OUT1`, `OUT2`
  - `state` used for boolean output state
  - `icon` used for icon properties
  - `name` used for output name properties
  - `ontime` used for main output end-time calculations

## Parsed Fields from `GET_DATA_NOPOLL`

Fields consumed by `WebastoDevice.dev_data`:

- `subscription.expiration` (Unix timestamp converted to `datetime`)
- `connection_lost` (bool; used as cloud connectivity indicator)

## Parsed Fields from `GET_SETTINGS`

Expected structure:

- `settings_tab`: array of groups
  - group object fields used:
    - `group`
    - `options` (array)
  - option object fields used:
    - `key`
    - `value`
    - `timeout` (for output timeout values)

Keys read by current code:

- In group `general`:
  - `allow_GPS`
  - `low_voltage_cutoff`
  - `ext_temp_comp`
- In groups `webasto` / `outputs`:
  - timeout keys `OUTH`, `OUTV`, `OUT1`, `OUT2`

## Known Gaps (Need Capture Validation)

- Exact content type sent/required for each endpoint
- Full response bodies for non-GET endpoints
- Whether both cookie names are always valid across accounts/regions
- Retry semantics for `403` and whether request replay is always safe
- Optional or region-specific fields not parsed by current implementation

## Capture Checklist for Future API Updates

When decoding new behavior, capture and sanitize:

1. Request URL + method
2. Request headers (redact secrets/cookies)
3. Request payload
4. Response status + response payload
5. Cookie set/refresh behavior
6. Sequence ordering between related calls
