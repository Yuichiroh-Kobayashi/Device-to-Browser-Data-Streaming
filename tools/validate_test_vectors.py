#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Yuichiroh-Kobayashi
# SPDX-License-Identifier: Apache-2.0
"""Validate d2b-stream 0.1 schemas and golden fixtures.

Only the Python standard library is used. This tool checks schema JSON syntax,
Draft 2020-12 declarations, local reference existence, Schema-equivalent rules
needed by the control fixtures, binary frames, and session continuity. It does
not perform complete JSON Schema meta-schema validation.
"""

from __future__ import annotations

import json
import math
import re
import struct
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILES = (
    ROOT / "schemas/client-message.schema.json",
    ROOT / "schemas/server-message.schema.json",
    ROOT / "schemas/capabilities.schema.json",
    ROOT / "schemas/public-status.schema.json",
)
VECTOR_FILES = (
    ROOT / "test-vectors/control-messages.json",
    ROOT / "test-vectors/capabilities.json",
    ROOT / "test-vectors/public-status.json",
    ROOT / "test-vectors/vi-frames.json",
    ROOT / "test-vectors/pcm-audio-frames.json",
)

FORMAT_ID = "d2b-stream-test-vectors/0.1"
PUBLIC_STATUS_SCHEMA_ID = "urn:d2b-stream:0.1:public-status:r1"
SAFE_UINT_MAX = 9007199254740991
CONTROL_LIMIT = 2048
ENVELOPE_SIZE = 32
ENVELOPE = struct.Struct("<4sBBBBIIQQ")
HEX_RE = re.compile(r"(?:[0-9a-f]{2})+")
IDENTIFIER_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}")
VERSION_RE = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")

FRAME_FIXED_RATE = 0x01
FRAME_TIMESTAMPED = 0x02
FRAME_STREAM_END = 0x10
FLAG_STREAM_START = 0x01
FLAG_STREAM_END = 0x02
FLAG_DISCONTINUITY = 0x04
FLAG_PRODUCER_OVERFLOW = 0x08
FLAG_OUTPUT_QUEUE_DROP = 0x10
FLAG_SOURCE_PAUSED = 0x20
FLAG_TIMEBASE_RESET = 0x40
FLAG_RESERVED = 0x80

ERROR_CODES = {
    "busy",
    "unauthorized",
    "unknown_stream",
    "unsupported_version",
    "unsupported_profile",
    "unsupported_parameters",
    "invalid_message",
    "invalid_state",
    "frame_too_large",
    "internal_error",
}
STANDARD_PROFILES = {"vi-measurement", "pcm-audio"}


class ValidationError(Exception):
    """A deterministic protocol-validation failure."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code


class FixtureError(Exception):
    """A structural or expectation error in a repository fixture."""


def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key {key!r}")
        result[key] = value
    return result


def reject_nonfinite_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value}")


def strict_json_loads(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=reject_duplicate_pairs,
        parse_constant=reject_nonfinite_constant,
    )


def load_json(path: Path) -> Any:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise FixtureError(f"{path}: cannot read: {exc}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FixtureError(f"{path}: not UTF-8: {exc}") from exc
    try:
        return strict_json_loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise FixtureError(f"{path}: invalid JSON: {exc}") from exc


def require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FixtureError(f"{context}: expected object")
    return value


def require_keys(obj: dict[str, Any], keys: set[str], context: str) -> None:
    missing = keys - obj.keys()
    if missing:
        raise FixtureError(f"{context}: missing keys {sorted(missing)}")


def resolve_local_ref(schema: Any, ref: str, path: Path) -> Any:
    if ref == "#":
        return schema
    if not ref.startswith("#/"):
        raise FixtureError(f"{path}: non-local $ref {ref!r}")
    current = schema
    for encoded in ref[2:].split("/"):
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            raise FixtureError(f"{path}: unresolved local $ref {ref!r}")
    return current


def validate_schema_files() -> None:
    for path in SCHEMA_FILES:
        schema = require_object(load_json(path), str(path))
        require_keys(schema, {"$schema", "$id", "$defs"}, str(path))
        if path.name in {"capabilities.schema.json", "public-status.schema.json"}:
            require_keys(schema, {"type", "properties"}, str(path))
        else:
            require_keys(schema, {"oneOf"}, str(path))
        if schema["$schema"] != "https://json-schema.org/draft/2020-12/schema":
            raise FixtureError(f"{path}: schema draft is not 2020-12")
        if path.name == "public-status.schema.json":
            expected_properties = {
                "protocol",
                "version",
                "state",
                "uptime_us",
                "producer_drop_count",
                "output_queue_drop_count",
                "queued_sample_count",
                "connected_client_count",
            }
            if (
                schema["$id"] != PUBLIC_STATUS_SCHEMA_ID
                or schema.get("type") != "object"
                or schema.get("additionalProperties") is not False
                or schema.get("required")
                != ["protocol", "version", "state", "uptime_us"]
                or set(schema.get("properties", {})) != expected_properties
                or schema.get("$defs", {}).get("safeUnsignedInteger")
                != {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": SAFE_UINT_MAX,
                }
            ):
                raise FixtureError(f"{path}: invalid Public Status Standard R1 boundary")

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                if "$ref" in value:
                    ref = value["$ref"]
                    if not isinstance(ref, str):
                        raise FixtureError(f"{path}: non-string $ref")
                    resolve_local_ref(schema, ref, path)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(schema)


def validate_schema_instance(
    schema: dict[str, Any], instance: Any, path: Path
) -> Any:
    """Validate the Draft 2020-12 subset used by public status."""

    def is_mathematical_integer(value: Any) -> bool:
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            or isinstance(value, float)
            and math.isfinite(value)
            and value.is_integer()
        )

    def visit(node: Any, value: Any, context: str) -> None:
        if not isinstance(node, dict):
            raise FixtureError(f"{path}: {context}: schema node is not an object")
        if "$ref" in node:
            ref = node["$ref"]
            if not isinstance(ref, str):
                raise FixtureError(f"{path}: {context}: non-string $ref")
            visit(resolve_local_ref(schema, ref, path), value, context)
        expected_type = node.get("type")
        if expected_type == "object" and not isinstance(value, dict):
            raise ValidationError("invalid_public_status", "expected object")
        if expected_type == "integer" and not is_mathematical_integer(value):
            raise ValidationError("invalid_public_status", "expected integer")
        if "const" in node and value != node["const"]:
            raise ValidationError("invalid_public_status", "constant mismatch")
        if "enum" in node and value not in node["enum"]:
            raise ValidationError("invalid_public_status", "enum mismatch")
        if "minimum" in node and value < node["minimum"]:
            raise ValidationError("invalid_public_status", "below minimum")
        if "maximum" in node and value > node["maximum"]:
            raise ValidationError("invalid_public_status", "above maximum")
        if isinstance(value, dict):
            required = node.get("required", [])
            if not isinstance(required, list) or not all(
                isinstance(key, str) for key in required
            ):
                raise FixtureError(f"{path}: {context}: invalid required keyword")
            if any(key not in value for key in required):
                raise ValidationError("invalid_public_status", "missing required field")
            properties = node.get("properties", {})
            if not isinstance(properties, dict):
                raise FixtureError(f"{path}: {context}: invalid properties keyword")
            if node.get("additionalProperties") is False and any(
                key not in properties for key in value
            ):
                raise ValidationError("invalid_public_status", "unknown field")
            for key, child in properties.items():
                if key in value:
                    visit(child, value[key], f"{context}.{key}")

    visit(schema, instance, "$")
    return instance


def validate_capabilities(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("invalid_capabilities", "capabilities is not an object")
    capabilities = value
    required = {
        "protocol",
        "version",
        "maximum_binary_frame_size",
        "maximum_control_message_size",
        "maximum_active_stream_sessions",
        "maximum_control_connections",
        "persistent_capture_supported",
        "security_mode",
        "streams",
    }
    if set(capabilities) != required:
        raise ValidationError("invalid_capabilities", "wrong capabilities fields")
    if capabilities["protocol"] != "d2b-stream" or capabilities["version"] != "0.1":
        raise ValidationError("invalid_capabilities", "wrong protocol or version")
    try:
        check_uint(
            capabilities["maximum_binary_frame_size"],
            "maximum_binary_frame_size",
            2**32 - 1,
            ENVELOPE_SIZE,
        )
        check_uint(
            capabilities["maximum_control_connections"],
            "maximum_control_connections",
            2**32 - 1,
            1,
        )
    except ValidationError as exc:
        raise ValidationError("invalid_capabilities", str(exc)) from exc
    if (
        capabilities["maximum_control_message_size"] != CONTROL_LIMIT
        or capabilities["maximum_active_stream_sessions"] != 1
        or not isinstance(capabilities["persistent_capture_supported"], bool)
        or capabilities["security_mode"]
        not in {"isolated", "unauthenticated-read-only", "pairing-token"}
    ):
        raise ValidationError("invalid_capabilities", "invalid fixed capability")
    streams = capabilities["streams"]
    if not isinstance(streams, list) or not 1 <= len(streams) <= 64:
        raise ValidationError("invalid_capabilities", "invalid streams")
    has_standard_profile = False
    stream_ids: set[str] = set()
    for stream in streams:
        if not isinstance(stream, dict) or set(stream) != {"id", "label", "profiles"}:
            raise ValidationError("invalid_capabilities", "invalid stream descriptor")
        stream_id = stream["id"]
        if (
            not isinstance(stream_id, str)
            or not IDENTIFIER_RE.fullmatch(stream_id)
            or stream_id in stream_ids
        ):
            raise ValidationError("invalid_capabilities", "invalid or duplicate stream id")
        stream_ids.add(stream_id)
        if not isinstance(stream["label"], str) or not 1 <= len(stream["label"]) <= 128:
            raise ValidationError("invalid_capabilities", "invalid stream label")
        profiles = stream["profiles"]
        if not isinstance(profiles, list) or not 1 <= len(profiles) <= 32:
            raise ValidationError("invalid_capabilities", "invalid profiles")
        profile_ids: set[str] = set()
        for descriptor in profiles:
            if not isinstance(descriptor, dict) or set(descriptor) != {
                "profile",
                "parameter_sets",
            }:
                raise ValidationError("invalid_capabilities", "invalid profile descriptor")
            profile = descriptor["profile"]
            if (
                not isinstance(profile, str)
                or not IDENTIFIER_RE.fullmatch(profile)
                or profile in profile_ids
            ):
                raise ValidationError("invalid_capabilities", "invalid or duplicate profile")
            profile_ids.add(profile)
            if profile in STANDARD_PROFILES:
                has_standard_profile = True
            parameter_sets = descriptor["parameter_sets"]
            if not isinstance(parameter_sets, list) or not 1 <= len(parameter_sets) <= 32:
                raise ValidationError("invalid_capabilities", "invalid parameter_sets")
            seen_parameter_sets: set[str] = set()
            for parameters in parameter_sets:
                try:
                    validate_parameter_shape(parameters)
                    canonical_parameters = json.dumps(
                        parameters,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                        allow_nan=False,
                    )
                    if canonical_parameters in seen_parameter_sets:
                        raise ValidationError(
                            "invalid_capabilities", "duplicate complete parameter set"
                        )
                    seen_parameter_sets.add(canonical_parameters)
                    if profile in STANDARD_PROFILES:
                        validate_parameters(parameters, profile)
                        required_frame_size = ENVELOPE_SIZE + (
                            16
                            if profile == "vi-measurement"
                            else parameters["samples_per_frame"]
                            * parameters["channel_count"]
                            * 2
                        )
                        if capabilities["maximum_binary_frame_size"] < required_frame_size:
                            raise ValidationError(
                                "invalid_capabilities",
                                "maximum_binary_frame_size "
                                f"{capabilities['maximum_binary_frame_size']} cannot carry "
                                f"advertised {profile} frame of {required_frame_size} bytes",
                            )
                except (TypeError, ValueError, ValidationError) as exc:
                    raise ValidationError("invalid_capabilities", str(exc)) from exc
    if not has_standard_profile:
        raise ValidationError(
            "invalid_capabilities", "capabilities advertises no standard profile"
        )
    return capabilities


def is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def check_uint(value: Any, field: str, maximum: int, minimum: int = 0) -> None:
    if not is_int(value) or not minimum <= value <= maximum:
        raise ValidationError("invalid_message", f"invalid {field}")


def check_string(value: Any, field: str, minimum: int, maximum: int) -> None:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise ValidationError("invalid_message", f"invalid {field}")


def require_exact_fields(
    message: dict[str, Any], required: set[str], optional: set[str]
) -> None:
    if not required <= message.keys() or not message.keys() <= required | optional:
        raise ValidationError("invalid_message", "wrong message fields")


def validate_parameter_shape(parameters: Any) -> dict[str, Any]:
    if not isinstance(parameters, dict) or len(parameters) > 32:
        raise ValidationError("invalid_message", "parameters is not a bounded object")
    if any(not isinstance(key, str) or not IDENTIFIER_RE.fullmatch(key) for key in parameters):
        raise ValidationError("invalid_message", "invalid parameter name")
    if "sample_format" in parameters:
        check_string(parameters["sample_format"], "sample_format", 1, 64)
    if "channel_count" in parameters:
        check_uint(parameters["channel_count"], "channel_count", 32, 1)
    if "channel_mask" in parameters:
        check_uint(parameters["channel_mask"], "channel_mask", 2**32 - 1)
    if "sample_rate" in parameters:
        rate = parameters["sample_rate"]
        if not isinstance(rate, dict) or set(rate) != {"numerator", "denominator"}:
            raise ValidationError("invalid_message", "invalid sample_rate fields")
        check_uint(rate["numerator"], "sample_rate.numerator", 2**32 - 1)
        check_uint(rate["denominator"], "sample_rate.denominator", 2**32 - 1)
    if "samples_per_frame" in parameters:
        check_uint(parameters["samples_per_frame"], "samples_per_frame", 2**32 - 1, 1)
    return parameters


def validate_parameters(parameters: Any, profile: str) -> dict[str, Any]:
    parameters = validate_parameter_shape(parameters)

    if profile == "vi-measurement":
        required = {"sample_format", "channel_count", "channel_mask", "sample_rate"}
        if set(parameters) != required:
            raise ValidationError("unsupported_parameters", "unsupported V/I fields")
        if (
            parameters["sample_format"] != "vi-f32le"
            or parameters["channel_count"] != 2
            or parameters["channel_mask"] != 3
        ):
            raise ValidationError("unsupported_parameters", "unsupported V/I parameters")
        numerator = parameters["sample_rate"]["numerator"]
        denominator = parameters["sample_rate"]["denominator"]
        if (numerator == 0) != (denominator == 0):
            raise ValidationError("unsupported_parameters", "unsupported V/I rate")
    elif profile == "pcm-audio":
        required = {
            "sample_format",
            "channel_count",
            "channel_mask",
            "sample_rate",
            "samples_per_frame",
        }
        if set(parameters) != required:
            raise ValidationError("unsupported_parameters", "unsupported PCM fields")
        if parameters["channel_mask"].bit_count() != parameters["channel_count"]:
            raise ValidationError("unsupported_parameters", "invalid PCM channel layout")
        numerator = parameters["sample_rate"]["numerator"]
        denominator = parameters["sample_rate"]["denominator"]
        if (
            parameters["sample_format"] != "pcm-s16le-interleaved"
            or parameters["channel_count"] != 1
            or parameters["channel_mask"] != 1
            or (numerator, denominator) != (16000, 1)
            or parameters["samples_per_frame"] != 256
        ):
            raise ValidationError("unsupported_parameters", "unsupported PCM parameter set")
    else:
        raise ValidationError("unsupported_profile", "unknown profile")
    return parameters


CLIENT_FIELDS = {
    "hello": ({"type", "protocol", "versions"}, {"client_name", "authentication"}),
    "start_stream": (
        {"type", "stream", "profile", "parameters"},
        {"options"},
    ),
    "stop_stream": ({"type"}, {"stream_id", "reason"}),
    "ping": ({"type", "correlation"}, set()),
}
SERVER_FIELDS = {
    "welcome": (
        {
            "type",
            "protocol",
            "version",
            "max_control_message_size",
            "max_binary_frame_size",
            "session_state",
        },
        {"server_name"},
    ),
    "stream_started": (
        {"type", "stream", "profile", "parameters", "stream_id"},
        set(),
    ),
    "stream_stopped": ({"type", "stream_id", "reason"}, set()),
    "status": (
        {
            "type",
            "state",
            "connected_client_count",
            "producer_drop_count",
            "output_queue_drop_count",
            "queued_sample_count",
            "source_paused",
            "uptime_us",
        },
        {"active_stream_id", "last_error"},
    ),
    "error": ({"type", "code", "message"}, {"correlation", "recoverable"}),
    "pong": ({"type", "correlation"}, set()),
}


def control_wire_value(message: Any) -> dict[str, Any]:
    if isinstance(message, bytes):
        raw = message
        if len(raw) > CONTROL_LIMIT:
            raise ValidationError("frame_too_large")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError("invalid_message", f"invalid UTF-8: {exc}") from exc
        try:
            parsed = strict_json_loads(text)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValidationError("invalid_message", f"invalid JSON: {exc}") from exc
    elif isinstance(message, str):
        raw = message.encode("utf-8")
        if len(raw) > CONTROL_LIMIT:
            raise ValidationError("frame_too_large")
        try:
            parsed = strict_json_loads(message)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValidationError("invalid_message", f"invalid JSON: {exc}") from exc
    else:
        raw = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        if len(raw) > CONTROL_LIMIT:
            raise ValidationError("frame_too_large")
        parsed = message
    if not isinstance(parsed, dict):
        raise ValidationError("invalid_message", "message is not an object")
    return parsed


def validate_authentication(authentication: Any) -> None:
    if not isinstance(authentication, dict) or set(authentication) != {"scheme", "token"}:
        raise ValidationError("invalid_message", "invalid authentication fields")
    if authentication["scheme"] != "pairing-token":
        raise ValidationError("invalid_message", "invalid authentication scheme")
    token = authentication["token"]
    if not isinstance(token, str) or not 1 <= len(token) <= 256:
        raise ValidationError("invalid_message", "invalid token length")
    if len(token.encode("utf-8")) > 256:
        raise ValidationError("invalid_message", "token exceeds 256 UTF-8 bytes")


def validate_control_message(message: Any, direction: str) -> dict[str, Any]:
    message = control_wire_value(message)
    table = CLIENT_FIELDS if direction == "client_to_server" else SERVER_FIELDS
    message_type = message.get("type")
    if message_type not in table:
        raise ValidationError("invalid_message", "unknown message type")
    required, optional = table[message_type]
    require_exact_fields(message, required, optional)

    if message_type == "hello":
        if message["protocol"] != "d2b-stream":
            raise ValidationError("invalid_message", "invalid protocol")
        versions = message["versions"]
        if (
            not isinstance(versions, list)
            or not 1 <= len(versions) <= 16
            or any(not isinstance(v, str) or not VERSION_RE.fullmatch(v) for v in versions)
            or len(set(versions)) != len(versions)
        ):
            raise ValidationError("invalid_message", "invalid versions")
        if "client_name" in message:
            check_string(message["client_name"], "client_name", 1, 128)
        if "authentication" in message:
            validate_authentication(message["authentication"])
    elif message_type == "welcome":
        if (
            message["protocol"] != "d2b-stream"
            or message["version"] != "0.1"
            or message["max_control_message_size"] != CONTROL_LIMIT
            or message["session_state"] != "ready"
        ):
            raise ValidationError("invalid_message", "invalid welcome")
        check_uint(
            message["max_binary_frame_size"],
            "max_binary_frame_size",
            2**32 - 1,
            ENVELOPE_SIZE,
        )
        if "server_name" in message:
            check_string(message["server_name"], "server_name", 1, 128)
    elif message_type in {"start_stream", "stream_started"}:
        stream = message["stream"]
        if not isinstance(stream, str) or not IDENTIFIER_RE.fullmatch(stream):
            raise ValidationError("invalid_message", "invalid stream")
        profile = message["profile"]
        if not isinstance(profile, str) or not IDENTIFIER_RE.fullmatch(profile):
            raise ValidationError("invalid_message", "invalid profile identifier")
        validate_parameter_shape(message["parameters"])
        if profile not in {"vi-measurement", "pcm-audio"}:
            raise ValidationError("unsupported_profile", "unsupported profile")
        validate_parameters(message["parameters"], profile)
        if "options" in message:
            options = message["options"]
            if not isinstance(options, dict) or len(options) > 32:
                raise ValidationError("invalid_message", "invalid options")
        if message_type == "stream_started":
            check_uint(message["stream_id"], "stream_id", 2**32 - 1, 1)
    elif message_type in {"stop_stream", "stream_stopped"}:
        if "stream_id" in message:
            check_uint(message["stream_id"], "stream_id", 2**32 - 1, 1)
        if "reason" in message:
            check_string(message["reason"], "reason", 1, 256)
    elif message_type == "status":
        if message["state"] not in {"idle", "streaming"}:
            raise ValidationError("invalid_message", "invalid status state")
        has_id = "active_stream_id" in message
        if has_id != (message["state"] == "streaming"):
            raise ValidationError("invalid_message", "active_stream_id/state mismatch")
        if has_id:
            check_uint(message["active_stream_id"], "active_stream_id", 2**32 - 1, 1)
        check_uint(message["connected_client_count"], "connected_client_count", 2**32 - 1)
        check_uint(message["producer_drop_count"], "producer_drop_count", 2**53 - 1)
        check_uint(
            message["output_queue_drop_count"],
            "output_queue_drop_count",
            2**53 - 1,
        )
        check_uint(message["queued_sample_count"], "queued_sample_count", 2**32 - 1)
        check_uint(message["uptime_us"], "uptime_us", 2**53 - 1)
        if not isinstance(message["source_paused"], bool):
            raise ValidationError("invalid_message", "invalid source_paused")
        if "last_error" in message and message["last_error"] is not None:
            detail = message["last_error"]
            if not isinstance(detail, dict) or set(detail) != {"code", "message"}:
                raise ValidationError("invalid_message", "invalid last_error")
            if detail["code"] not in ERROR_CODES:
                raise ValidationError("invalid_message", "invalid last_error code")
            check_string(detail["message"], "last_error.message", 1, 512)
    elif message_type == "error":
        if message["code"] not in ERROR_CODES:
            raise ValidationError("invalid_message", "invalid error code")
        check_string(message["message"], "message", 1, 512)
        if "correlation" in message:
            check_string(message["correlation"], "correlation", 1, 128)
        if "recoverable" in message and not isinstance(message["recoverable"], bool):
            raise ValidationError("invalid_message", "invalid recoverable")
    elif message_type in {"ping", "pong"}:
        check_string(message["correlation"], "correlation", 1, 128)
    return message


def validate_control_context(vector: dict[str, Any], result: dict[str, Any] | None) -> None:
    context = vector.get("context")
    if context is None:
        return
    if not isinstance(context, dict):
        raise FixtureError(f"{vector['name']}: context must be an object")
    if "state" in context:
        if set(context) != {"state", "owns_stream"}:
            raise FixtureError(f"{vector['name']}: invalid state context fields")
        state = context["state"]
        owns_stream = context["owns_stream"]
        if state not in {"CONNECTED", "READY", "STREAMING", "CLOSED"}:
            raise FixtureError(f"{vector['name']}: invalid control state")
        if not isinstance(owns_stream, bool):
            raise FixtureError(f"{vector['name']}: owns_stream must be boolean")
        if result is None or vector["direction"] != "client_to_server":
            raise FixtureError(f"{vector['name']}: state context requires a client message")
        allowed = {
            "CONNECTED": {"hello"},
            "READY": {"start_stream", "ping"},
            "STREAMING": {"stop_stream", "ping"},
            "CLOSED": set(),
        }
        message_type = result["type"]
        if message_type not in allowed[state]:
            raise ValidationError("invalid_state", f"{message_type} is invalid in {state}")
        if state == "STREAMING" and message_type == "stop_stream" and not owns_stream:
            raise ValidationError("invalid_state", "non-owner cannot stop stream")
        return
    scenario = context.get("scenario")
    request = context.get("request")
    if request is not None:
        validate_control_message(request, "client_to_server")
    if result is None:
        return

    if scenario == "second_client_busy":
        required = {"scenario", "connection_a", "connection_b", "request", "postcondition"}
        if set(context) != required:
            raise FixtureError(f"{vector['name']}: invalid busy context fields")
        if context["connection_a"] != {"state": "streaming", "owns_stream": True}:
            raise FixtureError(f"{vector['name']}: connection A must own STREAMING")
        if context["connection_b"] != {"state": "ready", "owns_stream": False}:
            raise FixtureError(f"{vector['name']}: connection B must be READY")
        if context["postcondition"] != {
            "connection_a_state": "streaming",
            "connection_a_owns_stream": True,
        }:
            raise FixtureError(f"{vector['name']}: owner postcondition is missing")
        if result.get("type") != "error" or result.get("code") != "busy":
            raise FixtureError(f"{vector['name']}: busy result mismatch")
    elif scenario == "unsupported_parameters":
        required = {"scenario", "request", "advertised_parameter_sets"}
        if set(context) != required or not isinstance(context["advertised_parameter_sets"], list):
            raise FixtureError(f"{vector['name']}: invalid parameter context")
        requested = request["parameters"]
        if requested in context["advertised_parameter_sets"]:
            raise FixtureError(f"{vector['name']}: requested parameters are advertised")
        if result.get("code") != "unsupported_parameters":
            raise FixtureError(f"{vector['name']}: unsupported_parameters result mismatch")
    elif scenario == "unknown_stream":
        required = {"scenario", "request", "advertised_streams"}
        if set(context) != required or not isinstance(context["advertised_streams"], list):
            raise FixtureError(f"{vector['name']}: invalid stream context")
        if request["stream"] in context["advertised_streams"]:
            raise FixtureError(f"{vector['name']}: requested stream is advertised")
        if result.get("code") != "unknown_stream":
            raise FixtureError(f"{vector['name']}: unknown_stream result mismatch")
    else:
        raise FixtureError(f"{vector['name']}: unknown control scenario {scenario!r}")


ENVELOPE_NAMES = (
    "magic",
    "protocol_major",
    "protocol_minor",
    "frame_type",
    "flags",
    "stream_id",
    "sample_count",
    "first_sample_sequence",
    "first_timestamp_us",
)


def parse_version(version: str) -> tuple[int, int]:
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        raise FixtureError(f"invalid negotiated version {version!r}")
    major, minor = version.split(".")
    return int(major), int(minor)


def decode_envelope(data: bytes, negotiated_version: str) -> dict[str, Any]:
    if len(data) < ENVELOPE_SIZE:
        raise ValidationError("envelope_too_short")
    decoded = dict(zip(ENVELOPE_NAMES, ENVELOPE.unpack_from(data)))
    if decoded["magic"] != b"D2BS":
        raise ValidationError("bad_magic")
    major, minor = parse_version(negotiated_version)
    if (decoded["protocol_major"], decoded["protocol_minor"]) != (major, minor):
        raise ValidationError("version_mismatch")
    flags = decoded["flags"]
    frame_type = decoded["frame_type"]
    if flags & FLAG_RESERVED:
        raise ValidationError("reserved_flag_set")
    if flags & FLAG_STREAM_START and flags & FLAG_STREAM_END:
        raise ValidationError("stream_start_end_conflict")
    if frame_type == FRAME_STREAM_END:
        if not flags & FLAG_STREAM_END:
            raise ValidationError("stream_end_flag_missing")
        if flags != FLAG_STREAM_END:
            raise ValidationError("invalid_stream_end_flags")
    elif flags & FLAG_STREAM_END:
        raise ValidationError("data_stream_end_flag")
    cause_flags = (
        FLAG_PRODUCER_OVERFLOW
        | FLAG_OUTPUT_QUEUE_DROP
        | FLAG_SOURCE_PAUSED
        | FLAG_TIMEBASE_RESET
    )
    if flags & cause_flags and not flags & FLAG_DISCONTINUITY:
        raise ValidationError("missing_discontinuity_flag")
    if flags & FLAG_TIMEBASE_RESET and not flags & FLAG_STREAM_START:
        raise ValidationError("timebase_reset_requires_new_session")
    if frame_type not in {FRAME_FIXED_RATE, FRAME_TIMESTAMPED, FRAME_STREAM_END}:
        raise ValidationError("unknown_frame_type")
    if decoded["stream_id"] == 0:
        raise ValidationError("invalid_stream_id")
    if frame_type == FRAME_STREAM_END:
        if decoded["sample_count"] != 0:
            raise ValidationError("invalid_stream_end")
    else:
        if decoded["sample_count"] == 0:
            raise ValidationError("sample_count_zero")
        if decoded["first_sample_sequence"] + decoded["sample_count"] - 1 > 2**64 - 1:
            raise ValidationError("sequence_overflow")
    decoded["magic"] = "D2BS"
    decoded["payload_length"] = len(data) - ENVELOPE_SIZE
    return decoded


CONTEXT_REQUIRED = {
    "negotiated_version",
    "session_state",
    "maximum_binary_frame_size",
    "stream_id",
    "profile",
    "parameters",
}
CONTEXT_PREVIOUS = {
    "previous_first_sample_sequence",
    "previous_sample_count",
    "previous_first_timestamp_us",
}
CONTEXT_ANCHOR = {"session_anchor_sequence", "session_anchor_timestamp_us"}
CONTEXT_VI_LAST = {"previous_last_timestamp_us"}


def validate_binary_context(context: Any, profile: str) -> dict[str, Any] | None:
    if context is None:
        return None
    if not isinstance(context, dict):
        raise FixtureError("binary context must be an object")
    allowed = CONTEXT_REQUIRED | CONTEXT_PREVIOUS | CONTEXT_ANCHOR | CONTEXT_VI_LAST
    if not CONTEXT_REQUIRED <= context.keys() or not context.keys() <= allowed:
        raise FixtureError("binary context has wrong fields")
    previous_present = CONTEXT_PREVIOUS & context.keys()
    if previous_present and previous_present != CONTEXT_PREVIOUS:
        raise FixtureError("binary context has incomplete previous-frame state")
    anchor_present = CONTEXT_ANCHOR & context.keys()
    if anchor_present and anchor_present != CONTEXT_ANCHOR:
        raise FixtureError("binary context has incomplete session anchor")
    if context["profile"] != profile:
        raise FixtureError("binary context profile does not match vector file")
    parse_version(context["negotiated_version"])
    if context["session_state"] not in {"READY", "STREAMING", "CLOSED"}:
        raise FixtureError("binary context has invalid session_state")
    integer_fields = {"stream_id", "maximum_binary_frame_size"}
    vi_last_present = CONTEXT_VI_LAST & context.keys()
    integer_fields |= previous_present | anchor_present | vi_last_present
    for field in integer_fields:
        if not is_int(context[field]) or context[field] < 0:
            raise FixtureError(f"binary context field {field} is not unsigned integer")
    if context["stream_id"] == 0 or context["maximum_binary_frame_size"] < ENVELOPE_SIZE:
        raise FixtureError("binary context has invalid stream or size limit")
    try:
        validate_parameters(context["parameters"], profile)
    except ValidationError as exc:
        raise FixtureError(f"binary context has invalid parameters: {exc.code}") from exc
    if profile == "pcm-audio":
        if anchor_present != CONTEXT_ANCHOR:
            raise FixtureError("PCM context requires a session anchor")
        if vi_last_present:
            raise FixtureError("PCM context contains V/I-only timestamp state")
    elif profile == "vi-measurement":
        if anchor_present:
            raise FixtureError("V/I context contains PCM-only session anchor")
        if previous_present and vi_last_present != CONTEXT_VI_LAST:
            raise FixtureError("V/I continuity context requires previous_last_timestamp_us")
        if not previous_present and vi_last_present:
            raise FixtureError("V/I last timestamp requires previous-frame state")
    return context


def validate_session_invariants(
    decoded: dict[str, Any], context: dict[str, Any] | None
) -> None:
    if context is None:
        return
    if decoded["stream_id"] != context["stream_id"]:
        raise ValidationError("stream_id_mismatch")


def decode_vi(payload: bytes, decoded: dict[str, Any]) -> None:
    if decoded["frame_type"] != FRAME_TIMESTAMPED:
        raise ValidationError("vi_frame_type_mismatch")
    if decoded["sample_count"] * 16 != len(payload):
        raise ValidationError("vi_payload_length_mismatch")

    previous_delta = -1
    first: tuple[int, int, float, float] | None = None
    last_delta = 0
    for index in range(decoded["sample_count"]):
        delta, valid_mask, voltage, current = struct.unpack_from("<IIff", payload, index * 16)
        if index == 0 and delta != 0:
            raise ValidationError("vi_first_delta_nonzero")
        if delta < previous_delta:
            raise ValidationError("vi_delta_regression")
        if valid_mask & ~3:
            raise ValidationError("vi_invalid_valid_mask")
        if valid_mask & 1 and not math.isfinite(voltage):
            raise ValidationError("vi_nonfinite_valid_value")
        if valid_mask & 2 and not math.isfinite(current):
            raise ValidationError("vi_nonfinite_valid_value")
        if decoded["first_timestamp_us"] + delta > 2**64 - 1:
            raise ValidationError("timestamp_overflow")
        if first is None:
            first = (delta, valid_mask, voltage, current)
        previous_delta = delta
        last_delta = delta
    assert first is not None
    decoded.update(
        {
            "first_delta_us": first[0],
            "last_delta_us": last_delta,
            "first_valid_mask": first[1],
            "first_voltage": first[2],
            "first_current": first[3],
        }
    )


def decode_pcm(
    payload: bytes, decoded: dict[str, Any], context: dict[str, Any] | None
) -> None:
    if decoded["frame_type"] != FRAME_FIXED_RATE:
        raise ValidationError("pcm_frame_type_mismatch")
    parameters = context["parameters"] if context else {
        "sample_format": "pcm-s16le-interleaved",
        "channel_count": 1,
        "channel_mask": 1,
        "sample_rate": {"numerator": 16000, "denominator": 1},
        "samples_per_frame": 256,
    }
    if decoded["sample_count"] != parameters["samples_per_frame"]:
        raise ValidationError("pcm_sample_count_mismatch")
    expected_size = decoded["sample_count"] * parameters["channel_count"] * 2
    if expected_size != len(payload):
        raise ValidationError("pcm_payload_length_mismatch")
    decoded["first_pcm_value"] = struct.unpack_from("<h", payload, 0)[0]
    decoded["last_pcm_value"] = struct.unpack_from("<h", payload, len(payload) - 2)[0]


def decode_stream_end(payload: bytes, decoded: dict[str, Any]) -> None:
    if payload:
        raise ValidationError("invalid_stream_end")


def validate_continuity(
    decoded: dict[str, Any], context: dict[str, Any] | None
) -> None:
    gap = 0
    has_previous = context is not None and CONTEXT_PREVIOUS <= context.keys()
    is_data = decoded["frame_type"] != FRAME_STREAM_END
    if is_data and not has_previous and not decoded["flags"] & FLAG_STREAM_START:
        raise ValidationError("missing_stream_start")
    if decoded["flags"] & FLAG_TIMEBASE_RESET and has_previous:
        raise ValidationError("timebase_reset_requires_new_session")
    if decoded["flags"] & FLAG_STREAM_START and has_previous:
        raise ValidationError("unexpected_stream_start")

    if context is None:
        decoded["gap_samples"] = gap
        return

    if has_previous:
        expected_sequence = (
            context["previous_first_sample_sequence"] + context["previous_sample_count"]
        )
        if expected_sequence > 2**64 - 1:
            raise ValidationError("sequence_overflow")
        decoded["expected_next_sequence"] = expected_sequence
        sequence = decoded["first_sample_sequence"]
        if sequence < expected_sequence:
            raise ValidationError("sequence_regression")
        gap = sequence - expected_sequence
        if gap and not decoded["flags"] & FLAG_DISCONTINUITY:
            raise ValidationError("missing_discontinuity_flag")
        if context["profile"] == "pcm-audio" and decoded["frame_type"] != FRAME_STREAM_END:
            cause_flags = (
                FLAG_PRODUCER_OVERFLOW | FLAG_OUTPUT_QUEUE_DROP | FLAG_SOURCE_PAUSED
            )
            if decoded["flags"] & cause_flags and gap == 0:
                raise ValidationError("cause_flag_without_gap")
        comparison_timestamp = context["previous_first_timestamp_us"]
        if context["profile"] == "vi-measurement":
            comparison_timestamp = context["previous_last_timestamp_us"]
        if decoded["first_timestamp_us"] < comparison_timestamp:
            raise ValidationError("timestamp_regression")

    if context["profile"] == "pcm-audio" and decoded["frame_type"] != FRAME_STREAM_END:
        if not CONTEXT_ANCHOR <= context.keys():
            raise FixtureError("PCM context requires session anchor")
        sequence_delta = decoded["first_sample_sequence"] - context["session_anchor_sequence"]
        if sequence_delta < 0:
            raise ValidationError("sequence_regression")
        expected_timestamp = Fraction(context["session_anchor_timestamp_us"], 1) + Fraction(
            sequence_delta
            * context["parameters"]["sample_rate"]["denominator"]
            * 1_000_000,
            context["parameters"]["sample_rate"]["numerator"],
        )
        timestamp_error = abs(Fraction(decoded["first_timestamp_us"], 1) - expected_timestamp)
        if timestamp_error > 1:
            raise ValidationError("pcm_timestamp_out_of_tolerance")
        decoded["pcm_expected_timestamp_floor_us"] = (
            expected_timestamp.numerator // expected_timestamp.denominator
        )
        decoded["pcm_timestamp_within_1us"] = True

    decoded["gap_samples"] = gap


def decode_binary_frame(
    data: bytes, profile: str, raw_context: Any
) -> dict[str, Any]:
    context = validate_binary_context(raw_context, profile)
    if context is not None:
        if len(data) > context["maximum_binary_frame_size"]:
            raise ValidationError("frame_too_large")
        if context["session_state"] != "STREAMING":
            raise ValidationError("invalid_state", "binary data before stream_started")
    negotiated_version = context["negotiated_version"] if context else "0.1"
    decoded = decode_envelope(data, negotiated_version)
    validate_session_invariants(decoded, context)
    payload = data[ENVELOPE_SIZE:]
    if decoded["frame_type"] == FRAME_STREAM_END:
        decode_stream_end(payload, decoded)
    elif profile == "vi-measurement":
        decode_vi(payload, decoded)
    elif profile == "pcm-audio":
        decode_pcm(payload, decoded, context)
    else:
        raise ValidationError("unknown_profile")

    decoded["discontinuity"] = bool(decoded["flags"] & FLAG_DISCONTINUITY)
    decoded["producer_overflow"] = bool(decoded["flags"] & FLAG_PRODUCER_OVERFLOW)
    decoded["output_queue_drop"] = bool(decoded["flags"] & FLAG_OUTPUT_QUEUE_DROP)
    decoded["stream_start"] = bool(decoded["flags"] & FLAG_STREAM_START)
    decoded["stream_end"] = bool(decoded["flags"] & FLAG_STREAM_END)
    decoded["source_paused"] = bool(decoded["flags"] & FLAG_SOURCE_PAUSED)
    decoded["timebase_reset"] = bool(decoded["flags"] & FLAG_TIMEBASE_RESET)
    validate_continuity(decoded, context)
    return decoded


def assert_expected(actual: Any, expected: Any, context: str) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise FixtureError(f"{context}: expected object, got {actual!r}")
        for key, expected_value in expected.items():
            if key not in actual:
                raise FixtureError(f"{context}: decoded field {key!r} is missing")
            assert_expected(actual[key], expected_value, f"{context}.{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise FixtureError(f"{context}: list mismatch")
        for index, expected_value in enumerate(expected):
            assert_expected(actual[index], expected_value, f"{context}[{index}]")
    elif actual != expected:
        raise FixtureError(f"{context}: expected {expected!r}, got {actual!r}")


def validate_vector_result(
    vector: dict[str, Any], result: dict[str, Any] | None, error: ValidationError | None
) -> None:
    name = vector["name"]
    expected_valid = vector["expected_valid"]
    if not isinstance(expected_valid, bool):
        raise FixtureError(f"{name}: expected_valid must be boolean")
    if expected_valid:
        if error is not None:
            raise FixtureError(f"{name}: expected valid, got {error.code}: {error}")
        if "expected_error" in vector or "expected_decoded" not in vector:
            raise FixtureError(f"{name}: malformed valid expectation")
        assert result is not None
        assert_expected(result, vector["expected_decoded"], name)
    else:
        if result is not None or error is None:
            raise FixtureError(f"{name}: expected invalid, but validation succeeded")
        if vector.get("expected_error") != error.code:
            raise FixtureError(
                f"{name}: expected error {vector.get('expected_error')!r}, got {error.code!r}"
            )


def register_vector_name(vector: dict[str, Any], names: set[str]) -> None:
    name = vector.get("name")
    if not isinstance(name, str) or not name:
        raise FixtureError("vector name must be a non-empty string")
    if name in names:
        raise FixtureError(f"duplicate vector name {name!r}")
    names.add(name)
    if not isinstance(vector.get("purpose"), str) or not vector["purpose"]:
        raise FixtureError(f"{name}: purpose must be a non-empty string")


CONTROL_VECTOR_REQUIRED = {
    "name",
    "purpose",
    "direction",
    "expected_valid",
}
CONTROL_VECTOR_ALLOWED = CONTROL_VECTOR_REQUIRED | {
    "message",
    "message_hex",
    "context",
    "expected_decoded",
    "expected_error",
}
BINARY_VECTOR_REQUIRED = {
    "name",
    "purpose",
    "frame_hex",
    "expected_valid",
}
BINARY_VECTOR_ALLOWED = BINARY_VECTOR_REQUIRED | {
    "context",
    "expected_decoded",
    "expected_error",
}
CAPABILITIES_VECTOR_REQUIRED = {
    "name",
    "purpose",
    "document",
    "expected_valid",
}
CAPABILITIES_VECTOR_ALLOWED = CAPABILITIES_VECTOR_REQUIRED | {
    "expected_decoded",
    "expected_error",
}
PUBLIC_STATUS_VECTOR_REQUIRED = {
    "name",
    "purpose",
    "category",
    "document",
    "expected_valid",
}
PUBLIC_STATUS_VECTOR_ALLOWED = PUBLIC_STATUS_VECTOR_REQUIRED | {
    "expected_decoded",
    "expected_error",
}


def validate_fixture_fields(
    vector: dict[str, Any], required: set[str], allowed: set[str], kind: str
) -> None:
    require_keys(vector, required, kind)
    unexpected = vector.keys() - allowed
    if unexpected:
        raise FixtureError(f"{vector.get('name', kind)}: unexpected fields {sorted(unexpected)}")
    expected_valid = vector.get("expected_valid")
    if expected_valid is True:
        if "expected_decoded" not in vector or "expected_error" in vector:
            raise FixtureError(f"{vector.get('name', kind)}: invalid success expectation fields")
    elif expected_valid is False:
        if "expected_error" not in vector or "expected_decoded" in vector:
            raise FixtureError(f"{vector.get('name', kind)}: invalid failure expectation fields")


def validate_control_vectors(document: dict[str, Any], names: set[str]) -> int:
    count = 0
    for raw_vector in document["vectors"]:
        vector = require_object(raw_vector, "control vector")
        validate_fixture_fields(
            vector, CONTROL_VECTOR_REQUIRED, CONTROL_VECTOR_ALLOWED, "control vector"
        )
        register_vector_name(vector, names)
        has_message = "message" in vector
        has_hex = "message_hex" in vector
        if has_message == has_hex:
            raise FixtureError(f"{vector['name']}: requires exactly one wire message field")
        if has_hex and (
            not isinstance(vector["message_hex"], str)
            or not HEX_RE.fullmatch(vector["message_hex"])
        ):
            raise FixtureError(f"{vector['name']}: invalid message_hex")
        if vector["name"] == "integer_as_float" and (
            not isinstance(vector.get("message"), str)
            or '"max_binary_frame_size":32.0' not in vector["message"]
        ):
            raise FixtureError(
                "integer_as_float: message must preserve the raw 32.0 token"
            )
        if vector["direction"] not in {"client_to_server", "server_to_client"}:
            raise FixtureError(f"{vector['name']}: invalid direction")
        result = None
        error = None
        try:
            wire_value = (
                bytes.fromhex(vector["message_hex"])
                if "message_hex" in vector
                else vector["message"]
            )
            parsed = validate_control_message(wire_value, vector["direction"])
            validate_control_context(vector, parsed)
            result = parsed
        except ValidationError as exc:
            error = exc
        validate_vector_result(vector, result, error)
        count += 1
    return count


def validate_binary_vectors(
    document: dict[str, Any], names: set[str]
) -> int:
    profile = document.get("profile")
    if profile not in {"vi-measurement", "pcm-audio"}:
        raise FixtureError("binary vector document has invalid profile")
    count = 0
    for raw_vector in document["vectors"]:
        vector = require_object(raw_vector, "binary vector")
        validate_fixture_fields(
            vector, BINARY_VECTOR_REQUIRED, BINARY_VECTOR_ALLOWED, "binary vector"
        )
        register_vector_name(vector, names)
        frame_hex = vector["frame_hex"]
        if not isinstance(frame_hex, str) or not HEX_RE.fullmatch(frame_hex):
            raise FixtureError(f"{vector['name']}: frame_hex is not lowercase hexadecimal")
        result = None
        error = None
        try:
            result = decode_binary_frame(
                bytes.fromhex(frame_hex), profile, vector.get("context")
            )
        except ValidationError as exc:
            error = exc
        validate_vector_result(vector, result, error)
        count += 1
    return count


def validate_capabilities_vectors(document: dict[str, Any], names: set[str]) -> int:
    count = 0
    for raw_vector in document["vectors"]:
        vector = require_object(raw_vector, "capabilities vector")
        validate_fixture_fields(
            vector,
            CAPABILITIES_VECTOR_REQUIRED,
            CAPABILITIES_VECTOR_ALLOWED,
            "capabilities vector",
        )
        register_vector_name(vector, names)
        result = None
        error = None
        try:
            result = validate_capabilities(vector["document"])
        except ValidationError as exc:
            error = exc
        validate_vector_result(vector, result, error)
        count += 1
    return count


def validate_public_status_vectors(
    document: dict[str, Any], names: set[str]
) -> int:
    schema_path = ROOT / "schemas/public-status.schema.json"
    schema = require_object(load_json(schema_path), str(schema_path))
    categories = {"positive": 0, "structural": 0, "numeric": 0, "privacy": 0}
    count = 0
    for raw_vector in document["vectors"]:
        vector = require_object(raw_vector, "public-status vector")
        validate_fixture_fields(
            vector,
            PUBLIC_STATUS_VECTOR_REQUIRED,
            PUBLIC_STATUS_VECTOR_ALLOWED,
            "public-status vector",
        )
        register_vector_name(vector, names)
        category = vector["category"]
        if category not in categories:
            raise FixtureError(f"{vector['name']}: invalid public-status category")
        categories[category] += 1
        result = None
        error = None
        try:
            result = validate_schema_instance(schema, vector["document"], schema_path)
        except ValidationError as exc:
            error = exc
        validate_vector_result(vector, result, error)
        count += 1
    if count < 31 or categories["positive"] < 7 or categories["privacy"] < 7:
        raise FixtureError(
            "public-status vectors require at least 31 total, 7 positive, and 7 privacy cases"
        )
    return count


def validate_vector_document(path: Path, names: set[str]) -> int:
    document = require_object(load_json(path), str(path))
    common_fields = {"format", "protocol", "version", "vectors"}
    if path.name == "public-status.json":
        expected_fields = common_fields | {"schema_draft", "schema_id"}
    elif path.name in {"control-messages.json", "capabilities.json"}:
        expected_fields = common_fields | {"schema_draft"}
    else:
        expected_fields = common_fields | {"profile"}
    require_keys(document, expected_fields, str(path))
    if set(document) != expected_fields:
        raise FixtureError(f"{path}: unexpected top-level fields {sorted(set(document) - expected_fields)}")
    if (
        document["format"] != FORMAT_ID
        or document["protocol"] != "d2b-stream"
        or document["version"] != "0.1"
        or not isinstance(document["vectors"], list)
        or not document["vectors"]
    ):
        raise FixtureError(f"{path}: invalid top-level metadata")
    if path.name in {
        "control-messages.json",
        "capabilities.json",
        "public-status.json",
    }:
        if document.get("schema_draft") != "2020-12":
            raise FixtureError(f"{path}: invalid schema_draft")
    if path.name == "public-status.json":
        if document.get("schema_id") != PUBLIC_STATUS_SCHEMA_ID:
            raise FixtureError(f"{path}: invalid public-status schema_id")
        return validate_public_status_vectors(document, names)
    if path.name == "control-messages.json":
        return validate_control_vectors(document, names)
    if path.name == "capabilities.json":
        return validate_capabilities_vectors(document, names)
    return validate_binary_vectors(document, names)


def run_negative_self_tests() -> int:
    tests = 0
    unknown = {
        "name": "unknown-field-self-test",
        "purpose": "exercise field rejection",
        "direction": "client_to_server",
        "message": {},
        "expected_valid": False,
        "expected_error": "invalid_message",
        "continuity": {},
    }
    try:
        validate_fixture_fields(
            unknown, CONTROL_VECTOR_REQUIRED, CONTROL_VECTOR_ALLOWED, "control vector"
        )
    except FixtureError:
        tests += 1
    else:
        raise FixtureError("negative self-test failed: unknown vector field accepted")

    names = {"duplicate-name-self-test"}
    duplicate = {"name": "duplicate-name-self-test", "purpose": "exercise uniqueness"}
    try:
        register_vector_name(duplicate, names)
    except FixtureError:
        tests += 1
    else:
        raise FixtureError("negative self-test failed: duplicate vector name accepted")
    return tests


def run_mutation_tests() -> int:
    """Confirm targeted corruptions of a known-good frame are rejected."""

    vi_parameters = {
        "sample_format": "vi-f32le",
        "channel_count": 2,
        "channel_mask": 3,
        "sample_rate": {"numerator": 0, "denominator": 0},
    }
    vi_context = {
        "negotiated_version": "0.1",
        "session_state": "STREAMING",
        "maximum_binary_frame_size": 65536,
        "stream_id": 1,
        "profile": "vi-measurement",
        "parameters": vi_parameters,
    }
    record = struct.pack("<IIff", 0, 3, 1.0, 0.5)
    baseline = ENVELOPE.pack(
        b"D2BS", 0, 1, FRAME_TIMESTAMPED, FLAG_STREAM_START, 1, 1, 0, 1000
    ) + record

    reserved = bytearray(baseline)
    reserved[7] |= FLAG_RESERVED
    count_mutation = bytearray(baseline)
    count_mutation[12] ^= 0x02
    header_bit = bytearray(baseline)
    header_bit[0] ^= 0x01
    sequence_boundary = ENVELOPE.pack(
        b"D2BS",
        0,
        1,
        FRAME_TIMESTAMPED,
        FLAG_STREAM_START,
        1,
        2,
        2**64 - 1,
        1000,
    ) + record * 2
    pcm_context = {
        "negotiated_version": "0.1",
        "session_state": "STREAMING",
        "maximum_binary_frame_size": 65536,
        "stream_id": 1,
        "profile": "pcm-audio",
        "parameters": {
            "sample_format": "pcm-s16le-interleaved",
            "channel_count": 1,
            "channel_mask": 1,
            "sample_rate": {"numerator": 16000, "denominator": 1},
            "samples_per_frame": 256,
        },
        "session_anchor_sequence": 0,
        "session_anchor_timestamp_us": 1000,
    }
    cases = (
        ("one-byte truncation", baseline[:-1], "vi-measurement", vi_context),
        ("one-byte extension", baseline + b"\x00", "vi-measurement", vi_context),
        ("single-bit header mutation", bytes(header_bit), "vi-measurement", vi_context),
        ("reserved-bit mutation", bytes(reserved), "vi-measurement", vi_context),
        ("sequence boundary mutation", sequence_boundary, "vi-measurement", vi_context),
        ("sample-count mutation", bytes(count_mutation), "vi-measurement", vi_context),
        ("profile mismatch", baseline, "pcm-audio", pcm_context),
    )
    for name, frame, profile, context_value in cases:
        try:
            decode_binary_frame(frame, profile, context_value)
        except ValidationError:
            continue
        raise FixtureError(f"mutation test accepted {name}")
    return len(cases)


def main() -> int:
    try:
        validate_schema_files()
        names: set[str] = set()
        counts = {
            path.name: validate_vector_document(path, names) for path in VECTOR_FILES
        }
        self_test_count = run_negative_self_tests()
        mutation_count = run_mutation_tests()
    except (FixtureError, OSError, ZeroDivisionError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    total = sum(counts.values())
    details = ", ".join(f"{name}={count}" for name, count in counts.items())
    print(
        f"PASS: validated {len(SCHEMA_FILES)} schemas, {total} golden vectors "
        f"({details}), {self_test_count} negative self-tests, and "
        f"{mutation_count} mutation tests"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
