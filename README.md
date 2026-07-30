# Device-to-Browser Data Streaming

A vendor-neutral protocol and browser reference design for continuously streaming measured or sampled data from embedded devices to web browsers.

## Status

This project is in the pre-1.0 specification phase.

The initial scope is:

- an HTTP and WebSocket transport model;
- a versioned binary streaming protocol;
- monotonic timestamps and sample sequences;
- explicit overflow, discontinuity, and gap semantics;
- a timestamped voltage/current measurement profile;
- a fixed-rate PCM audio profile;
- browser-side recording and export guidance.

This repository intentionally does not contain product-specific firmware.

## Design principles

- Device acquisition tasks must not block on network transmission or storage.
- Missing data must remain visible as missing data.
- Core protocol terminology must remain independent of individual products.
- Browser functionality must work without a CDN or mandatory framework.
- Administrative device operations are outside the read-only streaming protocol.

## Protocol identifier

The initial protocol identifier is:

```text
d2b-stream/0.1
```

## License

MIT License. See [LICENSE](LICENSE).
