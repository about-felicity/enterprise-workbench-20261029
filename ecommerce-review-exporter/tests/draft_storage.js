const fs = require("fs");
const path = require("path");
const vm = require("vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
const start = source.indexOf("  function productInfo()");
const end = source.indexOf("  function extractReview(");
if (start < 0 || end < 0) throw new Error("Cannot locate draft helpers");

const data = {};
const context = {
  URL,
  Map,
  Date,
  platform: { id: "jd" },
  location: { href: "https://item.jd.com/100051315585.html" },
  document: { title: "JD product", querySelectorAll: () => [] },
  normalizeText: (value) => String(value || "").trim(),
  isVisible: () => true,
  maxInput: { value: "100" },
  state: { rows: new Map(), draftKey: "", storageError: "" },
  updateMetrics: () => {},
  setStatus: () => {},
  chrome: { storage: { local: {
    get: async (key) => ({ [key]: data[key] }),
    set: async (items) => Object.assign(data, items),
  } } },
};
vm.createContext(context);
vm.runInContext(`${source.slice(start, end)} globalThis.testDraft = { productInfo, saveDraft, restoreDraft };`, context);

(async () => {
  const row = { key: "review-1", productId: "100051315585", productTitle: "JD product", productUrl: context.location.href, content: "Useful review" };
  context.state.rows.set(row.key, row);
  await context.testDraft.saveDraft();
  context.state.rows.clear();
  context.location.href = `https://cfe.m.jd.com/privatedomain/risk_handler/03101900/?returnurl=${encodeURIComponent(row.productUrl)}`;
  if (context.testDraft.productInfo().productId !== row.productId) throw new Error("Lost product ID after risk redirect");
  await context.testDraft.restoreDraft();
  if (context.state.rows.size !== 1 || context.state.rows.get(row.key)?.content !== row.content) throw new Error("Draft did not restore");
  console.log("draft recovery test passed");
})().catch((error) => { console.error(error); process.exitCode = 1; });
