# Device-to-Browser Data Streaming

English | [日本語](README_ja.md)

This repository specifies `d2b-stream`, a vendor-neutral application profile
and reference design for continuously delivering device-acquired measurements
or sampled data to a browser. It uses, rather than replaces, HTTP/1.1 and the
WebSocket protocol; its own scope is the application framing, session state,
sample identity, timing, and loss semantics above those standards.

## Current specification

The current protocol version is `0.1`. It defines:

- discovery and read-only status over HTTP;
- strict JSON control messages over WebSocket text frames;
- an exact 32-byte little-endian envelope and profile binary payloads;
- monotonic timestamps, sample-frame sequences, and explicit gaps;
- the `vi-measurement` and `pcm-audio` profiles;
- exact stream-parameter negotiation and optional pairing-token authentication;
- one active stream-session owner; and
- public redacted status with authenticated detail on the control connection.

Start with the [protocol specification](docs/protocol-v0.1.md). The
[architecture](docs/architecture.md), [browser reference parser](docs/browser-reference-parser.md),
[implementation guidance](docs/implementation-guidance.md),
[deployment guide](docs/deployment-guide.md), [conformance matrix](docs/conformance-matrix.md),
and profile documents provide the remaining details required for an independent
implementation.

[Public Status Standard R1](docs/public-status-standard-r1.md) formalizes the
existing `/d2b/v0/status` response as a closed, browser-safe, redacted version
0.1 representation. R1 is named in conformance material and is not added to the
response body.

The [prior-art and protocol-selection report](docs/prior-art-and-protocol-selection.md)
explains why the profile combines existing web standards instead of adopting a
serial, BLE, brokered, or laboratory streaming stack wholesale. The V/I
[SenML mapping](docs/profiles/vi-measurement-senml-mapping.md) defines an export
and interoperability layer without replacing the compact live binary profile.

## Repository contents

- `docs/`: normative application-profile, profile, security, compatibility,
  prior-art, interoperability, and validation documents;
- `schemas/`: self-contained JSON Schema Draft 2020-12 control-message,
  capabilities, and public-status schemas;
- `test-vectors/`: JSON-encoded golden control, capabilities, public-status,
  and binary frame vectors;
- `tools/validate_test_vectors.py`: standard-library-only manual validator for
  schema structure, strict control and public-status fixtures, binary frames,
  continuity, and targeted mutation tests;
- `tools/generate_test_vectors.py`: deterministic standard-library generator
  for all JSON-encoded golden vectors.

Run all vector checks with:

```sh
python3 tools/validate_test_vectors.py
```

The utility checks JSON syntax, Draft 2020-12 declarations, local reference
existence, Schema-equivalent constraints used by the fixtures, and golden
results. It does not perform full JSON Schema meta-schema validation. Refresh
vectors intentionally with `python3 tools/generate_test_vectors.py`.

This repository intentionally contains no product-specific firmware, server,
browser application, binary recording, or runtime dependency.

## Status and license

Version 0.1 is a pre-1.0 protocol. Compatibility rules are defined in the
[versioning policy](docs/versioning-policy.md).

Unless otherwise noted, the specifications, schemas, test vectors, and tools
in this repository are licensed under the Apache License 2.0.
Copyright 2026 Yuichiroh-Kobayashi. See [LICENSE](LICENSE).
