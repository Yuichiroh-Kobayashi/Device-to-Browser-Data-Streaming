# d2b-stream Golden Test Vectors

The JSON files in this directory are deterministic, reviewable fixtures for
protocol version 0.1. They are not captured measurement or audio recordings.

## Files

- `control-messages.json`: strict JSON, authentication, exact parameter
  negotiation, schema/semantic separation, control states, unsupported
  profiles/sets, limits, and ownership-aware `busy`;
- `capabilities.json`: implemented-profile advertisement, minimum-frame-size
  boundaries, duplicate-set rejection, standard/private presence semantics, and
  positive/negative endpoint documents validated against
  `schemas/capabilities.schema.json`;
- `vi-frames.json`: 32-byte envelopes, timestamped records, validity,
  sequence/timestamp overflow, payload equations, gaps, and stream end;
- `pcm-audio-frames.json`: mono PCM16 at 16000 Hz and 256 samples per frame,
  exact lengths, session invariants, gap segments, and anchor timestamps.

Binary frames are lowercase hexadecimal strings in `frame_hex`; no binary files
are required. Each vector has a globally unique `name`, `purpose`,
`expected_valid`, and either `expected_decoded` or `expected_error`.

## Control wire representation

Control vectors use `message`. When it is an object, compact UTF-8 JSON
serialization is the defined wire representation for size checking. When it is
a string, that string is the exact raw WebSocket text payload, including
whitespace, and its UTF-8 byte length is checked before JSON parsing. Thus the
2049-byte fixture is rejected before JSON parsing or normalization. A
`message_hex` fixture represents raw text-message bytes that cannot be expressed
as a JSON string, such as invalid UTF-8.

Optional control `context` describes scenario state not encoded in one message,
including `CONNECTED`, `READY`, `STREAMING`, and `CLOSED` validation.
The second-client fixture records that connection A owns a STREAMING session,
connection B is READY and sends `start_stream`, the result is `busy`, and A
remains STREAMING.

## Binary session context

Optional binary `context` supplies session state, negotiated limits/version,
stream ID, profile, negotiated parameter object, and optionally the immediately
preceding frame. PCM continuity contexts also contain the original session
sequence and timestamp anchor. The validator derives expected sequence and
timestamp from this state; the fixture does not supply the answers separately.

Run:

```sh
python3 tools/generate_test_vectors.py
python3 tools/validate_test_vectors.py
```

The standard-library utility checks schema JSON syntax, Draft 2020-12 markers,
local `$ref` existence, Schema-equivalent fixture constraints, binary framing,
session continuity, expected results, and the required one-byte/header/boundary/
profile mutation cases. It does not perform complete JSON Schema meta-schema
validation.
