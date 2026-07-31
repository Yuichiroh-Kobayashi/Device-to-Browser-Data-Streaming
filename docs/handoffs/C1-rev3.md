# C1 rev3 Handoff

## Scope

C1 rev3 specifies and validates the common, vendor-neutral protocol artifacts.
It contains no product firmware, WebSocket server, browser application, binary
recording, runtime dependency, or generated build output.

## Implemented contract

- exact 32-byte little-endian envelope;
- new flag registry with `OUTPUT_QUEUE_DROP`;
- first-frame `STREAM_START`, payload equations, and checked uint64 arithmetic;
- 16-byte V/I records with independent validity bits;
- mono PCM16LE, 16000 Hz, 256 sample frames per binary message;
- strict JSON including invalid UTF-8, duplicate-key, and non-finite-number
  rejection, with schema shape separated from semantic support errors;
- `CONNECTED`/`READY`/`STREAMING`/`CLOSED` validation;
- standard-profile rejection and fixed PCM parameter validation;
- PCM session-anchor timestamp generation and gap-preserving logical sequence;
- capabilities schema and positive/negative endpoint vectors;
- capabilities self-consistency checks for PCM/V/I minimum frame size and
  duplicate complete parameter sets;
- document-wide standard-profile presence with optional private-profile
  coexistence;
- public redacted `/status` with `Cache-Control: no-store`;
- browser common-decoder, SenML export, WAV gap, deployment, and conformance
  guidance; and
- checked-in, deterministically generated positive/negative golden vectors plus
  targeted mutation tests.

## Implementation boundary

Product acquisition sources must feed a bounded non-blocking queue and retain
original sequence/timestamp identity. Product repositories choose their own
HTTP/WebSocket libraries and implement device-specific acquisition. Browser and
firmware implementation begins only after this C1 contract is accepted.

## Validation entry points

Run `python3 tools/generate_test_vectors.py` only when intentionally refreshing
golden vectors. Run `python3 tools/validate_test_vectors.py` for schema, fixture,
positive, negative, continuity, and mutation validation. The complete acceptance
commands are listed in `docs/validation/protocol-validation-plan.md`.
