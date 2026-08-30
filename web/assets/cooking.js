(() => {
  "use strict";
  if (document.body.dataset.page !== "afk") return;

  const STORAGE_KEY = "osrs-profit-finder.cooking-profile.v1";
  const gp = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
  const esc = value => String(value ?? "").replace(/[&<>'\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[c]);
  let methods = [];

  function profile() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"); }
    catch (_) { return {}; }
  }

  function save(next) { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); }

  function probability(model, level, location, gauntlets, cape) {
    const minimum = Number(model.minimumLevel || 1);
    level = Math.max(minimum, Math.min(99, Number(level || minimum)));
    if (cape && level >= 99) return 1;
    let key = location || "range";
    if (gauntlets && model.gauntletsAffected && model.curves?.[`gauntlets_${key}`]) key = `gauntlets_${key}`;
    const curve = model.curves?.[key] || model.curves?.range;
    if (!curve) return 1;
    const roll = Number(curve.low) + (Number(curve.high) - Number(curve.low)) * (level - 1) / 98;
    return Math.max(0, Math.min(1, roll / 256));
  }

  function calculator(method) {
    const model = method.model?.cooking;
    if (!model) return "";
    const saved = profile();
    const level = Number(saved.level || model.defaults?.level || 99);
    const location = saved.location || model.defaults?.location || "range";
    const gauntlets = saved.gauntlets ?? model.defaults?.gauntlets ?? false;
    const cape = saved.cookingCape ?? model.defaults?.cookingCape ?? false;
    const success = probability(model, level, location, gauntlets, cape);
    const raw = method.inputs?.[0];
    const cooked = method.outputs?.[0];
    const rate = Number(method.mechanics?.cyclesPerHour || 0);
    const rawCost = Number(raw?.price || 0);
    const sell = Number(cooked?.geNetPerItem ?? cooked?.gePrice ?? 0);
    const gpHour = (sell * success - rawCost) * rate;
    return `<div class="cooking-calculator" data-cooking-method="${esc(method.methodId)}"><h3>My cooking setup</h3><div class="cooking-grid"><label>Cooking level<input data-cooking-field="level" type="number" min="1" max="99" value="${level}"></label><label>Location<select data-cooking-field="location"><option value="fire" ${location === "fire" ? "selected" : ""}>Fire</option><option value="range" ${location === "range" ? "selected" : ""}>Range</option><option value="hosidius_5" ${location === "hosidius_5" ? "selected" : ""}>Hosidius 5%</option><option value="hosidius_10" ${location === "hosidius_10" ? "selected" : ""}>Hosidius 10%</option></select></label><label class="cooking-check"><input data-cooking-field="gauntlets" type="checkbox" ${gauntlets ? "checked" : ""} ${model.gauntletsAffected ? "" : "disabled"}> Cooking gauntlets</label><label class="cooking-check"><input data-cooking-field="cookingCape" type="checkbox" ${cape ? "checked" : ""}> Cooking cape at 99</label></div><div class="cooking-result"><strong>${(success * 100).toFixed(1)}% cook chance</strong><span>${gp.format(rate * success)} cooked/h</span><span>${gp.format(rate * (1 - success))} burnt/h</span><span>${gp.format(gpHour)} gp/h at current prices</span></div><p class="muted">This calculator changes only your local view. Market prices remain the same; burn probability is recalculated from the catalogue's Wiki success-curve parameters.</p></div>`;
  }

  function enhance() {
    const map = new Map(methods.map(m => [m.methodId, m]));
    document.querySelectorAll("#afk-list [data-method-id]").forEach(record => {
      const method = map.get(record.dataset.methodId);
      if (!method?.model?.cooking || record.querySelector(".cooking-calculator")) return;
      record.querySelector(".detail-panel")?.insertAdjacentHTML("beforeend", calculator(method));
    });
  }

  document.addEventListener("change", event => {
    const field = event.target.closest("[data-cooking-field]");
    if (!field) return;
    const box = field.closest(".cooking-calculator");
    const record = field.closest("[data-method-id]");
    const method = methods.find(m => m.methodId === record?.dataset.methodId);
    if (!box || !method) return;
    const next = {
      level: Number(box.querySelector('[data-cooking-field="level"]').value || 1),
      location: box.querySelector('[data-cooking-field="location"]').value,
      gauntlets: box.querySelector('[data-cooking-field="gauntlets"]').checked,
      cookingCape: box.querySelector('[data-cooking-field="cookingCape"]').checked,
    };
    save(next);
    box.outerHTML = calculator(method);
  });

  const style = document.createElement("style");
  style.textContent = ".cooking-calculator{margin:14px 0;padding:12px;border:1px solid rgba(91,73,53,.45);background:rgba(234,217,173,.35)}.cooking-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.cooking-grid label{display:flex;flex-direction:column;gap:4px;font-weight:700}.cooking-grid input,.cooking-grid select{padding:7px}.cooking-grid .cooking-check{flex-direction:row;align-items:center}.cooking-result{display:flex;flex-wrap:wrap;gap:12px;margin-top:10px}.cooking-result span{padding-left:12px;border-left:1px solid rgba(91,73,53,.35)}@media(max-width:760px){.cooking-grid{grid-template-columns:1fr 1fr}}";
  document.head.appendChild(style);

  fetch("data/afk.json", { cache: "no-store" }).then(r => r.ok ? r.json() : Promise.reject()).then(data => {
    methods = data.methods || [];
    enhance();
    const list = document.querySelector("#afk-list");
    if (list) new MutationObserver(enhance).observe(list, { childList: true, subtree: false });
  }).catch(() => {});
})();
