# d2b-stream Application Profile Version 0.1

## 1. Status, conformance, and terminology

This document is the normative Core specification for `d2b-stream` version
`0.1`, a SenML-aligned live streaming application profile. It composes
HTTP/1.1 and WebSocket; it does not replace their transport semantics. The key
words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted as
described in RFC 2119 and RFC 8174 when they appear in all capitals.

A conforming implementation MUST implement this Core and at least one standard
profile. A *channel sample* is one value for one channel. A *sample frame* is
the set of channel samples acquired at one logical time. A *transport frame* is
one WebSocket binary message. Sequence numbers and `sample_count` count sample
frames, not channel values or transport frames.

## 2. Architecture

The normative data path is:

```text
device-specific acquisition
        -> bounded non-blocking queue
        -> profile-specific encoder
        -> common d2b session
        -> WebSocket
        -> browser common decoder and profile dispatch
```

Acquisition producers MUST NOT block on WebSocket transmission, HTTP handling,
filesystem writes, or browser behavior. V/I and PCM share transport, control,
ownership, stream identity, timing, discontinuity, validation, reconnect, and
common browser-decoder behavior. Payload layout, sample interpretation, rate
model, channel semantics, visualization, export, and profile validation remain
profile-specific. The two profiles do not share one payload layout.

## 3. Endpoints and transport

- Protocol name: `d2b-stream`
- Protocol version: `0.1` (major 0, minor 1)
- Binary magic: ASCII `D2BS`
- HTTP transport: HTTP/1.1
- Streaming transport: WebSocket in the HTTP origin's security context

The endpoints are:

```text
GET /d2b/v0/
GET /d2b/v0/capabilities
GET /d2b/v0/status
WS  /d2b/v0/stream
```

HTTP endpoints MUST be read-only. Dynamic responses, including `/status`, MUST
include `Cache-Control: no-store`. Tokens and session identifiers MUST NOT be
placed in URL query parameters.

Each control message MUST occupy exactly one WebSocket text message containing
one UTF-8 JSON value. Each sample transport frame MUST occupy exactly one
WebSocket binary message. A client MUST NOT send binary messages.

## 4. Strict JSON and control limits

The maximum control-message size is 2048 UTF-8 bytes and MUST be enforced on
the unmodified WebSocket message before parsing. A control parser MUST reject:

- invalid UTF-8, malformed JSON, and trailing data;
- `NaN`, `Infinity`, and `-Infinity`;
- duplicate object keys rather than silently keeping one value;
- type mismatches and unknown required enum values;
- out-of-range integers; and
- a floating-point value in an integer field, even when mathematically integral.

Malformed input produces `invalid_message`; an oversized message produces
`frame_too_large`. The schemas in `schemas/` are normative for identifier
syntax, field shape, JSON type, and scalar range. They intentionally do not
decide whether a valid profile identifier or structurally valid parameter
object is implemented by a device. Semantic validation performs that decision
after schema validation. Malformed shape, type, or range produces
`invalid_message`; an unknown or unimplemented profile produces
`unsupported_profile`; and a structurally valid but unsupported complete
parameter set produces `unsupported_parameters`.

## 5. Authentication and connection ownership

`hello.authentication` MAY carry a `pairing-token` of 1 through 256 UTF-8 bytes.
Pairing is Optional/Recommended, not a Core conformance requirement. A pairing
deployment MUST authenticate before sending `welcome`, control status, or data.
Tokens MUST NOT appear in URLs, logs, status responses, or error messages.

Every upgraded connection follows:

```text
CONNECTED --hello/welcome--> READY
READY --start_stream/stream_started--> STREAMING
STREAMING --stop, end, or disconnect--> READY or CLOSED
READY --disconnect--> CLOSED
```

`CONNECTED`, `READY`, `STREAMING`, and `CLOSED` are the control states. In
`CONNECTED`, only `hello` is accepted. In `READY`, `start_stream` and `ping` are
accepted; a second `hello` and `stop_stream` are invalid. In `STREAMING`, only
the owner may send `stop_stream`; another `start_stream` is invalid. `CLOSED`
accepts no messages. A control message that is valid in shape but disallowed by
the current state MUST produce `invalid_state`. The server MUST NOT send binary
data until it has sent `stream_started` and entered `STREAMING`.

At most one connection owns an active stream. A v0.1 implementation that
accepts only one simultaneous WebSocket control/data connection is conforming.
An implementation MAY advertise more than one READY connection. A second READY
connection requesting a stream while another owns one MUST receive `busy`; it
MUST NOT displace the owner. Multiple READY connections are Future/Experimental
reference behavior, not required by the v0.1 reference implementation.

Disconnect releases ownership. Reconnect MUST create a new stream session and
new nonzero `stream_id`; old and new sessions MUST NOT be treated as one
continuous stream.

## 6. Control protocol

The Core message types are:

| Direction | Type | Required fields | Optional fields |
| --- | --- | --- | --- |
| C→S | `hello` | `type`, `protocol`, `versions` | `client_name`, `authentication` |
| S→C | `welcome` | `type`, `protocol`, `version`, limits, `session_state` | `server_name` |
| C→S | `start_stream` | `type`, `stream`, `profile`, `parameters` | `options` |
| S→C | `stream_started` | `type`, `stream`, `profile`, `parameters`, `stream_id` | none |
| C→S | `stop_stream` | `type` | `stream_id`, `reason` |
| S→C | `stream_stopped` | `type`, `stream_id`, `reason` | none |
| S→C | `status` | state and bounded counters | active stream and last error |
| S→C | `error` | `type`, `code`, `message` | `correlation`, `recoverable` |
| C→S/S→C | `ping` / `pong` | `type`, `correlation` | none |

The server MUST select a complete version offered in `hello.versions` and return
it in `welcome.version`. Every binary envelope MUST exactly match that complete
version. Version `0.1` uses major `0`, minor `1`.

The specification repository defines exactly two standard v0.1 profile
identifiers: `vi-measurement` and `pcm-audio`. A conforming device implements
at least one and lists only its implemented profiles and supported complete
parameter sets in capabilities. Requesting an unlisted or otherwise
unimplemented profile produces `unsupported_profile`. An implementation MUST
NOT guess, fall back, or heuristically decode an unknown profile. It MUST return:

```json
{
  "type": "error",
  "code": "unsupported_profile",
  "message": "profile is not supported"
}
```

The v0.1 error codes are `busy`, `unauthorized`, `unknown_stream`,
`unsupported_version`, `unsupported_profile`, `unsupported_parameters`,
`invalid_message`, `invalid_state`, `frame_too_large`, and `internal_error`.
Human-readable `message` text is diagnostic and MUST NOT be parsed as a stable
identifier.

`stream_started.parameters` MUST exactly repeat the accepted parameter set.
Those parameters and the stream ID remain invariant until the session ends.
Profile metadata is not repeated in each binary frame.

## 7. Standard and private profiles

Standard identifiers are lowercase names registered by this specification.
A private identifier MUST use a reverse-domain prefix followed by a profile
name, for example `com.example.sensor-array`. The domain owner controls that
namespace. Private names MUST NOT use `vi-measurement` or `pcm-audio` semantics
unless they follow the corresponding standard profile.

A new profile specification MUST define its identifier, negotiated parameter
schema, frame type, payload equation and layout, channel and timing semantics,
validation limits, gap/export behavior, test vectors, and any SenML mapping.
Adding a document alone does not make a profile part of v0.1 Core. Unknown
standard or private profiles are rejected with `unsupported_profile`.

## 8. 32-byte common binary envelope

Every binary message starts with exactly this 32-byte envelope. All multi-byte
fields MUST be little-endian.

| Offset | Size | Type | Field |
| ---: | ---: | --- | --- |
| 0 | 4 | char[4] | magic `D2BS` |
| 4 | 1 | uint8 | protocol major |
| 5 | 1 | uint8 | protocol minor |
| 6 | 1 | uint8 | frame type |
| 7 | 1 | uint8 | flags |
| 8 | 4 | uint32 | stream ID |
| 12 | 4 | uint32 | sample count |
| 16 | 8 | uint64 | first sample sequence |
| 24 | 8 | uint64 | first sample timestamp in microseconds |

The payload length is the complete WebSocket binary-message length minus 32.
A receiver MUST enforce its negotiated maximum message size before allocation,
then require:

```text
actual_payload_length
== expected_payload_length(sample_count, negotiated_parameters)
```

Short payloads, long payloads, trailing bytes, and partial records are invalid.
The envelope intentionally contains no header-size, sample-format,
channel-count, channel-mask, sample-rate, or explicit payload-size field.

### 8.1 Frame types

| Value | Name | Profile/use |
| ---: | --- | --- |
| `0x01` | `FIXED_RATE_SAMPLES` | `pcm-audio` data |
| `0x02` | `TIMESTAMPED_SAMPLES` | `vi-measurement` data |
| `0x10` | `STREAM_END` | payload-free end marker |

Unknown frame types are invalid. Data frames MUST have `sample_count >= 1`.
`STREAM_END` MUST have `sample_count == 0`, no payload, and only the
`STREAM_END` flag. Its sequence is the next sequence that would have been used;
its timestamp is the monotonic time at which the end was recognized.

For every data frame the receiver MUST evaluate with checked uint64 arithmetic:

```text
first_sample_sequence + sample_count - 1
```

An overflow is invalid. Sequence wrap MUST NOT occur within a session.

### 8.2 Flags

| Bit | Mask | Name | Meaning |
| ---: | ---: | --- | --- |
| 0 | `0x01` | `STREAM_START` | first data frame of a stream ID |
| 1 | `0x02` | `STREAM_END` | payload-free end marker |
| 2 | `0x04` | `DISCONTINUITY` | a gap or time discontinuity precedes the frame |
| 3 | `0x08` | `PRODUCER_OVERFLOW` | acquisition or its immediate bounded queue could not retain samples |
| 4 | `0x10` | `OUTPUT_QUEUE_DROP` | data was discarded after acquisition and before transport-adapter acceptance |
| 5 | `0x20` | `SOURCE_PAUSED` | first data after a source pause |
| 6 | `0x40` | `TIMEBASE_RESET` | new session follows a timebase reset |
| 7 | `0x80` | reserved | MUST be zero |

`OUTPUT_QUEUE_DROP` does not mean TCP packet loss. TCP preserves the ordered
byte stream accepted by the transport; it does not preserve samples discarded
before transport acceptance.

Every new stream ID's first data frame MUST set `STREAM_START`; subsequent data
frames for that stream ID MUST NOT set it. `STREAM_START` and `STREAM_END` MUST
NOT coexist. Every cause flag MUST be accompanied by `DISCONTINUITY`.
`TIMEBASE_RESET` additionally requires a new stream ID and `STREAM_START`.

## 9. Sequence, timestamp, and gap semantics

Timestamps use a device-local monotonic microsecond clock. Browser arrival time
MUST NOT be substituted for measurement time. For consecutive data frames the
expected sequence is:

```text
previous_first_sample_sequence + previous_sample_count
```

A smaller value is regression and invalid. A larger value is a gap and requires
`DISCONTINUITY`. Missing samples MUST NOT be renumbered, silently interpolated,
zero-filled, removed, or hidden by time-axis compression. Exports MUST preserve
the gap or explicitly represent the chosen gap policy.

WebSocket/TCP ordering and acquisition continuity are separate properties. A
valid ordered transport can contain explicit acquisition or output-queue gaps.

PCM sequence numbers are logical sample-frame positions. Positions lost during
producer overflow, output-queue loss, or a known-duration source pause remain
as positive sequence gaps. A later PCM frame carrying `PRODUCER_OVERFLOW`,
`OUTPUT_QUEUE_DROP`, or `SOURCE_PAUSED` MUST therefore have a positive sequence
gap. If the exact number of missing positions during a pause is unavailable,
the sender MUST end the old stream and begin a new stream ID rather than guess.

## 10. Profile parameter summaries

`vi-measurement` uses `TIMESTAMPED_SAMPLES` and:

```json
{
  "sample_format": "vi-f32le",
  "channel_count": 2,
  "channel_mask": 3,
  "sample_rate": {"numerator": 0, "denominator": 0}
}
```

`0/0` means no nominal fixed V/I rate. A nonzero advertised V/I rate uses a
positive numerator and denominator; record timestamps remain authoritative.

The v0.1 reference `pcm-audio` set is exactly:

```json
{
  "sample_format": "pcm-s16le-interleaved",
  "channel_count": 1,
  "channel_mask": 1,
  "sample_rate": {"numerator": 16000, "denominator": 1},
  "samples_per_frame": 256
}
```

PCM negotiation MUST validate positive count/mask/rate values,
`popcount(channel_mask) == channel_count`, supported sample format, and the
complete supported parameter set. The v0.1 reference implementation MUST reject
other PCM sets with `unsupported_parameters`.

## 11. Capabilities

`GET /d2b/v0/capabilities` MUST return UTF-8 JSON conforming to
`schemas/capabilities.schema.json` and containing `protocol`,
`version`, positive `maximum_binary_frame_size`,
`maximum_control_message_size` equal to 2048,
`maximum_active_stream_sessions` equal to 1, positive
`maximum_control_connections`, `persistent_capture_supported`, `security_mode`,
and a non-empty `streams` array. `maximum_control_connections: 1` is conforming.

Each stream descriptor contains a neutral `id`, human-readable `label`, and
non-empty `profiles`. Every profile entry contains its exact identifier and a
non-empty `parameter_sets` array. A device MUST list only profiles it implements.
Complete parameter objects are listed rather than independent value arrays, so
impossible Cartesian combinations are never advertised. The server MUST accept
only a listed complete set. Within one profile descriptor, duplicate complete
parameter sets are invalid.

Core-conforming capabilities MUST advertise at least one standard profile
somewhere in the document. Advertising only private profiles is not Core
conforming and is `invalid_capabilities`. Standard and private profiles MAY be
advertised together. This document-wide condition is semantic validation, not
a JSON Schema structural constraint.

Semantic capabilities validation MUST ensure that
`maximum_binary_frame_size` can carry at least one transport frame for every
advertised complete parameter set. For `pcm-audio`, the required size is:

```text
32 + samples_per_frame * channel_count * 2
```

The v0.1 reference PCM set therefore requires at least 544 bytes. An advertised
`vi-measurement` profile requires at least 48 bytes: the 32-byte envelope plus
one 16-byte record. These cross-field requirements remain semantic validation;
the JSON Schema validates the individual field shape and range. Positive and
negative capability fixtures are in `test-vectors/capabilities.json`.

Example profile entry:

```json
{
  "profile": "pcm-audio",
  "parameter_sets": [
    {
      "sample_format": "pcm-s16le-interleaved",
      "channel_count": 1,
      "channel_mask": 1,
      "sample_rate": {"numerator": 16000, "denominator": 1},
      "samples_per_frame": 256
    }
  ]
}
```

## 12. Public status and authenticated control status

`GET /d2b/v0/status` is a public, unauthenticated, redacted endpoint. It MUST
include `Cache-Control: no-store` and MUST NOT expose a token, authentication
object, client identity, stream ID, detailed session parameters, or raw data.
It MAY expose the protocol/version, `idle` or `streaming` state, monotonic uptime,
and bounded aggregate counters.

An implementation that claims [Public Status Standard R1](public-status-standard-r1.md)
conformance MUST use the closed representation in
`schemas/public-status.schema.json`. R1 requires `protocol`, `version`, `state`,
and `uptime_us`; defines four optional aggregate metrics; and adds exact numeric,
restart, HTTP media-type, and privacy requirements. R1 is a named conformance
revision of this existing version 0.1 endpoint, not a wire-negotiated feature.
Its identifier does not appear in the response body.

The WebSocket `status` message is sent only after `hello` and, when configured,
successful authentication. It MAY include the schema-defined active stream ID,
queue state, `producer_drop_count`, `output_queue_drop_count`, source pause, and
last error. Counters MUST saturate at 9007199254740991 rather than wrap.

This separation makes pairing-token authentication consistent: the HTTP status
is public and redacted; detailed status uses the authenticated control channel.

## 13. Conformance scope

### Core v0.1

HTTP/WebSocket transport, strict JSON control, the 32-byte envelope, stream ID,
sequence, monotonic timestamp, flags and gap semantics, one active owner,
strict validation, and unknown-profile rejection are Core. The specification
repository defines both standard profiles. A conforming device implementation
MUST implement and advertise at least one standard profile; it need not
implement both.

### Optional / Recommended v0.1

Pairing token, redacted status counters, browser CSV export, browser SenML JSON
export, browser WAV export, reconnect UI, and detailed diagnostics are Optional
or Recommended. Their absence does not fail Core conformance.

### Future / Experimental

SenSML live streaming, SenML CBOR, RFC 9193 PCM mapping, a generic scalar
profile, dynamic channel UI, MQTT gateway, WebTransport, multiple READY control
connections, realtime PCM playback, and spectrograms are Future/Experimental.
They are not implemented by the v0.1 reference implementation and are not
required for conformance.

## Appendix A. Non-normative receiver order

Enforce the negotiated message-size limit; parse the 32-byte envelope; validate
magic, full version, frame type, flags, stream ID, count, and sequence arithmetic;
derive payload length; apply the negotiated profile equation and record checks;
then validate session continuity. Update browser-visible state only after all
checks succeed. Unknown profiles are never dispatched.
