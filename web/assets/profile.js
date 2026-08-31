(() => {
  "use strict";
  if (document.body.dataset.page !== "afk") return;

  const KEY = "osrs-profit-finder.player-profile.v1";
  const gp = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
  const sid = value => String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  const defaults = () => ({
    version: 1,
    members: true,
    skills: { cooking: 1, magic: 1, agility: 1, herblore: 1, crafting: 1, fishing: 1, mining: 1, woodcutting: 1, construction: 1 },
    equipment: [], unlocks: [], quests: [], diaries: [], pohFeatures: [],
    methodSettings: { cooking: { location: "range" } },
    filters: { onlyAvailable: false, autoBestVariant: true, showUnavailable: true },
  });
  const load = () => {
    try {
      const stored = JSON.parse(localStorage.getItem(KEY) || "{}");
      return { ...defaults(), ...stored, skills: { ...defaults().skills, ...(stored.skills || {}) }, methodSettings: { ...defaults().methodSettings, ...(stored.methodSettings || {}) }, filters: { ...defaults().filters, ...(stored.filters || {}) } };
    } catch (_) { return defaults(); }
  };
  const save = value => { try { localStorage.setItem(KEY, JSON.stringify(value)); } catch (_) {} };
  let profile = load();
  let methods = [];

  const has = (collection, value) => new Set((profile[collection] || []).map(sid)).has(sid(value));
  const requiredSkillMap = requirements => {
    const result = { ...((requirements || {}).skills || {}) };
    Object.entries(requirements || {}).forEach(([key, value]) => {
      if (Object.prototype.hasOwnProperty.call(profile.skills, key) && Number.isFinite(Number(value))) result[key] = Number(value);
    });
    return result;
  };

  function availability(method) {
    const req = method.requirements || {};
    const missing = [];
    if (req.members && !profile.members) missing.push("Membership");
    Object.entries(requiredSkillMap(req)).forEach(([skill, level]) => {
      if (Number(profile.skills[skill] || 1) < Number(level)) missing.push(`${level} ${skill[0].toUpperCase()}${skill.slice(1)}`);
    });
    for (const [key, label] of [["equipment", "Equipment"], ["unlocks", "Unlock"], ["quests", "Quest"], ["diaries", "Diary"], ["pohFeatures", "POH"]]) {
      const sourceKey = key === "pohFeatures" ? (req.pohFeatures ? "pohFeatures" : "poh_features") : key;
      (req[sourceKey] || []).forEach(value => { if (!has(key, value)) missing.push(`${label}: ${value}`); });
    }
    return { available: missing.length === 0, missing };
  }

  function accountPanel() {
    const existing = document.querySelector("#my-account-panel");
    if (existing) return existing;
    const anchor = document.querySelector(".filter-frame");
    if (!anchor) return null;
    const panel = document.createElement("section");
    panel.id = "my-account-panel";
    panel.className = "account-panel";
    panel.innerHTML = `
      <details><summary><strong>My Account</strong> <span class="muted">stored only in this browser</span></summary>
        <div class="account-grid">
          <label class="checkbox-field"><input data-profile="members" type="checkbox" ${profile.members ? "checked" : ""}><span>Members</span></label>
          ${Object.keys(profile.skills).map(skill => `<label class="field"><span>${skill[0].toUpperCase()}${skill.slice(1)}</span><input data-profile-skill="${skill}" type="number" min="1" max="99" value="${Number(profile.skills[skill] || 1)}"></label>`).join("")}
        </div>
        <h3>Equipment</h3><div class="account-checks">
          ${[
            ["cooking_gauntlets","Cooking gauntlets"],["cooking_cape","Cooking cape"],
            ["prescription_goggles","Prescription goggles"],["amulet_of_chemistry","Amulet of chemistry"],
            ["water_rune_supplying_staff","Water-rune supplying staff"],["earth_rune_supplying_staff","Earth-rune supplying staff"],
            ["fire_rune_supplying_staff","Fire-rune supplying staff"],["air_rune_supplying_staff","Air-rune supplying staff"],
            ["mud_battlestaff_or_equivalent","Mud battlestaff or equivalent"],["lava_battlestaff_or_equivalent","Lava battlestaff or equivalent"],
            ["fish_barrel","Fish barrel"],["radas_blessing_4","Rada's blessing 4"]
          ].map(([id,label]) => `<label><input data-profile-set="equipment" value="${id}" type="checkbox" ${has("equipment", id) ? "checked" : ""}> ${label}</label>`).join("")}
        </div>
        <h3>Spellbooks and POH</h3><div class="account-checks">
          ${[["unlocks","ancient_spellbook","Ancient"],["unlocks","lunar_spellbook","Lunar"],["unlocks","arceuus_spellbook","Arceuus"],["pohFeatures","oak_lectern","Oak lectern"],["pohFeatures","eagle_lectern","Eagle lectern"],["pohFeatures","teak_eagle_lectern","Teak eagle lectern"],["pohFeatures","mahogany_eagle_lectern","Mahogany eagle lectern"],["pohFeatures","marble_lectern","Marble lectern"],["pohFeatures","restoration_pool","Restoration pool"]].map(([set,id,label]) => `<label><input data-profile-set="${set}" value="${id}" type="checkbox" ${has(set, id) ? "checked" : ""}> ${label}</label>`).join("")}
        </div>
        <h3>Quest access</h3><div class="account-checks">
          ${[["desert_treasure_i","Desert Treasure I"],["lunar_diplomacy","Lunar Diplomacy"]].map(([id,label]) => `<label><input data-profile-set="quests" value="${id}" type="checkbox" ${has("quests", id) ? "checked" : ""}> ${label}</label>`).join("")}
        </div>
        <h3>Cooking setup</h3><label class="field"><span>Location</span><select data-profile-cooking="location"><option value="fire">Fire</option><option value="range">Range</option><option value="hosidius_5">Hosidius 5%</option><option value="hosidius_10">Hosidius 10%</option></select></label>
        <h3>Personalisation</h3><div class="account-checks">
          <label><input data-profile-filter="onlyAvailable" type="checkbox" ${profile.filters.onlyAvailable ? "checked" : ""}> Only methods I can perform</label>
          <label><input data-profile-filter="autoBestVariant" type="checkbox" ${profile.filters.autoBestVariant ? "checked" : ""}> Automatically use my best available variant</label>
          <label><input data-profile-filter="showUnavailable" type="checkbox" ${profile.filters.showUnavailable ? "checked" : ""}> Show unavailable methods</label>
        </div>
      </details>`;
    anchor.parentNode.insertBefore(panel, anchor);
    const location = panel.querySelector('[data-profile-cooking="location"]');
    if (location) location.value = profile.methodSettings?.cooking?.location || "range";
    return panel;
  }

  function syncLegacySkills() {
    document.querySelectorAll(".skill-level[data-skill]").forEach(input => {
      if (profile.skills[input.dataset.skill] != null) input.value = profile.skills[input.dataset.skill];
    });
  }

  function applyToRecords() {
    const byId = new Map(methods.map(method => [method.methodId, method]));
    const records = [...document.querySelectorAll("#afk-list [data-method-id]")];
    const groups = new Map();
    records.forEach(record => {
      const method = byId.get(record.dataset.methodId);
      if (!method) return;
      const state = availability(method);
      record.dataset.profileAvailable = state.available ? "true" : "false";
      record.querySelector(".profile-availability")?.remove();
      const marker = document.createElement("span");
      marker.className = `profile-availability ${state.available ? "available" : "unavailable"}`;
      marker.textContent = state.available ? "Available for my account" : `Unavailable: ${state.missing.join(", ")}`;
      record.querySelector(".detail-panel")?.prepend(marker);

      const base = method.baseMethodId || method.methodId;
      if (!groups.has(base)) groups.set(base, []);
      groups.get(base).push({ record, method, state });

      const cooking = method.model?.cooking;
      if (cooking && window.OsrsCookingMath) {
        record.querySelector(".profile-cooking-result")?.remove();
        const gauntlets = has("equipment", "cooking_gauntlets"), cape = has("equipment", "cooking_cape");
        const success = window.OsrsCookingMath.successProbability(cooking, profile.skills.cooking, profile.methodSettings?.cooking?.location || "range", gauntlets, cape);
        const rate = Number(method.mechanics?.cyclesPerHour || 0), raw = method.inputs?.[0], cooked = method.outputs?.[0];
        const profit = ((Number(cooked?.geNetPerItem ?? cooked?.gePrice ?? 0) * success) - Number(raw?.gePrice ?? raw?.price ?? 0)) * rate;
        const result = document.createElement("div");
        result.className = "profile-cooking-result";
        result.textContent = `My setup: ${(success * 100).toFixed(1)}% success · ${gp.format(rate * success)} cooked/h · ${gp.format(profit)} gp/h`;
        record.querySelector(".detail-panel")?.prepend(result);
      }
    });

    groups.forEach(rows => {
      let selected = null;
      if (profile.filters.autoBestVariant) {
        selected = rows.filter(row => row.state.available).sort((a, b) => {
          const expected = Number(b.method.scenarios?.expectedGpPerHour ?? -Infinity) - Number(a.method.scenarios?.expectedGpPerHour ?? -Infinity);
          if (Number.isFinite(expected) && expected !== 0) return expected;
          return Number(b.method.mechanics?.cyclesPerHour || 0) - Number(a.method.mechanics?.cyclesPerHour || 0);
        })[0] || null;
      }
      rows.forEach(row => {
        const hideUnavailable = !row.state.available && (profile.filters.onlyAvailable || !profile.filters.showUnavailable);
        const hideVariant = selected && row !== selected;
        row.record.style.display = hideUnavailable || hideVariant ? "none" : "";
      });
    });
  }

  document.addEventListener("change", event => {
    const target = event.target;
    if (target.matches("[data-profile-skill]")) profile.skills[target.dataset.profileSkill] = Math.max(1, Math.min(99, Number(target.value || 1)));
    else if (target.matches('[data-profile="members"]')) profile.members = target.checked;
    else if (target.matches("[data-profile-set]")) {
      const key = target.dataset.profileSet, values = new Set(profile[key] || []), value = sid(target.value);
      target.checked ? values.add(value) : values.delete(value); profile[key] = [...values];
    } else if (target.matches("[data-profile-filter]")) profile.filters[target.dataset.profileFilter] = target.checked;
    else if (target.matches("[data-profile-cooking]")) profile.methodSettings.cooking[target.dataset.profileCooking] = target.value;
    else return;
    save(profile); syncLegacySkills(); applyToRecords();
  });

  const style = document.createElement("style");
  style.textContent = ".account-panel{margin:14px 0;padding:12px;border:1px solid rgba(91,73,53,.45);background:rgba(234,217,173,.22)}.account-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}.account-checks{display:flex;flex-wrap:wrap;gap:8px 16px;margin:8px 0 14px}.profile-availability,.profile-cooking-result{display:block;margin:6px 0;padding:5px 8px;border-left:3px solid currentColor}.profile-availability.unavailable{opacity:.75}@media(max-width:760px){.account-grid{grid-template-columns:1fr 1fr}}";
  document.head.appendChild(style);

  accountPanel(); syncLegacySkills();
  fetch("data/afk.json", { cache: "no-store" }).then(response => response.ok ? response.json() : Promise.reject()).then(data => {
    methods = data.methods || [];
    applyToRecords();
    const list = document.querySelector("#afk-list");
    if (list) new MutationObserver(applyToRecords).observe(list, { childList: true, subtree: false });
  }).catch(() => {});
})();
