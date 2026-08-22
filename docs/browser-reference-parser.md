# Browser Reference Parser Behavior

This document is normative reference behavior, not a browser application. C1
does not ship HTML, UI, WebSocket server code, or runtime dependencies.

## Common decoder state

For the active session, retain the negotiated full version, profile, exact
parameters, stream ID, whether a data frame has been accepted, prior first
sequence/count/timestamp, prior V/I last timestamp where applicable, and the PCM
session anchor. Do not update this state until the whole message is valid.

## Binary message algorithm

Before this algorithm, require control state `STREAMING` after a valid
`stream_started`; binary data received in `CONNECTED` or `READY` is
`invalid_state` and MUST NOT initialize decoder state.

1. Reject a non-`ArrayBuffer` data message or one beyond the advertised limit.
2. Require at least 32 bytes and read envelope fields with `DataView`.
3. Compare magic, full version, frame type, flags, and stream ID.
4. Reject reserved flags, invalid flag combinations, zero data counts, and
   `first_sequence + sample_count - 1` uint64 overflow.
5. Compute `payloadLength = arrayBuffer.byteLength - 32`.
6. Dispatch only the already negotiated `vi-measurement` or `pcm-audio`
   profile. Reject all others with `unsupported_profile`.
7. Require the profile payload equation exactly, validate records/samples, then
   validate first/repeated `STREAM_START`, sequence, timestamp, and gaps.
8. Commit decoder state and expose a validated segment to visualization/export.

All uint64 values use `DataView.getBigUint64(offset, true)` and `BigInt`
arithmetic. The fixed offsets are:

```text
magic 0, major 4, minor 5, frame type 6, flags 7,
stream ID 8, sample count 12, first sequence 16, timestamp 24
```

V/I reads `delta_us`, `valid_mask`, voltage, and current from each 16-byte
record. PCM reads exactly 256 mono S16LE samples after checking a 512-byte
payload. No code derives format, channels, rate, or payload size from removed
envelope fields.

## Strict control parser

The parser operates on the complete text message and the unmodified UTF-8 byte
length. It rejects invalid UTF-8, duplicate object keys, trailing data,
non-finite numeric tokens, type mismatch, unknown enums, non-integral integer
fields, and integer range failures. Since JavaScript `JSON.parse` does not expose
duplicate keys, an implementation must tokenize object members or run an
equivalent duplicate-key scan before constructing the final object. Replacing
an earlier value silently is non-conforming. JSON Schema validates identifier
syntax, field shape, type, and range; after that, semantic dispatch returns
`unsupported_profile` or `unsupported_parameters` for structurally valid but
unsupported requests. State validation is performed separately and returns
`invalid_state` for a shape-valid message not allowed in the current state.

## Public status validation

`validatePublicStatus(value)` validates an already parsed
`GET /d2b/v0/status` value against Public Status Standard R1. It requires the
four identity/state fields, accepts only the four named optional metrics,
rejects unknown fields, and applies `Number.isSafeInteger` without coercion or
default insertion. Success returns the same object. Failure throws
`ProtocolError` with local code `invalid_public_status`; this code is not a new
WebSocket wire `error.code`.

Public status uses parsed JSON value semantics. Unlike strict control-message
parsing, it does not distinguish the JSON text spellings `1` and `1.0` when
both parse to the same mathematical integer.

## Gap-aware dispatch

The common decoder starts a new segment on every discontinuity and every new
stream ID. Profile views receive both values and segment/gap metadata. They MUST
NOT interpolate, zero-fill, join PCM lines across a gap, use browser arrival time
as measurement time, or merge a reconnect into the old session. Exporters apply
the explicit SenML and WAV policies in the profile documents.

The executable standard-library counterpart for these checks is
`tools/validate_test_vectors.py`. The dependency-free browser reference runs the
same tracked public-status vector corpus as the Python validator.
