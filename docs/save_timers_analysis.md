# `save_timers` Call Analysis (from dumps)

This note is based on concrete captures in:

- `docs/dumps/create-timer.txt`
- `docs/dumps/edit-timer.txt`
- `docs/dumps/enable-timer.txt`
- `docs/dumps/disable-timer.txt`
- `docs/dumps/delete-timer.txt`

No official Webasto documentation was used.

## Current implementation scope

- In-scope for upcoming module work: `simple` timers only.
- Out-of-scope for now: `smart` timers, due to lack of access to a setup that supports/verifies smart-timer behavior.
- `smart` observations in this document are kept as protocol notes, not as active implementation targets.

## Endpoint and method

- URL: `https://my.webastoconnect.com/webapi/save_timers`
- Method: `POST`
- Observed header: `X-Requested-With: XMLHttpRequest`
- Session appears cookie-based (`hssess-webclient` in captures), but cookie values are intentionally omitted.

## Top-level request shape

All observed requests send JSON with this top-level structure:

```json
{
  "line": "OUTH",
  "timers": []
}
```

Observations:

- `line` is `"OUTH"` in all captures.
- `timers` is a complete list of timers in the current state.
- Create/edit/delete operations resend the full list, not a partial delta.

## Timer types and fields

## `simple` timer (observed)

```json
{
  "type": "simple",
  "start": 1380,
  "duration": 1800,
  "repeat": 72,
  "location": {"lat": "REDACTED_LAT", "lon": "REDACTED_LON"},
  "enabled": true
}
```

Observed fields:

- `type` (string), value `"simple"`
- `start` (int)
- `duration` (int)
- `repeat` (int)
- `location.lat` (string), `location.lon` (string)
- `enabled` (bool) appears in create/enable/disable/delete

## `smart` timer (observed)

```json
{
  "type": "smart",
  "start": 830,
  "repeat": 30,
  "maxDuration": 3000,
  "comfortLevel": 5,
  "location": {"lat": "REDACTED_LAT", "lon": "REDACTED_LON"},
  "departure": 830
}
```

Observed fields:

- `type` (string), value `"smart"`
- `start` (int)
- `repeat` (int)
- `maxDuration` (int)
- `comfortLevel` (int)
- `departure` (int)
- `location.lat` (string), `location.lon` (string)

Status:

- Observed in captures, but currently out-of-scope for implementation.

## Operation behavior inferred from payloads

- Create timer:
  - Send existing timers plus the new timer in the same `timers` array.
- Edit timer:
  - Resend the full `timers` array, with one timer object modified.
  - Preserve the same timer ordering as returned by the API and only change the target object fields.
- Enable/disable timer:
  - Same timer object, only `enabled` toggles between `true` and `false`.
- Delete timer:
  - Send `timers` without the deleted timer.
  - If no timers remain: `timers: []`.

## Confirmed examples from dumps

- Create with 1 timer: `timers` contains one `simple` object.
- Create with 2 timers: `timers` contains two `simple` objects, including one with `repeat: 0`.
- Delete down to 0 timers: `timers: []`.
- Disable/enable: identical payload except `enabled`.
- Edit to smart/departure mode: `type` is `"smart"`, and `maxDuration`, `comfortLevel`, `departure` appear.

## Repeat bitmask mapping (confirmed)

From a capture with seven one-day timers (one per weekday), the following mapping is confirmed:

- `64` = Monday
- `1` = Tuesday
- `2` = Wednesday
- `4` = Thursday
- `8` = Friday
- `16` = Saturday
- `32` = Sunday

Examples:

- `repeat: 72` (`64 + 8`) = Monday + Friday
- `repeat: 31` (`1 + 2 + 4 + 8 + 16`) = Tuesday-Saturday

## Known uncertainties (not proven by these captures alone)

- Response contract (status codes/body) is not documented in these dump files.

## Field requirements

- For `simple` timers in current scope, `location` is optional.
- Observed on 2026-03-07: API accepted a `simple` timer payload without `location` and returned it without `location`.
- `enabled` must always be explicitly set to either `true` (enabled) or `false` (disabled).

## Duration semantics

- `duration` is considered unbounded (no practical upper limit enforced by the API contract used here).
- Numeric timer values are valid only when strictly greater than `0`.

## Concurrency semantics

- Concurrent timer saves follow a `last write wins` model.

## Time semantics

- `start` is interpreted as a UTC-based time value.
- `departure` is observed for `smart` timers only (currently out-of-scope).

## Minimum capture set recommended before coding API-level behavior

1. One successful create/edit/delete flow with full request + full response payloads.
2. One explicit auth failure example for `save_timers`.
3. One validation failure example (malformed/invalid timer payload).

## Suggested next implementation steps

1. Introduce an internal Python timer model for `simple` timers.
2. Build a serializer that always emits full `{"line":"OUTH","timers":[...]}` payloads.
3. Add field/type validation before POST.
4. Derive supported output lines from API data instead of hardcoding assumptions.
5. Keep module input API as TBD:
   - likely accept a single timer object from the caller
   - internally merge it into the full API-fetched timer list
   - preserve API order and send the full array in `save_timers`
