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
- timeouts and deadlines; and
- permitted mutations and their execution limits.

Network-transition material, finalization authority, and cleanup or recovery
commands MUST also be frozen where applicable. A change to a frozen item
requires a new declaration and MUST occur before `QUALIFICATION_EPOCH`.

## 3. SETUP_EPOCH

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

## 4. QUALIFICATION_EPOCH

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

## 5. FINALIZATION

`FINALIZATION` begins after claim-bearing product actions stop. It MUST:

1. prevent new qualification actions;
2. stop the observer deterministically and record the stop reason;
3. stop substantive writers and finalize all evidence streams;
4. finalize results and summaries;
5. generate and verify the inventory and checksum manifest;
6. seal the evidence generation;
7. perform only declared cleanup or recovery; and
8. state the exact claim boundary and exclusions.

Cleanup MUST NOT mutate sealed evidence. A finalization or cleanup failure MUST
be retained as part of the generation and MUST NOT be silently retried or
removed.

## 6. Generation boundary

Independent qualification claims SHOULD use separate evidence generations
unless their atomic co-execution is itself part of the declared requirement.

A specification that combines otherwise independent claims MUST document the
rationale, shared authorities, ordering, and failure coupling. It MUST state
whether one case failure invalidates later cases, whether execution stops, and
how partial results are classified. Convenience alone is not sufficient to
erase independent provenance or retry boundaries.

## 7. Related documents

See the [common contract overview](README.md), [host observer contract](host-observer-contract.md),
[evidence lifecycle](evidence-generation-and-durability.md), and
[WebSocket lifecycle qualification](websocket-lifecycle-qualification.md).
