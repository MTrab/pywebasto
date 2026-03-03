# `save_timers` Call Analysis (from dumps)

This note is based on concrete captures in:

- `docs/dumps/create-timer.txt`
- `docs/dumps/edit-timer.txt`
- `docs/dumps/enable-timer.txt`
- `docs/dumps/disable-timer.txt`
- `docs/dumps/delete-timer.txt`

No official Webasto documentation was used.

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

## Known uncertainties (not proven by these captures alone)

- Final bit mapping of `repeat`.
- Whether `enabled` is required in every edit scenario (one edit example omits it).
- Response contract (status codes/body) is not documented in these dump files.

## Duration semantics

- `duration` and `maxDuration` are considered unbounded (no practical upper limit enforced by the API contract used here).
- Numeric timer values are valid only when strictly greater than `0`.

## Concurrency semantics

- Concurrent timer saves follow a `last write wins` model.

## Time semantics

- `start` and `departure` are interpreted as UTC-based time values.

## Missing for a solid analysis

The current captures are enough to draft payload builders, but not enough to claim a complete API contract.
To reach a strong, implementation-grade analysis, the following evidence is still needed:

1. `repeat` bitmask mapping proof
   - Record one-day-only timers for each weekday (7 captures), then map mask bits deterministically.
2. Field requirement matrix
   - Verify which fields are required/optional per timer type (`simple` vs `smart`).
   - Specifically verify whether `enabled` is optional on edit, and defaults when omitted.
3. Limits and validation rules
   - Max number of timers and allowed `comfortLevel` range.
   - Backend handling of very large values (with `0` and negative values treated as invalid).

## Minimum capture set recommended before coding API-level behavior

1. One successful create/edit/delete flow with full request + full response payloads.
2. One explicit auth failure example for `save_timers`.
3. One validation failure example (malformed/invalid timer payload).
4. Seven weekday captures to lock `repeat` mapping.

## Suggested next implementation steps

1. Introduce internal Python timer models for `simple` and `smart`.
2. Build a serializer that always emits full `{"line":"OUTH","timers":[...]}` payloads.
3. Add field/type validation before POST.
4. Derive supported output lines from API data instead of hardcoding assumptions.
5. Keep module input API as TBD:
   - likely accept a single timer object from the caller
   - internally merge it into the full API-fetched timer list
   - preserve API order and send the full array in `save_timers`
6. Add capture-based verification of repeat behavior if UI must show accurate "next run" times.
