# Prior Art and Protocol Selection

This document is non-normative. It explains why `d2b-stream/0.1` is a small
application profile and reference design built on HTTP/1.1 and WebSocket, not a
replacement transport protocol. Browser implementation status in this document
was checked on 2026-07-31.

## Comparison

The comparison assumes a small embedded device sending voltage/current
measurements or PCM sample frames directly to a browser.

| Approach | Transport and deployment | Direct browser use | iPad Safari | Broker or server | ESP32 implementation load | Classroom clarity |
| --- | --- | --- | --- | --- | --- | --- |
| Arduino Serial Plotter | USB serial text, normally one newline-delimited record at a time | Not through the browser WebSocket API; a serial bridge or a separately supported browser serial API is needed | Not a baseline path | No broker; a host serial connection is required | Low | Very high for bring-up and simple plots |
| micro:bit Bluetooth Profile / BLE GATT | BLE GATT services and characteristics | Requires a Web Bluetooth implementation or a native bridge/application | Web Bluetooth is not a Safari baseline, so this is not the primary path | No broker | Moderate; BLE services and pairing are required | Good when BLE concepts are part of the lesson |
| Nordic UART Service | Vendor-specific BLE GATT service exposing TX/RX characteristics | Same Web Bluetooth or native-bridge constraint as other BLE GATT services | Not a Safari baseline | No broker | Low to moderate, but application framing still has to be designed | Simple byte-pipe mental model, with semantics left to the application |
| Firmata | Binary command protocol, traditionally over serial; transports and extensions vary by implementation | Normally requires a host-side client or bridge | No direct Safari baseline | Usually a host client/bridge | Moderate | Good for remote pin and board control; less direct for timestamped streams |
| MQTT 5 over WebSocket | MQTT packets over a WebSocket connection | Browser MQTT clients are possible | WebSocket is available, but an MQTT client implementation is still needed | A broker is normally required | Moderate, plus broker deployment and MQTT state | Useful for teaching pub/sub; more infrastructure than direct device-to-browser streaming |
| SenML / SenSML | Data model and serializations such as JSON or CBOR; transport is selected separately | JSON SenML is browser-friendly once delivered by HTTP or WebSocket | Compatible with ordinary browser JSON processing | No broker is inherent, but a transport endpoint is still required | Low to moderate for export; streaming serialization adds complexity | Strong standardized measurement vocabulary |
| Lab Streaming Layer (LSL) | Library-based time-series networking with discovery, time synchronization, and recording ecosystem | Requires an LSL implementation or gateway rather than only baseline browser APIs | No direct Safari baseline | No MQTT-style broker, but liblsl-capable participants or a gateway are required | High relative to the C1 target | Powerful for laboratories, but introduces more concepts and software |
| `d2b-stream/0.1` | HTTP/1.1 for resources and read-only JSON; WebSocket text control and binary samples | Directly uses baseline WebSocket, ArrayBuffer, and DataView APIs | Designed for the Safari WebSocket path | Device is the HTTP/WebSocket server; no external broker | Deliberately bounded: a small state machine and compact fixed header | Explicit sample-frame, gap, and ownership rules remain inspectable |

## Data-semantics comparison

| Approach | Timestamp and sequence | Gap and overflow | V/I measurements | PCM audio |
| --- | --- | --- | --- | --- |
| Arduino Serial Plotter | No standard monotonic timestamp or sequence in its plotting text | No standard loss indication | Labels and numeric values are convenient | Not an audio streaming format |
| micro:bit profile | Service-specific; not one common sample-frame contract | Service/application-specific | Sensor-oriented services are a useful reference | Not a general PCM contract |
| Nordic UART Service | None beyond application bytes | Application-specific | Possible with a new application format | Possible only with a new application format and BLE throughput constraints |
| Firmata | Protocol and extension-specific rather than the C1 monotonic sample-frame model | No common C1-style producer/transport cause flags | Analog reporting exists, but named SI measurement records require conventions | Not the target data model |
| MQTT 5 over WebSocket | MQTT ordering and identifiers do not define device sample timestamps or sample-frame sequences | Delivery QoS does not by itself describe producer overflow or acquisition gaps | Topic/payload design can carry V/I | Payload design can carry PCM, with broker and client buffering considerations |
| SenML / SenSML | Standard time fields and measurement names/units; no C1 stream-session sequence contract | Missing records can remain missing, but C1 cause flags are not supplied by the base model | Excellent fit for interoperable export | Not a compact interleaved PCM framing standard |
| LSL | Rich timestamps, clock synchronization, and stream metadata | Loss handling is ecosystem/application dependent | Strong fit for time-series measurements | Strong fit for sampled streams |
| `d2b-stream/0.1` | Device-local monotonic microseconds plus a sample-frame sequence and stream ID | Explicit discontinuity and producer-overflow, output-queue-drop, pause, or timebase cause semantics | Timestamped two-channel `vi-f32le` profile | Fixed-rate signed 16-bit little-endian interleaved profile |

## Selection

The C1 design uses HTTP/1.1 and WebSocket as existing standards. The custom
surface is intentionally limited to session negotiation, stream IDs,
sample-frame sequences, device-local monotonic timestamps, gap and overflow
semantics, compact binary framing, and the browser-facing state machine.

The voltage and current names, SI units, and standardized export guidance align
with SenML. SenML is used as an export and interoperability layer; it does not
replace the compact live binary representation. The mapping is described in
[V/I Measurement SenML Mapping](profiles/vi-measurement-senml-mapping.md).

PCM uses signed 16-bit little-endian interleaved encoding because it is compact,
unambiguous, and straightforward to decode with `DataView`. Arduino Serial
Plotter compatible text remains an optional diagnostic adapter. It is not the
primary protocol because it cannot preserve the required timestamps, sequences,
gaps, or audio framing.

The micro:bit Bluetooth design is useful prior art for understandable,
device-oriented services. It is not selected as the primary iPad Safari route:
the Web Bluetooth Community Group implementation-status page does not list
Safari as a supported implementation. A future implementation can add BLE as a
separate adapter without changing the WebSocket application profile.

MQTT 5 over WebSocket is mature and browser-capable, but a broker and MQTT client
stack are additional deployment components. It is therefore not the initial
direct device-to-browser path. LSL provides richer laboratory time-series
discovery, time synchronization, and recording support, but its library and
ecosystem requirements are heavier than the intended ESP32-to-browser baseline.

## References

- [Arduino Serial Plotter protocol](https://github.com/arduino/Arduino/blob/master/build/shared/ArduinoSerialPlotterProtocol.md)
- [BBC micro:bit Bluetooth overview](https://tech.microbit.org/bluetooth/)
- [BBC micro:bit Bluetooth profile](https://lancaster-university.github.io/microbit-docs/resources/bluetooth/bluetooth_profile.html)
- [Nordic UART Service](https://docs.nordicsemi.com/r/bundle/nrf5_sdk_v11.0.0/page/group_ble_sdk_srv_nus.html)
- [Firmata](https://firmata.org/)
- [MQTT Version 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html)
- [SenML, RFC 8428](https://www.rfc-editor.org/rfc/rfc8428.html)
- [Lab Streaming Layer: Getting Started](https://labstreaminglayer.readthedocs.io/info/getting_started.html)
- [Web Bluetooth implementation status](https://github.com/WebBluetoothCG/web-bluetooth/blob/main/implementation-status.md)
