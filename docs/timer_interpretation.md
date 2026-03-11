# Timer-fortolkning (Webasto API)

## Input-eksempel

```json
{
  "type": "simple",
  "repeat": 31,
  "start": 830,
  "duration": 5400,
  "enabled": true
}
```

## Felt-fortolkning

- `type`: timermode (`simple` i eksemplet).
- `enabled`: om timeren er aktiv.
- `start`: minutter efter midnat i **UTC**.
- `duration`: antal sekunder output skal køre.
- `repeat`: bitmask for ugedage.

## Repeat bitmask

Fortolkning:

- bit 0 = mandag
- bit 1 = tirsdag
- bit 2 = onsdag
- bit 3 = torsdag
- bit 4 = fredag
- bit 5 = lørdag
- bit 6 = søndag

Dermed bliver `repeat = 31` (`0b0011111`) = mandag-fredag.

## Tidsberegning i eksemplet

- `start = 830` minutter = 13:50 UTC.
- I dansk vintertid (UTC+1) vises det som 14:50 lokal tid.
- `duration = 5400` sekunder = 90 minutter = 1 time 30 min.

Det matcher beskrivelsen: start 14:50 og kør i 1,5 time på hverdage.

## Praktisk algoritme (til implementering senere)

1. Ignorer timer hvis `enabled != true`.
2. Dekod `repeat` til ugedage.
3. Beregn næste dato/tid i UTC ud fra `start`.
4. Konverter til HA/brugerens lokale tidszone i UI.
5. Vis varighed som `duration` i minutter eller `HH:MM`.

## Kendt usikkerhed

- DST/sommertid: hvis API altid bruger UTC-minutter, vil lokal klokkeslæt flytte sig med DST.
- Hvis API internt justerer `start` ved DST, vil lokal visning stadig være stabil.

Det bør verificeres på tværs af sommer-/vintertid med rigtige payloads.
