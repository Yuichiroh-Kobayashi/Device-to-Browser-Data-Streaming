# Evidence Generation and Durability

## 1. Scope and terminology

This document defines the lifecycle, publication, durability, copy, and
classification rules for qualification evidence. The key words MUST, MUST NOT,
SHOULD, SHOULD NOT, and MAY are to be interpreted as described in RFC 2119 and
RFC 8174 when they appear in all capitals.

An **evidence generation** is one collision-free root containing the evidence
and metadata for one declared execution boundary.

## 2. Fresh generation and immutable history

The target evidence root MUST NOT already exist. Creation MUST stop on a
collision. A runner MUST NOT delete, empty, overwrite, or repurpose the
colliding root to retry; it MUST use a new generation identity under separately
recorded authority.

Failed, incomplete, corrected, and superseded generations remain immutable
historical evidence.

A later reviewer MAY add an external classification or a successor reference,
but MUST NOT repair the original evidence bytes in place. A corrected execution
MUST use a new generation and SHOULD link to the earlier generation without
changing it.

## 3. No silent retry

A qualification failure, observer failure, or evidence failure MUST NOT be
silently retried within the same evidence generation unless the retry itself
was explicitly part of the predeclared procedure.

Every declared retry MUST be visible in chronology and results. An undeclared
retry requires a fresh generation and MUST NOT erase the failed attempt.

## 4. Writer declaration

The product specification or runner authority MUST declare:

- the filesystem class used by the authoritative evidence root;
- the writer runtime and version;
- which files are streaming objects and which are complete objects;
- the writable-handle lifecycle;
- the durability mechanism and its ordering;
- the finalizer and its failure behavior;
- copy or import steps and their authority; and
- the sealing mechanism and seal boundary.

The declaration SHOULD also identify temporary-file policy, process termination
order, and which files can still change during each finalization step. An
unqualified difference between the declared writer path and the physical runner
MUST be reported as a claim boundary.

## 5. Publication and streaming files

Where supported, a complete object SHOULD be written to a temporary file on the
same filesystem, finalized, and published through an atomic rename or replace.
The temporary and final paths MUST remain within the declared evidence
generation.

Streaming logs MUST be classified separately from complete objects. They MAY be
written incrementally, but MUST have an explicit stop point, writable-handle
closure, finalization result, and durability boundary. A partially finalized
stream MUST remain identified as partial evidence.

Atomic publication does not by itself establish durable storage. Durability and
publication are separate properties and MUST be evaluated separately.

## 6. Durability semantics

Evidence that must survive an immediately following process termination or
execution handoff MUST use a platform-supported durability mechanism through a
writable authority associated with the actual write, and that mechanism MUST be
exercised in production-execution-path preflight.

A read-only descriptor or handle reopened after a write MUST NOT be assumed to
be a portable durability-flush authority without host qualification.

The product specification owns the exact host API and MUST record the runtime,
filesystem class, success/failure observation, and residual guarantees. This
common contract establishes no host-specific API as qualified merely by naming
it.

## 7. Finalization order

Evidence sealing MUST begin only after every declared qualification action and
every cleanup or recovery action whose result belongs to the generation has
completed.

Finalization MUST use this ordering:

1. stop all substantive writers;
2. explicitly finalize streaming files;
3. finalize results and observer summaries;
4. generate the inventory;
5. generate `SHA256SUMS`;
6. independently verify the manifest;
7. record an outer identity for the manifest where required; and
8. seal the generation.

`SHA256SUMS` MUST NOT be followed by substantive evidence mutation. Metadata
whose design necessarily exists outside the manifest, such as an external
manifest identity or review annotation, MUST be clearly separated from the
sealed generation.

A failure at any finalization step MUST be recorded if safely possible. It MUST
NOT cause deletion or repair of the failed generation.

## 8. Copy and import

An evidence copy or import MUST record a source inventory and identity before
copy, a destination inventory and identity after copy, the copy mechanism and
result, and an explicit identity comparison. The destination MUST NOT be sealed
as an identical import unless the comparison succeeds.

A cross-filesystem copy MUST NOT be treated as an atomic rename. Failure or
partial copy MUST preserve the source authority and leave the destination
classified as incomplete.

## 9. Public and private evidence

Evidence MUST be classified before publication. Private evidence commonly
includes raw device output, credentials, test canaries, stable hardware
details, local absolute paths, private network identifiers, and unredacted
requests or responses. Public evidence commonly includes source and candidate
identities, a safe environment summary, redacted status, result matrices,
manifest hashes, claim boundaries, and explicit NOT RUN or NOT PERFORMED
entries.

Secrets and canaries MUST NOT appear in public evidence, logs intended for
publication, error text, or filenames. Public redaction MUST preserve enough
identity and chronology to support the reviewed claim without exposing private
material.

A product specification MAY tighten these categories. It MUST declare where
private evidence is stored, who may review it, what public derivative is
permitted, and how public/private identities are correlated without copying
secret material.

## 10. Related documents

See the [common contract overview](README.md), [host observer contract](host-observer-contract.md),
[physical session epochs](physical-session-epochs.md), and
[production execution-path preflight](production-execution-path-preflight.md).
