# Browser Compatibility

## 1. Normative language

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted
as described in RFC 2119 and RFC 8174 when they appear in all capitals.

## 2. Target baseline

The initial targets are current Windows Chrome or Edge and iPad Safari. A
version 0.1 browser receiver MUST be implementable using only:

- WebSocket;
- ArrayBuffer and DataView;
- Canvas 2D;
- Blob and Object URL;
- HTML anchor download.

The implementation MUST NOT require a CDN, npm runtime, React, Chart.js, File
System Access API, Service Worker, or WebRTC. These technologies MAY be optional
enhancements but MUST NOT be required for basic connection, display, or export.

In `pairing-token` mode the browser MUST send the token in the first
`hello.authentication` object. It MUST NOT place the token in the WebSocket URL.
The baseline does not depend on setting an arbitrary HTTP authorization header,
which the browser WebSocket constructor does not provide.

## 3. Binary decoding

The browser MUST request or accept binary WebSocket messages as `ArrayBuffer`
and MUST parse the common 32-byte envelope before profile dispatch. JavaScript
code using `DataView` MUST pass `true` for every multi-byte little-endian read.
The common decoder owns session state, exact stream ID, version/frame/flag
validation, uint64 sequence arithmetic with `BigInt`, timestamp continuity, gap
segments, payload-length derivation, and unknown-profile rejection. Only after
those checks succeed may it call the V/I or PCM decoder.

The control parser MUST apply the same strict JSON rules as the protocol. Plain
`JSON.parse` rejects non-standard numeric tokens and trailing data, but it does
not report duplicate object keys. A conforming reference parser therefore MUST
perform duplicate-key detection before or during object construction and MUST
reject the complete message when a duplicate is present.

The browser MUST retain sequence gaps and timeline segments in its data model.
Rendering MAY simplify dense data, but export MUST preserve discontinuities and
must not silently substitute values.

For PCM, the browser MUST build the acquisition time axis from the session
sequence/rate anchor. WebSocket arrival time MUST NOT determine audio frequency
or sample timing. A gap starts a new waveform segment. The v0.1 MVP covers
waveform display, period observation, frequency estimation, an explicit
five-second capture, and WAV export. Realtime playback, AudioWorklet, and
spectrograms are Future/Experimental.

S16LE values MUST be decoded explicitly. Future Web Audio playback would require
normalizing them to `Float32`; an `Int16Array` is not directly usable as Web
Audio channel data.

## 4. Download behavior

Blob creation, `URL.createObjectURL()`, and a user-activated anchor download are
the standard export path on both target groups and specifically on iPad Safari.
The receiver SHOULD revoke Object URLs after the download interaction is safe.

On supporting Windows browsers, `showSaveFilePicker()` MAY provide streaming or
destination-controlled saving. The receiver MUST retain the Blob/anchor path as
the compatible fallback. Browser-side recording MUST require explicit user
action.

PCM WAV export MUST either create one WAV per contiguous segment or insert
silence for missing intervals while retaining separate gap metadata. It MUST NOT
silently shorten the time axis. Archival V/I SenML JSON export MUST use the
paired device-monotonic/browser-Unix capture anchor and `bt`/`t` mapping defined
by the V/I SenML document; it MUST NOT export raw device-monotonic microseconds
as absolute SenML time.

## 5. Filtered-network test matrix

Deployments behind web filters such as i-FILTER MUST test each layer separately;
success at one layer MUST NOT be taken as proof of another.

| Test | Action | Expected evidence |
| --- | --- | --- |
| Static HTML | Load `/d2b/v0/` | Entry asset and local assets load without CDN |
| REST capabilities/status | Fetch both JSON endpoints | HTTP success, valid UTF-8 JSON, no mutation |
| WebSocket Upgrade | Connect to `/d2b/v0/stream` | Successful Upgrade and `hello`/`welcome` |
| Continuous binary streaming | Run a representative sustained stream | Ordered binary messages without filter timeout or content rewriting |
| Blob download | Export a bounded capture | User can save or share the resulting file |

Tests SHOULD record browser/OS versions, network path, filter policy, duration,
frame rate, disconnect behavior, and any size threshold. HTTP access alone does
not demonstrate that WebSocket Upgrade or continuous binary traffic is allowed.

## 6. Non-normative implementation notes

Canvas rendering should be decoupled from decode rate, for example by batching
updates to animation frames. Large captures can be kept in bounded chunks before
Blob assembly. iPad memory pressure makes bounded recording duration and a clear
size estimate particularly useful.
