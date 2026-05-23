# ThermoConnect Android App Static Analysis

This document records static findings from `ThermoConnect_3.3.0_APKPure.apk`.
It is separate from `docs/protocol.md`, which describes the web API used by
`pywebasto`.

This file contains both static APK findings and a small number of manually
executed live checks against `control.webastoconnect.com`. Live observations are
called out explicitly and use placeholders instead of real client secrets,
device ids, and check ids.

## Scope and Evidence

- APK file: `ThermoConnect_3.3.0_APKPure.apk`
- App package: `embelin.webasto`
- App name: `ThermoConnect`
- Version: `3.3.0`
- Version code: `48`
- Static analysis tools used:
  - `unzip`
  - `strings`
  - `androguard` in an isolated local virtual environment under `.analysis/`

## Important Separation From Web API Notes

The Android app does not use the already documented `/webapi` paths as its
primary app backend in the static code inspected here.

The APK contains these app backend strings:

- `https://control.webastoconnect.com/`
- `remuc/mobile-api`

It also contains browser/deep-link strings such as:

- `https://my.webastoconnect.com`
- `https://my.webastoconnect.com/webastoconnect-dev`
- `https://my.webastoconnect.com/index.html?lang=<locale>`

Those browser URLs must not be treated as evidence that the Android app uses
the same `/webapi` protocol as the web client.

## Manifest Observations

Observed permissions include:

- `android.permission.INTERNET`
- `android.permission.ACCESS_NETWORK_STATE`
- `android.permission.CAMERA`
- `android.permission.ACCESS_COARSE_LOCATION`
- `android.permission.ACCESS_FINE_LOCATION`
- `android.permission.BLUETOOTH`
- `android.permission.BLUETOOTH_ADMIN`
- `android.permission.BLUETOOTH_CONNECT`
- `android.permission.BLUETOOTH_SCAN`
- `android.permission.POST_NOTIFICATIONS`
- `android.permission.RECEIVE_BOOT_COMPLETED`
- `android.permission.WAKE_LOCK`

Relevant app classes observed:

- `embelin.webasto.WebclientLogin`
- `embelin.webasto.MainActivity`
- `embelin.webasto.MyFcmListenerService`
- `embelin.webasto.activities.DeviceID`
- `embelin.webasto.fragment.AssocRequestFragment`
- `embelin.webasto.fragment.SubscriptionFragment`
- `embelin.webasto.room.AppDatabase`

The app includes ZXing barcode scanner classes and BLE-related classes. This
supports, but does not yet prove, that device onboarding may involve QR scanning
and/or Bluetooth.

## Network Manager Findings

The central app request builder appears to be the obfuscated class:

- `Ls8/b0;`

Its constructor loads these Android string resources:

- `server`: `https://control.webastoconnect.com/`
- `server_mobile_api`: `remuc/mobile-api`

The request wrapper appears to be:

- `Ls8/a0;`

Observed fields on `Ls8/a0;` include:

- `a`: request type integer
- `d`: first string parameter
- `e`: second string parameter / payload-like value
- `c`: built HTTP request object

The low-level HTTP builder sets explicit 10 second connect/read style timeouts
and uses:

- `GET` via `Lo6/c;->l(...)`
- `POST` via `Lo6/c;->m(...)`

For POST calls, the request body is created from `Ls8/a0;->a()` using
`La8/a;->b(String)`, which appears to wrap the string as request content.

## Static Endpoint Map

The following map was decoded from the packed switch in `Ls8/b0;->b(Ls8/a0;)Z`.
Request type numbers are implementation details from the APK, not public API.

| Request type | Method | Static path |
| --- | --- | --- |
| `0` | `GET` | `/client_id` |
| `1` | `POST` | `/register` |
| `2` | `POST` | `/info` |
| `3` | `GET` | `/info` |
| `4` | `POST` | `/assoc2` |
| `5` | `POST` | `/cmd` |
| `6` | `POST` | `/setandroiduri` |
| `7` | `POST` | `/setassoc` |
| `8` | `GET` | `/assocstatus2` |
| `9` | `POST` | `/timers2` |
| `10` | `GET` | `/timers2` |
| `11` | `GET` | `/status` |
| `12` | `POST` | `/assoc3` |
| `13` | `POST` | `/confirmmsg` |
| `14` | `GET` | `/location2` |
| `15` | `GET` | `/assocreqs` |
| `16` | `POST` | `/ack` |
| `17` | `POST` | `/updatelang` |
| `18` | `GET` | `/seen` |
| `19` | `GET` | `/fleetpage` |
| `20` | `POST` | `/startevent` |
| `21` | `POST` | `/stopevent` |
| `22` | `POST` | `/updateevent` |
| `23` | `POST` | `/pinpointevent` |
| `24` | `POST` | `/assoc3` |
| `25` | `GET` | `/radminpermission` |
| `26` | `POST` | `/changeradminpermission` |
| `27` | `POST` | `/assoc3` |
| `28` | `POST` | `/assoc3` |
| `29` | `POST` | `/assoc3` |
| `30` | `GET` | `/webclientlogincode` |
| `31` | `POST` | `/approveterms` |
| `32` | `GET` | `/all?api_v=8` |
| `33` | `POST` | `/journal` |
| `34` | `POST` | `/heatermode` |
| `35` | `POST` | `/delete-message` |
| `36` | `POST` | `/location-services` |
| `37` | `POST` | `/cronus-info` |
| `38` | `POST` | `/term-approval` |
| `39` | `POST` | `/term-approval-cronus` |
| `40` | `POST` | `/assoc3` |

Observed URL construction patterns:

- Mobile API pattern:
  - `https://control.webastoconnect.com/remuc/mobile-api/client/<clientId>/<path>`
  - `https://control.webastoconnect.com/remuc/mobile-api/client/<clientId>/device/<deviceId>/<path>`
- Remote pattern:
  - `https://control.webastoconnect.com/remote/client/<clientId>/device/<deviceId>/<path>`

Which pattern is used varies by request type. This table documents static path
selection only; capture evidence is still needed before implementing any of
these as fact in `pywebasto`.

## Client Registration

`Ls8/b0;->f()` generates a random UUID, removes hyphens, and sends:

```json
{
  "secret": "<generated-client-secret>"
}
```

through request type `1`, which maps to `POST /register`.

The generated value is stored locally under the key `clientSecret`.

Static code also reads local keys named:

- `clientId`
- `clientSecret`
- `fcmToken`
- `termsApproved`
- `lang`

These are APK-local storage keys observed in code. They are not configuration
environment variables for this repository.

## Candidate App Backend Flow

This is the concrete app-backend flow indicated by static analysis and limited
manual checks. Unverified steps must still be treated as candidate sequence
items.

### 1. Register a mobile client

If no local `clientId` / `clientSecret` exists, the app appears to:

1. Generate a random UUID.
2. Remove hyphens.
3. Store it locally as `clientSecret`.
4. Fetch a server-issued client id.
5. Send request type `1`.

Verified manually on 2026-05-23:

```http
GET https://control.webastoconnect.com/remuc/mobile-api/client_id
```

The returned `clientId` is then used in:

```http
POST https://control.webastoconnect.com/remuc/mobile-api/client/<clientId>/register
```

Verified JSON body shape:

```json
{
  "secret": "<generated-client-secret>"
}
```

Manual verification result:

- `POST /remuc/mobile-api/client/<clientId>/register` returned `200 OK` with
  the JSON body shape above.

Follow-up implementation test on 2026-05-23:

- `/register` returned `403 Forbidden` for the same body unless
  `Content-Type: application/json` was set.
- This differs from command, association, mode, timer, and location POSTs, which
  were live-tested with raw UTF-8 bodies and no explicit JSON content type.

Inferred local app behavior:

- app stores the fetched `clientId`
- app stores the generated `clientSecret`

Capture needed:

- exact response body
- whether any response headers are relevant to later calls

Note: an earlier draft shortened this to `/remuc/mobile-api/register`. That
path is not what the static request builder constructs.

### Authentication for registered-client calls

Verified by static analysis of `Ls8/b0;->b(...)` and `Lr5/b;->i(...)`:

- request type `0` (`GET /client_id`) is sent without Authorization
- request type `1` (`POST /register`) is sent without Authorization
- all other built requests set:

```http
Authorization: <clientSecret>
```

`clientSecret` is the same hyphen-free UUID value sent as `secret` during
registration.

### Header behavior

Static APK evidence from the Google HTTP client classes used by the app:

- `Lr5/b;` initializes `Accept-Encoding` to `gzip`.
- `Lr5/d.a()` sets `User-Agent` to
  `Google-HTTP-Java-Client/1.24.1 (gzip)` when no user-agent is already set.
- `Ls8/b0.b(...)` adds the raw `clientSecret` as the `Authorization` header for
  all request types except `0` (`GET /client_id`) and `1` (`POST /register`).
- `La8/a.b(String)` wraps POST bodies as UTF-8 bytes. No app-specific JSON
  `Content-Type` header is set in this wrapper.

Practical header set for app-backend calls after registration:

```http
Authorization: <clientSecret>
Accept-Encoding: gzip
User-Agent: Google-HTTP-Java-Client/1.24.1 (gzip)
```

Live tests in this analysis succeeded with only `Authorization` explicitly set.
Treat `Accept-Encoding` and `User-Agent` as app-compatible headers to mirror the
Android client, not currently as proven server requirements.

Implementation note: if we add app-backend support in `pywebasto`, send
`User-Agent: Google-HTTP-Java-Client/1.24.1 (gzip)` by default for this backend
unless future captures show that the Android app uses a different value.

For app-backend POSTs, do not assume `Content-Type: application/json` is
required. The Android app sends raw UTF-8 bodies through `La8/a`; live tests for
commands, heater mode, association, and timers succeeded without explicitly
setting a JSON content type.

### 2. Send app/build information

After registration, the app can send request type `2`:

```http
POST https://control.webastoconnect.com/remuc/mobile-api/client/<clientId>/info
```

Observed payload source:

- app/build string built from Android app version/build date resources

This is app info, not device info.

### 3. Register Android push token

If `fcmToken` exists locally, the app sends request type `6`:

```http
POST https://control.webastoconnect.com/remuc/mobile-api/client/<clientId>/setandroiduri
```

Observed payload source:

- local `fcmToken`

Capture needed:

- exact payload format
- whether push registration is mandatory for association completion

### 4. Fetch account/device data

The main app data fetch appears to be request type `32`:

```http
GET https://control.webastoconnect.com/remuc/mobile-api/client/<clientId>/all?api_v=8
Authorization: <clientSecret>
```

Static code suggests this is the primary candidate for reading the device list,
device state, settings, timers, messages, and local association state.

Verified manually on 2026-05-23 for a newly registered client with no associated
devices:

```json
{
  "messages": [],
  "devices": [],
  "android_version_available": "2.41",
  "ios_version_available": "2.4"
}
```

Capture needed:

- full response schema for a client with one associated device
- where device id, check id, name, status, outputs, timers, temperature,
  voltage, location, and subscription data appear
- whether response includes all devices for the registered mobile client

### 5. Send output commands

Commands appear to use request type `5`:

```http
POST https://control.webastoconnect.com/remote/client/<clientId>/device/<deviceId>/cmd
Authorization: <clientSecret>
```

Static analysis of `Ls8/b0;->b(...)` shows the APK sends the request payload
string directly as UTF-8 body content for `/cmd`. It does not wrap the command
in JSON at this layer.

Observed command strings include:

- `OUT H ON`
- `OUT H OFF`
- `TEMP <line> <value>`
- `WB LEVEL <line> <value>`
- `WB MODE <line> <ECO|BOOST|NORMAL>`

Manual verification result on 2026-05-23:

```http
POST https://control.webastoconnect.com/remote/client/<clientId>/device/<deviceId>/cmd
Authorization: <clientSecret>
```

with raw body:

```text
OUT H ON
```

returned:

- status: `200 OK`
- response body: empty

Follow-up `/all?api_v=8` showed the `OUTH` output changed to:

```json
{
  "line": "OUTH",
  "state": "ON",
  "ontime": "<timestamp>"
}
```

Second manual verification on 2026-05-23:

```http
POST https://control.webastoconnect.com/remote/client/<clientId>/device/<deviceId>/cmd
Authorization: <clientSecret>
```

with raw body:

```text
OUT H OFF
```

returned:

- status: `200 OK`
- response body: empty

Follow-up `/all?api_v=8` showed the `OUTH` output changed back to:

```json
{
  "line": "OUTH",
  "state": "OFF",
  "ontime": 0
}
```

Capture needed:

- exact command strings for ventilation, AUX, and air-heater modes
- response body and failure modes
- whether duplicate command retries are unsafe

### 6. Change heater mode

Heater mode changes appear to use request type `34`:

```http
POST https://control.webastoconnect.com/remuc/mobile-api/client/<clientId>/heatermode
Authorization: <clientSecret>
```

Static analysis of `Ls8/m.g0(...)` shows the app sends this when the output
mode has changed:

```json
{
  "dev_id": "<deviceId>",
  "mode": 0
}
```

Observed mapping from app code:

- `mode: 0` when the selected output mode is `"heating"`
- `mode: 1` when the selected output mode is `"ventilation"`

The app UI stores the current mode as a string in the output JSON field
`mode`, using values such as:

- `heating`
- `ventilation`

When the user toggles from heating to ventilation, `Ls8/m.onClick(...)` changes
the local output JSON field:

```json
{
  "mode": "ventilation"
}
```

Then `Ls8/m.g0(...)` sends `/heatermode` with:

```json
{
  "dev_id": "<deviceId>",
  "mode": 1
}
```

When toggling back to heating, it sends:

```json
{
  "dev_id": "<deviceId>",
  "mode": 0
}
```

This flow is static-analysis verified but not yet live-verified.

Manual verification on 2026-05-23 confirmed the URL above. An earlier attempt
with `/client/<clientId>/device/<deviceId>/heatermode` returned `404 Not Found`;
the app-built endpoint does not include `/device/<deviceId>` in the path.

Ventilation mode request:

```json
{
  "dev_id": "<deviceId>",
  "mode": 1
}
```

returned:

- status: `200 OK`
- response body: small HTML `200 OK` page

Follow-up `/all?api_v=8` showed `OUTV` moved into `outputs` and `OUTH` moved
into `disabled_outputs`.

Heating mode request:

```json
{
  "dev_id": "<deviceId>",
  "mode": 0
}
```

returned:

- status: `200 OK`
- response body: small HTML `200 OK` page

Follow-up `/all?api_v=8` showed `OUTH` moved back into `outputs` and `OUTV`
moved back into `disabled_outputs`.

### 7. Timers

Static APK evidence:

- `TimerListFragment.c(String)` builds the timer-save body.
- request type `9`: `POST /remote/client/<clientId>/device/<deviceId>/timers2`
- request type `10`: `GET /remote/client/<clientId>/device/<deviceId>/timers2`
- authorization uses the raw `clientSecret` header, same as other non-register
  app-backend requests.

App-backend timer save body:

```json
{
  "output": "H",
  "timers": []
}
```

Important difference from the web API:

- web API `/save_timers` uses `"line": "OUTH"`.
- Android app backend `/timers2` uses the last character of the output line:
  - `OUTH` -> `"H"`
  - `OUTV` -> `"V"`
  - `OUTA` -> `"A"`
  - `OUT1` -> `"1"`
  - `OUT2` -> `"2"`

The app sends the full timer list for the selected output. Create, edit,
enable/disable, and delete are therefore full-list replacements, not partial
delta operations.

Observed app-built simple timer fields:

```json
{
  "repeat": 0,
  "type": "simple",
  "start": 135,
  "duration": 60,
  "enabled": false
}
```

`start` is stored as minutes after midnight in UTC. The Android UI converts
this to local time when displaying timers. For example, during Danish summer
time, local Tuesday 04:15 is sent as `start: 135` because 04:15 CEST is 02:15
UTC.

Observed app-built smart timer fields:

```json
{
  "repeat": 30,
  "type": "smart",
  "departure": 830,
  "maxDuration": 3000,
  "comfortLevel": 5,
  "location": {
    "lat": 0.0,
    "lon": 0.0
  },
  "enabled": true
}
```

`location` is only added when both latitude and longitude exist in the
`ControlTimer` object.

Live test evidence on 2026-05-23:

1. Read current state with `/all?api_v=8`; `OUTH` had one timer.
2. `GET /timers2` returned `200 OK` with body `[]`.
3. `POST /timers2` with
   `{"output":"H","timers":[<original>,<disabled-test-timer>]}`
   returned `200 OK`.
4. Follow-up `/all?api_v=8` showed two `OUTH` timers and the disabled test
   timer was present.
5. `POST /timers2` with the original timer list returned `200 OK`.
6. Follow-up `/all?api_v=8` showed one `OUTH` timer and the disabled test
   timer was gone.

Deletion flow:

```json
{
  "output": "H",
  "timers": [
    "<all remaining timers except the deleted one>"
  ]
}
```

If all timers are deleted for an output, send `"timers": []`.

Follow-up correction on 2026-05-23:

- A timer sent as `repeat: 2`, `start: 255`, `duration: 7200` appeared in the
  Android app as Tuesday 06:15 in Denmark.
- Replacing the same timer with `start: 135` was accepted with `200 OK`, and
  `/all?api_v=8` confirmed the old `start: 255` timer was removed and the
  corrected `start: 135` timer was present.

Related app call:

- request type `37`: `POST /remuc/mobile-api/client/<clientId>/cronus-info`

### 8. Location

The app backend exposes location through both the main `/all?api_v=8` response
and a dedicated device endpoint.

Main data response:

```json
{
  "devices": [
    {
      "location_services": "ON",
      "location": {
        "state": "ON",
        "lat": "<redacted>",
        "lon": "<redacted>",
        "timestamp": "<redacted>"
      }
    }
  ]
}
```

Live read-only verification on 2026-05-23 confirmed:

- `location_services` was present on the device object.
- `location.state` was present.
- `location.lat` and `location.lon` were present when location was enabled.
- `location.timestamp` was present.

Dedicated location endpoint:

```http
GET https://control.webastoconnect.com/remote/client/<clientId>/device/<deviceId>/location2
Authorization: <clientSecret>
```

This maps to request type `14`.

Live read-only verification returned `200 OK` with a plain-text body shaped like:

```text
GPSSTATE:ON ALT:<redacted> BEARING:<redacted> DATE:<redacted> TIME:<redacted> POSITION:<redacted_lat>,<redacted_lon>
```

Location services toggle:

```http
POST https://control.webastoconnect.com/remuc/mobile-api/client/<clientId>/location-services
Authorization: <clientSecret>
```

This maps to request type `36`.

Static APK evidence from `La9/a.o(String, boolean)` shows this body:

```json
{
  "dev_id": "<deviceId>",
  "state": "ON"
}
```

For disabling:

```json
{
  "dev_id": "<deviceId>",
  "state": "OFF"
}
```

The app stores the same state locally under a key shaped like
`locationServices<deviceId>` before sending the backend request.

Live toggle verification on 2026-05-23:

1. Initial `/all?api_v=8` state:
   - `location_services: "ON"`
   - `location.state: "ON"`
   - `location.lat` and `location.lon` present
2. `POST /location-services` with `state: "OFF"` returned `200 OK`.
3. Follow-up `/all?api_v=8` showed:
   - `location_services: "OFF"`
   - `location.state: "DISABLED"`
   - no `lat` / `lon`
4. `POST /location-services` with `state: "ON"` returned `200 OK`.
5. Follow-up `/all?api_v=8` showed:
   - `location_services: "ON"`
   - `location.state: "WAITING_FOR_LOCATION"`
   - no `lat` / `lon` immediately after enabling

Enabling location services appears to be asynchronous: the backend accepts the
setting immediately, but a fresh GPS position may not be available immediately.

## Minimum Requirements Before Implementing App Backend Support

To use the Android app backend as a real data and command source in
`pywebasto`, we need the following evidence:

1. A sanitized registration capture:
   - `/client_id`
   - `/register`
   - exact response bodies and headers
2. A sanitized app setup capture:
   - `/info`
   - `/setandroiduri`, if required
3. A sanitized data capture:
   - `/all?api_v=8`
   - response with one known device
4. Sanitized command captures:
   - heater on
   - heater off
   - ventilation mode change
   - one failed/invalid command if safely observable
5. A sanitized add-device capture:
   - `/assocreqs`
   - `/assocstatus2`
   - `/setassoc`
   - `/assoc2` / `/assoc3`
   - any FCM-driven `ASSOCREQ`, `ASSOCRESULT`, `ASSOCDONE` steps
6. Confirmation of auth/session behavior:
   - whether `clientId`/`clientSecret` are sent as URL path, header, body, or a
     request object header
   - whether cookies are used at all by the app backend
7. Rate behavior:
   - app polling interval for `/all?api_v=8`
   - whether commands are followed by forced refreshes

Without app captures or a broader set of controlled live observations, the app
backend can only be documented as a candidate protocol, not implemented as
supported behavior.

## Device Association Findings

Association-related endpoints observed:

- `GET /assocreqs`
- `POST /assoc2`
- `POST /assoc3`
- `GET /assocstatus2`
- `POST /assocstatus2`
- `POST /setassoc`

`embelin.webasto.fragment.AssocRequestFragment` is involved in handling
association requests.

Observed association actions:

- One path sends request type `7` (`POST /setassoc`) with:
  - first parameter: device id from `Ly8/e;->b`
  - payload-like string: `<clientId> none`
- Dialog click handlers also send request type `7` with payload-like suffixes:
  - `<value> none`
  - `<value> master`
- Another path sends request type `40` (`POST /assoc3`) with a JSON body that
  includes:
  - `checkId`
  - `msg`

The FCM listener handles association-related push message bodies:

- `ASSOCREQ`
- `ASSOCRESULT`
- `ASSOCDONE`

This suggests the add-device / association flow is at least partly asynchronous
and push-driven. A live app capture is required to confirm the exact sequence,
payloads, status values, and timing.

## Observed Device Association Flow

This section describes the device association flow from static analysis plus the
manually verified client registration and one live association attempt on
2026-05-23. These calls can change server-side association state, so do not run
them repeatedly.

Known prerequisite:

1. Fetch `clientId`:

```http
GET https://control.webastoconnect.com/remuc/mobile-api/client_id
```

2. Register that client with a generated/stored `clientSecret`:

```http
POST https://control.webastoconnect.com/remuc/mobile-api/client/<clientId>/register
```

```json
{
  "secret": "<generated-client-secret>"
}
```

Negative association test:

```http
POST https://control.webastoconnect.com/remote/client/<clientId>/device/<deviceId>/setassoc
Authorization: <clientSecret>
```

Observed body shape from `AssocRequestFragment.S()`:

```text
<clientId> none
```

Manual verification result on 2026-05-23 before `/assoc3`:

- status: `401 Unauthorized`
- response body:

```text
Client does not own this device
```

Follow-up reads after this call still returned no associated devices and
`assocstatus2` stayed `none`.

Manual verification result on 2026-05-23 after `/assoc3` had changed the
association status to `pending`:

- same request shape
- status: `401 Unauthorized`
- response body:

```text
Client does not own this device
```

Follow-up reads after this second call kept `assocstatus2` at `pending`.

Observed alternatives from dialog handlers:

```text
<value> none
<value> master
```

Open questions:

- whether `<value>` is always `clientId` or sometimes an association-request id
- whether `master` requests admin/master access
- whether `none` requests normal/non-admin access
- whether `/setassoc` is only used after an association request already exists
  or after the client already owns the device

Status / pending request checks:

```http
GET https://control.webastoconnect.com/remote/client/<clientId>/assocreqs
Authorization: <clientSecret>
```

Verified manually on 2026-05-23 for a newly registered client with no pending
association requests:

- status: `200 OK`
- response body: empty

```http
GET https://control.webastoconnect.com/remote/client/<clientId>/device/<deviceId>/assocstatus2
Authorization: <clientSecret>
```

Verified manually on 2026-05-23 for a newly registered client and known
unassociated device id:

- status: `200 OK`
- response body:

```text
none
```

Initial DeviceID/CheckID association request:

```http
POST https://control.webastoconnect.com/remote/client/<clientId>/device/<deviceId>/assoc3
Authorization: <clientSecret>
```

Observed JSON body shape from `AssocRequestFragment.onClick()`:

```json
{
  "checkId": "<checkId>",
  "msg": "<user-entered-message>"
}
```

For the new-device scanner/manual-entry flow, static analysis of `Lx8/f.S()`
shows the app:

1. creates a local device model with the entered/scanned `deviceId`
2. stores the entered `checkId` on that local model
3. marks the local association status as `new`
4. sends request type `40`, which maps to `/assoc3`

Observed JSON body shape from that flow:

```json
{
  "checkId": "<checkId>",
  "msg": ""
}
```

Manual verification result on 2026-05-23:

```http
POST https://control.webastoconnect.com/remote/client/<clientId>/device/<deviceId>/assoc3
Authorization: <clientSecret>
Content-Type: application/json
```

with body:

```json
{
  "checkId": "<checkId>",
  "msg": ""
}
```

returned:

- status: `200 OK`
- response body:

```text
body required
```

Despite that response body, follow-up reads showed server-side association state
changed:

```http
GET https://control.webastoconnect.com/remote/client/<clientId>/device/<deviceId>/assocstatus2
Authorization: <clientSecret>
```

returned:

```text
pending
```

and:

```http
GET https://control.webastoconnect.com/remuc/mobile-api/client/<clientId>/all?api_v=8
Authorization: <clientSecret>
```

returned a device entry with the sanitized shape:

```json
{
  "messages": [],
  "devices": [
    {
      "id": "<deviceId>",
      "assocStatus": "pending"
    }
  ],
  "android_version_available": "2.41",
  "ios_version_available": "2.4"
}
```

This is the first verified evidence that a user-provided DeviceID/CheckID pair
can create a pending association for a newly registered mobile client.

Second manual verification on 2026-05-23 used a non-empty message and no
explicit content type, which appears closer to the APK's raw UTF-8 request body:

```http
POST https://control.webastoconnect.com/remote/client/<clientId>/device/<deviceId>/assoc3
Authorization: <clientSecret>
```

with body:

```json
{
  "checkId": "<checkId>",
  "msg": "Association request"
}
```

returned:

- status: `200 OK`
- response body:

```text
pending
```

Follow-up reads still showed:

- `assocstatus2`: `pending`
- `/assocreqs`: empty body
- `/all?api_v=8`: device entry with `assocStatus: "pending"`

No owner-visible Web UI, existing app notification, push notification, or SMS
was observed by the user after the pending association was created.

After a short delay, the existing owner app did receive a notification. When the
user accepted that notification, the newly registered client changed state.

Manual verification result after owner acceptance on 2026-05-23:

```http
GET https://control.webastoconnect.com/remote/client/<clientId>/device/<deviceId>/assocstatus2
Authorization: <clientSecret>
```

returned:

```text
master
```

and:

```http
GET https://control.webastoconnect.com/remuc/mobile-api/client/<clientId>/all?api_v=8
Authorization: <clientSecret>
```

returned a full device entry with the sanitized shape:

```json
{
  "messages": [],
  "devices": [
    {
      "id": "<deviceId>",
      "check_id": "<checkId>",
      "assocStatus": "ok",
      "temperature": "<temperature>",
      "voltage": "<voltage>",
      "outputs": [
        {
          "line": "OUTH",
          "name": "Heater",
          "icon": "car_heat",
          "sound": false,
          "state": "OFF",
          "type": "water",
          "ontime": 0,
          "parking_heating_mode_available": true,
          "ventilation_mode_available": true,
          "eco_mode_available": false,
          "boost_mode_available": false,
          "water_heater_continuous_heating": false,
          "timers": [
            {
              "type": "simple",
              "repeat": 0,
              "start": 135,
              "duration": 5400,
              "enabled": false
            }
          ]
        },
        {
          "line": "OUTA",
          "name": "",
          "icon": "alert_on",
          "sound": false,
          "state": "ON",
          "type": "water",
          "ontime": 0,
          "parking_heating_mode_available": true,
          "ventilation_mode_available": true,
          "eco_mode_available": true,
          "boost_mode_available": true,
          "water_heater_continuous_heating": true,
          "timers": []
        }
      ],
      "inputs": [],
      "seen": "<seconds-or-age>",
      "location": {
        "state": "ON",
        "lat": "<redacted>",
        "lon": "<redacted>",
        "timestamp": "<timestamp>"
      },
      "assocreqs": [],
      "myremucpwpassing": false,
      "diagnosticmode": true,
      "journal": {},
      "subscription": {
        "status": "ok",
        "expiration": "<timestamp>",
        "message": ""
      },
      "nextEvent": {},
      "alarms": "CONF",
      "connection_lost": false,
      "vwarn": false,
      "call_supported": false,
      "location_services": "ON",
      "disabled_outputs": [
        {
          "line": "OUTV",
          "name": "Ventilation",
          "icon": "car_vent",
          "sound": false,
          "state": "OFF",
          "type": "water",
          "ontime": 0,
          "parking_heating_mode_available": true,
          "ventilation_mode_available": true,
          "eco_mode_available": false,
          "boost_mode_available": false,
          "water_heater_continuous_heating": false,
          "timers": []
        }
      ],
      "sw_version": "<version>",
      "hw_version": "<version>",
      "geofence_enabled": false,
      "term-approvals": [
        {
          "id": "privacy_policy",
          "approved": false,
          "current": 1
        },
        {
          "id": "tos",
          "approved": false,
          "current": 1
        },
        {
          "id": "ownership_transfer_agreement",
          "approved": false,
          "current": 1
        }
      ]
    }
  ],
  "android_version_available": "2.41",
  "ios_version_available": "2.4"
}
```

This verifies the full add-device flow:

1. register mobile client
2. send `/assoc3` with `checkId` and a non-empty `msg`
3. wait for owner app notification
4. owner accepts
5. new client reads `assocstatus2 = master`
6. new client reads `/all?api_v=8` with `assocStatus = ok`

## Observed Device Disassociation Flow

Static analysis shows a remove path in `AssocRequestFragment`.

The fragment layout wires two buttons:

- message button: sends `/assoc3`
- remove button: opens a confirmation dialog and then calls
  `AssocRequestFragment.S()`

`AssocRequestFragment.S()` first removes/updates the device in the local Room
database through `Ly8/c` with operation value `2`. It then checks the local
device status. If the local status matches:

```text
new|deleted|not_verified|failed
```

the method returns without sending a server request.

If the local status does not match that expression, for example an associated
device with local status `ok`, the method sends:

```http
POST https://control.webastoconnect.com/remote/client/<clientId>/device/<deviceId>/setassoc
Authorization: <clientSecret>
```

with body:

```text
<clientId> none
```

This is the same endpoint/body shape that returned `401 Client does not own
this device` before and during the pending association state. Static evidence
suggests the call is intended for an already associated client.

Manual verification result on 2026-05-23 after the client had been accepted and
`assocstatus2` returned `master`:

- status: `200 OK`
- response body: empty

Follow-up status check:

```http
GET https://control.webastoconnect.com/remote/client/<clientId>/device/<deviceId>/assocstatus2
Authorization: <clientSecret>
```

returned:

```text
none
```

and:

```http
GET https://control.webastoconnect.com/remuc/mobile-api/client/<clientId>/all?api_v=8
Authorization: <clientSecret>
```

returned:

```json
{
  "messages": [],
  "devices": [],
  "android_version_available": "2.41",
  "ios_version_available": "2.4"
}
```

This verifies that `/setassoc` with body `<clientId> none` disassociates the
current associated client from the device.

## Refresh And Push Behavior

No static evidence of WebSocket, Server-Sent Events, or another persistent event
stream was found in the APK strings or request builder. The observed refresh
model is:

- periodic polling through `/all?api_v=8`
- Firebase Cloud Messaging push events that trigger an immediate `/all?api_v=8`
  refresh

The central refresh method is `Ls8/b0;->c()`. It checks that both `clientId` and
`clientSecret` exist locally, then sends request type `32`:

```http
GET https://control.webastoconnect.com/remuc/mobile-api/client/<clientId>/all?api_v=8
Authorization: <clientSecret>
```

`MainActivity.w()` calls:

1. `Ls8/b0;->g()` for app info/lang setup
2. `Ls8/b0;->c()` for an immediate data refresh
3. schedules handler message `0` after `60000` ms

The handler class `Ls8/z;->handleMessage(...)` handles message `0` by:

1. calling `Ls8/b0;->c()`
2. scheduling message `0` again after `60000` ms

So the app's normal foreground polling interval appears to be 60 seconds.

The same handler has a separate message `4` path used around BLE/device detail
state. That path schedules itself after `10000` ms while relevant BLE state is
active; it is not evidence of cloud event streaming.

`Ls8/b0;->e(...)`, the network response handler, stores `lastFetchAll` when
processing `/all?api_v=8`. UI code in `Ls8/m.n0()` uses `lastFetchAll` to decide
whether a visible force-refresh control should be shown. The threshold observed
there is `300` seconds.

Some command/settings flows reset `lastFetchAll` to `0`, which appears to force
the next UI refresh to fetch fresh `/all?api_v=8` data.

`MyFcmListenerService.d(...)` handles FCM `RemoteMessage` data payloads. For
these message body prefixes, the app calls `Ls8/b0;->c()` immediately:

- `ASSOCREQ`
- `MESSAGES`
- `FLEETPAGE`
- `STATUS`
- some `ASSOCRESULT` / `ASSOCDONE` branches when the message references a known
  local device

For `STATUS`, the app also inspects the FCM `status` JSON payload and may create
or cancel Android notifications, including a heater-off action notification.

FCM token registration is request type `6`:

```http
POST https://control.webastoconnect.com/remuc/mobile-api/client/<clientId>/setandroiduri
Authorization: <clientSecret>
```

with the local `fcmToken` as the request body. This makes push-triggered refresh
available to the Android app, but a non-Android client can still refresh by
polling `/all?api_v=8`.

Expected asynchronous signals:

- `ASSOCREQ`
- `ASSOCRESULT`
- `ASSOCDONE`

These are handled by `MyFcmListenerService`, so FCM registration through
`/setandroiduri` may be required for the app to complete association normally.

Minimal manual test sequence for one device:

1. Register a fresh client.
2. Call `GET /all?api_v=8` with `Authorization: <clientSecret>` and save the
   sanitized empty/initial response.
3. Optionally register FCM if using the real Android app.
4. Call `GET /remote/client/<clientId>/assocreqs` with
   `Authorization: <clientSecret>` and save the sanitized response. A fresh
   client may return `200 OK` with an empty body.
5. Call `GET /remote/client/<clientId>/device/<deviceId>/assocstatus2` with
   `Authorization: <clientSecret>` and save the sanitized response.
6. Call `POST /remote/client/<clientId>/device/<deviceId>/assoc3` once with
   body `{"checkId":"<checkId>","msg":""}`.
7. Wait; do not loop.
8. Check `GET /remote/client/<clientId>/device/<deviceId>/assocstatus2`.
9. Check `GET /remuc/mobile-api/client/<clientId>/all?api_v=8`.
10. If the Android app receives a push notification, capture whether it later
   sends `/setassoc`, `/assocstatus2`, or another `/assoc3` call.

Do not implement this in `pywebasto` until the sequence above is capture-
verified with sanitized request and response bodies.

## Observed Payload Keys

Static code references these keys in request payload or response handling near
network and association flows:

- `secret`
- `clientId`
- `clientSecret`
- `fcmToken`
- `dev_id`
- `cmd`
- `state`
- `checkId`
- `msg`
- `message_dbid`
- `terms`
- `term-approvals`
- `body`
- `id`
- `status`
- `line`
- `output`
- `timers`
- `repeat`
- `type`
- `start`
- `duration`
- `enabled`
- `departure`
- `maxDuration`
- `comfortLevel`
- `location`

Do not treat this list as a complete schema.

## Output Line Notes

Observed output line meanings from static analysis and live `/all?api_v=8`
responses:

| Line | App label / evidence | Notes |
| --- | --- | --- |
| `OUTH` | `Heater` | Live-verified on/off command uses `OUT H ON/OFF`. Active in heating mode. |
| `OUTV` | `Ventilation` | Live-verified as the active output after `/heatermode` with `mode: 1`. |
| `OUTA` | `Geo-fence` / alarm-related | Static label mapping in `La9/a.c(...)` maps `OUTA` to the localized `Geo-fence` string. Live `/all` showed icon `alert_on` and top-level `alarms: "CONF"`. Static code in `Ls8/m.V()` sends `OUT A ON` / `OUT A OFF`, and alarm helpers inspect `alarms`, inputs, `alarmlevel`, and `activestate`. Treat as geofence/alarm output, not normal heater/ventilation. |
| `OUT1` | `Heater` fallback label | Static mapping falls back to heater label for `OUT1` in `La9/a.c(...)`; not live-verified here. |
| `OUTI` | `Heater` fallback label | Static mapping groups `OUTI` with `OUTH`; not live-verified here. |

`OUTA` also appears in timer configuration code, where some timer controls are
hidden or adjusted for `OUTA`. That supports treating it as a special
alarm/geofence output rather than a normal controllable heater channel.

## Settings Not Found In App Backend

The existing web API notes and `pywebasto` implementation know about these
settings:

- `device_settings.low_voltage_cutoff`
- `device_settings.ext_temp_comp`

Those are documented in `docs/protocol.md` for the web API `/post_settings`
flow.

Targeted static analysis of the Android app backend did not find these keys or
equivalent app-backend write calls in `ThermoConnect_3.3.0_APKPure.apk`.

Search evidence:

- APK strings did not contain `low_voltage_cutoff`, `ext_temp_comp`,
  `temperature compensation`, `cutoff`, or a clear equivalent setting key.
- `embelin.webasto.activities.Settings` exposes app settings such as:
  - `confirmControlClicks`
  - `showVoltage`
  - location usage consent
  - diagnostic mode
  - device rename / device id display
  - output heating-time configuration
- All observed calls to `Ls8/b0;->a(I, String, String)` were reviewed for JSON
  payload keys near app classes. Observed write-like app backend flows include:
  - `/cmd`
  - `/heatermode`
  - `/timers2` request type `9`
  - `/location-services`
  - `/cronus-info`
  - `/term-approval`
  - `/term-approval-cronus`
  - `/delete-message`
  - `/setassoc`
  - `/assoc3`
  - `/setandroiduri`
- None of those observed app payloads included low-voltage cutoff or
  temperature compensation fields.

Current conclusion:

- Low-voltage cutoff and temperature compensation are currently only evidenced
  through the web API.
- No Android app endpoint for setting them has been identified.
- Do not implement app-backend support for these settings unless a future app
  capture or APK version shows concrete endpoint and payload evidence.

## Web API Bootstrap Evidence

Sanitized web API evidence from `GET /webapi/get_service_data?poll=false` shows
that the response can include the current device id and check id at the top
level:

```json
{
  "id": "<deviceId>",
  "check_id": "<checkId>",
  "assocStatus": "ok",
  "account_info": {
    "devices": [
      ["<deviceId>", "<deviceName>"]
    ]
  }
}
```

This is used only as a bridge when a user logs in with email/password but has no
stored app `client_id` / `client_secret`: the library can create an app client
and start `/assoc3` using the web API `id` and `check_id`.

## Capture Plan

Before any implementation:

1. Use a test account and, if possible, a test device.
2. Capture only manual app actions through a local HTTPS proxy.
3. Do not fuzz, replay, or loop requests.
4. Keep at least 15 seconds between repeated refresh-like actions until the app
   rate is measured.
5. Stop immediately on `429`, `403`, repeated `5xx`, or unexpected account
   state changes.
6. Sanitize captures before adding anything to the repository:
   - remove credentials
   - remove cookies/tokens
   - remove client IDs/secrets
   - remove device IDs/check IDs
   - remove GPS/location data
7. Confirm for each app call:
   - full endpoint path
   - method
   - request body
   - headers relevant to auth/session
   - response status
   - response fields
   - whether FCM/push is required for completion

## Current Limitations

- This combines static analysis with limited manual live checks; it is not a
  full app traffic capture.
- No live Android app traffic has been captured yet.
- Exact response schemas for an approved/fully associated device are not
  confirmed.
- The initial add-device request is now observed to create `pending`, but the
  completion/approval sequence is not confirmed.
- BLE/QR involvement is indicated by app permissions/classes, but not yet tied
  to a complete cloud onboarding flow.
