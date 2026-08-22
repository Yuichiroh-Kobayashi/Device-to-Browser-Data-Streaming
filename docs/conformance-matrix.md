# d2b-stream 0.1 Conformance Matrix

This matrix separates mandatory Core behavior from optional and experimental
work. A mention in repository documentation does not promote an optional or
future feature into Core.

| Area | Core v0.1 | Optional / Recommended v0.1 | Future / Experimental |
| --- | --- | --- | --- |
| Transport | HTTP/1.1 resources; WebSocket text control and binary data | reconnect UI and detailed diagnostics | WebTransport, MQTT gateway |
| Control | strict JSON; required messages; explicit errors | pairing token; detailed authenticated status | multiple READY reference behavior |
| Binary | exact 32-byte envelope; little-endian; payload equation | — | other versioned envelopes |
| Session | one active owner; new stream ID on reconnect | — | multiple active owners |
| Continuity | uint64 sequence/timestamp; flags; gaps preserved | redacted status counters | concealment algorithms |
| Public status | public, read-only, redacted `/d2b/v0/status` | closed Public Status Standard R1 schema, vectors, and reference validator | a new coordinated named public-status revision |
| Profiles | implement and advertise at least one of `vi-measurement` or `pcm-audio`; reject unimplemented/unknown profiles | implementing both standard profiles | generic scalar and private-profile implementations |
| V/I export | binary live profile and normative SenML mapping | CSV and SenML JSON files | SenSML live and SenML CBOR |
| PCM browser | waveform data model and segment behavior | five-second capture and WAV export | realtime playback, AudioWorklet, spectrogram |
| PCM interoperability | S16LE binary live payload | — | RFC 9193 PCM mapping |
| UI | common validated dispatch architecture | reconnect and diagnostics UI | dynamic channel UI |

The specification repository defines both standard profiles, but a conforming
device need implement only one. Capabilities MUST list only implemented
profiles. Core receivers MUST reject unsupported profiles and parameter sets;
they MUST not activate Future behavior through fallback. Optional exporters
remain bound by Core gap and timestamp semantics.
