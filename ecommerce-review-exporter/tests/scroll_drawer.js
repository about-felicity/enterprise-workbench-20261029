const fs = require("fs");
const path = require("path");
const vm = require("vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
const start = source.indexOf("  function reviewScrollContainer");
const end = source.indexOf("  async function scrape");
if (start < 0 || end < 0) throw new Error("Cannot locate scroll functions");

const drawer = {
  parentElement: null,
  clientHeight: 800,
  scrollHeight: 8000,
  scrollTop: 0,
};
const card = { parentElement: drawer };
const context = {
  document: { body: {}, documentElement: {} },
  getComputedStyle: () => ({ overflowY: "auto" }),
  findNextOrMoreButton: () => null,
  sleep: async () => {},
  window: { scrollY: 0 },
  innerHeight: 800,
};
vm.createContext(context);
vm.runInContext(`${source.slice(start, end)} globalThis.testScroll = requestMore;`, context);

(async () => {
  const first = await context.testScroll([card]);
  if (!first.moved || drawer.scrollTop !== 560) throw new Error("Drawer did not advance one screen");
  let count = 1;
  while (drawer.scrollTop < 7200 && count < 20) {
    await context.testScroll([card]);
    count += 1;
  }
  if (drawer.scrollTop !== 7200 || count < 10) throw new Error("Drawer skipped intermediate screens");
  const last = await context.testScroll([card]);
  if (last.moved) throw new Error("Drawer incorrectly reported movement at the bottom");
  console.log("drawer scroll test passed");
})();
