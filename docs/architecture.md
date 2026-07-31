# d2b-stream Architecture

## 1. Scope

This document describes the normative architecture of the `d2b-stream`
application profile version 0.1. The profile uses HTTP/1.1 and WebSocket as its
transport standards; it does not redefine either transport. The key words MUST,
MUST NOT, REQUIRED, SHOULD, SHOULD NOT, and MAY are to
be interpreted as described in RFC 2119 and RFC 8174 when, and only when, they
appear in all capitals.

The protocol carries read-only sampled data from a device to a browser. Device
administration, configuration, calibration, firmware update, and persistent
recording are outside this protocol.

## 2. Components and responsibilities

An implementation has five logical roles:

1. An acquisition producer obtains sensor or microphone sample frames.
2. A bounded queue or ring buffer transfers sample frames across the acquisition
   and transport boundary.
3. A profile encoder builds V/I records or PCM payloads.
4. A common HTTP/WebSocket session adds the 32-byte envelope and owns transport.
5. A browser common decoder validates session and continuity before dispatching
   to profile-specific display and export code.

The roles MAY share a process, but their blocking behavior MUST remain isolated.
The producer MUST NOT send WebSocket data, handle HTTP requests, write directly
to a filesystem, or wait for browser or network behavior. WebSocket, HTTP, and
filesystem latency MUST NOT block acquisition.

The producer-consumer buffer MUST be bounded. On overflow, the implementation
MUST discard the oldest queued sample frame, MUST continue acquisition, and MUST
increment the producer-drop counter. The next binary frame that can be sent MUST
set both `DISCONTINUITY` and `PRODUCER_OVERFLOW`.

## 3. Transport architecture

HTTP/1.1 serves the following normative resources:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/d2b/v0/` | Static browser entry asset |
| `GET` | `/d2b/v0/capabilities` | Immutable or infrequently changing capabilities |
| `GET` | `/d2b/v0/status` | Dynamic, read-only status |
| WebSocket Upgrade | `/d2b/v0/stream` | Control and sample stream |

`v0` identifies protocol major version 0. Control messages MUST be one complete
UTF-8 JSON value in one WebSocket text message. Sample data MUST use binary
messages. A server MUST reject binary messages received from a client.

Version 0.1 permits one active stream-session owner. A one-connection server is
conforming. Multiple authenticated `READY` control connections MAY coexist up
to `maximum_control_connections`, but are not required by the reference design.
If another READY connection requests a stream while an owner is STREAMING, it
MUST receive `busy`; the owner MUST NOT be displaced. Ownership is released on
stop or owner disconnect. An implementation without another socket MAY reject
the WebSocket Upgrade with HTTP 503 instead; this is resource rejection, not a
protocol-level `busy` response.

The client MUST request one exact advertised profile parameter set, and the
server MUST confirm it in `stream_started`. The network consumer MUST validate
every binary frame against the negotiated version, stream ID, profile, and
selected parameters before making samples visible.

## 4. Data and time model

A *channel sample* is one value for one channel. A *sample frame* is the set of
channel samples acquired at one logical time. A *transport frame* is one binary
WebSocket message containing the 32-byte common envelope and a profile payload.

Sequences count sample frames, not transport frames. Timestamps use a
device-local monotonic clock in microseconds. Missing sample frames remain gaps
in sequence and time; they MUST NOT be hidden by interpolation, zero fill,
renumbering, or time-axis compression.

For fixed-rate PCM, the sender reads the device monotonic clock for the first
sample-frame session anchor and derives later timestamps from that anchor,
sequence, and negotiated rational rate. It does not independently read a timer
for every transport frame. Receiver timing uses the same sequence/rate anchor,
not WebSocket arrival time. Selected PCM format, layout, and rate remain fixed
throughout the session.

## 5. Resource ownership and backpressure

The transport consumer SHOULD bound its pending WebSocket output separately
from the acquisition buffer. If backpressure discards samples or whole frames
after acquisition but before the WebSocket transport adapter accepts them, the
server MUST increment `output_queue_drop_count`. The next delivered frame MUST
set `DISCONTINUITY | OUTPUT_QUEUE_DROP` and preserve the original sequence and
timestamp. This condition is not TCP packet loss.

HTTP status and capability reads MUST NOT consume or mutate stream data.
Starting, stopping, or disconnecting a client MUST NOT require the producer to
wait for browser work.

## 6. Non-normative deployment view

A small implementation can use an interrupt or real-time task as producer, a
fixed-capacity ring buffer, and a lower-priority network task as consumer. The
browser can decode each binary message with `ArrayBuffer` and `DataView`, retain
gaps in its model, render with Canvas 2D, and export through a Blob URL.

Wi-Fi topology is a deployment-layer decision; the wire protocol does not
specify SoftAP channel selection. The baseline modes and operational risks are
described in `deployment-guide.md`.

Selection against existing serial, BLE, publish/subscribe, sensor-data, and
laboratory streaming approaches is documented in
`prior-art-and-protocol-selection.md`.
