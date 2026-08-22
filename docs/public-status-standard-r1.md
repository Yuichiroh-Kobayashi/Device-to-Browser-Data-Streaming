# Public Status Standard R1

## 1. Status and scope

Public Status Standard R1 is a named conformance revision for the existing
public, unauthenticated, read-only, redacted response from
`GET /d2b/v0/status`. It applies to `d2b-stream` version `0.1`; it does not
change that version, the `/d2b/v0/status` path, the binary envelope, control
messages, capabilities, stream profiles, or the one-active-owner policy.

R1 is not negotiated on the wire. In particular, the response body contains no
R1 identifier, `schema_version`, or `boot_id`. An implementation claims R1
conformance out of band against the schema whose identifier is:

```text
urn:d2b-stream:0.1:public-status:r1
```

The key words MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT, and MAY are to be
interpreted as described in RFC 2119 and RFC 8174 when, and only when, they
appear in all capitals.

## 2. Representation

An R1 response body MUST be a JSON object accepted by
`schemas/public-status.schema.json`. The required fields are `protocol`,
`version`, `state`, and `uptime_us`. The optional metrics are
`producer_drop_count`, `output_queue_drop_count`, `queued_sample_count`, and
`connected_client_count`. No other field is permitted.

`protocol` MUST equal `d2b-stream`, `version` MUST equal `0.1`, and `state` MUST
be either `idle` or `streaming`. `idle` means that no active stream session
exists. `streaming` means that an active stream session exists. Product-specific
fault, pause, stopping, or readiness states MUST NOT be added to the public R1
state enumeration.

Every numeric value MUST be a nonnegative mathematical integer no greater than
9007199254740991. Validators MUST NOT coerce strings, null, booleans, or
fractional values, and MUST NOT round, floor, or truncate an invalid value. R1
uses parsed JSON value semantics: the JSON texts `1` and `1.0` denote the same
mathematical integer for this contract.

Omission of an optional metric means unavailable or not reported. A consumer
MUST NOT substitute zero for an omitted metric.

## 3. Metric semantics

`uptime_us` is device-local monotonic time in microseconds since the current
boot or reset epoch. It is required. An implementation whose internal uptime
exceeds the browser-safe maximum MUST report 9007199254740991. Time elapsed
after saturation cannot be recovered exactly from this field.

`producer_drop_count` and `output_queue_drop_count`, when present, are
cumulative counts of logical sample frames lost during the current boot or
reset epoch. They do not report TCP packet loss. `producer_drop_count` covers
logical sample frames lost because acquisition or its immediate bounded
producer queue could not retain them. `output_queue_drop_count` covers logical
sample frames discarded after acquisition and before transport-adapter
acceptance.

If one queued item contains multiple logical sample frames, a drop counter MUST
increase by the number of logical sample frames lost, not merely by one queue
node. An implementation that cannot report that unit accurately MUST omit the
affected optional field. Within one observed epoch, a reported cumulative
counter MUST NOT decrease. A counter MAY saturate at 9007199254740991; the
saturated value is a lower bound, and later deltas are unknown.

`queued_sample_count`, when present, is the instantaneous number of logical
sample frames retained in bounded pipeline queues at the observation point. It
is not a byte, transport-packet, or queue-node count unless each queue node
represents exactly one logical sample frame. It is a gauge and may increase or
decrease.

`connected_client_count`, when present, is the instantaneous number of current
WebSocket control connections. A one-connection implementation reports zero or
one. If an implementation permits multiple `READY` control connections, it
reports all current control connections rather than only the active stream
owner. This gauge may increase or decrease.

## 4. Restart and delta processing

A reboot or reset may reset `uptime_us` and cumulative counters. An observed
decrease in `uptime_us` establishes a new epoch. If boot continuity across a
disconnect or reconnect cannot be established, a consumer MUST start a new
counter baseline and MUST NOT join a later counter delta to an earlier epoch.
R1 deliberately has no `boot_id`.

Gauge values are not subject to nondecreasing or cumulative-delta checks.
Consumers MUST NOT synthesize a zero when an optional metric disappears.

## 5. HTTP and privacy boundary

A successful R1 response MUST use `Content-Type: application/json` and MUST
include `Cache-Control: no-store`. Content-Type parameter ordering and JSON
object property ordering are not normative.

Public status MUST NOT expose authentication data, tokens, credentials, client
identity, MAC or IP addresses, device serials, stream or session identifiers,
detailed negotiated parameters, raw samples, voltage, current, filesystem
paths or names, Wi-Fi credentials, raw requests or headers, or private error
detail. An implementation MUST NOT encode such data into an otherwise permitted
field. The authenticated WebSocket `status` representation MUST NOT be reused
as the public HTTP response.

## 6. Conformance and evolution

The schema, `test-vectors/public-status.json`, Python validator, and browser
reference validator define the executable R1 acceptance boundary. The reference
validator error code `invalid_public_status` is local validation output; it is
not a new WebSocket wire `error.code`.

R1 is closed because existing strict consumers reject unknown properties. A
future public-status field requires a new named public-status revision and a
coordinated producer/consumer update. Implementations MUST NOT silently widen
R1 or change its unknown-field rule to ignore extensions.
