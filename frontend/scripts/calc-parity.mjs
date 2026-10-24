// Runs every case in backend/tests/calc_cases.json through the TypeScript engine and compares with the Python result.
// node --experimental-strip-types scripts/calc-parity.mjs
import { readFileSync } from "node:fs";
import { makeEngine } from "../src/calc/engine.ts";

const tools = JSON.parse(readFileSync(new URL("../src/shared/tools.json", import.meta.url)));
const constants = JSON.parse(readFileSync(new URL("../src/shared/constants.json", import.meta.url)));
const cases = JSON.parse(readFileSync(new URL("../../backend/tests/calc_cases.json", import.meta.url)));
const E = makeEngine(tools, constants);

function same(a, b, path, errs) {
  if (typeof a === "number" && typeof b === "number") {
    const tol = Math.max(1e-9, Math.abs(b) * 1e-9);
    if (Math.abs(a - b) > tol) errs.push(`${path}: ts=${a} py=${b}`);
    return;
  }
  if (Array.isArray(b)) {
    if (!Array.isArray(a) || a.length !== b.length) { errs.push(`${path}: length ts=${a?.length} py=${b.length}`); return; }
    b.forEach((x, i) => same(a[i], x, `${path}[${i}]`, errs));
    return;
  }
  if (b && typeof b === "object") {
    if (!a || typeof a !== "object") { errs.push(`${path}: ts=${JSON.stringify(a)} py=object`); return; }
    const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
    for (const k of keys) {
      if ((a[k] === null || a[k] === undefined) && (b[k] === null || b[k] === undefined)) continue;
      same(a[k], b[k], `${path}.${k}`, errs);
    }
    return;
  }
  if (a !== b) errs.push(`${path}: ts=${JSON.stringify(a)} py=${JSON.stringify(b)}`);
}

let fails = 0;
for (const c of cases) {
  let res;
  try { res = E.run(c.slug, c.inputs); } catch (e) { console.log(`✗ ${c.slug} ${JSON.stringify(c.inputs)} threw ${e.message}`); fails += 1; continue; }
  const errs = [];
  same(JSON.parse(JSON.stringify(res)), c.result, c.slug, errs);
  if (errs.length) { fails += 1; console.log(`✗ ${c.slug} ${JSON.stringify(c.inputs)}\n   ${errs.slice(0, 6).join("\n   ")}`); }
}
console.log(`${cases.length - fails}/${cases.length} cases match`);
process.exit(fails ? 1 : 0);
