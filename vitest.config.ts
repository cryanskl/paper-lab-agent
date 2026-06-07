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
    // Default tests must be deterministic and no-network.
    // Integration tests (not present in V1) would be a separate suite.
    pool: "forks",
    testTimeout: 10000,
  },
});
