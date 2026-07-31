# Deployment Guide

This guide is non-normative. Wi-Fi topology, radio planning, firewall policy,
and device discovery are deployment concerns and do not change the `d2b-stream`
wire protocol.

## Mode A: Direct SoftAP

- one device;
- one browser; and
- isolated local use.

Use WPA2 or stronger protection and a non-default credential. This mode is
simple for individual use but does not scale merely by putting many SoftAPs in
one room.

## Mode B: Classroom local WLAN

- a dedicated local access point;
- multiple devices;
- no Internet requirement; and
- client isolation disabled so browsers can reach devices.

Plan addressing, discovery, access-point capacity, airtime, and stream load.
Pairing tokens are Recommended on a shared LAN. The protocol permits only one
active stream owner per device, regardless of the WLAN's client count.

## Mode C: School LAN

This mode is subject to firewall, VLAN, web-filter, multicast, WebSocket, and
client-isolation policy. Validate static HTTP, capabilities/status, WebSocket
Upgrade, sustained binary traffic, and browser download independently. Approval
for one path does not demonstrate that the others work.

## Dense classroom risk

Operating roughly 40 device SoftAPs in one room can create severe co-channel
and adjacent-channel interference, beacon overhead, association confusion, and
device-management burden. Automatic channel selection alone does not solve
limited spectrum or airtime contention. Prefer a planned classroom WLAN when
many devices must operate concurrently, and measure the actual venue before
claiming capacity.

SoftAP channel-selection algorithms are deliberately outside C1 and MUST NOT be
treated as part of `d2b-stream` conformance.
