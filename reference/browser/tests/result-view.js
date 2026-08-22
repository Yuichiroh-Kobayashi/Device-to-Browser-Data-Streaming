// SPDX-License-Identifier: Apache-2.0

import { normalizeForDisplay } from "./vector-runner.js";

function text(value) {
  if (value === undefined) return "";
  return typeof value === "string" ? value : JSON.stringify(normalizeForDisplay(value));
}

function addCell(row, value) {
  const cell = document.createElement("td");
  cell.textContent = text(value);
  row.append(cell);
}

export function renderResults(target, run, selfTests, metadata) {
  target.replaceChildren();
  const metadataList = document.createElement("dl");
  for (const [label, value] of Object.entries(metadata)) {
    const term = document.createElement("dt");
    term.textContent = label;
    const definition = document.createElement("dd");
    definition.textContent = String(value);
    metadataList.append(term, definition);
  }
  target.append(metadataList);

  const summary = document.createElement("pre");
  summary.textContent = [`Golden vectors ${run.pass}/${run.total}`, ...["control", "capabilities", "public-status", "V/I", "PCM"].map((category) => `${category}: ${run.summaries[category].pass}/${run.summaries[category].total}`), `total: ${run.pass}/${run.total}`, `FAIL: ${run.fail}`, "", `Parser-core self-tests ${selfTests.fail === 0 ? "all PASS" : `${selfTests.pass}/${selfTests.total}`}`, `count: ${selfTests.pass}/${selfTests.total}`, `FAIL: ${selfTests.fail}`].join("\n");
  target.append(summary);

  const selfTestList = document.createElement("ul");
  for (const result of selfTests.results) {
    const item = document.createElement("li");
    item.textContent = `${result.pass ? "PASS" : "FAIL"}: ${result.name}${result.detail ? ` — ${result.detail}` : ""}`;
    selfTestList.append(item);
  }
  target.append(selfTestList);

  const table = document.createElement("table");
  const header = document.createElement("tr");
  ["vector name", "category", "expected valid", "actual valid", "expected error", "actual error", "expected decoded subset", "actual decoded values", "PASS/FAIL", "failure detail"].forEach((label) => {
    const cell = document.createElement("th");
    cell.textContent = label;
    header.append(cell);
  });
  table.append(header);
  for (const result of run.results) {
    const row = document.createElement("tr");
    row.className = result.pass ? "pass" : "fail";
    addCell(row, result.name);
    addCell(row, result.category);
    addCell(row, result.expectedValid ? "valid" : "invalid");
    addCell(row, result.actualValid ? "valid" : "invalid");
    addCell(row, result.expectedError);
    addCell(row, result.actualError);
    addCell(row, result.expectedDecoded);
    addCell(row, result.actualDecoded);
    addCell(row, result.pass ? "PASS" : "FAIL");
    addCell(row, result.detail || (result.expectedValid ? "" : `state unchanged: ${result.stateUnchanged}`));
    table.append(row);
  }
  target.append(table);
}
