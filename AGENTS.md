# Repository guidance

This file applies to the entire repository.

## Purpose

This repository defines a vendor-neutral device-to-browser streaming protocol,
browser-side reference behavior, schemas, validation material, and golden test
vectors.

Product-specific firmware belongs in the corresponding product repositories.

## Protocol requirements

- Use the protocol identifier `d2b-stream`.
- Keep the core protocol independent of product and manufacturer names.
- Use RFC-style MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY terminology
  consistently.
- All multi-byte binary fields MUST use little-endian byte order.
- Device timestamps MUST use a monotonic device-local clock.
- Sample sequence numbers MUST count sample frames, not transport frames.
- Missing samples MUST be represented as gaps and MUST NOT be silently
  interpolated, zero-filled, or removed from the time axis.
- Acquisition producers MUST NOT block on WebSocket transmission, HTTP
  handling, filesystem writes, or browser behavior.
- Version 0.1 supports at most one active stream-session owner.
- An implementation may advertise support for multiple READY control
  connections.

## Initial profiles

The initial profiles are:

- timestamped voltage/current measurement;
- fixed-rate signed 16-bit PCM audio.

Use neutral profile names. Do not use VAMeter, AtomNyan, Stack-chan, M5Stack, or
other product names in normative core protocol identifiers.

## C1 scope

The C1 change may add or modify only:

- documentation;
- JSON schemas;
- protocol golden test vectors;
- host-side validation utilities that use only the Python standard library.

C1 MUST NOT add:

- embedded firmware;
- a WebSocket server;
- a browser application;
- product-specific code;
- external JavaScript or Python dependencies;
- binary audio or measurement recordings;
- generated build artifacts.

## Working practices

- Preserve UTF-8 text and LF line endings.
- Do not commit transient generated files or build artifacts. Deterministically
  generated golden JSON vectors under `test-vectors/` are reviewed protocol
  source artifacts and MAY be committed when intentionally refreshed together
  with their generator.
- Run `git diff --check`.
- Validate every JSON file before reporting completion.
- Do not commit, push, create a pull request, or modify remotes unless the user
  explicitly instructs you to do so.
