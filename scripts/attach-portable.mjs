import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

if (process.platform !== "win32") {
  console.log("attach-portable: ignorado fora do Windows.");
  process.exit(0);
}

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const python = path.join(
  root,
  "apps",
  "desktop",
  "src-tauri",
  "resources",
  "python",
  "python.exe",
);
const script = path.join(path.dirname(fileURLToPath(import.meta.url)), "attach-portable-payload.py");

const result = spawnSync(python, [script], { stdio: "inherit" });
process.exit(result.status ?? 1);
