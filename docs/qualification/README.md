# Common Physical Qualification Contract

## 1. Purpose and scope

This directory defines the vendor-neutral qualification contract for observing,
preserving, and judging a physical implementation of `d2b-stream`. The key words
MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted as described
in RFC 2119 and RFC 8174 when they appear in all capitals.

This contract governs:

- physical qualification infrastructure;
- the host observer and its health authority;
- evidence generations and their lifecycle;
- physical session epochs;
- WebSocket negative and lifecycle qualification; and
- production execution-path preflight.

It does not define or change:

- wire, schema, or golden-vector semantics;
- product-specific acceptance values;
- product user interfaces or setup instructions;
- product-specific topology or service-exclusion rules;
- a specific host runtime or API;
- firmware or browser implementation behavior; or
- protocol versioning, authentication, or close-code semantics.

The [protocol specification](../protocol-v0.1.md), schemas, and golden vectors
remain the authority for wire behavior. This contract is normative only for
qualification procedure, observer authority, evidence lifecycle, epoch
declaration, lifecycle case classification, execution-path preflight, and claim
boundaries.

## 2. Authority hierarchy

```text
protocol/schema/vector authority
        -> common qualification contract
        -> product-specific qualification specification
        -> dated evidence generation
        -> reviewed claim
```

Each layer MUST remain traceable to the authority above it. A dated evidence
generation records one execution; it does not replace the current contract or
authorize a later execution. A product specification MAY tighten this contract
or add product acceptance requirements, but it MUST NOT weaken protocol
requirements or silently redefine this contract.

## 3. Result vocabulary

- **PASS**: the declared requirement was executed and the required observer and
  evidence authority establish that it held.
- **FAIL**: the declared requirement was executed and the required behavior did
  not hold.
- **HOLD**: execution or a claim is suspended because authority, a precondition,
  observer health, or required review is missing. HOLD does not establish a
  product failure.
- **INCONCLUSIVE**: execution began, but the available evidence cannot support
  either PASS or FAIL, for example because correlation failed or observer health
  was lost.
- **NOT RUN**: a case or stage planned for the generation was not started.
- **NOT PERFORMED**: a case was deliberately excluded, deferred, or declared not
  applicable. NOT PERFORMED MUST NOT be interpreted as PASS.

`STOP` is an execution-control instruction. It ends further execution or
mutation under the current authority; it is not a result. After a STOP, the
generation MUST still be finalized as far as safely possible and assigned an
applicable result from the vocabulary above.

## 4. Claim boundary

Passing a host, build, simulation, or synthetic layer MUST NOT be reported as
establishing a physical, browser/device, classroom, or product claim.

A claim MUST identify its evidence layer, declared requirement, candidate,
observer authority, evidence generation, and exclusions. Evidence from one
layer MAY support a later procedure, but it MUST NOT be promoted to a claim
whose physical behavior was not observed.

## 5. Product-specification declaration checklist

Before execution, each product-specific qualification specification MUST
declare:

- protocol authority;
- product and source authority;
- candidate authority;
- stable device identity and the method used to verify it;
- observer authority;
- observer health requirements;
- setup-epoch permissions;
- qualification-epoch prohibitions;
- finalization requirements;
- network-transition and offline-handoff requirements;
- qualification stages;
- the evidence-generation boundary for each stage;
- positive lifecycle cases;
- handshake-negative cases;
- accepted-session negative cases;
- abrupt-lifecycle cases;
- owner and session correlation identifiers;
- the health evidence required for absence claims;
- the public/private evidence boundary;
- the durability mechanism and its host/filesystem qualification;
- finalization order;
- collision behavior;
- retry policy;
- timeout and deadline semantics;
- success, failure, and hold markers;
- the physical claim boundary; and
- rollback or recovery boundaries where applicable.

A product specification MUST identify every deviation from a SHOULD in this
contract, give its rationale, and record the residual risk. Product acceptance
values, device operations, and diagnostic representations remain extension
points owned by that product specification.

## 6. Reading order

Read this overview first, followed by:

1. [Production execution-path preflight](production-execution-path-preflight.md)
2. [Host observer contract](host-observer-contract.md)
3. [Physical session epochs](physical-session-epochs.md)
4. [WebSocket lifecycle qualification](websocket-lifecycle-qualification.md)
5. [Evidence generation and durability](evidence-generation-and-durability.md)

The product-specific qualification specification completes the procedure after
these common documents.
