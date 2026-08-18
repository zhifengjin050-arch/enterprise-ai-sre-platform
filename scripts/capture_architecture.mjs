import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const frontend = path.join(root, "frontend");
const require = createRequire(path.join(frontend, "package.json"));
const { chromium } = require("playwright");

const out = path.join(root, "screenshots", "07-architecture.png");
const html = path.join(root, "scripts", "architecture.html");

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1600, height: 1400 },
  deviceScaleFactor: 2,
});
await page.goto(pathToFileURL(html).href, { waitUntil: "networkidle" });
await page.locator("#capture").waitFor({ timeout: 10000 });
await page.waitForTimeout(400);
await page.locator("#capture").screenshot({ path: out, type: "png" });
await browser.close();
console.log("wrote", out);
