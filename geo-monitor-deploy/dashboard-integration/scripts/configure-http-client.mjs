import fs from "node:fs";

const file = "package.json";
const config = JSON.parse(fs.readFileSync(file, "utf8"));
config.dependencies.undici = "8.12.4";
config.engines.node = ">=22.19.0";
config.scripts.start = "node scripts/patch-vinext-windows.mjs && node --import ./scripts/http-client.mjs ./node_modules/vinext/dist/cli.js start";
fs.writeFileSync(file, JSON.stringify(config, null, 2) + "\n");
