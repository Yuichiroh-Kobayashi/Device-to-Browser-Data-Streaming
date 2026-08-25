# `vi-measurement` Profile Version 0.1

## 1. Scope and negotiation

This normative profile carries timestamped voltage/current measurements in
WebSocket binary messages. It uses common frame type `TIMESTAMPED_SAMPLES`
(`0x02`) and the negotiated parameter set:

```json
{
  "sample_format": "vi-f32le",
  "channel_count": 2,
  "channel_mask": 3,
  "sample_rate": {"numerator": 0, "denominator": 0}
}
```

Channel-mask bit 0 is voltage and bit 1 is current. Both channels are present in
every payload record; validity is represented independently. `0/0` means that
no nominal fixed rate is declared. When a nominal rate is advertised, numerator
and denominator MUST both be positive, but record timestamps remain authoritative.

## 2. Payload

The 32-byte common envelope is followed by exactly `sample_count` records.
Each record is 16 bytes and all multi-byte fields are little-endian:

| Offset | Size | Type | Field |
| ---: | ---: | --- | --- |
| 0 | 4 | uint32 | `delta_us` |
| 4 | 4 | uint32 | `valid_mask` |
| 8 | 4 | IEEE 754 binary32 | voltage in V |
| 12 | 4 | IEEE 754 binary32 | current in A |

The receiver MUST require:

```text
actual_payload_length == sample_count * 16
```

`sample_count` MUST be at least one. Short, long, or partial records are invalid.

## 3. Sequence and timestamps

The envelope's `first_sample_sequence` belongs to payload record zero. Record
`i` has sequence `first_sample_sequence + i`. The common receiver MUST reject
overflow of the last sequence.

The envelope's `first_sample_timestamp_us` is the timestamp of record zero.
Record timestamps are reconstructed as:

```text
first_sample_timestamp_us + delta_us
```

Record zero MUST have `delta_us == 0`. Subsequent `delta_us` values MUST be
nondecreasing; equal timestamps are allowed for sources whose clock resolution
is coarser than acquisition. Every timestamp addition MUST be checked as uint64,
and overflow is invalid.

For `vi-measurement`, each reconstructed record timestamp denotes the
measurement/acquisition time of the V/I sample frame represented by that record
in the device-local monotonic clock domain. A sender MUST assign or preserve
that measurement/acquisition timestamp at the measurement source/acquisition
boundary. It MUST NOT replace that timestamp with later producer
materialization, queue publication, transport enqueue, WebSocket send, or
browser arrival time. The `pcm-audio` producer-visible materialization fallback
does not apply to `vi-measurement`; record timestamps remain authoritative.

## 4. Validity

`valid_mask` has these assignments:

| Bit | Mask | Meaning |
| ---: | ---: | --- |
| 0 | `0x00000001` | voltage value valid |
| 1 | `0x00000002` | current value valid |
| 2–31 | — | reserved, MUST be zero |

A value whose validity bit is set MUST be finite. A cleared bit means the
corresponding float MUST NOT be interpreted as a measurement; it may be zero or
another implementation-defined placeholder. Invalid, overrange, unavailable,
and sensor-error states therefore remain distinguishable from valid 0 V or 0 A.

Future status detail MAY distinguish invalidity causes, but changing validity
bits or record size requires an explicitly specified compatible extension.

## 5. Gaps and browser behavior

The first frame for a new stream ID MUST set `STREAM_START`. Sequence or
timestamp discontinuities use the common flags. A browser MUST retain the exact
sequence, monotonic timestamp, validity, and segment boundary. It MUST NOT use
arrival time, synthesize missing readings, or compress a gap out of CSV or
SenML export.

The normative SenML mapping and export-time conversion are defined in
[`vi-measurement-senml-mapping.md`](vi-measurement-senml-mapping.md). SenML is
not the live payload format.
