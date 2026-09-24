import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

// The source uses WXT's `@/` alias, which normally comes from the generated
// .wxt/tsconfig.json. Vitest doesn't read that, so the alias is restated here.
// Only the pure-logic modules are unit-tested; anything touching the browser
// APIs belongs in an extension integration test, which this is deliberately not.
export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL(".", import.meta.url)),
    },
  },
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
  },
});
