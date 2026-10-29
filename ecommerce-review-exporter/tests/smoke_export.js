const fs = require("fs");
const path = require("path");
const vm = require("vm");

const contentPath = path.join(__dirname, "..", "content.js");
const source = fs.readFileSync(contentPath, "utf8");
const start = source.indexOf("  function xmlEscape");
const end = source.indexOf("  function exportExcel");

if (start < 0 || end < 0 || end <= start) throw new Error("Could not locate XLSX generator in content.js");

const context = {
  Blob,
  TextEncoder,
  platform: { id: "taobao", name: "淘宝" },
};
vm.createContext(context);
vm.runInContext(`
  const normalizeText = (value) => String(value || "").replace(/\\s+/g, " ").trim();
  const clip = (value, limit = 32000) => normalizeText(value).slice(0, limit);
  ${source.slice(start, end)}
  globalThis.generated = createXlsx([
    { platform: "淘宝", content: "中文评论：很好用 & <满意>", images: "https://example.com/a.jpg" },
    { platform: "京东", content: "第二条评论", images: "" }
  ], [["平台", "platform"], ["评论内容", "content"], ["图片", "images"]], [70, 420, 300]);
`, context);

(async () => {
  const bytes = Buffer.from(await context.generated.arrayBuffer());
  fs.writeFileSync(path.join(__dirname, "smoke.xlsx"), bytes);
  console.log(`generated ${bytes.length} bytes`);
})();
