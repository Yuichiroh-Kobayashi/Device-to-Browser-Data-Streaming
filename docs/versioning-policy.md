# d2b-stream Versioning Policy

## 1. Normative policy

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted
as described in RFC 2119 and RFC 8174 when they appear in all capitals.

`d2b-stream` uses complete `major.minor` versions. The HTTP path contains the
major version (`/d2b/v0/`); `hello.versions`, `welcome.version`, and every binary
envelope carry or select the complete version.

The server MUST select one complete version offered by the client. Every binary
envelope's major and minor MUST exactly equal that selected version. A receiver
MUST NOT infer minor-version compatibility from a matching major alone.

A negotiated 0.1 session uses the exact 32-byte envelope defined by the core
specification. It has no length or extension field. A 0.1 receiver therefore
derives payload length by subtracting 32 from the complete WebSocket binary
message and applies the negotiated profile equation. Extra bytes are payload
and cause a length failure unless the profile equation accounts for them.

A future negotiated version MAY define a different envelope or an explicitly
specified extension mechanism. Such bytes MUST NOT be sent in a 0.1 session.
A major change indicates incompatible framing, semantics, or endpoint behavior.
A minor version MAY add registry values, profiles, or extensions, but MUST NOT
change an earlier negotiated version's field meanings. Registry values MUST NOT
be reassigned; deprecated values remain reserved.

Public Status Standard R1 is a named conformance revision of the existing
version 0.1 HTTP endpoint and is not carried in the response body. Its schema is
closed because current strict consumers reject unknown fields. Adding a public
status field requires a new named public-status revision and a coordinated
producer/consumer update; an implementation MUST NOT silently widen R1.

## 2. Profile evolution

A new standard profile requires a complete profile specification, negotiated
parameter schema, payload validation equation, browser behavior, and vectors.
Private profiles use reverse-domain identifiers. A receiver MUST reject every
profile it does not explicitly implement with `unsupported_profile`; version
negotiation does not authorize heuristic profile fallback.

## 3. Pre-1.0 status (non-normative)

Major version zero signals that later work may introduce incompatible changes.
Full-version negotiation prevents such a change from being accepted silently.
