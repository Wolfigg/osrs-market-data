(() => {
  "use strict";
  if (document.body.dataset.page !== "afk") return;
  const KEY = "osrs-profit-finder.cooking-profile.v1";
  const gp = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
  let methods = [];
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (_) { return {}; } };
  const save = value => localStorage.setItem(KEY, JSON.stringify(value));

  function chance(model, level, location, gauntlets, cape) {
    level = Math.max(Number(model.minimumLevel || 1), Math.min(99, Number(level || 1)));
    if (cape && level >= 99) return 1;
    let key = location || "range";
    if (gauntlets && model.gauntletsAffected && model.curves?.[`gauntlets_${key}`]) key = `gauntlets_${key}`;
    const curve = model.curves?.[key] || model.curves?.range;
    if (!curve) return 1;
    return Math.max(0, Math.min(1, (Number(curve.low) + (Number(curve.high) - Number(curve.low)) * (level - 1) / 98) / 256));
  }

  function html(method) {
    const model = method.model?.cooking;
    const p = load();
    const level = Number(p.level || model.defaults?.level || 99), location = p.location || model.defaults?.location || "range";
    const gauntlets = p.gauntlets ?? model.defaults?.gauntlets ?? false, cape = p.cookingCape ?? model.defaults?.cookingCape ?? false;
    const success = chance(model, level, location, gauntlets, cape), rate = Number(method.mechanics?.cyclesPerHour || 0);
    const raw = method.inputs?.[0], cooked = method.outputs?.[0];
    const gpHour = ((Number(cooked?.geNetPerItem ?? cooked?.gePrice ?? 0) * success) - Number(raw?.price || 0)) * rate;
    return `<div class="cooking-calculator"><h3>My cooking setup</h3><div class="cooking-grid"><label>Cooking level<input data-cooking="level" type="number" min="1" max="99" value="${level}"></label><label>Location<select data-cooking="location"><option value="fire" ${location === "fire" ? "selected" : ""}>Fire</option><option value="range" ${location === "range" ? "selected" : ""}>Range</option><option value="hosidius_5" ${location === "hosidius_5" ? "selected" : ""}>Hosidius 5%</option><option value="hosidius_10" ${location === "hosidius_10" ? "selected" : ""}>Hosidius 10%</option></select></label><label class="cooking-check"><input data-cooking="gauntlets" type="checkbox" ${gauntlets ? "checked" : ""} ${model.gauntletsAffected ? "" : "disabled"}> Cooking gauntlets</label><label class="cooking-check"><input data-cooking="cookingCape" type="checkbox" ${cape ? "checked" : ""}> Cooking cape at 99</label></div><div class="cooking-result"><strong>${(success * 100).toFixed(1)}% cook chance</strong><span>${gp.format(rate * success)} cooked/h</span><span>${gp.format(rate * (1 - success))} burnt/h</span><span>${gp.format(gpHour)} gp/h at current prices</span></div><p class="muted">Local calculator only. It recalculates burn probability from the catalogue's Wiki success-curve parameters without changing market prices.</p></div>`;
  }

  function enhance() {
    const map = new Map(methods.map(m => [m.methodId, m]));
    document.querySelectorAll("#afk-list [data-method-id]").forEach(record => {
      const method = map.get(record.dataset.methodId);
      if (!method?.model?.cooking || record.querySelector(".cooking-calculator")) return;
      record.querySelector(".detail-panel")?.insertAdjacentHTML("beforeend", html(method));
    });
  }

  document.addEventListener("change", event => {
    const field = event.target.closest("[data-cooking]"); if (!field) return;
    const box = field.closest(".cooking-calculator"), record = field.closest("[data-method-id]");
    const method = methods.find(m => m.methodId === record?.dataset.methodId); if (!box || !method) return;
    save({level: Number(box.querySelector('[data-cooking="level"]').value || 1), location: box.querySelector('[data-cooking="location"]').value, gauntlets: box.querySelector('[data-cooking="gauntlets"]').checked, cookingCape: box.querySelector('[data-cooking="cookingCape"]').checked});
    box.outerHTML = html(method);
  });

  const style = document.createElement("style");
  style.textContent = ".cooking-calculator{margin:14px 0;padding:12px;border:1px solid rgba(91,73,53,.45);background:rgba(234,217,173,.35)}.cooking-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.cooking-grid label{display:flex;flex-direction:column;gap:4px;font-weight:700}.cooking-grid input,.cooking-grid select{padding:7px}.cooking-grid .cooking-check{flex-direction:row;align-items:center}.cooking-result{display:flex;flex-wrap:wrap;gap:12px;margin-top:10px}.cooking-result span{padding-left:12px;border-left:1px solid rgba(91,73,53,.35)}@media(max-width:760px){.cooking-grid{grid-template-columns:1fr 1fr}}";
  document.head.appendChild(style);
  fetch("data/afk.json", {cache:"no-store"}).then(r => r.ok ? r.json() : Promise.reject()).then(data => { methods = data.methods || []; enhance(); const list = document.querySelector("#afk-list"); if (list) new MutationObserver(enhance).observe(list,{childList:true,subtree:false}); }).catch(() => {});
})();
