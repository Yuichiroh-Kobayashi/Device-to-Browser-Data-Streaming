// SPDX-License-Identifier: Apache-2.0

import { validateCapabilities } from "../src/capabilities-validator.js";
import { parseControlMessageText } from "../src/control-parser.js";
import { cloneDecoderState, createDecoderState } from "../src/decoder-state.js";
import { decodeBinaryFrame } from "../src/decoder.js";
import { ProtocolError } from "../src/errors.js";
import { validatePublicStatus } from "../src/public-status-validator.js";
import { runBinaryVector, runVectorDocuments } from "./vector-runner.js";

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function bytesFromHex(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let index = 0; index < bytes.length; index += 1) bytes[index] = Number.parseInt(hex.slice(index * 2, index * 2 + 2), 16);
  return bytes;
}

function contextWithoutPrevious(context) {
  const fresh = cloneJson(context);
  for (const key of [
    "previous_first_sample_sequence", "previous_sample_count", "previous_first_timestamp_us", "previous_last_timestamp_us",
    "session_anchor_sequence", "session_anchor_timestamp_us",
  ]) delete fresh[key];
  return fresh;
}

function documentFor(entries, category) {
  const entry = entries.find((candidate) => candidate.category === category);
  if (!entry) throw new Error(`missing ${category} vector document`);
  return entry.document;
}

function firstFreshValidFrame(document) {
  const vector = document.vectors.find((candidate) => candidate.expected_valid && candidate.context &&
    !Object.hasOwn(candidate.context, "previous_first_sample_sequence") && candidate.expected_decoded?.stream_start === true);
  if (!vector) throw new Error("missing fresh valid frame fixture");
  return vector;
}

function firstValidCapabilitiesWithVi(document) {
  const vector = document.vectors.find((candidate) => candidate.expected_valid && candidate.document?.streams.some((stream) =>
    stream.profiles.some((descriptor) => descriptor.profile === "vi-measurement")));
  if (!vector) throw new Error("missing valid V/I capabilities fixture");
  return vector.document;
}

function expectProtocolError(action, expectedCode) {
  try {
    action();
  } catch (error) {
    if (error instanceof ProtocolError && error.code === expectedCode) return;
    throw new Error(`expected ProtocolError(${expectedCode}), got ${error?.name || typeof error}(${error?.code || "no code"})`);
  }
  throw new Error(`expected ProtocolError(${expectedCode})`);
}

function runTest(name, action) {
  try {
    action();
    return Object.freeze({ name, pass: true, detail: "" });
  } catch (error) {
    return Object.freeze({ name, pass: false, detail: error?.stack || String(error) });
  }
}

/** Dependency-free parser-core regressions, distinct from the tracked golden vectors. */
export function runParserCoreSelfTests(entries) {
  const pcmVector = firstFreshValidFrame(documentFor(entries, "PCM"));
  const viVector = firstFreshValidFrame(documentFor(entries, "V/I"));
  const pcmContext = contextWithoutPrevious(pcmVector.context);
  const viContext = contextWithoutPrevious(viVector.context);
  const pcmBytes = bytesFromHex(pcmVector.frame_hex).buffer;
  const viBytes = bytesFromHex(viVector.frame_hex).buffer;
  const results = [];

  results.push(runTest("public status returns the same object without defaults", () => {
    const value = { protocol: "d2b-stream", version: "0.1", state: "idle", uptime_us: 0 };
    if (validatePublicStatus(value) !== value || Object.keys(value).length !== 4) throw new Error("public status was copied or defaulted");
  }));

  results.push(runTest("public status errors do not echo private values", () => {
    try {
      validatePublicStatus({ protocol: "d2b-stream", version: "0.1", state: "idle", uptime_us: 0, token: "secret-value" });
    } catch (error) {
      if (error instanceof ProtocolError && error.code === "invalid_public_status" && !String(error.message).includes("secret-value")) return;
      throw error;
    }
    throw new Error("private public-status field was accepted");
  }));

  results.push(runTest("fresh PCM state has anchor=null", () => {
    const state = createDecoderState(pcmContext);
    if (state.acceptedData !== false || state.previous !== null || state.anchor !== null || state.nextSegmentId !== 0) throw new Error("fresh PCM state is not canonical");
  }));

  results.push(runTest("first PCM frame establishes anchor", () => {
    const state = createDecoderState(pcmContext);
    const result = decodeBinaryFrame(pcmBytes, state);
    if (result.nextState.anchor?.sequence !== result.decoded.first_sample_sequence || result.nextState.anchor?.timestampUs !== result.decoded.first_timestamp_us) throw new Error("first PCM frame did not establish anchor");
  }));

  results.push(runTest("harness detects a fresh PCM fixture anchor mismatch", () => {
    const originalSnapshot = JSON.stringify(pcmVector.context);
    const modified = cloneJson(pcmVector);
    modified.context.session_anchor_timestamp_us += 1;
    const outcome = runBinaryVector(modified, "pcm-audio");
    if (!(outcome.error instanceof ProtocolError) || outcome.error.code !== "invalid_message") throw new Error("fixture anchor mismatch was not detected");
    const rerun = runVectorDocuments([{ category: "PCM", document: { profile: "pcm-audio", vectors: [modified] } }]);
    if (rerun.pass !== 0 || rerun.fail !== 1) throw new Error("fixture anchor mismatch did not make the vector fail");
    if (JSON.stringify(pcmVector.context) !== originalSnapshot) throw new Error("original fixture context was mutated");
  }));

  results.push(runTest("fresh PCM preloaded anchor is rejected", () => {
    expectProtocolError(() => createDecoderState(pcmVector.context), "invalid_state");
  }));

  results.push(runTest("malformed acceptedData/previous state is invalid_state", () => {
    const malformed = { ...createDecoderState(pcmContext), acceptedData: true, previous: null };
    expectProtocolError(() => decodeBinaryFrame(pcmBytes, malformed), "invalid_state");
  }));

  results.push(runTest("PCM previous sample count must be 256", () => {
    const first = decodeBinaryFrame(pcmBytes, createDecoderState(pcmContext));
    const malformed = cloneDecoderState(first.nextState);
    malformed.previous.sampleCount = 255n;
    expectProtocolError(() => decodeBinaryFrame(pcmBytes, malformed), "invalid_state");
  }));

  results.push(runTest("PCM previous timestamp must match anchor", () => {
    const first = decodeBinaryFrame(pcmBytes, createDecoderState(pcmContext));
    const malformed = cloneDecoderState(first.nextState);
    malformed.previous.firstTimestampUs += 2n;
    expectProtocolError(() => decodeBinaryFrame(pcmBytes, malformed), "invalid_state");
  }));

  results.push(runTest("V/I previous last timestamp cannot precede first", () => {
    const first = decodeBinaryFrame(viBytes, createDecoderState(viContext));
    const malformed = cloneDecoderState(first.nextState);
    malformed.previous.lastTimestampUs = malformed.previous.firstTimestampUs - 1n;
    expectProtocolError(() => decodeBinaryFrame(viBytes, malformed), "invalid_state");
  }));

  results.push(runTest("incomplete previous context is rejected", () => {
    const incomplete = { ...pcmContext, previous_last_timestamp_us: 0 };
    expectProtocolError(() => createDecoderState(incomplete), "invalid_state");
  }));

  results.push(runTest("welcome max_control_message_size rejects 2048.0", () => {
    const message = '{"type":"welcome","protocol":"d2b-stream","version":"0.1","max_control_message_size":2048.0,"max_binary_frame_size":65536,"session_state":"ready"}';
    expectProtocolError(() => parseControlMessageText(message, "server_to_client"), "invalid_message");
  }));

  results.push(runTest("capability parameter sets canonicalize negative zero", () => {
    const capabilities = cloneJson(firstValidCapabilitiesWithVi(documentFor(entries, "capabilities")));
    const descriptor = capabilities.streams.flatMap((stream) => stream.profiles).find((candidate) => candidate.profile === "vi-measurement");
    const duplicate = cloneJson(descriptor.parameter_sets[0]);
    duplicate.sample_rate.numerator = -0;
    descriptor.parameter_sets.push(duplicate);
    expectProtocolError(() => validateCapabilities(capabilities), "invalid_capabilities");
  }));

  results.push(runTest("profile payload validation precedes continuity", () => {
    const malformed = bytesFromHex(viVector.frame_hex);
    malformed[7] &= ~1;
    expectProtocolError(() => decodeBinaryFrame(malformed.slice(0, malformed.length - 1).buffer, createDecoderState(viContext)), "vi_payload_length_mismatch");
  }));

  const pass = results.filter((result) => result.pass).length;
  return Object.freeze({ results: Object.freeze(results), total: results.length, pass, fail: results.length - pass });
}
