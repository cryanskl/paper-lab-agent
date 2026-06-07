import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
    // Default `pnpm test` must be deterministic and no-network.
    // Live-source tests live under tests/integration/ and are run by an
    // explicit opt-in script (e.g. pnpm test:integration:arxiv).
    exclude: ["tests/integration/**", "node_modules/**", ".next/**"],
    pool: "forks",
    testTimeout: 10000,
  },
});
