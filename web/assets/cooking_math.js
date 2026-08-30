((root, factory) => {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.OsrsCookingMath = api;
})(typeof globalThis !== "undefined" ? globalThis : this, () => {
  "use strict";

  function successProbability(model, level, location, gauntlets, cookingCape) {
    const minimum = Number(model?.minimumLevel || 1);
    level = Math.max(minimum, Math.min(99, Number(level || 1)));
    if (cookingCape && level >= 99) return 1;
    let key = String(location || "range");
    if (gauntlets && model?.gauntletsAffected && model?.curves?.[`gauntlets_${key}`]) key = `gauntlets_${key}`;
    const curve = model?.curves?.[key] || model?.curves?.range;
    if (!curve) return 1;
    const low = Number(curve.low), high = Number(curve.high);
    const value = Math.floor(low * (99 - level) / 98 + high * (level - 1) / 98 + 0.5) + 1;
    return Math.max(0, Math.min(1, value / 256));
  }

  return { successProbability };
});
