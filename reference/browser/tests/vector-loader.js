// SPDX-License-Identifier: Apache-2.0

const VECTOR_SOURCES = Object.freeze([
  ["control", "../../../test-vectors/control-messages.json"],
  ["capabilities", "../../../test-vectors/capabilities.json"],
  ["public-status", "../../../test-vectors/public-status.json"],
  ["V/I", "../../../test-vectors/vi-frames.json"],
  ["PCM", "../../../test-vectors/pcm-audio-frames.json"],
]);

export async function loadVectorDocuments() {
  const entries = await Promise.all(VECTOR_SOURCES.map(async ([category, url]) => {
    const response = await fetch(new URL(url, import.meta.url), { cache: "no-store" });
    if (!response.ok) throw new Error(`cannot load ${url}: HTTP ${response.status}`);
    return Object.freeze({ category, source: url, document: await response.json() });
  }));
  return Object.freeze(entries);
}
