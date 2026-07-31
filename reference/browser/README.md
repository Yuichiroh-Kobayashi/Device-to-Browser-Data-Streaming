# Browser reference parser and synthetic-vector runner

This directory is a product-neutral, dependency-free browser reference for the
`d2b-stream/0.1` common parser. It is not a WebSocket server, product UI,
graphing tool, recorder, exporter, PWA, or firmware implementation.

It implements strict control parsing, capabilities validation, the 32-byte
binary envelope, V/I and PCM profile decoding, continuity/gap metadata, and a
static browser page that runs the four tracked synthetic vector documents.

## Run locally

From the repository root, start the standard-library server:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Open the following URL in Chrome or Edge:

```text
http://127.0.0.1:8000/reference/browser/
```

The page loads tracked JSON over HTTP; it does not support `file://` use. It
displays per-vector expected/actual results, invalid-state preservation,
golden-vector and parser-core self-test summaries separately, browser metadata,
elapsed execution time, and window error diagnostics.

## Scope and safety properties

- Raw byte input is authoritative for control-message UTF-8 validation and the
  2048-byte limit. The string input validates only its current encoded size.
- The strict scanner rejects duplicate keys, trailing data, non-finite numeric
  tokens, and float/exponent tokens in schema integer fields.
- Context-based control-state checks cover `client_to_server` request
  validation. Server-message transition management remains the caller's
  responsibility.
- Decoder state is committed only after a full binary frame is valid. Rejected
  inputs publish no samples and retain their input state unchanged.
- PCM timing derives from the negotiated rational rate and session anchor, not
  browser arrival time. V/I invalid channels are not published as measurements.

No npm packages, CDN assets, framework, service worker, or custom HTTP server
are required.
