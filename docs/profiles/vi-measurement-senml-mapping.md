# V/I Measurement SenML Mapping

## 1. Status and scope

This document normatively defines how a browser-side SenML producer exports
valid `vi-measurement` samples as a SenML JSON Pack. It does not change the live
wire format: both V/I and PCM live data continue to use the common binary
envelope and profile payload.

`d2b-stream` is a SenML-aligned live streaming application profile. A browser
that performs this export is a SenML producer implementation. A device is not
required to emit SenML JSON for v0.1 conformance.

## 2. Record mapping

For each valid channel in one V/I sample, the exporter emits one SenML Record:

| Source channel | SenML name `n` | IANA SenML Unit `u` | Numeric value `v` |
| --- | --- | --- | --- |
| voltage | `voltage` | `V` | voltage in volts |
| current | `current` | `A` | current in amperes |

The basic mapping uses the standard SenML fields `n`, `u`, and `v`. It does not
claim that SenML defines a general `quantity` field. Records derived from the
same sample MUST use the same SenML time.

If a validity bit is clear, the exporter MUST omit that channel's numeric
record. It MUST NOT emit a valid-looking zero. An exporter MAY add a separately
documented extension record for invalidity status, but extensions MUST NOT
change the meaning of the standard numeric records.

Example archival records using the time anchor in Section 3 are:

```json
[
  {"bt": 1785456000.0, "n": "voltage", "u": "V", "v": 3.3, "t": 0.0},
  {"n": "current", "u": "A", "v": 0.125, "t": 0.0}
]
```

## 3. Time conversion

A device-local monotonic microsecond value is not automatically a valid SenML
absolute time. An exporter MUST NOT copy the raw device timestamp directly to
`t` and describe it as Unix or calendar time.

For browser-side archival export, the capture MUST store a device monotonic
timestamp `T0` paired with browser Unix time `W0` at the capture anchor. For a
sample at device monotonic timestamp `Ts`, the SenML mapping is:

```text
bt = W0
t = (Ts - T0) / 1,000,000
```

The first applicable record carries `bt`; resolved record time is `bt + t`.
Export metadata MUST document the browser clock source, anchor acquisition
method, and uncertainty. The exporter MUST NOT substitute capture-stop "now"
for `W0` or copy the device monotonic timestamp as calendar time.

If no wall-clock mapping is available, relative SenML time MAY be used only in
an immediate communication context whose current-time reference is understood
by both parties. An archival file MUST NOT fabricate an absolute time or use an
arbitrary capture epoch as if it were RFC 8428 calendar time. Such an archive
MUST either omit SenML time fields or retain device monotonic timing in clearly
identified adjacent non-SenML capture metadata.

## 4. Gaps and identity

The SenML numeric mapping alone does not carry the complete `stream_id`, sample
sequence, validity mask, or discontinuity cause contract. An export MUST retain
that information in adjacent capture metadata or a documented extension when
needed for round-trip interpretation.

Every gap starts a new contiguous segment. The exporter MUST preserve the
missing time interval and MUST NOT renumber, interpolate, zero-fill, or
time-compress samples. A reconnect with a new stream ID starts a new capture
segment and MUST NOT be merged silently with the prior stream.

## 5. Serialization scope

Browser-side SenML JSON export is Optional/Recommended v0.1. SenSML live
streaming and SenML CBOR are Future/Experimental. Neither is a Core live-wire
serialization. RFC 9193 PCM Data Value experiments are described only in the
non-normative appendix of `pcm-audio-v0.1.md`.
