import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

if (process.platform !== "win32") {
  console.log("prepare-bundle: ignorado (o runtime portátil só é montado no Windows).");
  process.exit(0);
}

const script = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "prepare-windows-bundle.ps1",
);

const result = spawnSync(
  "powershell",
  ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script],
  { stdio: "inherit" },
);

process.exit(result.status ?? 1);
