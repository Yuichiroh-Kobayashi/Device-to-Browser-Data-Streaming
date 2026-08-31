# Production Execution-Path Preflight

## 1. Purpose

Unit, mock, syntax, import, and simulation checks can validate isolated logic,
but they do not qualify the shell, runtime, child-process, filesystem, writer,
finalizer, and handoff path that will execute physical qualification. This
document defines the host-only preflight for that production path.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted
as described in RFC 2119 and RFC 8174 when they appear in all capitals.

## 2. Same-path principle

Before physical qualification, the qualification-critical production execution
path SHOULD be exercised host-only with, where technically practical, the:

- same executable;
- same runtime version;
- same runner entrypoint;
- same child-process launcher;
- same shell boundary;
- same argument-vector materialization;
- same filesystem class;
- same evidence writer;
- same failure finalizer; and
- same inventory, checksum, and sealing path.

The preflight MUST record each difference from the intended physical path. Each
difference MUST be declared as an unqualified boundary with its reason and
residual risk. A product specification MUST NOT imply that a different path was
qualified.

## 3. Mock boundary

A mock, simplified writer, alternate launcher, or different filesystem class
does not qualify a different production execution path.

Mocks MAY establish logic-level properties, but their PASS MUST remain labeled
at that layer. Production-path preflight requires the actual path components
whose behavior is being claimed.

## 4. Positive and failure paths

The preflight plan MUST consider and classify at least:

- successful generation creation, execution, finalization, and seal;
- target-root collision;
- intentional child exit;
- primary runner failure;
- observer loss;
- partial evidence;
- evidence-writer failure;
- finalizer failure;
- manifest-verification failure;
- cleanup behavior; and
- failed-generation preservation.

Where safe deterministic injection is technically practical, these paths SHOULD
be executed through the production runner. A path not exercised MUST be listed
as NOT RUN or NOT PERFORMED with its claim boundary; it MUST NOT be inferred
from a mock.

The preflight MUST demonstrate that a failure does not silently retry, overwrite
an existing generation, delete partial evidence, or publish an invalid seal.

## 5. Cross-shell execution

Shell expansion, quoting, path conversion, working directory, environment
materialization, and child-process argument vectors are part of the execution
path. A cross-shell boundary MUST be recorded and exercised when it exists in
the physical runner.

Qualification SHOULD use materialized scripts and argument manifests instead
of deeply nested inline commands. The preflight SHOULD compare the materialized
argument vector and working directory with the authority frozen for physical
execution.

## 6. Network-context transition and offline handoff

If qualification changes the host network context in a way that can sever the
controlling session, all qualification-critical commands and authorities MUST
be materialized before that transition.

The materialized handoff MUST include:

- target endpoint;
- runner identity;
- observer identity;
- exact executable;
- exact argument vector;
- working directory;
- evidence root;
- expected success, failure, and hold markers;
- timeout and deadline semantics; and
- rollback, recovery, or cleanup command where applicable.

It MUST also identify the frozen candidate, stable device-identity method,
permitted mutations, finalizer, and seal path when those authorities are not
already embedded in the runner manifest. The offline path MUST NOT depend on
fetching new instructions or changing expectations after the transition.

## 7. Result and claim boundary

Preflight PASS establishes only that the declared host execution path behaved
as observed with the declared fixture. It does not establish physical device,
browser/device, network-quality, classroom, performance, or product PASS.

A preflight report MUST list its fixture, exercised paths, unqualified
differences, NOT RUN and NOT PERFORMED paths, retained failed generations, and
the exact claim boundary.

## 8. Related documents

See the [common contract overview](README.md), [host observer contract](host-observer-contract.md),
[physical session epochs](physical-session-epochs.md), and
[evidence lifecycle](evidence-generation-and-durability.md).
