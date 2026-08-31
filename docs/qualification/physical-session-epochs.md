# Physical Session Epochs

## 1. Scope and terminology

This document defines the common phase model for a physical qualification
session. The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be
interpreted as described in RFC 2119 and RFC 8174 when they appear in all
capitals.

The required phase order is:

```text
PREPARATION
    -> SETUP_EPOCH
    -> QUALIFICATION_EPOCH
    -> FINALIZATION
```

The product specification MUST define observable entry and exit conditions for
each phase. The physical claim window does not begin before the declared entry
to `QUALIFICATION_EPOCH`.

## 2. PREPARATION

Before any setup or claim-bearing action, `PREPARATION` MUST freeze:

- protocol authority;
- product, source, and candidate authority;
- observer and runner identity;
- evidence-root identity and confirmed absence;
- exact commands and argument vectors;
- target endpoint and stable device-identity method;
- expected result markers;
- the purpose, authority, value, and expiration result for every timeout,
  deadline, watchdog, and observation window; and
- permitted mutations and their execution limits.

Network-transition material, finalization authority, and cleanup or recovery
commands MUST also be frozen where applicable. A change to a frozen item
requires a new declaration and MUST occur before `QUALIFICATION_EPOCH`.

## 3. Time-bound classification

The product specification MUST classify every timeout, deadline, watchdog, and
observation window by purpose and MUST declare the result produced by its
expiration. The common purpose categories are:

- **`PROTOCOL_OR_PRODUCT_DEADLINE`**: satisfaction of the time bound is itself
  an implementation or product requirement;
- **`OBSERVATION_OR_LOGICAL_DURATION`**: a logical duration or exact observation
  amount defines the claim window through logical timestamps, exact records,
  exact samples, or another product-declared authority;
- **`OBSERVER_HEALTH_WATCHDOG`**: the bound detects observer stagnation or loss;
- **`HOST_ORCHESTRATION_ESCAPE`**: a wall-clock escape prevents the host harness
  from waiting indefinitely; and
- **`CLEANUP_OR_FINALIZATION_DEADLINE`**: the bound limits a declared cleanup or
  finalization operation.

These categories are qualification vocabulary, not wire-protocol data. If one
time bound serves more than one purpose, the product specification MUST declare
each authority and the result associated with each expiration meaning.

Expiration of an `OBSERVER_HEALTH_WATCHDOG` or `HOST_ORCHESTRATION_ESCAPE` MUST
NOT be reported as a protocol or product timing failure unless the product
specification explicitly defines that same time bound as a protocol or product
requirement. A logical-duration or exact-count acceptance criterion MAY remain
authoritative independently of a wider wall-clock escape deadline. Expiration
of any timeout, deadline, or watchdog MUST NOT silently trigger retry.

## 4. SETUP_EPOCH

`SETUP_EPOCH` establishes the declared observation and execution environment.
Only operations allowed by the product specification MAY occur. Examples of
declarable setup operations include:

- starting the observer;
- opening or intentionally resetting a capture association;
- same-device re-enumeration with stable-identity revalidation;
- activating a required service;
- associating the host with the target network context; and
- establishing chronology or correlation markers.

Every permitted reset, replacement, re-enumeration, or association change MUST
be declared. Completion of setup MUST establish the observer-health baseline,
candidate identity, runner identity, and evidence authority needed to enter the
claim window.

## 5. QUALIFICATION_EPOCH

Unless an operation is explicitly part of the predeclared case,
`QUALIFICATION_EPOCH` prohibits:

- silent retry;
- expectation or acceptance-criterion changes;
- undeclared observer replacement;
- undeclared transport-handle reopening;
- undeclared device reset or re-enumeration;
- runner or configuration mutation;
- evidence-root change; and
- candidate, server, or executable generation change.

The qualification epoch MUST record its start and end markers and correlate all
claim-bearing observations to the frozen authorities. Unexpected observer loss,
identity ambiguity, runner failure, or evidence failure MUST NOT produce PASS.
The product specification MUST predeclare whether the applicable result is
HOLD, INCONCLUSIVE, or FAIL.

Any rollback or recovery whose outcome contributes to the qualification claim
MUST be executed and observed within `QUALIFICATION_EPOCH`, or within a
separately declared qualification epoch or evidence generation, before
`FINALIZATION` begins. A product specification is not required to include
rollback or recovery, but it MUST classify any such declared action by its
claim and evidence boundary.

## 6. FINALIZATION

Before `FINALIZATION` begins, every claim-bearing qualification action,
including any declared claim-bearing rollback or recovery, MUST have completed.
Declared non-claim-bearing cleanup whose outcome belongs to the current
evidence generation MUST also complete before the observer and substantive
writers are stopped.

`FINALIZATION` then MUST:

1. prevent new qualification actions;
2. stop the observer deterministically and record the stop reason;
3. stop substantive writers;
4. finalize streams, results, and summaries;
5. generate the inventory;
6. generate `SHA256SUMS`;
7. independently verify the manifest;
8. record an outer identity for the manifest where required;
9. seal the evidence generation; and
10. state the exact claim boundary and exclusions.

The resulting action order is:

```text
qualification actions
    -> claim-bearing rollback/recovery when declared
    -> same-generation cleanup whose result is retained
    -> FINALIZATION
    -> deterministic observer stop
    -> substantive writer stop
    -> stream/result/summary finalization
    -> inventory
    -> SHA256SUMS
    -> independent manifest verification
    -> outer manifest identity where required
    -> seal
    -> only non-evidence-mutating post-seal cleanup
```

A same-generation cleanup failure MUST be retained and classified before
sealing and MUST NOT be silently retried or removed. Post-seal cleanup MAY occur
only when it cannot mutate the sealed generation. If retention of its result as
evidence is required, it MUST be written to a separately declared outer
operation record or a new evidence generation; it MUST NOT be appended to the
sealed generation.

## 7. Generation boundary

Independent qualification claims SHOULD use separate evidence generations
unless their atomic co-execution is itself part of the declared requirement.

A specification that combines otherwise independent claims MUST document the
rationale, shared authorities, ordering, and failure coupling. It MUST state
whether one case failure invalidates later cases, whether execution stops, and
how partial results are classified. Convenience alone is not sufficient to
erase independent provenance or retry boundaries.

## 8. Related documents

See the [common contract overview](README.md), [host observer contract](host-observer-contract.md),
[evidence lifecycle](evidence-generation-and-durability.md), and
[WebSocket lifecycle qualification](websocket-lifecycle-qualification.md).
