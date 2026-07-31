// SPDX-License-Identifier: Apache-2.0

import { ProtocolError } from "../src/errors.js";
import { parseControlMessageBytes, parseControlMessageText } from "../src/control-parser.js";
import { validateCapabilities } from "../src/capabilities-validator.js";
import { createDecoderState } from "../src/decoder-state.js";
import { decodeBinaryFrame, decodeBinaryFrameStructural } from "../src/decoder.js";

function cloneJson(value) {
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
}

export function normalizeForDisplay(value) {
  if (typeof value === "bigint") return `${value}n`;
  if (Array.isArray(value)) return value.map(normalizeForDisplay);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().filter((key) => value[key] !== undefined).map((key) => [key, normalizeForDisplay(value[key])]));
  }
  return value;
}

function snapshot(value) {
  return JSON.stringify(normalizeForDisplay(value));
}

function equivalent(actual, expected) {
  if (typeof actual === "bigint" && typeof expected === "number" && Number.isSafeInteger(expected)) return actual === BigInt(expected);
  if (Array.isArray(expected)) return Array.isArray(actual) && actual.length === expected.length && expected.every((item, index) => equivalent(actual[index], item));
  if (expected !== null && typeof expected === "object") return actual !== null && typeof actual === "object" && Object.keys(expected).every((key) => Object.hasOwn(actual, key) && equivalent(actual[key], expected[key]));
  return Object.is(actual, expected);
}

function bytesFromHex(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let index = 0; index < bytes.length; index += 1) bytes[index] = Number.parseInt(hex.slice(index * 2, index * 2 + 2), 16);
  return bytes;
}

function fixtureAnchor(context) {
  if (context?.profile !== "pcm-audio") return null;
  const previousKeys = ["previous_first_sample_sequence", "previous_sample_count", "previous_first_timestamp_us", "previous_last_timestamp_us"];
  if (previousKeys.some((key) => Object.hasOwn(context, key))) return null;
  const sequencePresent = Object.hasOwn(context, "session_anchor_sequence");
  const timestampPresent = Object.hasOwn(context, "session_anchor_timestamp_us");
  if (!sequencePresent || !timestampPresent || !Number.isSafeInteger(context.session_anchor_sequence) || context.session_anchor_sequence < 0 || !Number.isSafeInteger(context.session_anchor_timestamp_us) || context.session_anchor_timestamp_us < 0) {
    throw new ProtocolError("invalid_message", "invalid fresh PCM fixture anchor");
  }
  return Object.freeze({ sequence: BigInt(context.session_anchor_sequence), timestampUs: BigInt(context.session_anchor_timestamp_us) });
}

function createVectorDecoderState(context) {
  if (context === undefined) return { state: null, fixtureAnchor: null };
  const expectedAnchor = fixtureAnchor(context);
  const normalized = cloneJson(context);
  const hasPrevious = ["previous_first_sample_sequence", "previous_sample_count", "previous_first_timestamp_us", "previous_last_timestamp_us"].some((key) => Object.hasOwn(normalized, key));
  // A fresh fixture records the expected anchor, while the public state API
  // derives the active anchor from the first accepted frame.
  if (normalized.profile === "pcm-audio" && !hasPrevious) {
    delete normalized.session_anchor_sequence;
    delete normalized.session_anchor_timestamp_us;
  }
  return { state: createDecoderState(normalized), fixtureAnchor: expectedAnchor };
}

function requireFixtureAnchor(decoded, nextState, expectedAnchor) {
  if (expectedAnchor === null) return;
  const checks = [
    [decoded.first_sample_sequence, expectedAnchor.sequence],
    [decoded.first_timestamp_us, expectedAnchor.timestampUs],
    [nextState.anchor?.sequence, expectedAnchor.sequence],
    [nextState.anchor?.timestampUs, expectedAnchor.timestampUs],
  ];
  if (checks.some(([actual, expected]) => !equivalent(actual, expected))) {
    throw new ProtocolError("invalid_message", "fresh PCM fixture anchor mismatch");
  }
}

function executeBusyScenario(context, result) {
  if (context?.scenario !== "second_client_busy") return;
  const owner = cloneJson(context.connection_a);
  const requester = cloneJson(context.connection_b);
  parseControlMessageText(JSON.stringify(context.request), "client_to_server", { state: requester.state.toUpperCase(), owns_stream: requester.owns_stream });
  if (owner.state !== "streaming" || owner.owns_stream !== true || result.type !== "error" || result.code !== "busy") {
    throw new ProtocolError("invalid_message", "invalid busy ownership scenario");
  }
  if (!equivalent(owner, context.connection_a) || owner.state !== context.postcondition.connection_a_state || owner.owns_stream !== context.postcondition.connection_a_owns_stream) {
    throw new ProtocolError("invalid_message", "busy displaced owner");
  }
}

function runControl(vector) {
  const controlState = { context: cloneJson(vector.context), published: [] };
  const before = snapshot(controlState);
  try {
    const actual = Object.hasOwn(vector, "message_hex")
      ? parseControlMessageBytes(bytesFromHex(vector.message_hex), vector.direction, controlState.context)
      : parseControlMessageText(typeof vector.message === "string" ? vector.message : JSON.stringify(vector.message), vector.direction, controlState.context);
    executeBusyScenario(controlState.context, actual);
    return { actual, stateUnchanged: before === snapshot(controlState) };
  } catch (error) {
    return { error, stateUnchanged: before === snapshot(controlState) };
  }
}

function runCapabilities(vector) {
  const state = { document: cloneJson(vector.document), published: [] };
  const before = snapshot(state);
  try {
    return { actual: validateCapabilities(state.document), stateUnchanged: before === snapshot(state) };
  } catch (error) {
    return { error, stateUnchanged: before === snapshot(state) };
  }
}

export function runBinaryVector(vector, profile) {
  let state = null;
  let before = "";
  try {
    const prepared = createVectorDecoderState(vector.context);
    state = prepared.state;
    before = snapshot(state);
    const bytes = bytesFromHex(vector.frame_hex);
    const result = vector.context
      ? decodeBinaryFrame(bytes.buffer, state)
      : decodeBinaryFrameStructural(bytes.buffer, profile);
    requireFixtureAnchor(result.decoded, result.nextState, prepared.fixtureAnchor);
    return { actual: result.decoded, stateUnchanged: before === snapshot(state) };
  } catch (error) {
    return { error, stateUnchanged: state === null || before === snapshot(state) };
  }
}

function categoryRunner(category, vector, profile) {
  if (category === "control") return runControl(vector);
  if (category === "capabilities") return runCapabilities(vector);
  return runBinaryVector(vector, profile);
}

export function runVectorDocuments(entries) {
  const results = [];
  for (const entry of entries) {
    for (const vector of entry.document.vectors) {
      const outcome = categoryRunner(entry.category, vector, entry.document.profile);
      const actualError = outcome.error instanceof ProtocolError ? outcome.error.code : outcome.error ? "internal_error" : undefined;
      const resultMatches = vector.expected_valid
        ? outcome.error === undefined && equivalent(outcome.actual, vector.expected_decoded)
        : actualError === vector.expected_error;
      const stateMatches = vector.expected_valid || outcome.stateUnchanged;
      const pass = resultMatches && stateMatches;
      const detail = pass ? "" : [
        resultMatches ? "" : vector.expected_valid ? "decoded subset mismatch" : "error mismatch",
        stateMatches ? "" : "invalid vector mutated state",
        outcome.error && !(outcome.error instanceof ProtocolError) ? String(outcome.error) : "",
      ].filter(Boolean).join("; ");
      results.push(Object.freeze({
        name: vector.name, category: entry.category, expectedValid: vector.expected_valid,
        actualValid: outcome.error === undefined, expectedError: vector.expected_error,
        actualError, expectedDecoded: vector.expected_decoded,
        actualDecoded: outcome.actual, stateUnchanged: outcome.stateUnchanged, pass, detail,
      }));
    }
  }
  const categories = ["control", "capabilities", "V/I", "PCM"];
  const summaries = Object.fromEntries(categories.map((category) => {
    const categoryResults = results.filter((result) => result.category === category);
    return [category, Object.freeze({ total: categoryResults.length, pass: categoryResults.filter((result) => result.pass).length, fail: categoryResults.filter((result) => !result.pass).length })];
  }));
  return Object.freeze({ results: Object.freeze(results), summaries: Object.freeze(summaries), total: results.length, pass: results.filter((result) => result.pass).length, fail: results.filter((result) => !result.pass).length });
}
