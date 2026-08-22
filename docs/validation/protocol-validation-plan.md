# Protocol Validation Plan

## 1. Purpose

This plan verifies specification artifacts and guides independent sender and
receiver conformance testing. The key words MUST, MUST NOT, SHOULD, SHOULD NOT,
and MAY are to be interpreted as described in RFC 2119 and RFC 8174 when they
appear in all capitals.

## 2. Artifact validation

Every JSON artifact MUST decode as UTF-8 and parse as JSON. Schemas MUST
identify JSON Schema Draft 2020-12 and MUST resolve without retrieving external
schemas over the network. Every binary vector hex string MUST be lowercase,
contain an even number of hexadecimal digits, and decode to the stated frame.

`tools/validate_test_vectors.py` MUST use only the Python standard library. It
MUST check schema JSON syntax, the Draft 2020-12 declaration, local-only `$ref`
values, and existence of every referenced local JSON Pointer. It performs
Schema-equivalent manual validation for the control and public-status fixtures,
not full JSON Schema meta-schema validation.

The utility MUST also validate vector structure and unique names, capabilities,
raw UTF-8
control size before parsing, `options.maxProperties`, authentication and
strict JSON rules, structural-versus-semantic errors, control state, parameter
constraints, the exact 32-byte envelope, flag
invariants, checked sequence/timestamp arithmetic, profile payload equations,
first-frame `STREAM_START`, session invariants, PCM anchor timing, and expected
results.

## 3. Required vector coverage

Control coverage includes authentication, messages and status, invalid UTF-8,
duplicate keys, non-finite values, trailing data, integer/type/range errors,
unknown profiles, invalid channel masks, unsupported PCM sets, oversized text,
the four control states, and `busy` owner preservation. Capability coverage
includes at least one implemented standard profile, endpoint shape, limits, and
advertised parameter semantics. It MUST test the PCM minimum frame boundary at
543/544 bytes, the V/I minimum boundary at 47/48 bytes, and duplicate complete
parameter sets. It MUST also reject private-only capabilities while accepting a
standard profile alongside a private profile; both documents remain
schema-valid. Binary coverage includes V/I and mono PCM16 at 16000 Hz and 256
sample frames, wrong magic/version, reserved bits, first/repeated start, zero counts,
short/long/partial payloads, sequence/timestamp overflow, stream mismatch,
regression and unexplained gaps, validity/delta failures, anchor timing,
output-queue/producer/pause causes with and without gaps, binary before
`stream_started`, maximum-size rejection, profile mismatch, and stream end.
Public-status coverage includes the four required fields, every optional metric,
all optional metrics omitted, both states, browser-safe integer boundaries,
closed-field rejection, and explicit privacy-invalid injections. The Python and
browser reference validators MUST run the same public-status vector corpus.

## 4. Independent implementation tests

A sender under test SHOULD be decoded by a separately written host receiver.
A receiver under test SHOULD consume both golden bytes and mutated/fuzzed
variants. Mutation tests MUST reject one-byte truncation, one-byte extension,
targeted single-bit envelope and reserved-bit changes, sequence boundary and
sample-count changes, and profile mismatch. Tests MUST cover integer boundaries
before allocating based on an envelope. Unknown reserved values, invalid UTF-8,
oversized control data, and
state-invalid messages MUST be rejected deterministically.

## 5. Runtime and concurrency tests

The acquisition producer MUST be instrumented under WebSocket stalls, slow HTTP
clients, filesystem delays in unrelated tasks, disconnect storms, and a full
ring buffer. The test passes only if acquisition does not block, oldest samples
are discarded, drop counters increase by sample frame, and the next delivered
frame contains the required discontinuity/cause flags.

When multiple READY connections are implemented, two clients SHOULD race to
start streaming. Exactly one may own the stream;
the other MUST receive `busy`, and the owner MUST remain STREAMING. HTTP 503
Upgrade rejection for socket capacity SHOULD be tested separately. Stop, abrupt
close, reboot, new-session timebase reset, and sequence-near-limit behavior
SHOULD be tested.

## 6. Browser/deployment matrix

Run the compatibility matrix in `browser-compatibility.md` on Windows Chrome or
Edge and iPad Safari. For filtered networks, record independent results for
static assets, REST, Upgrade, continuous binary traffic, and Blob download.

## 7. Acceptance commands

From the repository root, run:

```sh
git diff --check
python3 -m json.tool schemas/client-message.schema.json >/dev/null
python3 -m json.tool schemas/server-message.schema.json >/dev/null
python3 -m json.tool schemas/capabilities.schema.json >/dev/null
python3 -m json.tool schemas/public-status.schema.json >/dev/null
python3 -m json.tool test-vectors/control-messages.json >/dev/null
python3 -m json.tool test-vectors/capabilities.json >/dev/null
python3 -m json.tool test-vectors/public-status.json >/dev/null
python3 -m json.tool test-vectors/vi-frames.json >/dev/null
python3 -m json.tool test-vectors/pcm-audio-frames.json >/dev/null
PYTHONPYCACHEPREFIX=/tmp/d2b-stream-pycache python3 -m py_compile \
  tools/generate_test_vectors.py tools/validate_test_vectors.py
python3 tools/generate_test_vectors.py
python3 tools/validate_test_vectors.py
```

All commands MUST succeed. Generated bytecode MUST NOT be committed.

For an independent review when the third-party `jsonschema` package is already
installed, reviewers SHOULD run `Draft202012Validator.check_schema` for all
schemas and validate vector message/document shapes. This is a review check,
not a repository runtime dependency. In particular, the semantic-negative
control fixtures for unknown profile, invalid channel-mask combination,
unsupported PCM rate, and unsupported PCM frame size MUST remain schema-valid.
Independent capability review SHOULD confirm that all four minimum-frame-size
boundary documents are schema-valid while semantic validation rejects only the
two undersized documents.
