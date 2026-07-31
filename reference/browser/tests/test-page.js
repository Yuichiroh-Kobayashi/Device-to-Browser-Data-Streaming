// SPDX-License-Identifier: Apache-2.0

import { loadVectorDocuments } from "./vector-loader.js";
import { runParserCoreSelfTests } from "./parser-core-self-tests.js";
import { runVectorDocuments } from "./vector-runner.js";
import { renderResults } from "./result-view.js";

function browserNameVersion() {
  const brands = navigator.userAgentData?.brands;
  if (Array.isArray(brands) && brands.length) return brands.map((brand) => `${brand.brand} ${brand.version}`).join(", ");
  const match = navigator.userAgent.match(/(?:Edg|Chrome|Version)\/([0-9.]+)/);
  if (match) return `${navigator.userAgent.includes("Edg/") ? "Edge" : navigator.userAgent.includes("Chrome/") ? "Chrome" : "Browser"} ${match[1]}`;
  return "not reliably derivable";
}

function osIndication() {
  if (navigator.userAgentData?.platform) return navigator.userAgentData.platform;
  if (/Windows NT/.test(navigator.userAgent)) return "Windows";
  if (/iPad|iPhone|Mac OS X/.test(navigator.userAgent)) return "Apple platform";
  if (/Linux/.test(navigator.userAgent)) return "Linux";
  return "not reliably derivable";
}

const root = document.querySelector("#results");
const started = performance.now();
try {
  const documents = await loadVectorDocuments();
  const run = runVectorDocuments(documents);
  const selfTests = runParserCoreSelfTests(documents);
  await new Promise((resolve) => setTimeout(resolve, 0));
  const diagnostics = window.__d2bDiagnostics ?? { errors: [] };
  renderResults(root, run, selfTests, {
    "navigator.userAgent": navigator.userAgent,
    "browser name/version": browserNameVersion(),
    "OS indication": osIndication(),
    URL: location.href,
    "vector count": run.total,
    "parser-core self-test count": selfTests.total,
    PASS: run.pass,
    FAIL: run.fail,
    "execution time": `${(performance.now() - started).toFixed(1)} ms`,
    "window error/unhandled rejection summary": diagnostics.errors.length ? diagnostics.errors.join(" | ") : "none",
  });
} catch (error) {
  root.textContent = `Harness initialization failed: ${error?.stack || error}`;
  throw error;
}
