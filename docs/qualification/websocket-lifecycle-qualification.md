# WebSocket Lifecycle Qualification

## 1. Scope and terminology

This document classifies physical WebSocket negative and lifecycle cases. It
does not add to or change WebSocket or `d2b-stream` wire, authentication,
ownership, error, or close semantics. The protocol specification and product
specification provide the expected behavior for each case.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted
as described in RFC 2119 and RFC 8174 when they appear in all capitals.

Each case MUST use exactly one primary class:

```text
HANDSHAKE_NEGATIVE
SESSION_CONTROL_NEGATIVE
LIFECYCLE_POSITIVE
ABRUPT_LIFECYCLE
```

## 2. HANDSHAKE_NEGATIVE

`HANDSHAKE_NEGATIVE` covers rejection before a WebSocket session is accepted.
Depending on existing protocol and product requirements, hard semantics can
include:

- no successful upgrade;
- no unintended ownership acquisition or displacement beyond the
  product-declared exclusion or handoff policy;
- no binary data on the rejected attempt; and
- preservation of an active owner or service when the product specification
  explicitly declares that owner or service protected from the competing
  admission attempt.

The product specification MUST identify which semantics are authoritative and
how they are observed. Client-runtime terminal event ordering, local error text,
and a transport close code are diagnostic-only unless the protocol or product
specification explicitly makes them normative. Qualification MUST NOT invent a
new close requirement to make a client harness deterministic.

This policy flexibility MUST NOT weaken ordinary single-D2B-owner
qualification. When the protocol or product contract protects the current D2B
owner from a rejected second D2B owner attempt, that owner MUST remain unchanged
and healthy as declared.

## 3. SESSION_CONTROL_NEGATIVE

`SESSION_CONTROL_NEGATIVE` covers an invalid operation after a WebSocket
connection has been accepted. It is separate from handshake rejection.

Cases MAY cover invalid state, malformed or unsupported messages, disallowed
frame types, size-limit violations, and authentication or authorization failure
within an accepted session. The product specification MUST declare the expected
control, error, ownership, data, and connection behavior from existing protocol
authority. A harness MUST NOT apply handshake-negative terminal expectations to
an accepted-session case.

## 4. LIFECYCLE_POSITIVE

`LIFECYCLE_POSITIVE` establishes the declared orderly path and SHOULD correlate:

```text
admission
    -> owner acquisition
    -> session and stream start
    -> control and data progress
    -> orderly stop acceptance
    -> orderly completion
    -> owner release
    -> idle or drained state
```

The case MUST identify which events are protocol requirements, which are
product diagnostics, and which observer-health evidence supports the timeline.
Orderly completion MUST NOT be inferred from connection closure alone.

## 5. ABRUPT_LIFECYCLE

`ABRUPT_LIFECYCLE` begins with ungraceful transport loss or another declared
abrupt termination. Qualification MUST consider:

- cleanup of the former owner;
- absence of stale-owner debt;
- absence of fabricated orderly completion unless existing protocol authority
  requires such completion;
- successful later admission;
- a new connection, session, or stream identity where required;
- absence of stale control or data on the new lifecycle; and
- a later orderly stop and completion.

An abrupt case MUST NOT be judged by silently converting it into an orderly
stop. Reconnect evidence MUST correlate the old and new lifecycle identities
without treating them as one continuous stream.

## 6. Single-owner qualification

A single-owner rejection case MUST correlate evidence from:

- the rejected client;
- the protected active owner;
- device ownership state; and
- observer health for the case window.

A terminal event from the rejected client is insufficient authority by itself.
PASS requires the declared evidence that no forbidden acquisition or
displacement occurred and that the protected owner remained healthy when that
health is part of the requirement.

## 7. Cross-service exclusion and handoff qualification

A product MAY declare D2B mutually exclusive with another long-lived service.
The product specification MUST define the admission and transition policy in
each direction, including the product-declared exclusion states, stable states,
and recoverability requirements.

The common contract does not require an already-active non-D2B service to
remain active after a competing D2B admission attempt. A product specification
MAY declare preservation of that service, its intentional stop or invalidation
as part of a handoff, or another protocol-compatible transition. The common
contract MUST NOT choose among those policies and MUST NOT require directional
policies to be symmetric.

For each declared exclusion or handoff transition, qualification MUST establish
that:

- conflicting ownership or reservations do not coexist;
- a rejected or transitional admission does not acquire unintended ownership;
- every declared stop, invalidation, handoff, or cleanup reaches its declared
  completion;
- no stale reservation, inhibition, or transition debt remains;
- the exclusion state reaches the product-declared stable state; and
- a later admission declared recoverable can demonstrably succeed.

These invariants MUST be correlated across the competing admission, active or
transitioning service, product-declared exclusion state, and observer health.
They constrain state integrity and recoverability without requiring every
rejected admission to be side-effect-free.

## 8. Correlation identifiers

The product specification MUST declare the stable identifiers available to
correlate admission, owner, connection, session, stream, server generation,
device epoch, and observer chronology as applicable. It MUST also define the
scope and uniqueness of each identifier and the handling of missing or
ambiguous correlation.

This contract does not mandate one diagnostic schema or require every
implementation to expose the same identifiers. The declared set MUST be
sufficient to distinguish relevant old, rejected, active, and new lifecycles.

## 9. Secret and log-leak boundary

When a negative case uses a credential, secret, or test canary, the product
specification MUST declare where it may appear, the private evidence that can
contain it, and the public evidence from which it is prohibited. The canary
SHOULD be unique to the evidence generation and MUST NOT grant unintended
authority beyond the case.

Public logs, reports, error text, filenames, and redacted evidence MUST be
scanned for the canary and other declared secrets before publication. A leak is
an evidence/security failure under the product specification and MUST NOT be
hidden by redaction after the generation is sealed.

## 10. Related documents

See the [common contract overview](README.md), [host observer contract](host-observer-contract.md),
[physical session epochs](physical-session-epochs.md), and
[evidence lifecycle](evidence-generation-and-durability.md).
