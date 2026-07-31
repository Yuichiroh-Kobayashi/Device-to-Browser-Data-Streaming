# Security Model

## 1. Normative language and boundary

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted
as described in RFC 2119 and RFC 8174 when they appear in all capitals.

`d2b-stream` version 0.1 is a read-only observation protocol. It MUST NOT expose
Wi-Fi configuration changes, calibration, firmware update, filesystem deletion
or formatting, remote reboot, administrative settings, or automatic persistent
audio recording.

Any present or future administrative API MUST use a separate security boundary,
authorization policy, and endpoint namespace. Possession of stream access MUST
NOT imply administrative access.

## 2. Deployment modes

### 2.1 Isolated local SoftAP

An isolated device-hosted SoftAP MAY use `isolated` security mode when network
access is physically and operationally constrained. Operators SHOULD use WPA2
or stronger link security and a non-default credential. The HTTP and WebSocket
origin MUST expose only read-only streaming resources.

### 2.2 Shared LAN

A shared LAN deployment SHOULD use `pairing-token` mode. It SHOULD use TLS
(`https`/`wss`) or equivalent link protection; without it, the token and stream
remain exposed to passive interception despite application authentication. The
token MUST have sufficient entropy, MUST NOT be placed in URLs, and SHOULD be
scoped to read-only stream access. Implementations SHOULD support rotation or
expiration without changing administrative identity.

### 2.3 Unauthenticated read-only

`unauthenticated-read-only` MAY be used only after considering that any host able
to reach the device can observe available streams. The capability response MUST
advertise this mode. Read-only does not make measurement or audio data public or
non-sensitive.

## 3. Client and origin controls

Version 0.1 MUST enforce one active stream-session owner. A conforming reference
implementation MAY accept only one WebSocket control/data connection. If it
advertises more, it MUST retain no more than that number. A READY connection requesting
an owned stream MUST receive `busy` and MUST NOT displace the owner. Servers
SHOULD validate the HTTP `Origin` header against an implementation-configured
policy.

The browser-compatible normative token path is `hello.authentication`, because
the browser WebSocket API cannot set an arbitrary `Authorization` header. The
scheme MUST be `pairing-token`, and the token MUST be 1 through 256 UTF-8 bytes.
It MUST NOT appear in a URL query. Before successful authentication the server
MUST NOT send `welcome`, status details, or sample data. On failure it SHOULD
send a redacted `unauthorized` error when possible and MUST close the connection.
Cookie authentication and a separate HTTP pairing API are not defined in 0.1.

`GET /d2b/v0/status` is deliberately public and redacted, so it does not depend
on the WebSocket pairing token. It MUST NOT return tokens, client identity,
stream IDs, detailed session parameters, or raw data, and MUST include
`Cache-Control: no-store`. Detailed status is available only as a control
message after `hello` and successful authentication when pairing is configured.

## 4. Malformed input and resource limits

Implementations MUST apply the 2048-byte control-message limit before JSON
processing and the advertised maximum binary frame size before allocation. They
MUST validate UTF-8, duplicate JSON keys, non-finite numbers, JSON shape,
integer types and ranges, the 32-byte envelope, overflow-safe sequence and
length arithmetic, frame types, flags, negotiated profile parameters, and
profile payload equations. Invalid input MUST NOT reach acquisition code.

Servers SHOULD rate-limit repeated malformed requests, bound all queues, avoid
reflecting untrusted diagnostic strings, and close connections that repeatedly
violate the protocol. Error messages MUST NOT reveal credentials, memory
contents, filesystem paths, or administrative secrets.

## 5. Audio privacy and persistence

Audio can contain speech and environmental information. Device-side persistent
audio capture MUST be disabled by default. The stream protocol MUST NOT start
automatic persistent recording. Browser-side recording MUST begin only after an
explicit user action and SHOULD visibly indicate recording state and destination.
Deployments SHOULD provide a clear physical or on-screen indication of active
audio acquisition where feasible.

## 6. Log redaction

Logs MUST NOT contain pairing tokens, authentication objects, raw audio payloads,
or full measurement streams. Implementations SHOULD redact client identifiers
and network addresses according to deployment policy. Counts, error codes,
stream descriptor IDs, and bounded diagnostic context MAY be logged when they do
not reveal protected data.

## 7. Non-normative threat summary

The principal risks are unauthorized observation, privacy leakage, resource
exhaustion through malformed or oversized input, and accidental mixing of
administrative authority with stream access. Network segmentation, pairing,
strict limits, and a separate administrative plane reduce those risks.
