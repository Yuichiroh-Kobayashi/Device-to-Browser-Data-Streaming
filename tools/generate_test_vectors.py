#!/usr/bin/env python3
"""Generate the JSON-encoded d2b-stream 0.1 golden vectors."""

from __future__ import annotations

import json
import math
import struct
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test-vectors"
ENVELOPE = struct.Struct("<4sBBBBIIQQ")
VI_RECORD = struct.Struct("<IIff")

FRAME_FIXED_RATE = 0x01
FRAME_TIMESTAMPED = 0x02
FRAME_STREAM_END = 0x10

STREAM_START = 0x01
STREAM_END = 0x02
DISCONTINUITY = 0x04
PRODUCER_OVERFLOW = 0x08
OUTPUT_QUEUE_DROP = 0x10
SOURCE_PAUSED = 0x20
TIMEBASE_RESET = 0x40
RESERVED = 0x80

VI_PARAMETERS = {
    "sample_format": "vi-f32le",
    "channel_count": 2,
    "channel_mask": 3,
    "sample_rate": {"numerator": 0, "denominator": 0},
}
PCM_PARAMETERS = {
    "sample_format": "pcm-s16le-interleaved",
    "channel_count": 1,
    "channel_mask": 1,
    "sample_rate": {"numerator": 16000, "denominator": 1},
    "samples_per_frame": 256,
}
CAPABILITIES_PCM_ONLY = {
    "protocol": "d2b-stream",
    "version": "0.1",
    "maximum_binary_frame_size": 65536,
    "maximum_control_message_size": 2048,
    "maximum_active_stream_sessions": 1,
    "maximum_control_connections": 1,
    "persistent_capture_supported": False,
    "security_mode": "pairing-token",
    "streams": [
        {
            "id": "audio-0",
            "label": "Audio input",
            "profiles": [
                {"profile": "pcm-audio", "parameter_sets": [PCM_PARAMETERS]}
            ],
        }
    ],
}
CAPABILITIES_VI_ONLY = {
    "protocol": "d2b-stream",
    "version": "0.1",
    "maximum_binary_frame_size": 65536,
    "maximum_control_message_size": 2048,
    "maximum_active_stream_sessions": 1,
    "maximum_control_connections": 1,
    "persistent_capture_supported": False,
    "security_mode": "pairing-token",
    "streams": [
        {
            "id": "measurement-0",
            "label": "Voltage and current",
            "profiles": [
                {"profile": "vi-measurement", "parameter_sets": [VI_PARAMETERS]}
            ],
        }
    ],
}


def envelope(
    frame_type: int,
    flags: int,
    stream_id: int,
    sample_count: int,
    sequence: int,
    timestamp_us: int,
    payload: bytes = b"",
    *,
    magic: bytes = b"D2BS",
    major: int = 0,
    minor: int = 1,
) -> bytes:
    return ENVELOPE.pack(
        magic,
        major,
        minor,
        frame_type,
        flags,
        stream_id,
        sample_count,
        sequence,
        timestamp_us,
    ) + payload


def vi_payload(*records: tuple[int, int, float, float]) -> bytes:
    return b"".join(VI_RECORD.pack(*record) for record in records)


def pcm_payload(count: int = 256) -> bytes:
    values = [((index * 257) % 65536) - 32768 for index in range(count)]
    return struct.pack(f"<{count}h", *values)


def context(
    profile: str,
    stream_id: int,
    *,
    previous: tuple[int, int, int] | None = None,
    previous_last_timestamp_us: int | None = None,
    anchor: tuple[int, int] | None = None,
    session_state: str = "STREAMING",
    maximum_binary_frame_size: int = 65536,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "negotiated_version": "0.1",
        "session_state": session_state,
        "maximum_binary_frame_size": maximum_binary_frame_size,
        "stream_id": stream_id,
        "profile": profile,
        "parameters": VI_PARAMETERS if profile == "vi-measurement" else PCM_PARAMETERS,
    }
    if previous is not None:
        result.update(
            {
                "previous_first_sample_sequence": previous[0],
                "previous_sample_count": previous[1],
                "previous_first_timestamp_us": previous[2],
            }
        )
        if profile == "vi-measurement":
            assert previous_last_timestamp_us is not None
            result["previous_last_timestamp_us"] = previous_last_timestamp_us
    if profile == "pcm-audio":
        assert anchor is not None
        result.update(
            {
                "session_anchor_sequence": anchor[0],
                "session_anchor_timestamp_us": anchor[1],
            }
        )
    return result


def binary_vector(
    name: str,
    purpose: str,
    frame: bytes,
    *,
    context_value: dict[str, Any] | None = None,
    decoded: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "name": name,
        "purpose": purpose,
        "frame_hex": frame.hex(),
        "expected_valid": error is None,
    }
    if context_value is not None:
        item["context"] = context_value
    if error is None:
        item["expected_decoded"] = decoded or {}
    else:
        item["expected_error"] = error
    return item


def control_vector(
    name: str,
    purpose: str,
    direction: str,
    message: Any,
    *,
    context_value: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "name": name,
        "purpose": purpose,
        "direction": direction,
        "message": message,
        "expected_valid": error is None,
    }
    if context_value is not None:
        item["context"] = context_value
    if error is None:
        item["expected_decoded"] = message
    else:
        item["expected_error"] = error
    return item


def control_vectors() -> list[dict[str, Any]]:
    start_pcm = {
        "type": "start_stream",
        "stream": "audio-0",
        "profile": "pcm-audio",
        "parameters": PCM_PARAMETERS,
    }
    start_vi = {
        "type": "start_stream",
        "stream": "measurement-0",
        "profile": "vi-measurement",
        "parameters": VI_PARAMETERS,
    }
    vectors = [
        control_vector("client_hello", "Accept version negotiation.", "client_to_server", {"type": "hello", "protocol": "d2b-stream", "versions": ["0.1"]}, context_value={"state": "CONNECTED", "owns_stream": False}),
        control_vector("client_hello_pairing", "Accept pairing-token authentication.", "client_to_server", {"type": "hello", "protocol": "d2b-stream", "versions": ["0.1"], "authentication": {"scheme": "pairing-token", "token": "classroom-token"}}),
        control_vector("server_welcome", "Accept the negotiated limits.", "server_to_client", {"type": "welcome", "protocol": "d2b-stream", "version": "0.1", "max_control_message_size": 2048, "max_binary_frame_size": 65536, "session_state": "ready"}),
        control_vector("client_start_vi", "Accept the standard V/I profile.", "client_to_server", start_vi, context_value={"state": "READY", "owns_stream": False}),
        control_vector("client_start_pcm", "Accept the v0.1 PCM reference set.", "client_to_server", start_pcm, context_value={"state": "READY", "owns_stream": False}),
        control_vector("server_started_pcm", "Confirm the exact PCM parameter set.", "server_to_client", {"type": "stream_started", "stream": "audio-0", "profile": "pcm-audio", "parameters": PCM_PARAMETERS, "stream_id": 7}),
        control_vector("client_stop", "Accept a targeted stop.", "client_to_server", {"type": "stop_stream", "stream_id": 7, "reason": "capture complete"}, context_value={"state": "STREAMING", "owns_stream": True}),
        control_vector("server_stopped", "Accept stream completion.", "server_to_client", {"type": "stream_stopped", "stream_id": 7, "reason": "capture complete"}),
        control_vector("client_ping", "Accept a ping.", "client_to_server", {"type": "ping", "correlation": "p-1"}),
        control_vector("server_pong", "Accept the matching pong shape.", "server_to_client", {"type": "pong", "correlation": "p-1"}),
        control_vector("server_status", "Accept detailed authenticated control status.", "server_to_client", {"type": "status", "state": "streaming", "active_stream_id": 7, "connected_client_count": 1, "producer_drop_count": 2, "output_queue_drop_count": 3, "queued_sample_count": 8, "source_paused": False, "uptime_us": 123456}),
        control_vector("server_unsupported_profile", "Represent explicit unknown-profile rejection.", "server_to_client", {"type": "error", "code": "unsupported_profile", "message": "profile is not supported", "recoverable": True}),
        control_vector("unsupported_profile", "Reject an unknown profile without fallback.", "client_to_server", {"type": "start_stream", "stream": "x", "profile": "com.example.private", "parameters": {}}, error="unsupported_profile"),
        control_vector("invalid_channel_mask", "Reject impossible PCM channel count/mask combinations.", "client_to_server", {"type": "start_stream", "stream": "audio-0", "profile": "pcm-audio", "parameters": {**PCM_PARAMETERS, "channel_count": 2}}, error="unsupported_parameters"),
        control_vector("unsupported_pcm_rate", "Reject a non-reference PCM rate.", "client_to_server", {"type": "start_stream", "stream": "audio-0", "profile": "pcm-audio", "parameters": {**PCM_PARAMETERS, "sample_rate": {"numerator": 48000, "denominator": 1}}}, error="unsupported_parameters"),
        control_vector("unsupported_pcm_frame_size", "Reject a non-reference PCM samples-per-frame value.", "client_to_server", {"type": "start_stream", "stream": "audio-0", "profile": "pcm-audio", "parameters": {**PCM_PARAMETERS, "samples_per_frame": 128}}, error="unsupported_parameters"),
        control_vector("duplicate_json_key", "Reject duplicate object keys.", "client_to_server", '{"type":"ping","correlation":"a","correlation":"b"}', error="invalid_message"),
        control_vector("json_nan", "Reject NaN.", "client_to_server", '{"type":"ping","correlation":NaN}', error="invalid_message"),
        control_vector("json_infinity", "Reject Infinity.", "client_to_server", '{"type":"ping","correlation":Infinity}', error="invalid_message"),
        control_vector("json_negative_infinity", "Reject negative Infinity.", "client_to_server", '{"type":"ping","correlation":-Infinity}', error="invalid_message"),
        control_vector("json_trailing_data", "Reject trailing JSON data.", "client_to_server", '{"type":"ping","correlation":"a"} false', error="invalid_message"),
        control_vector(
            "integer_as_float",
            "Reject a floating-point token in an integer field.",
            "server_to_client",
            (
                '{"type":"welcome",'
                '"protocol":"d2b-stream",'
                '"version":"0.1",'
                '"max_control_message_size":2048,'
                '"max_binary_frame_size":32.0,'
                '"session_state":"ready"}'
            ),
            error="invalid_message",
        ),
        control_vector("integer_out_of_range", "Reject an out-of-range stream ID.", "server_to_client", {"type": "stream_started", "stream": "measurement-0", "profile": "vi-measurement", "parameters": VI_PARAMETERS, "stream_id": 4294967296}, error="invalid_message"),
        control_vector("type_mismatch", "Reject a string where an array is required.", "client_to_server", {"type": "hello", "protocol": "d2b-stream", "versions": "0.1"}, error="invalid_message"),
        control_vector("unknown_message_enum", "Reject an unknown control type.", "client_to_server", {"type": "begin"}, error="invalid_message"),
        control_vector("raw_control_too_large", "Enforce the raw 2048-byte limit.", "client_to_server", " " * 2049, error="frame_too_large"),
        {"name": "invalid_utf8", "purpose": "Reject invalid UTF-8 before JSON parsing.", "direction": "client_to_server", "message_hex": "ff", "expected_valid": False, "expected_error": "invalid_message"},
        control_vector("start_before_hello", "Reject start_stream while CONNECTED.", "client_to_server", start_pcm, context_value={"state": "CONNECTED", "owns_stream": False}, error="invalid_state"),
        control_vector("second_hello", "Reject a second hello while READY.", "client_to_server", {"type": "hello", "protocol": "d2b-stream", "versions": ["0.1"]}, context_value={"state": "READY", "owns_stream": False}, error="invalid_state"),
        control_vector("stop_while_ready", "Reject stop_stream while READY.", "client_to_server", {"type": "stop_stream", "stream_id": 7}, context_value={"state": "READY", "owns_stream": False}, error="invalid_state"),
        control_vector("start_while_streaming", "Reject start_stream while STREAMING.", "client_to_server", start_pcm, context_value={"state": "STREAMING", "owns_stream": True}, error="invalid_state"),
        control_vector("non_owner_stop", "Reject stop_stream from a non-owner.", "client_to_server", {"type": "stop_stream", "stream_id": 7}, context_value={"state": "STREAMING", "owns_stream": False}, error="invalid_state"),
        control_vector("message_while_closed", "Reject control input after CLOSED.", "client_to_server", {"type": "ping", "correlation": "closed"}, context_value={"state": "CLOSED", "owns_stream": False}, error="invalid_state"),
        control_vector("second_client_busy", "Preserve the existing stream owner.", "server_to_client", {"type": "error", "code": "busy", "message": "stream already owned", "recoverable": True}, context_value={"scenario": "second_client_busy", "connection_a": {"state": "streaming", "owns_stream": True}, "connection_b": {"state": "ready", "owns_stream": False}, "request": start_pcm, "postcondition": {"connection_a_state": "streaming", "connection_a_owns_stream": True}}),
    ]
    return vectors


def vi_vectors() -> list[dict[str, Any]]:
    first_ctx = context("vi-measurement", 11)
    previous_ctx = context("vi-measurement", 11, previous=(100, 2, 1_000_000), previous_last_timestamp_us=1_001_000)
    one = vi_payload((0, 3, 3.25, -0.125))
    two = vi_payload((0, 3, 3.25, 0.1), (1000, 3, 3.2, 0.2))
    valid_first = envelope(FRAME_TIMESTAMPED, STREAM_START, 11, 1, 100, 1_000_000, one)
    valid_next = envelope(FRAME_TIMESTAMPED, 0, 11, 2, 102, 1_002_000, two)
    return [
        binary_vector("vi_first_frame", "Decode the first V/I frame with the 32-byte envelope.", valid_first, context_value=first_ctx, decoded={"magic": "D2BS", "sample_count": 1, "payload_length": 16, "stream_start": True, "first_valid_mask": 3, "first_voltage": 3.25, "first_current": -0.125, "gap_samples": 0}),
        binary_vector("vi_continuous_frame", "Decode a continuous multi-record V/I frame.", valid_next, context_value=previous_ctx, decoded={"sample_count": 2, "first_sample_sequence": 102, "last_delta_us": 1000, "gap_samples": 0}),
        binary_vector("vi_producer_overflow", "Accept a producer-overflow discontinuity without renumbering.", envelope(FRAME_TIMESTAMPED, DISCONTINUITY | PRODUCER_OVERFLOW, 11, 1, 105, 1_005_000, one), context_value=previous_ctx, decoded={"gap_samples": 3, "discontinuity": True, "producer_overflow": True}),
        binary_vector("vi_output_queue_gap", "Preserve a post-acquisition queue gap.", envelope(FRAME_TIMESTAMPED, DISCONTINUITY | OUTPUT_QUEUE_DROP, 11, 1, 105, 1_005_000, one), context_value=previous_ctx, decoded={"gap_samples": 3, "discontinuity": True, "output_queue_drop": True}),
        binary_vector("vi_timebase_reset", "Accept a signaled timebase reset only on a new session.", envelope(FRAME_TIMESTAMPED, STREAM_START | DISCONTINUITY | TIMEBASE_RESET, 11, 1, 0, 500, one), context_value=first_ctx, decoded={"stream_start": True, "discontinuity": True, "timebase_reset": True}),
        binary_vector("vi_wrong_magic", "Reject wrong magic.", envelope(FRAME_TIMESTAMPED, STREAM_START, 11, 1, 100, 1_000_000, one, magic=b"X2BS"), error="bad_magic"),
        binary_vector("vi_unsupported_major", "Reject an unsupported binary major version.", envelope(FRAME_TIMESTAMPED, STREAM_START, 11, 1, 100, 1_000_000, one, major=1), error="version_mismatch"),
        binary_vector("vi_reserved_flag", "Reject the reserved flag bit.", envelope(FRAME_TIMESTAMPED, STREAM_START | RESERVED, 11, 1, 100, 1_000_000, one), error="reserved_flag_set"),
        binary_vector("vi_missing_stream_start", "Require STREAM_START on a first data frame.", envelope(FRAME_TIMESTAMPED, 0, 11, 1, 100, 1_000_000, one), context_value=first_ctx, error="missing_stream_start"),
        binary_vector("vi_repeated_stream_start", "Reject STREAM_START on a later frame.", envelope(FRAME_TIMESTAMPED, STREAM_START, 11, 1, 102, 1_002_000, one), context_value=previous_ctx, error="unexpected_stream_start"),
        binary_vector("vi_sample_count_zero", "Reject zero sample count on data frames.", envelope(FRAME_TIMESTAMPED, STREAM_START, 11, 0, 100, 1_000_000), error="sample_count_zero"),
        binary_vector("vi_payload_too_short", "Reject a short V/I payload.", valid_first[:-1], error="vi_payload_length_mismatch"),
        binary_vector("vi_payload_too_long", "Reject an extended V/I payload.", valid_first + b"\x00", error="vi_payload_length_mismatch"),
        binary_vector("vi_partial_record", "Reject a partial V/I record.", envelope(FRAME_TIMESTAMPED, STREAM_START, 11, 1, 100, 1_000_000, one[:8]), error="vi_payload_length_mismatch"),
        binary_vector("vi_sequence_overflow", "Reject first sequence plus count overflow.", envelope(FRAME_TIMESTAMPED, STREAM_START, 11, 2, 2**64 - 1, 1_000_000, two), error="sequence_overflow"),
        binary_vector("vi_timestamp_overflow", "Reject timestamp plus delta overflow.", envelope(FRAME_TIMESTAMPED, STREAM_START, 11, 2, 100, 2**64 - 1, vi_payload((0, 3, 1.0, 1.0), (1, 3, 1.0, 1.0))), error="timestamp_overflow"),
        binary_vector("vi_stream_id_mismatch", "Reject a frame from another stream.", envelope(FRAME_TIMESTAMPED, STREAM_START, 12, 1, 100, 1_000_000, one), context_value=first_ctx, error="stream_id_mismatch"),
        binary_vector("vi_sequence_regression", "Reject sequence regression.", envelope(FRAME_TIMESTAMPED, 0, 11, 1, 101, 1_002_000, one), context_value=previous_ctx, error="sequence_regression"),
        binary_vector("vi_unexplained_sequence_gap", "Reject a sequence gap without DISCONTINUITY.", envelope(FRAME_TIMESTAMPED, 0, 11, 1, 105, 1_005_000, one), context_value=previous_ctx, error="missing_discontinuity_flag"),
        binary_vector("vi_malformed_valid_mask", "Reject unknown validity bits.", envelope(FRAME_TIMESTAMPED, STREAM_START, 11, 1, 100, 1_000_000, vi_payload((0, 4, 1.0, 1.0))), error="vi_invalid_valid_mask"),
        binary_vector("vi_invalid_delta_order", "Reject decreasing delta_us values.", envelope(FRAME_TIMESTAMPED, STREAM_START, 11, 3, 100, 1_000_000, vi_payload((0, 3, 1.0, 1.0), (2, 3, 1.0, 1.0), (1, 3, 1.0, 1.0))), error="vi_delta_regression"),
        binary_vector("vi_first_delta_nonzero", "Require zero delta on the first record.", envelope(FRAME_TIMESTAMPED, STREAM_START, 11, 1, 100, 1_000_000, vi_payload((1, 3, 1.0, 1.0))), error="vi_first_delta_nonzero"),
        binary_vector("vi_nonfinite_valid_value", "Reject a non-finite value marked valid.", envelope(FRAME_TIMESTAMPED, STREAM_START, 11, 1, 100, 1_000_000, vi_payload((0, 3, math.inf, 1.0))), error="vi_nonfinite_valid_value"),
        binary_vector("vi_cause_without_discontinuity", "Require DISCONTINUITY with producer overflow.", envelope(FRAME_TIMESTAMPED, STREAM_START | PRODUCER_OVERFLOW, 11, 1, 100, 1_000_000, one), error="missing_discontinuity_flag"),
        binary_vector("vi_stream_end", "Accept a payload-free stream end marker.", envelope(FRAME_STREAM_END, STREAM_END, 11, 0, 102, 1_003_000), context_value=previous_ctx, decoded={"stream_end": True, "sample_count": 0, "payload_length": 0}),
    ]


def pcm_vectors() -> list[dict[str, Any]]:
    first_ctx = context("pcm-audio", 21, anchor=(0, 2_000_000))
    previous_ctx = context("pcm-audio", 21, previous=(0, 256, 2_000_000), anchor=(0, 2_000_000))
    payload = pcm_payload()
    first = envelope(FRAME_FIXED_RATE, STREAM_START, 21, 256, 0, 2_000_000, payload)
    next_frame = envelope(FRAME_FIXED_RATE, 0, 21, 256, 256, 2_016_000, payload)
    return [
        binary_vector("pcm_first_frame", "Decode the v0.1 PCM reference frame.", first, context_value=first_ctx, decoded={"sample_count": 256, "payload_length": 512, "stream_start": True, "first_pcm_value": -32768, "gap_samples": 0}),
        binary_vector("pcm_continuous_frame", "Decode the next anchored PCM frame.", next_frame, context_value=previous_ctx, decoded={"first_sample_sequence": 256, "pcm_timestamp_within_1us": True, "gap_samples": 0}),
        binary_vector("pcm_producer_overflow_gap", "Require producer overflow to retain missing logical positions.", envelope(FRAME_FIXED_RATE, DISCONTINUITY | PRODUCER_OVERFLOW, 21, 256, 512, 2_032_000, payload), context_value=previous_ctx, decoded={"producer_overflow": True, "gap_samples": 256}),
        binary_vector("pcm_source_paused", "Retain paused logical sample positions as a sequence gap.", envelope(FRAME_FIXED_RATE, DISCONTINUITY | SOURCE_PAUSED, 21, 256, 512, 2_032_000, payload), context_value=previous_ctx, decoded={"source_paused": True, "discontinuity": True, "gap_samples": 256, "pcm_expected_timestamp_floor_us": 2032000}),
        binary_vector("pcm_output_queue_gap", "Preserve a PCM gap and cause.", envelope(FRAME_FIXED_RATE, DISCONTINUITY | OUTPUT_QUEUE_DROP, 21, 256, 512, 2_032_000, payload), context_value=previous_ctx, decoded={"gap_samples": 256, "output_queue_drop": True}),
        binary_vector("pcm_producer_cause_without_gap", "Reject producer overflow without missing logical positions.", envelope(FRAME_FIXED_RATE, DISCONTINUITY | PRODUCER_OVERFLOW, 21, 256, 256, 2_016_000, payload), context_value=previous_ctx, error="cause_flag_without_gap"),
        binary_vector("pcm_output_cause_without_gap", "Reject output queue drop without missing logical positions.", envelope(FRAME_FIXED_RATE, DISCONTINUITY | OUTPUT_QUEUE_DROP, 21, 256, 256, 2_016_000, payload), context_value=previous_ctx, error="cause_flag_without_gap"),
        binary_vector("pcm_pause_cause_without_gap", "Reject SOURCE_PAUSED without missing logical positions.", envelope(FRAME_FIXED_RATE, DISCONTINUITY | SOURCE_PAUSED, 21, 256, 256, 2_016_000, payload), context_value=previous_ctx, error="cause_flag_without_gap"),
        binary_vector("binary_before_stream_started", "Reject binary data while the control session is READY.", first, context_value=context("pcm-audio", 21, anchor=(0, 2_000_000), session_state="READY"), error="invalid_state"),
        binary_vector("binary_maximum_size_exceeded", "Reject a binary message beyond the negotiated maximum.", first, context_value=context("pcm-audio", 21, anchor=(0, 2_000_000), maximum_binary_frame_size=32), error="frame_too_large"),
        binary_vector("pcm_payload_too_short", "Reject one-byte truncation.", first[:-1], context_value=first_ctx, error="pcm_payload_length_mismatch"),
        binary_vector("pcm_payload_too_long", "Reject one-byte extension.", first + b"\x00", context_value=first_ctx, error="pcm_payload_length_mismatch"),
        binary_vector("pcm_sample_count_zero", "Reject zero samples in a data frame.", envelope(FRAME_FIXED_RATE, STREAM_START, 21, 0, 0, 2_000_000), error="sample_count_zero"),
        binary_vector("pcm_unsupported_frame_count", "Reject a non-reference PCM frame count.", envelope(FRAME_FIXED_RATE, STREAM_START, 21, 255, 0, 2_000_000, pcm_payload(255)), context_value=first_ctx, error="pcm_sample_count_mismatch"),
        binary_vector("pcm_sequence_overflow", "Reject sample sequence arithmetic overflow.", envelope(FRAME_FIXED_RATE, STREAM_START, 21, 256, 2**64 - 255, 2_000_000, payload), error="sequence_overflow"),
        binary_vector("pcm_reserved_flag", "Reject the reserved bit.", envelope(FRAME_FIXED_RATE, STREAM_START | RESERVED, 21, 256, 0, 2_000_000, payload), error="reserved_flag_set"),
        binary_vector("pcm_missing_stream_start", "Require STREAM_START on the first PCM frame.", envelope(FRAME_FIXED_RATE, 0, 21, 256, 0, 2_000_000, payload), context_value=first_ctx, error="missing_stream_start"),
        binary_vector("pcm_repeated_stream_start", "Reject repeated STREAM_START.", envelope(FRAME_FIXED_RATE, STREAM_START, 21, 256, 256, 2_016_000, payload), context_value=previous_ctx, error="unexpected_stream_start"),
        binary_vector("pcm_stream_id_mismatch", "Reject another stream ID.", envelope(FRAME_FIXED_RATE, STREAM_START, 22, 256, 0, 2_000_000, payload), context_value=first_ctx, error="stream_id_mismatch"),
        binary_vector("pcm_sequence_regression", "Reject sequence regression.", envelope(FRAME_FIXED_RATE, 0, 21, 256, 255, 2_015_938, payload), context_value=previous_ctx, error="sequence_regression"),
        binary_vector("pcm_unexplained_sequence_gap", "Reject a PCM gap without DISCONTINUITY.", envelope(FRAME_FIXED_RATE, 0, 21, 256, 512, 2_032_000, payload), context_value=previous_ctx, error="missing_discontinuity_flag"),
        binary_vector("pcm_timestamp_outside_tolerance", "Reject an anchor-derived timestamp error.", envelope(FRAME_FIXED_RATE, 0, 21, 256, 256, 2_016_002, payload), context_value=previous_ctx, error="pcm_timestamp_out_of_tolerance"),
        binary_vector("pcm_profile_mismatch", "Reject a timestamped V/I-shaped frame as PCM.", envelope(FRAME_TIMESTAMPED, STREAM_START, 21, 1, 0, 2_000_000, vi_payload((0, 3, 1.0, 1.0))), context_value=first_ctx, error="pcm_frame_type_mismatch"),
        binary_vector("pcm_stream_end", "Accept a PCM stream end marker.", envelope(FRAME_STREAM_END, STREAM_END, 21, 0, 256, 2_016_000), context_value=previous_ctx, decoded={"stream_end": True, "sample_count": 0, "payload_length": 0}),
    ]


def capabilities_vectors() -> list[dict[str, Any]]:
    positive = json.loads(json.dumps(CAPABILITIES_PCM_ONLY))
    missing_streams = {key: value for key, value in positive.items() if key != "streams"}
    zero_connections = json.loads(json.dumps(positive))
    zero_connections["maximum_control_connections"] = 0
    empty_parameter_sets = json.loads(json.dumps(positive))
    empty_parameter_sets["streams"][0]["profiles"][0]["parameter_sets"] = []
    unsupported_pcm = json.loads(json.dumps(positive))
    unsupported_pcm["streams"][0]["profiles"][0]["parameter_sets"][0]["sample_rate"] = {
        "numerator": 48000,
        "denominator": 1,
    }
    pcm_max_543 = json.loads(json.dumps(positive))
    pcm_max_543["maximum_binary_frame_size"] = 543
    pcm_max_544 = json.loads(json.dumps(positive))
    pcm_max_544["maximum_binary_frame_size"] = 544
    vi_max_47 = json.loads(json.dumps(CAPABILITIES_VI_ONLY))
    vi_max_47["maximum_binary_frame_size"] = 47
    vi_max_48 = json.loads(json.dumps(CAPABILITIES_VI_ONLY))
    vi_max_48["maximum_binary_frame_size"] = 48
    duplicate_pcm = json.loads(json.dumps(positive))
    duplicate_pcm["streams"][0]["profiles"][0]["parameter_sets"].append(
        json.loads(json.dumps(PCM_PARAMETERS))
    )
    private_descriptor = {
        "profile": "com.example.private",
        "parameter_sets": [{}],
    }
    private_only = json.loads(json.dumps(positive))
    private_only["streams"][0]["profiles"] = [private_descriptor]
    standard_plus_private = json.loads(json.dumps(CAPABILITIES_VI_ONLY))
    standard_plus_private["streams"][0]["profiles"].append(
        json.loads(json.dumps(private_descriptor))
    )
    return [
        {"name": "capabilities_pcm_only", "purpose": "Accept capabilities listing only the implemented standard profile.", "document": positive, "expected_valid": True, "expected_decoded": positive},
        {"name": "capabilities_missing_streams", "purpose": "Reject a missing required field.", "document": missing_streams, "expected_valid": False, "expected_error": "invalid_capabilities"},
        {"name": "capabilities_zero_connections", "purpose": "Reject zero control-connection capacity.", "document": zero_connections, "expected_valid": False, "expected_error": "invalid_capabilities"},
        {"name": "capabilities_empty_parameter_sets", "purpose": "Reject an empty parameter_sets array.", "document": empty_parameter_sets, "expected_valid": False, "expected_error": "invalid_capabilities"},
        {"name": "capabilities_unsupported_pcm", "purpose": "Reject an advertised unsupported standard parameter set.", "document": unsupported_pcm, "expected_valid": False, "expected_error": "invalid_capabilities"},
        {"name": "capabilities_pcm_max_size_543", "purpose": "Reject PCM capabilities whose maximum cannot carry one advertised frame.", "document": pcm_max_543, "expected_valid": False, "expected_error": "invalid_capabilities"},
        {"name": "capabilities_pcm_max_size_544", "purpose": "Accept the exact minimum size for one v0.1 PCM frame.", "document": pcm_max_544, "expected_valid": True, "expected_decoded": pcm_max_544},
        {"name": "capabilities_vi_max_size_47", "purpose": "Reject V/I capabilities whose maximum cannot carry one record.", "document": vi_max_47, "expected_valid": False, "expected_error": "invalid_capabilities"},
        {"name": "capabilities_vi_max_size_48", "purpose": "Accept the exact minimum size for one V/I record.", "document": vi_max_48, "expected_valid": True, "expected_decoded": vi_max_48},
        {"name": "capabilities_duplicate_pcm_parameter_set", "purpose": "Reject a duplicate complete parameter set within one profile.", "document": duplicate_pcm, "expected_valid": False, "expected_error": "invalid_capabilities"},
        {"name": "capabilities_private_only", "purpose": "Reject capabilities that advertise no standard profile.", "document": private_only, "expected_valid": False, "expected_error": "invalid_capabilities"},
        {"name": "capabilities_standard_plus_private", "purpose": "Accept a standard profile advertised alongside a private profile.", "document": standard_plus_private, "expected_valid": True, "expected_decoded": standard_plus_private},
    ]


def document(vectors: list[dict[str, Any]], *, profile: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "format": "d2b-stream-test-vectors/0.1",
        "protocol": "d2b-stream",
        "version": "0.1",
        "vectors": vectors,
    }
    if profile is None:
        result["schema_draft"] = "2020-12"
    else:
        result["profile"] = profile
    return result


def write(name: str, value: dict[str, Any]) -> None:
    (OUT / name).write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    write("control-messages.json", document(control_vectors()))
    write("capabilities.json", document(capabilities_vectors()))
    write("vi-frames.json", document(vi_vectors(), profile="vi-measurement"))
    write("pcm-audio-frames.json", document(pcm_vectors(), profile="pcm-audio"))
    print("Generated control, capabilities, V/I, and PCM golden vectors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
