# Host Observer Contract

## 1. Scope and terminology

This document defines the authority and health model for a host observer used
during physical qualification. The key words MUST, MUST NOT, SHOULD, SHOULD NOT,
and MAY are to be interpreted as described in RFC 2119 and RFC 8174 when they
appear in all capitals.

## 2. Observer session model

One observer session is the composition of:

- helper process identity;
- stable hardware identity;
- zero or more transport-handle epochs;
- a raw stream;
- a decoded stream;
- a liveness stream;
- a byte-progress stream;
- health intervals; and
- a final summary.

An observer session is a logical evidence authority, not a transport handle.
Continuous observation MUST NOT be equated with one continuously open handle.
The raw, decoded, liveness, and byte-progress streams MAY be separate files or
records, provided their chronology and identity can be correlated.

The product specification MUST define when the observer session begins, which
events it is responsible for detecting, and which health dimensions are
required for each claim.

## 3. Health separation

```text
process alive != observer healthy
port exists != observer healthy
network reachable != serial evidence healthy
```

Observer health has separate dimensions:

- **process liveness**: whether the declared helper process was running;
- **transport association**: whether a handle was associated with the declared
  stable hardware identity;
- **byte progress**: whether new raw evidence bytes arrived as required by the
  declared observation model;
- **decode progress**: whether raw input was decoded and relevant events could
  be recognized without an unreported decoder failure; and
- **finalization**: whether streams and summaries were closed and finalized in
  the declared manner.

Evidence of one dimension MUST NOT be substituted for another. A product
specification MUST state which dimensions and progress expectations establish a
healthy interval, including how an intentionally quiet interval is
distinguished from observer failure.

## 4. Stable device identity

A port name alone is insufficient device authority. The product specification
MUST declare a stable hardware identity method and the independently recorded
attributes used to resolve it.

Permitted categories include a hardware-provided stable identifier, transport
enumeration identity, interface identity, controlled physical topology, or a
combination of independently observed attributes. This contract does not
mandate one bus, operating system, enumeration scheme, or diagnostic format.

Identity MUST be checked before association and after any re-enumeration. An
ambiguous or changed identity MUST end the affected health interval and MUST
NOT be silently accepted as the same device.

## 5. Transport-handle epochs and re-enumeration

A transport-handle epoch begins when the observer associates a new handle with
the declared hardware identity and ends when that association is lost or
closed. Handle epochs MUST be recorded with their start and end reasons.

During `SETUP_EPOCH`, a product specification MAY declare that handle loss and
re-enumeration of the same verified hardware remain within one observer
session. The transition MUST create a new handle epoch, revalidate identity,
and record the resulting health interval.

During `QUALIFICATION_EPOCH`, re-enumeration, handle reopening, or helper
replacement MUST NOT be treated as transparent recovery unless the product
specification explicitly declares that transition as part of the case. An
undeclared transition invalidates continuous-health claims for the affected
window and requires the declared HOLD, INCONCLUSIVE, or FAIL handling.

## 6. Absence claims

An absence claim is invalid unless the observer responsible for detecting the
event was demonstrably healthy throughout the relevant observation window.

The absence of a decoded event or log entry is insufficient by itself. The
evidence MUST identify the window boundaries and establish all health
dimensions required by the product specification throughout that window.
Depending on the observation model, this can include process liveness,
transport association, expected byte progress, decoder progress, relevant
events before and after the window, and an independent client or status
correlation.

If required health cannot be established for the complete window, the absence
MUST NOT be reported as PASS. The applicable result is HOLD, INCONCLUSIVE, or
FAIL as predeclared by the product specification.

## 7. Final summary

The observer MUST emit a final summary that conceptually records at least:

- observer process, executable, and runtime identity;
- stable hardware identity and verification result;
- observer-session start and stop times or monotonic chronology markers;
- transport-handle epoch count and each transition reason;
- liveness intervals;
- associated transport intervals;
- raw byte totals and byte-progress observations;
- decoded event counts and decode-error counts;
- observer loss, recovery, or identity ambiguity;
- start and stop reasons;
- finalization result; and
- clean or unclean termination.

The summary MUST be correlatable with the raw and decoded streams. This
contract does not require one product-specific breadcrumb or summary schema.

## 8. Related documents

See the [common contract overview](README.md), [physical session epochs](physical-session-epochs.md),
[evidence lifecycle](evidence-generation-and-durability.md), and
[production execution-path preflight](production-execution-path-preflight.md).
