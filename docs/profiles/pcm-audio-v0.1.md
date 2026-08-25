# `pcm-audio` Profile Version 0.1

## 1. Reference parameter set

This normative profile carries fixed-rate PCM in WebSocket binary messages.
The v0.1 reference implementation supports exactly:

```json
{
  "sample_format": "pcm-s16le-interleaved",
  "channel_count": 1,
  "channel_mask": 1,
  "sample_rate": {"numerator": 16000, "denominator": 1},
  "samples_per_frame": 256
}
```

Negotiation MUST validate `channel_count >= 1`, nonzero `channel_mask`,
`popcount(channel_mask) == channel_count`, positive rate numerator and
denominator, supported format, and supported complete parameter set. The v0.1
reference implementation MUST return `unsupported_parameters` for every other
set. A future protocol version may specify other sets without changing this
v0.1 requirement.

## 2. Payload and length

PCM data uses common frame type `FIXED_RATE_SAMPLES` (`0x01`). The 32-byte
envelope is followed immediately by signed PCM16 little-endian samples. There
is no profile-specific payload header. Channel samples would be interleaved by
sample frame; the v0.1 set is mono.

`sample_count` counts sample frames per channel and MUST be 256 for every normal
v0.1 reference data frame. The receiver MUST calculate with checked arithmetic:

```text
expected_payload_length = sample_count * channel_count * 2
```

Actual length MUST equal expected length exactly. Short payloads, long payloads,
partial channel frames, and non-reference sample counts are invalid.

## 3. Timing

For each new stream, the sender MUST establish exactly one PCM media-timeline
anchor for the first logical PCM sample position of that stream. The anchor is
the pair `anchor_sequence` and `anchor_timestamp_us`.

If the source exposes a valid acquisition timestamp for that first logical PCM
sample position in the device-local monotonic clock domain, the sender MUST use
that timestamp as `anchor_timestamp_us`. This path does not require a fallback
device-clock reading; the sender performs zero such fallback readings.

Otherwise, the sender MUST take exactly one device-monotonic clock reading at
the earliest producer-visible event at which the first converted PCM sample of
the new stream becomes available to the application's bounded acquisition
pipeline. This is the *producer-visible PCM materialization event*. If an
acquisition API exposes completed blocks rather than sample-by-sample events,
the first block-ready event MAY be this fallback event if and only if it is the
earliest producer-visible event at which that first converted sample becomes
available to the bounded acquisition pipeline.

A sender MUST NOT assign the current device-monotonic time to a PCM buffer whose
first sample had already become producer-visible before that reading. If no
source acquisition timestamp is available for samples that were already
materialized before the fallback event can be observed, those samples MUST NOT
be selected as the first logical PCM sample position of the new stream. The
sender MUST instead select a later sample position whose materialization event
can be observed prospectively. It also MUST NOT infer or backdate the anchor by
subtracting a nominal frame duration from a completion time. A record/start
request time, a later completion, poll, or consumer observation after an earlier
producer-visible materialization event, transport enqueue time, WebSocket send
time, browser arrival time, and wall-clock or SNTP time MUST NOT substitute for
the required anchor source event.

The fallback timestamp is not an acoustic wavefront timestamp and does not
guarantee a hardware or DMA acquisition edge. Version 0.1 does not represent
acquisition-to-materialization latency on the wire. Receivers continue to
interpret `first_sample_timestamp_us` as the stream's device-monotonic PCM
media-timeline anchor for the first logical sample position; they cannot
distinguish the acquisition and fallback paths from the wire and MUST NOT infer
acoustic or DMA latency from that field.

For every later transport frame at sequence `s`, the sender MUST generate the
nominal media timestamp from the single anchor and the negotiated rational rate:

```text
anchor_timestamp_us
  + (s - anchor_sequence) * rate_denominator * 1,000,000 / rate_numerator
```

Rational arithmetic avoids accumulated rounding. A receiver MAY allow at most
one microsecond of integer timestamp rounding error. The sender MUST NOT
independently read a timer to timestamp every later transport frame. A receiver
SHOULD retain the first frame's sequence/timestamp and validate later frames
against the same formula. Browser arrival time is not an audio timestamp.

PCM sequence is the logical sample-frame position, not a count of delivered
samples. Positions discarded during producer overflow, output-queue loss, or a
known-duration pause remain missing sequence positions. Consequently, a later
frame with `PRODUCER_OVERFLOW`, `OUTPUT_QUEUE_DROP`, or `SOURCE_PAUSED` MUST have
a positive sequence gap as well as `DISCONTINUITY`. If the exact number of
missing positions during a pause is unavailable, the sender MUST end the old
stream and start a new stream ID rather than estimate the gap.

## 4. Browser reference behavior

The v0.1 browser MVP provides waveform display, period observation, frequency
estimation, an explicit five-second capture, and WAV export. Realtime playback,
AudioWorklet, and spectrograms are outside Core v0.1.

S16LE samples can be read with `DataView.getInt16(offset, true)` or an aligned
little-endian `Int16Array`. Web Audio processing uses normalized `Float32`
samples; an `Int16Array` cannot be supplied as though it were an AudioBuffer
channel. Conversion for playback is a future feature.

## 5. Gaps and WAV export

A PCM discontinuity creates a new waveform segment. A browser MUST NOT draw a
line across the missing interval as if samples were continuous.

WAV export MUST use one explicit policy:

1. generate a separate WAV file for every contiguous segment; or
2. insert silence equal to the missing interval and preserve separate gap
   metadata.

The chosen policy MUST be visible to the user or export metadata. An exporter
MUST NOT silently delete the missing interval and shorten time.

## Appendix A. Experimental RFC 9193 mapping (non-normative)

Mapping PCM through the RFC 9193 SenML Data Value mechanism is Experimental.
It is not implemented by the v0.1 reference implementation and is not required
for conformance. It is not the live streaming path and is not required for WAV
export. Interoperability experiments MUST label the serialization and mapping
explicitly and MUST NOT imply that ordinary SenML JSON numeric records are a
PCM transport.
