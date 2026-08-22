# Implementation Guidance

This document is non-normative except where it restates requirements from the
core protocol or profiles.

## 1. Device pipeline

Use a high-priority acquisition producer and a lower-priority network consumer
joined by a fixed-capacity queue or ring buffer. Assign sequence and monotonic
timestamp at acquisition, before queueing. Keeping those values attached to the
sample makes loss visible even if queue or network delays vary.

When the acquisition queue is full, remove the oldest sample frame, saturating-
increment the producer drop count, and enqueue the new sample. Let the consumer
latch cause flags until it successfully sends a frame. A separate bounded
output queue makes post-acquisition drops distinguishable.

## 2. Frame construction

Calculate payload size with checked arithmetic before allocation. Build the
fixed 32-byte envelope using explicit little-endian stores; do not transmit a C
or C++ struct whose padding and endianness depend on the compiler. Format,
channel layout, rate, and reference frame size come from the accepted
`stream_started.parameters`, not from each data frame. Copy payload records only
after validating `sample_count` and profile limits.

Batch size balances overhead against latency and loss granularity. It must never
exceed the advertised maximum frame size. Sequence increments by sample frame,
even when a transport frame batches many frames or audio has several channels.

## 3. Receiver validation order

Validate outer message type and size before parsing. For binary messages, a
useful order is negotiated maximum length, the 32-byte minimum, magic, exact
version, frame type, flags, stream ID, nonzero data count, sequence overflow,
then the profile payload-length equation and record validation.
Update continuity state only after the complete frame has passed validation.

Keep per-stream state containing negotiated version, stream ID, profile,
selected format/layout/rate, next sequence, and the session timestamp anchor.
For PCM, read the device monotonic clock once for the first-sample anchor, then
generate every later transport-frame timestamp from that anchor and logical
sequence with rational or checked integer arithmetic. Do not independently read
a timer for each frame or add rounded frame durations repeatedly. A receiver
can apply a fixed ±1 microsecond tolerance. Never reinterpret an invalid
channel's float field as real data.

## 4. Concurrency and lifecycle

Allocate `stream_id` when accepting `start_stream`, not when the socket opens.
The first data frame MUST carry `STREAM_START`. On orderly stop, flush only
already accepted data that can be sent without blocking acquisition, then send a
`STREAM_END` binary frame and `stream_stopped`. On abrupt disconnect, release
client ownership promptly without stopping the producer in a blocking path.
The reference design may accept only one WebSocket connection. If multiple READY
sockets are implemented, ownership remains one atomic resource; test-and-claim
it without disrupting an existing owner.

## 5. Capability design

Give every physical or logical stream a stable neutral ID. A conforming device
implements at least one standard profile and advertises only profiles and
combinations it can sustain under its current build and resource limits.
Use exact `parameter_sets` and rational rates to avoid ambiguous Cartesian
combinations or floating-point negotiation. Treat capabilities as
read-only declarations and status as a snapshot; neither endpoint should have
side effects.

Capabilities containing only private profiles are not Core conforming. At least
one `vi-measurement` or `pcm-audio` descriptor must be present; private profiles
may be advertised alongside that standard profile.

Before advertising a profile, verify that `maximum_binary_frame_size` can hold
its minimum frame. The v0.1 PCM set requires 544 bytes and V/I requires 48
bytes. Do not advertise duplicate complete parameter sets within one profile.

## 6. Browser data handling

Decode with `DataView`, retaining raw sequence and timestamp values. JavaScript
numbers exactly represent integers only through 2^53-1, so long-running uint64
values should use `getBigUint64()` and `BigInt` where available. Convert to
relative plotting coordinates only after preserving the exact values.

For display, downsample or aggregate explicitly and keep the raw capture model
separate. For export, include gap markers rather than inventing samples. Use
bounded in-memory chunks and an explicit record/download action.

## 7. Public status implementation

Build public status from an explicit redacted snapshot; do not serialize the
authenticated WebSocket status object and remove selected fields afterward.
Set `Content-Type: application/json` and `Cache-Control: no-store` on successful
responses. Saturate every reported numeric field at the browser-safe maximum.

Drop and queue metrics use logical sample-frame units. If an output queue node
batches multiple logical sample frames, add its sample count to a drop counter
and queue gauge rather than adding one. Omit an optional metric if that unit
cannot be reported accurately. Do not turn omission into a synthesized zero.

A one-connection server can implement `connected_client_count` as the presence
of its sole control connection. A server that permits multiple `READY` control
connections must count all current control connections, not only the active
stream owner. Keep product queue capacities and connection limits outside the
vendor-neutral R1 schema.

Consumers should start a new cumulative-counter baseline after a detected
restart or whenever boot continuity across a reconnect is unknown. They should
not calculate deltas for gauges or for saturated cumulative counters.

## 8. Defensive checks

Fuzz short envelopes, huge count products, reserved flags, unsupported profiles,
invalid or truncated UTF-8, duplicate JSON keys, non-finite JSON numbers,
deeply nested options, state-invalid messages, binary data before
`stream_started`, binary messages beyond the negotiated maximum, cause flags
without PCM sequence gaps, duplicate connection
attempts, and disconnects during backpressure. All queues and logs should have
hard bounds. Tests should demonstrate that network stalls never stall the
acquisition producer.

## 9. Optional Arduino Serial Plotter diagnostic adapter

For USB serial bring-up, debugging, simple classroom plotting, or diagnosis of
a failed WebSocket path, an implementation may emit a separate text adapter:

```text
voltage:3.214	current:0.152
```

This follows the Arduino Serial Plotter label/value and tab-separated form. It
is not the primary stream path: it cannot preserve the application profile's
timestamp, sequence, gap, overflow, session, or PCM audio semantics. It should
therefore be disabled or routed independently during normal browser streaming.
