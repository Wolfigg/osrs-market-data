import fs from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { successProbability } = require("../web/assets/cooking_math.js");
const fixtures = JSON.parse(fs.readFileSync(new URL("./fixtures/cooking_parity.json", import.meta.url), "utf8"));

for (const fixture of fixtures) {
  const actual = successProbability(fixture.model, fixture.level, fixture.location, fixture.gauntlets, fixture.cookingCape);
  if (Math.abs(actual - fixture.expected) > 1e-12) {
    throw new Error(`${fixture.name}: expected ${fixture.expected}, got ${actual}`);
  }
}
console.log(`Cooking parity: ${fixtures.length} fixtures passed`);
