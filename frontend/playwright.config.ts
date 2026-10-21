import { defineConfig } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(frontendRoot, "..");
const databaseFile = path.join(repoRoot, "backend", "data", "e2e.db");

export default defineConfig({
  testDir: "./e2e",
  testIgnore: ["**/screenshots.spec.ts"],
  timeout: 120_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5105",
    viewport: { width: 1440, height: 900 },
  },
  webServer: [
    {
      command: "uv run python -m app",
      cwd: path.join(repoRoot, "backend"),
      url: "http://127.0.0.1:8105/ready",
      timeout: 180_000,
      reuseExistingServer: false,
      env: {
        ...process.env,
        APP_ENV: "demo",
        HOST: "127.0.0.1",
        PORT: "8105",
        ALLOW_NETWORK_BIND: "false",
        DATABASE_URL: `sqlite:///${databaseFile.replaceAll("\\", "/")}`,
        AUTO_SEED: "true",
        RUN_MIGRATIONS: "true",
        EMBEDDINGS_ENABLED: "false",
        CORS_ORIGINS: "http://127.0.0.1:5105,http://localhost:5105",
      },
    },
    {
      command: "pnpm dev",
      cwd: frontendRoot,
      url: "http://127.0.0.1:5105",
      timeout: 120_000,
      reuseExistingServer: false,
    },
  ],
});
