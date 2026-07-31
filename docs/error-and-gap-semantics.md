# Error and Gap Semantics

## 1. Normative language

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted
as described in RFC 2119 and RFC 8174 when they appear in all capitals.

## 2. Gap definition and detection

A gap is one or more sample frames that were acquired or expected on a stream's
timeline but are unavailable to the receiver. A receiver MUST compare, for the
same `stream_id`:

- expected sequence (`previous first sequence + previous sample count`) with
  the next `first_sample_sequence`;
- profile-derived or explicit timestamps with the next first timestamp; and
- `DISCONTINUITY`, producer-overflow, output-queue-drop, source-paused, and
  timebase flags.

Any forward sequence jump is a gap and MUST be accompanied by `DISCONTINUITY`.
When the cause is known, its producer-overflow, output-queue-drop, source-paused,
or timebase-reset flag MUST also be present. A backward sequence is invalid.
For timestamped samples, the next frame's first timestamp MUST be greater than
or equal to the previous frame's last absolute sample timestamp; equality is
permitted. A smaller value is timestamp regression and is always invalid within
one stream ID.

The receiver MUST retain a detected gap as metadata on the time axis. It MUST
NOT hide it by zero filling, holding a previous value, silent interpolation,
compressing the time axis, or renumbering later sequences. Applications MAY
offer clearly labeled visualization or playback concealment, but retained raw
data and exports MUST preserve the gap and MUST distinguish synthetic values.

## 3. Producer overflow

Acquisition MUST feed a bounded queue or ring buffer. When full, the producer
MUST discard the oldest queued sample frame, increment `producer_drop_count` by
the number of discarded sample frames, and continue without blocking. The next
successfully sent sample frame MUST preserve its original sequence and timestamp
and MUST set `DISCONTINUITY | PRODUCER_OVERFLOW`.

The overflow flag reports that overflow occurred since the prior successfully
sent frame. It does not encode the drop count. A receiver uses sequence and
status counters to determine the count when available.

For fixed-rate PCM, a later frame carrying `PRODUCER_OVERFLOW` MUST have a
positive sequence gap. A cause flag with no missing logical position is invalid.

## 4. Output-queue loss

If an output queue discards sample frames after acquisition but before the
WebSocket transport adapter accepts them, the server MUST increment
`output_queue_drop_count` by the number discarded. The next delivered sample
frame MUST set `DISCONTINUITY | OUTPUT_QUEUE_DROP` and retain its original
sequence and timestamp. A server MUST NOT relabel output-queue loss as producer
overflow. `OUTPUT_QUEUE_DROP` does not report TCP packet loss.

For fixed-rate PCM, a later frame carrying `OUTPUT_QUEUE_DROP` MUST have a
positive sequence gap. A cause flag with no missing logical position is invalid.

TCP preserves the ordered bytes accepted by transport, and WebSocket preserves
message ordering while connected. Neither preserves samples discarded before
transport acceptance. An unexplained sequence gap MUST still set
`DISCONTINUITY` and be preserved even when no cause flag is available.

## 5. Pause and timebase reset

While a source is paused, the sender MUST NOT fabricate samples to imply normal
acquisition. The first data frame after a pause MUST set
`SOURCE_PAUSED | DISCONTINUITY`; `SOURCE_PAUSED` alone is invalid. Fixed-rate
audio silence MUST NOT be synthesized solely to cover suspension. If an exact
missing count is unavailable, the sender MUST end the old session and start a
new stream ID rather than guess a sequence.

For fixed-rate PCM, a later frame carrying `SOURCE_PAUSED` MUST have a positive
sequence gap. Known paused positions remain missing logical sample positions.

A disconnect or timebase reset MUST end the old session. A reconnect or reset
MUST use a new `stream_id` and its first data frame MUST set `STREAM_START`;
when signaling the reset it MUST also set `TIMEBASE_RESET | DISCONTINUITY`.
The flag cannot legalize
timestamp regression within the prior stream ID.

## 6. Control and frame errors

Malformed or schema-invalid control input produces `invalid_message`. Messages
that exceed an advertised limit produce `frame_too_large`. Messages valid in
shape but wrong for session state produce `invalid_state`. Unknown streams,
profiles, or exact parameter combinations produce `unknown_stream`,
`unsupported_profile`, or `unsupported_parameters`. Negotiation failure produces
`unsupported_version`, failed authentication produces `unauthorized`, and an
already-owned stream produces `busy`.

A receiver MUST reject a malformed binary frame as a whole and MUST NOT decode
or partially publish its payload. A server SHOULD report a control `error` when
possible. It MAY close the WebSocket after malformed input, repeated violations,
or any condition where continued parsing would be unsafe.

## 7. Counter behavior

Drop counters are unsigned cumulative sample-frame counts for the current device
uptime. They MUST NOT count transport frames. They MUST be monotonic until reboot
or explicit implementation-wide counter reset. A reset SHOULD be inferable from
`uptime_us` regression or a new device session. Counter saturation MUST retain
the maximum value rather than wrap.

## 8. Non-normative examples

If a frame carries sequences 0–9 and the next carries 15–19, sequences 10–14
remain a five-frame gap. If an audio source pauses between those frames, the UI
can show a muted interval, but an exported raw timeline should mark it missing
rather than insert five zero-valued PCM frames.
